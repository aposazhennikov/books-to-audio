"""V2-only synthesis orchestration services."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from book_normalizer.chunking.manifest_v2 import flatten_manifest, load_manifest
from book_normalizer.comfyui.client import ComfyUIClient
from book_normalizer.comfyui.generation_options import GenerationOptions
from book_normalizer.comfyui.server import ComfyUIStartError, ensure_local_comfyui
from book_normalizer.comfyui.synthesis import (
    collect_pending_chunks,
    count_done_chunks,
    load_speaker_overrides,
    save_manifest,
    synthesize_manifest,
)
from book_normalizer.comfyui.workflow_builder import WorkflowBuilder
from book_normalizer.tts.artifact_qa import (
    DEFAULT_ARTIFACT_REPORT_NAME,
    annotate_manifest_with_artifacts,
    run_artifact_qa,
    write_artifact_report,
)
from book_normalizer.tts.asr_qa import (
    DEFAULT_ASR_REPORT_NAME,
    AsrQaConfig,
    FasterWhisperBackend,
    annotate_manifest_with_asr,
    run_asr_qa,
    write_asr_diff,
    write_asr_report,
)
from book_normalizer.tts.quality_gate import split_problem_chunks_for_retry

ProgressCallback = Callable[[int, int, str, int, int, float, int, int, int], None]
StatusCallback = Callable[[str], None]
LogCallback = Callable[[str], None]


def _format_eta(seconds: float) -> str:
    """Format a remaining-time estimate for GUI progress labels."""
    total_seconds = max(0, int(seconds))
    if total_seconds < 60:
        return f"{total_seconds}s"
    minutes, sec = divmod(total_seconds, 60)
    if minutes < 60:
        return f"{minutes}m {sec:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


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
    clone_config_path: Path | None = None
    generation_options: GenerationOptions | dict[str, Any] | None = None
    quality_loop: bool = False
    artifact_qa: bool = False
    asr_qa_after_synthesis: bool = False
    asr_model: str = "small"
    asr_device: str = "auto"
    asr_timeout_seconds: float = 180.0
    max_resynthesis_attempts: int = 2
    auto_start_comfyui: bool = True
    comfyui_start_wait_seconds: float = 300.0


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
            self._try_start_comfyui()
        if not client.is_reachable():
            raise ConnectionError(f"ComfyUI server not reachable at {request.comfyui_url}")
        self._emit_log(f"ComfyUI: connected to {request.comfyui_url}")

        builder = WorkflowBuilder(workflow_path)
        self._emit_log(f"Workflow template: {workflow_path}")
        speaker_overrides = load_speaker_overrides(request.clone_config_path)
        if speaker_overrides:
            self._emit_log(f"CustomVoice overrides: {len(speaker_overrides)} role mapping(s)")
        self._emit_status("__model_ready__")

        done_start = count_done_chunks(manifest, request.chapter)
        current_done = done_start
        progress_started_at = time.monotonic()

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
            remaining = max(0, total_val - current_done)
            synthesized_this_run = max(0, current_done - done_start)
            eta = ""
            if remaining == 0:
                eta = "0s"
            elif synthesized_this_run > 0:
                elapsed = max(0.0, time.monotonic() - progress_started_at)
                eta = _format_eta((elapsed / synthesized_this_run) * remaining)
            self._emit_progress(
                current_done,
                total_val,
                eta,
                0,
                0,
                0.0,
                remaining,
                0,
                0,
            )

        synthesized_total = 0
        skipped = done_start
        max_passes = max(1, int(request.max_resynthesis_attempts) + 1)
        for pass_index in range(max_passes):
            retry_pass = pass_index > 0
            if retry_pass:
                self._emit_log(f"Quality retry pass {pass_index}/{max_passes - 1}")
            summary = synthesize_manifest(
                manifest=manifest,
                manifest_path=request.manifest_path,
                client=client,
                builder=builder,
                out_dir=audio_dir,
                chapter_filter=request.chapter,
                chunk_timeout=request.chunk_timeout,
                failed_only=request.failed_only or retry_pass,
                speaker_overrides=speaker_overrides,
                generation_options=request.generation_options,
                progress=on_line,
            )
            synthesized_total += summary.synthesized
            skipped = summary.skipped

            if not (request.quality_loop or request.artifact_qa or request.asr_qa_after_synthesis):
                break

            self._run_quality_gates(manifest, request)
            if not request.quality_loop:
                break

            splits = split_problem_chunks_for_retry(manifest)
            if splits:
                save_manifest(request.manifest_path, manifest)
                self._emit_log(f"Quality loop split {splits} repeated/overlong chunk(s) for retry.")

            retry_pending = collect_pending_chunks(
                manifest,
                request.chapter,
                failed_only=True,
            )
            if not retry_pending:
                break
            if pass_index == max_passes - 1:
                self._emit_log(
                    f"Quality loop stopped: {len(retry_pending)} chunk(s) still need attention."
                )
                break
            self._emit_log(
                f"Quality loop reset {len(retry_pending)} bad chunk(s) for resynthesis."
            )

        self._emit_progress(total, total, "0s", 0, 0, 0.0, 0, 0, 0)
        return SynthesisRunResult(
            audio_dir=audio_dir,
            synthesized=synthesized_total,
            skipped=skipped,
        )

    def _try_start_comfyui(self) -> None:
        """Start local ComfyUI when the request allows it and the API is down."""
        request = self._request
        if not request.auto_start_comfyui:
            return

        self._emit_log(f"ComfyUI: {request.comfyui_url} is not reachable; trying to start local portable server...")
        try:
            result = ensure_local_comfyui(
                request.comfyui_url,
                wait_seconds=request.comfyui_start_wait_seconds,
            )
        except ComfyUIStartError as exc:
            raise ConnectionError(
                f"ComfyUI server not reachable at {request.comfyui_url}; auto-start failed: {exc}"
            ) from exc
        self._emit_log(result.message)

    def _run_quality_gates(self, manifest: dict[str, Any], request: SynthesisRequest) -> None:
        """Run configured post-synthesis QA gates and update the manifest."""
        if request.artifact_qa or request.quality_loop:
            report_path = request.manifest_path.with_name(DEFAULT_ARTIFACT_REPORT_NAME)
            self._emit_log("Artifact QA: checking clipping, silence, dropouts, and repeats...")
            artifact_result = run_artifact_qa(manifest, manifest_path=request.manifest_path)
            write_artifact_report(report_path, artifact_result)
            annotate_manifest_with_artifacts(
                manifest,
                artifact_result,
                report_path=report_path.resolve(),
                reset_bad_chunks=request.quality_loop,
                max_resynthesis_attempts=request.max_resynthesis_attempts,
            )
            summary = artifact_result.summary
            self._emit_log(
                "Artifact QA: "
                f"status={artifact_result.status}, failed={summary['failed']}, "
                f"warnings={summary['warning']}, errors={summary['error']}."
            )
            save_manifest(request.manifest_path, manifest)

        if request.asr_qa_after_synthesis:
            report_path = request.manifest_path.with_name(DEFAULT_ASR_REPORT_NAME)
            self._emit_log(f"ASR QA: backend=faster-whisper model={request.asr_model}")
            asr_result = run_asr_qa(
                manifest,
                config=AsrQaConfig(
                    model=request.asr_model,
                    device=request.asr_device,
                    timeout_seconds=request.asr_timeout_seconds,
                ),
                backend=FasterWhisperBackend(request.asr_model, device=request.asr_device),
                manifest_path=request.manifest_path,
            )
            write_asr_report(report_path, asr_result)
            write_asr_diff(report_path.with_suffix(".diff.txt"), asr_result)
            annotate_manifest_with_asr(
                manifest,
                asr_result,
                report_path=report_path.resolve(),
                reset_bad_chunks=request.quality_loop,
                max_resynthesis_attempts=request.max_resynthesis_attempts,
            )
            summary = asr_result.summary
            self._emit_log(
                "ASR QA: "
                f"status={asr_result.status.value}, failed={summary['failed']}, "
                f"warnings={summary['warning']}, errors={summary['error']}."
            )
            save_manifest(request.manifest_path, manifest)

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
