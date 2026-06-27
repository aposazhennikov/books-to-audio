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
from book_normalizer.observability import StageObserver
from book_normalizer.production.run_contract import build_run_contract, write_run_contract
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
from book_normalizer.tts.engine_synthesis import (
    preflight_engine_command,
    synthesize_engine_manifest,
)
from book_normalizer.tts.engines import get_tts_engine, unsupported_tts_engine_message
from book_normalizer.tts.perceptual_qa import (
    DEFAULT_PERCEPTUAL_BACKENDS,
    DEFAULT_PERCEPTUAL_REPORT_NAME,
    PerceptualQaConfig,
    annotate_manifest_with_perceptual,
    run_perceptual_qa,
    write_perceptual_report,
)
from book_normalizer.tts.quality_gate import split_problem_chunks_for_retry

ProgressCallback = Callable[[int, int, str, int, int, float, int, int, int], None]
StatusCallback = Callable[[str], None]
LogCallback = Callable[[str], None]

_LOG_LANGS = {"en", "ru", "zh", "kk", "uz"}
_LOG_MESSAGES: dict[str, dict[str, str]] = {
    "connected": {
        "en": "ComfyUI: connected to {url}",
        "ru": "ComfyUI: подключено к {url}",
        "zh": "ComfyUI：已连接到 {url}",
        "kk": "ComfyUI: {url} мекенжайына қосылды",
        "uz": "ComfyUI: {url} ga ulandi",
    },
    "workflow": {
        "en": "Workflow template: {path}",
        "ru": "Шаблон workflow: {path}",
        "zh": "工作流模板：{path}",
        "kk": "Workflow үлгісі: {path}",
        "uz": "Workflow shabloni: {path}",
    },
    "custom_voice": {
        "en": "CustomVoice overrides: {count} role mapping(s)",
        "ru": "CustomVoice: переопределений ролей {count}",
        "zh": "CustomVoice 覆盖：{count} 个角色映射",
        "kk": "CustomVoice: {count} рөл сәйкестігі",
        "uz": "CustomVoice: {count} rol moslamasi",
    },
    "recovery_check": {
        "en": "ComfyUI recovery attempt {attempt}: checking local server...",
        "ru": "Восстановление ComfyUI, попытка {attempt}: проверяем локальный сервер...",
        "zh": "ComfyUI 恢复尝试 {attempt}：检查本地服务器...",
        "kk": "ComfyUI қалпына келтіру, {attempt}-әрекет: жергілікті сервер тексерілуде...",
        "uz": "ComfyUI tiklash urinishi {attempt}: lokal server tekshirilmoqda...",
    },
    "recovery_ready": {
        "en": "ComfyUI recovery: server is reachable; retrying current chunk.",
        "ru": "Восстановление ComfyUI: сервер доступен, повторяем текущий чанк.",
        "zh": "ComfyUI 恢复：服务器可用，重试当前分块。",
        "kk": "ComfyUI қалпына келді: сервер қолжетімді, ағымдағы чанк қайталанады.",
        "uz": "ComfyUI tiklandi: server mavjud, joriy bo'lak qayta uriniladi.",
    },
    "start_server": {
        "en": "ComfyUI: {url} is not reachable; {action} local portable server...",
        "ru": "ComfyUI: {url} недоступен; {action} локальный portable-сервер...",
        "zh": "ComfyUI：{url} 不可访问；{action} 本地 portable 服务器...",
        "kk": "ComfyUI: {url} қолжетімсіз; жергілікті portable сервер {action}...",
        "uz": "ComfyUI: {url} mavjud emas; lokal portable server {action}...",
    },
    "start_action_start": {
        "en": "trying to start",
        "ru": "запускаем",
        "zh": "正在启动",
        "kk": "іске қосылуда",
        "uz": "ishga tushirilmoqda",
    },
    "start_action_restart": {
        "en": "restarting",
        "ru": "перезапускаем",
        "zh": "正在重启",
        "kk": "қайта іске қосылуда",
        "uz": "qayta ishga tushirilmoqda",
    },
    "quality_retry": {
        "en": "Quality retry pass {index}/{total}",
        "ru": "Повтор качества {index}/{total}",
        "zh": "质量重试轮次 {index}/{total}",
        "kk": "Сапа қайталау кезеңі {index}/{total}",
        "uz": "Sifat qayta urinish bosqichi {index}/{total}",
    },
    "quality_split": {
        "en": "Quality loop split {count} repeated/overlong chunk(s) for retry.",
        "ru": "Цикл качества разделил {count} повторяющихся/слишком длинных чанков для повтора.",
        "zh": "质量循环拆分了 {count} 个重复/过长分块以便重试。",
        "kk": "Сапа циклі қайталау үшін {count} қайталанған/тым ұзын чанк бөлді.",
        "uz": "Sifat sikli qayta urinish uchun {count} takroriy/juda uzun bo'lakni ajratdi.",
    },
    "quality_stopped": {
        "en": "Quality loop stopped: {count} chunk(s) still need attention.",
        "ru": "Цикл качества остановлен: {count} чанков всё ещё требуют внимания.",
        "zh": "质量循环已停止：仍有 {count} 个分块需要处理。",
        "kk": "Сапа циклі тоқтады: {count} чанк әлі назар қажет етеді.",
        "uz": "Sifat sikli to'xtadi: {count} bo'lak hali e'tibor talab qiladi.",
    },
    "quality_reset": {
        "en": "Quality loop reset {count} bad chunk(s) for resynthesis.",
        "ru": "Цикл качества сбросил {count} проблемных чанков на пересинтез.",
        "zh": "质量循环已将 {count} 个问题分块重置为重新合成。",
        "kk": "Сапа циклі {count} нашар чанкты қайта синтезге жіберді.",
        "uz": "Sifat sikli {count} yomon bo'lakni qayta sintezga qaytardi.",
    },
}


