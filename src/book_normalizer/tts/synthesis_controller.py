"""V2-only synthesis orchestration services."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from book_normalizer.chunking.manifest_v2 import flatten_manifest, load_manifest
from book_normalizer.comfyui.client import ComfyUIClient
from book_normalizer.comfyui.synthesis import count_done_chunks, synthesize_manifest
from book_normalizer.comfyui.workflow_builder import WorkflowBuilder

ProgressCallback = Callable[[int, int, str, int, int, float, int, int, int], None]
StatusCallback = Callable[[str], None]
LogCallback = Callable[[str], None]


@dataclass(frozen=True)
class SynthesisRequest:
    """Configuration for one v2 synthesis run."""

    manifest_path: Path
    output_dir: Path
    workflow_path: Path
    comfyui_url: str = "http://localhost:8188"
    chapter: int | None = None
    chunk_timeout: float = 300.0
    failed_only: bool = False
    merge_chapters: bool = True


@dataclass(frozen=True)
class SynthesisRunResult:
    """Counters and paths from one synthesis run."""

    audio_dir: Path
    synthesized: int
    skipped: int


class SynthesisController:
    """Run v2 manifest synthesis without depending on Qt."""

    def __init__(
        self,
        request: SynthesisRequest,
        *,
        progress: ProgressCallback | None = None,
        status: StatusCallback | None = None,
        log: LogCallback | None = None,
    ) -> None:
        self._request = request
        self._progress = progress
        self._status = status
        self._log = log

    def run(self) -> SynthesisRunResult:
        """Run ComfyUI synthesis for the request."""
        request = self._request
        manifest_model = load_manifest(request.manifest_path)
        manifest = manifest_model.to_record()
        total = len(flatten_manifest(manifest_model, request.chapter))
        if total == 0:
            raise ValueError("No chunks found in chunks_manifest_v2.json.")

        audio_dir = request.output_dir / "audio_chunks"
        workflow_path = request.workflow_path
        if not workflow_path.exists():
            raise FileNotFoundError(f"ComfyUI workflow not found: {workflow_path}")

        self._emit_status("__loading__")
        client = ComfyUIClient(request.comfyui_url)
        if not client.is_reachable():
            raise ConnectionError(f"ComfyUI server not reachable at {request.comfyui_url}")
        self._emit_log(f"ComfyUI: connected to {request.comfyui_url}")

        builder = WorkflowBuilder(workflow_path)
        self._emit_log(f"Workflow template: {workflow_path}")
        self._emit_status("__model_ready__")

        done_start = count_done_chunks(manifest, request.chapter)
        current_done = done_start

        def on_line(line: str) -> None:
            nonlocal current_done
            self._emit_log(line)
            if not line.startswith("PROGRESS "):
                return
            parts = line.split()
            if len(parts) < 2 or "/" not in parts[1]:
                return
            left, right = parts[1].split("/", 1)
            try:
                current_done = int(left)
                total_val = int(right)
            except ValueError:
                return
            self._emit_progress(
                current_done,
                total_val,
                "",
                0,
                0,
                0.0,
                max(0, total_val - current_done),
                0,
                0,
            )

        summary = synthesize_manifest(
            manifest=manifest,
            manifest_path=request.manifest_path,
            client=client,
            builder=builder,
            out_dir=audio_dir,
            chapter_filter=request.chapter,
            chunk_timeout=request.chunk_timeout,
            failed_only=request.failed_only,
            progress=on_line,
        )
        self._emit_progress(total, total, "0s", 0, 0, 0.0, 0, 0, 0)
        return SynthesisRunResult(
            audio_dir=audio_dir,
            synthesized=summary.synthesized,
            skipped=summary.skipped,
        )

    def _emit_progress(
        self,
        done: int,
        total: int,
        eta: str,
        chapter: int,
        chunk_chars: int,
        chunk_sec: float,
        remaining: int,
        remaining_chars: int,
        total_chars: int,
    ) -> None:
        if self._progress:
            self._progress(
                done,
                total,
                eta,
                chapter,
                chunk_chars,
                chunk_sec,
                remaining,
                remaining_chars,
                total_chars,
            )

    def _emit_status(self, message: str) -> None:
        if self._status:
            self._status(message)

    def _emit_log(self, line: str) -> None:
        if self._log:
            self._log(line)

