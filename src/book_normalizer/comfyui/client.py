"""ComfyUI HTTP API client for audio synthesis.

Wraps the standard ComfyUI REST API:
  POST  /prompt          — queue a workflow execution
  GET   /history/{id}   — poll execution status
  GET   /view            — download output file

Usage example::

    client = ComfyUIClient("http://localhost:8188")
    from book_normalizer.comfyui.workflow_builder import WorkflowBuilder
    builder = WorkflowBuilder("comfyui_workflows/qwen3_tts_template.json")
    workflow = builder.build(text="Привет мир.", voice_id="narrator_calm",
                             mood="neutral", output_filename="chunk_001.wav")
    prompt_id = client.queue_prompt(workflow)
    output_info = client.wait_for_completion(prompt_id, timeout=300)
    local_path = client.download_audio(
        output_info["filename"],
        output_info["subfolder"],
        dst_path=Path("output/chunk_001.wav"),
    )
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# How often (seconds) to poll /history while waiting for completion.
_POLL_INTERVAL = 2.0


class ComfyUIError(Exception):
    """Raised when a ComfyUI API call returns an unexpected response."""


class ComfyUIClient:
    """Synchronous HTTP client for the ComfyUI server API.

    All network operations use ``httpx`` (already a project dependency).
    """

    def __init__(self, base_url: str = "http://localhost:8188") -> None:
        self._base = base_url.rstrip("/")

    # ── Public API ──────────────────────────────────────────────────────────

    def queue_prompt(self, workflow: dict[str, Any]) -> str:
        """Submit a workflow for execution and return the prompt_id.

        Args:
            workflow: ComfyUI workflow dict in API format (node_id → node).

        Returns:
            Opaque ``prompt_id`` string used to poll status.

        Raises:
            ComfyUIError: If the server rejects the workflow.
        """
        import httpx

        payload = {"prompt": workflow}
        try:
            resp = httpx.post(f"{self._base}/prompt", json=payload, timeout=30.0)
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ComfyUIError(f"ComfyUI /prompt returned {exc.response.status_code}: {exc.response.text}") from exc
        except Exception as exc:
            raise ComfyUIError(f"ComfyUI /prompt request failed: {exc}") from exc

        data = resp.json()
        prompt_id: str = data.get("prompt_id", "")
        if not prompt_id:
            raise ComfyUIError(f"ComfyUI /prompt did not return a prompt_id: {data}")

        logger.debug("Queued prompt: %s", prompt_id)
        return prompt_id

    def get_history(self, prompt_id: str) -> dict[str, Any]:
        """Return the history entry for the given prompt_id.

        Returns an empty dict if the execution has not finished yet.
        """
        import httpx

        try:
            resp = httpx.get(
                f"{self._base}/history/{prompt_id}",
                timeout=15.0,
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            return data.get(prompt_id, {})
        except Exception as exc:
            logger.warning("ComfyUI /history poll failed: %s", exc)
            return {}

    def wait_for_completion(
        self,
        prompt_id: str,
        timeout: float = 300.0,
    ) -> dict[str, Any]:
        """Block until the prompt finishes and return the first output audio info.

        The returned dict has keys: ``filename``, ``subfolder``, ``type``.

        Args:
            prompt_id: ID returned by :meth:`queue_prompt`.
            timeout: Maximum seconds to wait before raising ``ComfyUIError``.

        Raises:
            ComfyUIError: On timeout or if ComfyUI reports an execution error.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            history = self.get_history(prompt_id)
            if not history:
                time.sleep(_POLL_INTERVAL)
                continue

            # Check for execution errors.
            status: dict[str, Any] = history.get("status", {})
            if status.get("status_str") == "error":
                messages = status.get("messages", [])
                raise ComfyUIError(f"ComfyUI execution error for {prompt_id}: {messages}")

            # Scan all node outputs for audio files.
            outputs: dict[str, Any] = history.get("outputs", {})
            for _node_id, node_out in outputs.items():
                audio_list = node_out.get("audio") or node_out.get("audios") or []
                if audio_list:
                    info = audio_list[0]
                    logger.debug(
                        "Prompt %s done: %s/%s",
                        prompt_id, info.get("subfolder", ""), info.get("filename", ""),
                    )
                    return {
                        "filename": info.get("filename", ""),
                        "subfolder": info.get("subfolder", ""),
                        "type": info.get("type", "output"),
                    }

            time.sleep(_POLL_INTERVAL)

        raise ComfyUIError(
            f"Timeout ({timeout}s) waiting for ComfyUI prompt {prompt_id}"
        )

    def wait_for_execution(
        self,
        prompt_id: str,
        timeout: float = 300.0,
    ) -> dict[str, Any]:
        """Block until a prompt finishes, even when it has no audio output.

        Voice-save workflows often end in a side-effect node such as
        ``FB_Qwen3TTSSaveVoice`` and therefore do not return downloadable
        audio. This method waits for the history entry to finish successfully
        and returns the full history payload.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            history = self.get_history(prompt_id)
            if not history:
                time.sleep(_POLL_INTERVAL)
                continue

            status: dict[str, Any] = history.get("status", {})
            if status.get("status_str") == "error":
                messages = status.get("messages", [])
                raise ComfyUIError(f"ComfyUI execution error for {prompt_id}: {messages}")

            if "outputs" in history:
                return history

            time.sleep(_POLL_INTERVAL)

        raise ComfyUIError(
            f"Timeout ({timeout}s) waiting for ComfyUI prompt {prompt_id}"
        )

    def download_audio(
        self,
        filename: str,
        subfolder: str,
        dst_path: Path,
        file_type: str = "output",
    ) -> Path:
        """Download a generated audio file from the ComfyUI output directory.

        Args:
            filename: Filename as returned by :meth:`wait_for_completion`.
            subfolder: Subfolder within the ComfyUI output directory.
            dst_path: Local path to save the file.
            file_type: ComfyUI file type (default: ``"output"``).

        Returns:
            The resolved ``dst_path`` after writing.
        """
        import httpx

        params: dict[str, str] = {
            "filename": filename,
            "type": file_type,
        }
        if subfolder:
            params["subfolder"] = subfolder

        try:
            with httpx.stream(
                "GET",
                f"{self._base}/view",
                params=params,
                timeout=120.0,
            ) as resp:
                resp.raise_for_status()
                dst_path = Path(dst_path)
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                with dst_path.open("wb") as fh:
                    for chunk in resp.iter_bytes(chunk_size=65536):
                        fh.write(chunk)
        except Exception as exc:
            raise ComfyUIError(f"Failed to download {filename}: {exc}") from exc

        logger.debug("Downloaded audio → %s (%d bytes)", dst_path, dst_path.stat().st_size)
        return dst_path

    def synthesize_chunk(
        self,
        workflow: dict[str, Any],
        output_path: Path,
        timeout: float = 300.0,
    ) -> Path:
        """Queue a workflow, wait for it, and download the resulting audio.

        This is a convenience wrapper around :meth:`queue_prompt`,
        :meth:`wait_for_completion`, and :meth:`download_audio`.

        Args:
            workflow: Pre-built ComfyUI workflow dict (use WorkflowBuilder).
            output_path: Where to save the downloaded WAV file.
            timeout: Max seconds to wait for synthesis.

        Returns:
            Path to the downloaded audio file.
        """
        prompt_id = self.queue_prompt(workflow)
        audio_info = self.wait_for_completion(prompt_id, timeout=timeout)
        return self.download_audio(
            audio_info["filename"],
            audio_info["subfolder"],
            dst_path=output_path,
            file_type=audio_info.get("type", "output"),
        )

    def upload_audio(self, audio_path: Path) -> str:
        """Upload a local audio file to the ComfyUI input directory.

        Uses the same ``/upload/image`` endpoint that the UI uses for audio
        uploads (``audio_upload: true`` fields).  The uploaded file becomes
        available as an option in ``LoadAudio`` dropdowns.

        Args:
            audio_path: Path to a local WAV / FLAC / OGG audio file.

        Returns:
            The filename (basename) as stored on the ComfyUI server — pass
            this value to :meth:`WorkflowBuilder.build_voice_setup` as
            ``audio_filename``.

        Raises:
            ComfyUIError: If the upload fails.
        """
        import httpx

        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise ComfyUIError(f"Audio file not found: {audio_path}")

        try:
            with audio_path.open("rb") as fh:
                files = {"image": (audio_path.name, fh, "audio/wav")}
                resp = httpx.post(
                    f"{self._base}/upload/image",
                    files=files,
                    data={"type": "input", "overwrite": "true"},
                    timeout=120.0,
                )
                resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ComfyUIError(
                f"ComfyUI audio upload returned {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except Exception as exc:
            raise ComfyUIError(f"ComfyUI audio upload failed: {exc}") from exc

        data = resp.json()
        uploaded_name: str = data.get("name", audio_path.name)
        logger.debug("Uploaded audio %s → %s", audio_path.name, uploaded_name)
        return uploaded_name

    def list_saved_speakers(self) -> list[str]:
        """Return names of voices saved via FB_Qwen3TTSSaveVoice.

        Fetches the ``/object_info`` endpoint and reads the filename options
        from the ``FB_Qwen3TTSLoadSpeaker`` node.  Returns an empty list
        when no speakers have been saved or when the node is not installed.
        """
        import httpx

        try:
            resp = httpx.get(f"{self._base}/object_info", timeout=15.0)
            resp.raise_for_status()
            data: dict = resp.json()
        except Exception as exc:
            logger.warning("Could not fetch /object_info: %s", exc)
            return []

        node = data.get("FB_Qwen3TTSLoadSpeaker", {})
        options: list = (
            node.get("input", {})
            .get("required", {})
            .get("filename", [[]])[0]
        )
        return [o for o in options if o and o != "None"]

    def is_reachable(self) -> bool:
        """Return True if the ComfyUI server responds to a health check."""
        import httpx

        try:
            resp = httpx.get(f"{self._base}/system_stats", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False