def _log_language(language: str) -> str:
    normalized = (language or "").strip().lower()
    return normalized if normalized in _LOG_LANGS else "en"


def _log_text(language: str, key: str, **kwargs: Any) -> str:
    entry = _LOG_MESSAGES[key]
    return entry.get(_log_language(language), entry["en"]).format(**kwargs)


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
    tts_engine: str = "qwen3-customvoice-1.7b"
    models_dir: str = ""
    comfyui_url: str = "http://localhost:8188"
    chapter: int | None = None
    chunk_timeout: float = 300.0
    failed_only: bool = False
    merge_chapters: bool = True
    clone_config_path: Path | None = None
    generation_options: GenerationOptions | dict[str, Any] | None = None
    quality_loop: bool = False
    artifact_qa: bool = False
    perceptual_qa: bool = False
    perceptual_backends: tuple[str, ...] = DEFAULT_PERCEPTUAL_BACKENDS
    perceptual_min_mos: float = 2.70
    perceptual_warn_mos: float = 3.30
    asr_qa_after_synthesis: bool = False
    asr_model: str = "small"
    asr_device: str = "auto"
    asr_timeout_seconds: float = 180.0
    max_resynthesis_attempts: int = 2
    auto_start_comfyui: bool = True
    comfyui_start_wait_seconds: float = 300.0
    comfyui_recovery_retries: int = 2
    log_language: str = "en"


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
        contract = build_run_contract(
            output_dir=request.output_dir,
            stage="tts_synthesis",
            manifest_path=request.manifest_path,
            workflow_path=request.workflow_path,
            voice_preset_paths=[request.clone_config_path] if request.clone_config_path else [],
            model_versions={"tts_engine": request.tts_engine, "asr_model": request.asr_model},
            resume_from="failed_only" if request.failed_only else "manifest_state",
            parameters={
                "chapter": request.chapter,
                "chunk_timeout": request.chunk_timeout,
                "failed_only": request.failed_only,
                "resume_mode": "failed_only" if request.failed_only else "manifest_state",
                "merge_chapters": request.merge_chapters,
                "models_dir": request.models_dir,
                "quality_loop": request.quality_loop,
                "artifact_qa": request.artifact_qa,
                "perceptual_qa": request.perceptual_qa,
                "perceptual_backends": list(request.perceptual_backends),
                "asr_qa_after_synthesis": request.asr_qa_after_synthesis,
                "max_resynthesis_attempts": request.max_resynthesis_attempts,
                "comfyui_url": request.comfyui_url,
            },
        )
        contract_path = write_run_contract(request.output_dir, contract)
        observer = StageObserver(request.output_dir, str(contract["run_id"]), "tts_synthesis")
        observer.log("started", contract_path=str(contract_path))
        unsupported = unsupported_tts_engine_message(request.tts_engine)
        if unsupported:
            observer.log("unsupported_engine", engine=request.tts_engine, message=unsupported)
            observer.finish("failed", error=unsupported)
            raise NotImplementedError(unsupported)

        manifest_model = load_manifest(request.manifest_path)
        manifest = manifest_model.to_record()
        total = len(flatten_manifest(manifest_model, request.chapter))
        if total == 0:
            observer.log("empty_manifest", manifest_path=str(request.manifest_path))
            observer.finish("failed", error="No chunks found")
            raise ValueError("No chunks found in chunks_manifest_v2.json.")

        audio_dir = request.output_dir / "audio_chunks"
        engine = get_tts_engine(request.tts_engine)
        if engine is not None and engine.backend != "comfyui":
            preflight = preflight_engine_command(engine.engine_id, request.models_dir or None)
            self._emit_log(f"TTS engine: {preflight.display_name} ({preflight.engine_id})")
            self._emit_log(f"Command template: {preflight.command_template}")
            self._emit_log(f"Command preview: {preflight.preview_command}")
            if not preflight.ok:
                message = (
                    f"{preflight.display_name} CLI is not available: "
                    f"`{preflight.executable}` was not found on PATH.\n"
                    f"What to install: {preflight.install_hint}\n"
                    f"Command that would be invoked: {preflight.preview_command}"
                )
                observer.log(
                    "local_command_preflight_failed",
                    engine=preflight.engine_id,
                    executable=preflight.executable,
                    env_name=preflight.env_name,
                    command_preview=preflight.preview_command,
                )
                observer.finish("failed", error=message)
                raise FileNotFoundError(message)
            self._emit_log(f"Executable: {preflight.executable_path}")
            self._emit_status("__loading__")
            done_start = count_done_chunks(
                manifest,
                request.chapter,
                manifest_path=request.manifest_path,
            )
            progress_started_at = time.monotonic()

            def on_engine_line(line: str) -> None:
                self._emit_log(line)
                observer.log("log_line", line=line)
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
                eta = "0s" if remaining == 0 else ""
                if remaining and synthesized_this_run > 0:
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
                observer.counters["done_chunks"] = current_done
                observer.counters["remaining_chunks"] = remaining

            summary = synthesize_engine_manifest(
                manifest=manifest,
                manifest_path=request.manifest_path,
                engine_id=engine.engine_id,
                out_dir=audio_dir,
                models_dir=request.models_dir or None,
                chapter_filter=request.chapter,
                failed_only=request.failed_only,
                clone_config_path=request.clone_config_path,
                chunk_timeout=request.chunk_timeout,
                progress=on_engine_line,
            )
            observer.increment("synthesized_chunks", summary.synthesized)
            observer.increment("failed_chunks", summary.failed)
            observer.increment("skipped_chunks", summary.skipped)

            if (
                request.quality_loop
                or request.artifact_qa
                or request.perceptual_qa
                or request.asr_qa_after_synthesis
            ):
                self._run_quality_gates(manifest, request)
                observer.increment("quality_passes", 1)

            self._emit_progress(total, total, "0s", 0, 0, 0.0, 0, 0, 0)
            observer.finish(
                "completed",
                elapsed_seconds=0.0,
                synthesized=summary.synthesized,
                skipped=summary.skipped,
                manifest_path=str(request.manifest_path),
            )
            return SynthesisRunResult(
                audio_dir=audio_dir,
                synthesized=summary.synthesized,
                skipped=summary.skipped,
            )

        workflow_path = request.workflow_path
        if not workflow_path.exists():
            observer.log("missing_workflow", path=str(workflow_path))
            observer.finish("failed", error=f"ComfyUI workflow not found: {workflow_path}")
            raise FileNotFoundError(f"ComfyUI workflow not found: {workflow_path}")

        self._emit_status("__loading__")
        client = ComfyUIClient(request.comfyui_url)
        if not client.is_reachable():
            self._try_start_comfyui()
        if not client.is_reachable():
            observer.log("comfyui_unreachable", url=request.comfyui_url)
            observer.finish("failed", error=f"ComfyUI server not reachable at {request.comfyui_url}")
            raise ConnectionError(f"ComfyUI server not reachable at {request.comfyui_url}")
        self._emit_log(_log_text(request.log_language, "connected", url=request.comfyui_url))

        builder = WorkflowBuilder(workflow_path)
        self._emit_log(_log_text(request.log_language, "workflow", path=workflow_path))
        speaker_overrides = load_speaker_overrides(request.clone_config_path)
        if speaker_overrides:
            self._emit_log(
                _log_text(
                    request.log_language,
                    "custom_voice",
                    count=len(speaker_overrides),
                )
            )
        self._emit_status("__model_ready__")

        done_start = count_done_chunks(manifest, request.chapter)
        current_done = done_start
        progress_started_at = time.monotonic()

        def on_line(line: str) -> None:
            nonlocal current_done
            self._emit_log(line)
            observer.log("log_line", line=line)
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
            observer.counters["done_chunks"] = current_done
            observer.counters["remaining_chunks"] = remaining

        def recover_comfyui(_exc: Exception, attempt: int) -> ComfyUIClient | None:
            self._emit_log(_log_text(request.log_language, "recovery_check", attempt=attempt))
            self._try_start_comfyui(restart=True)
            recovered = ComfyUIClient(request.comfyui_url)
            if not recovered.is_reachable():
                raise ConnectionError(
                    f"ComfyUI server not reachable after recovery attempt {attempt} "
                    f"at {request.comfyui_url}"
                )
            self._emit_log(_log_text(request.log_language, "recovery_ready"))
            return recovered

        synthesized_total = 0
        skipped = done_start
        max_passes = max(1, int(request.max_resynthesis_attempts) + 1)
        for pass_index in range(max_passes):
            retry_pass = pass_index > 0
            if retry_pass:
                self._emit_log(
                    _log_text(
                        request.log_language,
                        "quality_retry",
                        index=pass_index,
                        total=max_passes - 1,
                    )
                )
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
                recovery=recover_comfyui if request.auto_start_comfyui else None,
                max_recovery_retries=request.comfyui_recovery_retries,
                log_language=request.log_language,
            )
            synthesized_total += summary.synthesized
            skipped = summary.skipped
            observer.increment("synthesized_chunks", summary.synthesized)
            observer.increment("failed_chunks", summary.failed)
            observer.increment("skipped_chunks", summary.skipped)

            if not (
                request.quality_loop
                or request.artifact_qa
                or request.perceptual_qa
                or request.asr_qa_after_synthesis
            ):
                break

            self._run_quality_gates(manifest, request)
            observer.increment("quality_passes", 1)
            if not request.quality_loop:
                break

            splits = split_problem_chunks_for_retry(manifest)
            if splits:
                save_manifest(request.manifest_path, manifest)
                self._emit_log(
                    _log_text(request.log_language, "quality_split", count=splits)
                )

            retry_pending = collect_pending_chunks(
                manifest,
                request.chapter,
                failed_only=True,
            )
            if not retry_pending:
                break
            if pass_index == max_passes - 1:
                self._emit_log(
                    _log_text(
                        request.log_language,
                        "quality_stopped",
                        count=len(retry_pending),
                    )
                )
                break
            self._emit_log(
                _log_text(
                    request.log_language,
                    "quality_reset",
                    count=len(retry_pending),
                )
            )

        self._emit_progress(total, total, "0s", 0, 0, 0.0, 0, 0, 0)
        observer.finish(
            "completed",
            elapsed_seconds=0.0,
            synthesized=synthesized_total,
            skipped=skipped,
            manifest_path=str(request.manifest_path),
        )
        return SynthesisRunResult(
            audio_dir=audio_dir,
            synthesized=synthesized_total,
            skipped=skipped,
        )

    def _try_start_comfyui(self, *, restart: bool = False) -> None:
        """Start local ComfyUI when the request allows it and the API is down."""
        request = self._request
        if not request.auto_start_comfyui:
            return

        action_key = "start_action_restart" if restart else "start_action_start"
        self._emit_log(
            _log_text(
                request.log_language,
                "start_server",
                url=request.comfyui_url,
                action=_log_text(request.log_language, action_key),
            )
        )
        try:
            result = ensure_local_comfyui(
                request.comfyui_url,
                wait_seconds=request.comfyui_start_wait_seconds,
                restart=restart,
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

        if request.perceptual_qa or request.quality_loop:
            report_path = request.manifest_path.with_name(DEFAULT_PERCEPTUAL_REPORT_NAME)
            self._emit_log(
                "Perceptual QA: "
                f"backends={','.join(request.perceptual_backends)} "
                f"min_mos={request.perceptual_min_mos:.2f}"
            )
            perceptual_result = run_perceptual_qa(
                manifest,
                config=PerceptualQaConfig(
                    backends=request.perceptual_backends,
                    min_mos=request.perceptual_min_mos,
                    warn_mos=request.perceptual_warn_mos,
                ),
                manifest_path=request.manifest_path,
            )
            write_perceptual_report(report_path, perceptual_result)
            annotate_manifest_with_perceptual(
                manifest,
                perceptual_result,
                report_path=report_path.resolve(),
                reset_bad_chunks=request.quality_loop,
                max_resynthesis_attempts=request.max_resynthesis_attempts,
            )
            summary = perceptual_result.summary
            self._emit_log(
                "Perceptual QA: "
                f"status={perceptual_result.status}, failed={summary['failed']}, "
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
