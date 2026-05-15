"""Background worker for TTS synthesis via WSL subprocess."""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from book_normalizer.gui.i18n import t
from book_normalizer.tts.model_paths import default_comfyui_models_dir
from book_normalizer.tts.wsl_runtime import build_wsl_tts_activation_script


def _flatten_manifest_chunks(data: object) -> list[dict]:
    """Return v1-compatible chunk records from v1 or v2 manifest JSON."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []

    chunks: list[dict] = []
    for chapter in data.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter_index = chapter.get("chapter_index", 0)
        for chunk in chapter.get("chunks", []):
            if isinstance(chunk, dict):
                chunks.append({"chapter_index": chapter_index, **chunk})
    return chunks


class ExportSegmentsWorker(QThread):
    """Export voice-annotated segments (line-level) from a processed book."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(
        self,
        book: object,
        output_dir: Path,
        speaker_mode: str = "heuristic",
        llm_endpoint: str = "",
        llm_model: str = "",
        llm_api_key: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self._book = book
        self._output_dir = output_dir
        self._speaker_mode = speaker_mode
        self._llm_endpoint = llm_endpoint
        self._llm_model = llm_model
        self._llm_api_key = llm_api_key

    def run(self) -> None:
        try:
            from book_normalizer.chunking.voice_splitter import (
                extract_segments_book,
            )
            from book_normalizer.dialogue.attribution import (
                SpeakerMode,
                create_attributor,
            )
            from book_normalizer.dialogue.detector import DialogueDetector

            self.progress.emit(t("voice.detecting_dialogue"))
            detector = DialogueDetector()
            annotated = detector.detect_book(self._book)

            self.progress.emit(
                t("voice.attributing", mode=self._speaker_mode),
            )
            attr_mode = SpeakerMode(self._speaker_mode)
            attributor = create_attributor(
                attr_mode,
                cache_dir=self._output_dir / "speaker_cache",
                llm_endpoint=self._llm_endpoint or "",
                llm_model=self._llm_model or "qwen3:8b",
                llm_api_key=self._llm_api_key or "",
            )
            attributor.attribute(annotated)

            self.progress.emit(t("voice.extracting_segments"))
            segments = extract_segments_book(annotated)

            manifest = []
            for seg in segments:
                manifest.append({
                    "segment_index": seg.segment_index,
                    "chapter_index": seg.chapter_index,
                    "is_dialogue": seg.is_dialogue,
                    "role": seg.role.value,
                    "voice_id": seg.voice_id,
                    "intonation": seg.intonation,
                    "text": seg.text,
                })

            self._output_dir.mkdir(parents=True, exist_ok=True)
            manifest_path = (
                self._output_dir / "segments_manifest.json"
            )
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            self.progress.emit(
                t("voice.exported_segments", n=len(manifest)),
            )
            self.finished.emit(str(manifest_path))

        except Exception as exc:
            self.error.emit(str(exc))


class ExportChunksWorker(QThread):
    """Legacy: export voice-annotated chunks from a processed book."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(
        self,
        book: object,
        output_dir: Path,
        speaker_mode: str = "heuristic",
        max_chunk_chars: int = 600,
        parent=None,
    ):
        super().__init__(parent)
        self._book = book
        self._output_dir = output_dir
        self._speaker_mode = speaker_mode
        self._max_chunk_chars = max_chunk_chars

    def run(self) -> None:
        try:
            from book_normalizer.chunking.voice_splitter import (
                chunk_annotated_book,
            )
            from book_normalizer.dialogue.attribution import (
                SpeakerMode,
                create_attributor,
            )
            from book_normalizer.dialogue.detector import DialogueDetector

            self.progress.emit(t("voice.detecting_dialogue"))
            detector = DialogueDetector()
            annotated = detector.detect_book(self._book)

            self.progress.emit(
                t("voice.attributing", mode=self._speaker_mode),
            )
            attr_mode = SpeakerMode(self._speaker_mode)
            attributor = create_attributor(
                attr_mode,
                cache_dir=self._output_dir / "speaker_cache",
            )
            attributor.attribute(annotated)

            self.progress.emit(t("voice.chunking"))
            chunked = chunk_annotated_book(
                annotated,
                max_chunk_chars=self._max_chunk_chars,
            )

            manifest = []
            for ch_idx in sorted(chunked.keys()):
                for chunk in chunked[ch_idx]:
                    manifest.append({
                        "chapter_index": chunk.chapter_index,
                        "chunk_index": chunk.index,
                        "role": chunk.role.value,
                        "voice_id": chunk.voice_id,
                        "text": chunk.text,
                    })

            self._output_dir.mkdir(parents=True, exist_ok=True)
            manifest_path = self._output_dir / "chunks_manifest.json"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            self.progress.emit(
                t("voice.exported_chunks", n=len(manifest)),
            )
            self.finished.emit(str(manifest_path))

        except Exception as exc:
            self.error.emit(str(exc))


class TTSSynthesisWorker(QThread):
    """Run TTS synthesis via WSL subprocess and monitor progress."""

    progress = pyqtSignal(
        int, int, str, int,
        int, float, int, int, int,
    )
    status = pyqtSignal(str)
    log_line = pyqtSignal(str)
    finished = pyqtSignal(str, int, int)
    error = pyqtSignal(str)

    def __init__(
        self,
        manifest_path: Path,
        output_dir: Path,
        model: str = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        chapter: int | None = None,
        batch_size: int = 1,
        resume: bool = False,
        chunk_timeout: int = 300,
        use_compile: bool = False,
        clone_config: str = "",
        use_sage_attention: bool = False,
        models_dir: str = "",
        comfyui_url: str = "http://localhost:8188",
        workflow_path: str = "",
        failed_only: bool = False,
        temperature: float = 1.0,
        top_p: float = 0.8,
        top_k: int = 20,
        repetition_penalty: float = 1.05,
        max_new_tokens: int = 2048,
        seed: int = -1,
        output_format: str = "flac",
        merge_chapters: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self._manifest_path = manifest_path
        self._output_dir = output_dir
        self._model = model
        self._chapter = chapter
        self._batch_size = batch_size
        self._resume = resume
        self._chunk_timeout = chunk_timeout
        self._use_compile = use_compile
        self._clone_config = clone_config
        self._use_sage_attention = use_sage_attention
        self._models_dir = models_dir
        self._comfyui_url = comfyui_url
        self._workflow_path = workflow_path
        self._failed_only = failed_only
        self._temperature = temperature
        self._top_p = top_p
        self._top_k = top_k
        self._repetition_penalty = repetition_penalty
        self._max_new_tokens = max_new_tokens
        self._seed = seed
        self._output_format = output_format
        self._merge_chapters = merge_chapters
        self._process: subprocess.Popen | None = None
        self._cancelled = False

    def cancel(self) -> None:
        """Request cancellation of synthesis."""
        self._cancelled = True
        if self._process:
            self._process.terminate()

    def run(self) -> None:
        try:
            runner_manifest_path, manifest = self._prepare_runner_manifest()
            total = len(manifest)
            if self._chapter is not None:
                total = sum(
                    1 for c in manifest
                    if c.get("chapter_index") == self._chapter - 1
                )

            if total == 0:
                self.error.emit(t("synth.err_no_chunks"))
                return

            script_path = (
                Path(__file__).resolve().parent.parent.parent.parent.parent
                / "scripts" / "tts_runner.py"
            )

            args = [
                "python", "-u",
                self._wsl_path(script_path),
                "--chunks-json", self._wsl_path(runner_manifest_path),
                "--out", self._wsl_path(self._output_dir),
                "--model", self._model,
                "--batch-size", str(self._batch_size),
                "--log-file", self._wsl_path(self._output_dir / "synthesis_log.txt"),
                "--chunk-timeout", str(self._chunk_timeout),
                "--temperature", str(self._temperature),
                "--top-p", str(self._top_p),
                "--top-k", str(self._top_k),
                "--repetition-penalty", str(self._repetition_penalty),
                "--max-new-tokens", str(self._max_new_tokens),
                "--seed", str(self._seed),
                "--output-format", self._output_format,
            ]
            models_dir = self._models_dir.strip() or str(default_comfyui_models_dir())
            if models_dir:
                args.extend(["--models-dir", self._wsl_path_text(models_dir)])
            if self._chapter is not None:
                args.extend(["--chapter", str(self._chapter)])
            if self._resume:
                args.append("--resume")
            if self._use_compile:
                args.append("--compile")
            clone_config_path = self._prepare_clone_config()
            if clone_config_path:
                args.extend([
                    "--clone-config",
                    self._wsl_path(clone_config_path),
                ])
            if self._use_sage_attention:
                args.append("--sage-attention")
            if self._merge_chapters:
                args.append("--merge-chapters")

            bash_cmd = (
                build_wsl_tts_activation_script()
                + "\nPYTHONUNBUFFERED=1 "
                + " ".join(shlex.quote(arg) for arg in args)
            )
            cmd = [
                "wsl", "-e", "bash", "-c",
                bash_cmd,
            ]

            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            self.status.emit("__loading__")

            synthesized = 0
            skipped = 0
            last_lines: list[str] = []
            for line in iter(self._process.stdout.readline, ""):
                if self._cancelled:
                    break
                line = line.strip()
                if not line:
                    continue

                self.log_line.emit(line)
                last_lines.append(line)
                if len(last_lines) > 50:
                    last_lines.pop(0)

                if "Model loaded" in line:
                    self.status.emit("__model_ready__")

                if line.startswith("VOICE_PROMPT "):
                    try:
                        kv = dict(re.findall(r"(\w+)=([^\s]+)", line))
                        event = kv.get("event", "")
                        done_val = int(kv.get("done", "0"))
                        total_val = int(kv.get("total", "1"))
                        if event == "start":
                            self.status.emit(t("synth.sample_extracting"))
                        elif event == "done":
                            sec = float(kv.get("sec", "0"))
                            self.status.emit(
                                t(
                                    "synth.sample_extracted",
                                    done=done_val,
                                    total=total_val,
                                    sec=sec,
                                ),
                            )
                    except (ValueError, TypeError):
                        pass
                elif line.startswith("PROGRESS "):
                    try:
                        kv = dict(
                            re.findall(r"(\w+)=([\d.]+)", line),
                        )
                        done_val = int(kv.get("done", 0))
                        total_val = int(kv.get("total", total))
                        remaining = int(kv.get("remaining", 0))
                        chunk_chars = int(kv.get("chunk_chars", 0))
                        chunk_sec = float(kv.get("chunk_sec", 0))
                        remaining_chars = int(kv.get("remaining_chars", 0))
                        total_chars = int(kv.get("total_chars", 0))
                        eta_sec = int(kv.get("eta_sec", 0))
                        ch_num = int(kv.get("ch", 0))
                        eta_str = self._format_eta(eta_sec)
                        self.progress.emit(
                            done_val, total_val, eta_str, ch_num,
                            chunk_chars, chunk_sec,
                            remaining, remaining_chars, total_chars,
                        )
                    except (ValueError, KeyError, TypeError):
                        pass
                elif line.startswith("["):
                    try:
                        parts = line.split("]")[0].replace("[", "").strip()
                        current, _tot = parts.split("/")
                        synthesized = int(current)
                        eta_part = ""
                        if "ETA:" in line:
                            eta_part = line.split("ETA:")[1].strip().rstrip(")")
                        ch_match = re.search(r"\bch(\d+)\b", line)
                        chapter = int(ch_match.group(1)) if ch_match else 0
                        self.progress.emit(
                            synthesized, total, eta_part, chapter,
                            0, 0.0, total - synthesized, 0, 0,
                        )
                    except (ValueError, IndexError):
                        pass

                if line.startswith("Done:"):
                    try:
                        parts = line.split(",")
                        for p in parts:
                            p = p.strip()
                            if "synthesized" in p:
                                synthesized = int(p.split()[0].replace("Done:", "").strip())
                            elif "skipped" in p:
                                skipped = int(p.split()[0])
                    except (ValueError, IndexError):
                        pass
                    self.progress.emit(
                        total, total, "0s", 0,
                        0, 0.0, 0, 0, 0,
                    )

            self._process.wait()
            rc = self._process.returncode

            if self._cancelled:
                self.error.emit(t("synth.cancelled"))
            elif rc != 0:
                tail = "\n".join(last_lines[-10:])
                self.error.emit(
                    t("synth.err_exit_code", code=rc) + f"\n{tail}",
                )
            else:
                out_path = str(
                    self._output_dir / "audio_chunks",
                )
                self.finished.emit(out_path, synthesized, skipped)

        except Exception as exc:
            self.error.emit(str(exc))

    def _run_comfyui_v2(self, manifest: dict) -> None:
        """Run the recommended v2 manifest -> ComfyUI synthesis path."""
        total = len(_flatten_manifest_chunks(manifest))
        if self._chapter is not None:
            total = sum(
                1
                for c in _flatten_manifest_chunks(manifest)
                if c.get("chapter_index") == self._chapter - 1
            )

        if total == 0:
            self.error.emit(t("synth.err_no_chunks"))
            return

        done_start = sum(
            1
            for c in _flatten_manifest_chunks(manifest)
            if c.get("synthesized", False)
            and (self._chapter is None or c.get("chapter_index") == self._chapter - 1)
        )

        workflow_path = Path(self._workflow_path) if self._workflow_path else (
            Path(__file__).resolve().parent.parent.parent.parent.parent
            / "comfyui_workflows"
            / "qwen3_tts_template.json"
        )
        if not workflow_path.exists():
            self.error.emit(f"ComfyUI workflow not found: {workflow_path}")
            return

        script_path = (
            Path(__file__).resolve().parent.parent.parent.parent.parent
            / "scripts" / "synthesize_comfyui.py"
        )
        audio_dir = self._output_dir / "audio_chunks"
        args = [
            sys.executable,
            "-u",
            str(script_path),
            "--chunks-json",
            str(self._manifest_path),
            "--out",
            str(audio_dir),
            "--workflow",
            str(workflow_path),
            "--comfyui-url",
            self._comfyui_url or "http://localhost:8188",
            "--chunk-timeout",
            str(self._chunk_timeout),
        ]
        if self._chapter is not None:
            args.extend(["--chapter", str(self._chapter)])
        if self._failed_only:
            args.append("--failed-only")

        self._process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        self.status.emit("__loading__")
        current_done = done_start
        last_lines: list[str] = []
        for line in iter(self._process.stdout.readline, ""):
            if self._cancelled:
                break
            line = line.strip()
            if not line:
                continue
            self.log_line.emit(line)
            last_lines.append(line)
            if len(last_lines) > 50:
                last_lines.pop(0)

            if "ComfyUI: connected" in line or "Workflow template:" in line:
                self.status.emit("__model_ready__")

            progress_match = re.match(r"PROGRESS\s+(\d+)/(\d+)", line)
            if progress_match:
                current_done = int(progress_match.group(1))
                total_val = int(progress_match.group(2))
                self.progress.emit(
                    current_done, total_val, "", 0,
                    0, 0.0, max(0, total_val - current_done), 0, 0,
                )

        self._process.wait()
        rc = self._process.returncode
        if self._cancelled:
            self.error.emit(t("synth.cancelled"))
        elif rc != 0:
            tail = "\n".join(last_lines[-10:])
            self.error.emit(t("synth.err_exit_code", code=rc) + f"\n{tail}")
        else:
            self.progress.emit(total, total, "0s", 0, 0, 0.0, 0, 0, 0)
            self.finished.emit(
                str(audio_dir),
                max(0, current_done - done_start),
                done_start,
            )

    def _prepare_runner_manifest(self) -> tuple[Path, list[dict]]:
        """Load v1/v2 manifest and return a v1-compatible runner path."""
        data = json.loads(self._manifest_path.read_text(encoding="utf-8"))
        chunks = _flatten_manifest_chunks(data)
        if isinstance(data, list):
            return self._manifest_path, chunks

        self._output_dir.mkdir(parents=True, exist_ok=True)
        runner_manifest_path = self._output_dir / ".tts_runner_manifest.v1.json"
        runner_manifest_path.write_text(
            json.dumps(chunks, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return runner_manifest_path, chunks

    def _prepare_clone_config(self) -> Path | None:
        """Write a WSL-readable clone config with converted audio paths."""
        if not self._clone_config:
            return None

        src = Path(self._clone_config)
        data = json.loads(src.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return src

        for cfg in data.values():
            if isinstance(cfg, dict) and cfg.get("ref_audio"):
                cfg["ref_audio"] = self._wsl_path_text(str(cfg["ref_audio"]))

        self._output_dir.mkdir(parents=True, exist_ok=True)
        out_path = self._output_dir / ".tts_clone_config.wsl.json"
        out_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return out_path

    @staticmethod
    def _format_eta(seconds: int) -> str:
        """Format seconds to HH:MM:SS or MmSs."""
        if seconds <= 0:
            return "0s"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            return f"{h}h{m:02d}m{s:02d}s"
        if m > 0:
            return f"{m}m{s:02d}s"
        return f"{s}s"

    @staticmethod
    def _wsl_path(path: Path) -> str:
        """Convert Windows path to WSL path."""
        p = str(path.resolve()).replace("\\", "/")
        if len(p) >= 2 and p[1] == ":":
            drive = p[0].lower()
            p = f"/mnt/{drive}{p[2:]}"
        return p

    @staticmethod
    def _wsl_path_text(path_text: str) -> str:
        """Convert a user-entered Windows path string to a WSL path."""
        p = path_text.strip().replace("\\", "/")
        if len(p) >= 2 and p[1] == ":":
            drive = p[0].lower()
            p = f"/mnt/{drive}{p[2:]}"
        return p


class ComfyVoiceSaveWorker(QThread):
    """Save a reusable custom voice through the ComfyUI voice setup workflow."""

    status = pyqtSignal(str)
    finished = pyqtSignal(str, list)
    error = pyqtSignal(str)

    def __init__(
        self,
        audio_path: Path,
        voice_name: str,
        ref_text: str,
        comfyui_url: str = "http://localhost:8188",
        workflow_path: Path | None = None,
        timeout: float = 300.0,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._audio_path = audio_path
        self._voice_name = voice_name
        self._ref_text = ref_text
        self._comfyui_url = comfyui_url
        self._workflow_path = workflow_path or (
            Path(__file__).resolve().parent.parent.parent.parent.parent
            / "comfyui_workflows"
            / "voice_setup_template.json"
        )
        self._timeout = timeout

    def run(self) -> None:
        try:
            from book_normalizer.comfyui.client import ComfyUIClient
            from book_normalizer.comfyui.workflow_builder import WorkflowBuilder

            if not self._audio_path.exists():
                self.error.emit(f"Audio file not found: {self._audio_path}")
                return
            if not self._voice_name.strip():
                self.error.emit("Voice name is required.")
                return

            self.status.emit(t("synth.train_connecting"))
            client = ComfyUIClient(self._comfyui_url)
            if not client.is_reachable():
                self.error.emit(t("synth.train_err_comfyui", url=self._comfyui_url))
                return

            self.status.emit(t("synth.train_uploading", file=self._audio_path.name))
            uploaded_name = client.upload_audio(self._audio_path)

            self.status.emit(t("synth.train_extracting", name=self._voice_name))
            builder = WorkflowBuilder(self._workflow_path)
            workflow = builder.build_voice_setup(
                audio_filename=uploaded_name,
                voice_name=self._voice_name.strip(),
                ref_text=self._ref_text.strip(),
            )
            prompt_id = client.queue_prompt(workflow)
            client.wait_for_execution(prompt_id, timeout=self._timeout)

            speakers = client.list_saved_speakers()
            self.finished.emit(self._voice_name.strip(), speakers)
        except Exception as exc:
            self.error.emit(str(exc))
