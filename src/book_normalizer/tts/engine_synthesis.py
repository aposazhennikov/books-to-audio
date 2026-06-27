"""Local-command synthesis adapters for non-ComfyUI TTS engines."""

from __future__ import annotations

import json
import logging
import os
import shlex
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from string import Formatter
from typing import Any

from book_normalizer.comfyui.synthesis import (
    SynthesisSummary,
    build_output_path,
    collect_pending_chunks,
    count_done_chunks,
    save_manifest,
)
from book_normalizer.runtime_paths import configured_ffmpeg_bin
from book_normalizer.tts.compatible_audio import export_compatible_mp3
from book_normalizer.tts.engines import get_tts_engine
from book_normalizer.tts.model_download import tts_model_install_path
from book_normalizer.tts.voice_mapping import primary_voice_mapping_key

ProgressCallback = Callable[[str], None]
CancelRequested = Callable[[], bool]

logger = logging.getLogger(__name__)


class TTSEngineSynthesisError(RuntimeError):
    """Raised when a local TTS engine cannot synthesize a chunk."""


class TTSEngineSynthesisCancelled(TTSEngineSynthesisError):  # noqa: N818
    """Raised when local-engine synthesis is cancelled cooperatively."""


@dataclass(frozen=True)
class TTSEngineCommand:
    """Command template and model location for one local TTS engine."""

    engine_id: str
    command_template: str
    model_id: str
    model_path: Path


@dataclass(frozen=True)
class TTSEnginePreflightCheck:
    """One structured readiness check for a local-command TTS engine."""

    name: str
    ok: bool
    required: bool
    message: str


@dataclass(frozen=True)
class TTSEnginePreflight:
    """Resolved local-command readiness details for GUI/CLI preflight."""

    engine_id: str
    display_name: str
    command_template: str
    preview_command: str
    executable: str
    executable_path: str | None
    env_name: str
    install_hint: str
    model_path: str
    output_dir: str | None
    ffmpeg_path: str | None
    checks: tuple[TTSEnginePreflightCheck, ...]

    @property
    def ok(self) -> bool:
        """Return true when all required preflight checks pass."""
        return all(check.ok or not check.required for check in self.checks)


DEFAULT_COMMAND_TEMPLATES: dict[str, str] = {
    "fish-speech-1.5": (
        "fish-speech-cli text-to-speech --text-file {text_file} --output {output_file} "
        "--model {model_path} --reference-audio {ref_audio} --reference-text-file {ref_text_file}"
    ),
    "f5-tts": (
        "f5-tts_infer-cli --gen_file {text_file} --output_dir {output_dir} "
        "--output_file {output_name} --ref_audio {ref_audio} --ref_text {ref_text}"
    ),
    "xtts-v2": (
        "tts --model_path {model_path} --text {text} --out_path {output_file} "
        "--speaker_wav {ref_audio} --language_idx {language}"
    ),
    "cosyvoice-3": (
        "cosyvoice-cli --model-dir {model_path} --text-file {text_file} --output {output_file} "
        "--prompt-audio {ref_audio} --prompt-text-file {ref_text_file}"
    ),
}

INSTALL_HINTS: dict[str, str] = {
    "fish-speech-1.5": (
        "Install Fish Speech CLI and make `fish-speech-cli` available on PATH, "
        "or set {env_name} to your adapter command template."
    ),
    "f5-tts": (
        "Install F5-TTS CLI and make `f5-tts_infer-cli` available on PATH, "
        "or set {env_name} to your adapter command template."
    ),
    "xtts-v2": (
        "Install Coqui TTS and make `tts` available on PATH, "
        "or set {env_name} to your adapter command template."
    ),
    "cosyvoice-3": (
        "Install CosyVoice CLI and make `cosyvoice-cli` available on PATH, "
        "or set {env_name} to your adapter command template."
    ),
}


def synthesize_engine_manifest(
    *,
    manifest: dict[str, Any],
    manifest_path: Path,
    engine_id: str,
    out_dir: Path,
    models_dir: str | Path | None = None,
    chapter_filter: int | None = None,
    failed_only: bool = False,
    clone_config_path: Path | None = None,
    chunk_timeout: float = 300.0,
    progress: ProgressCallback | None = None,
    cancel_requested: CancelRequested | None = None,
) -> SynthesisSummary:
    """Synthesize a v2 manifest with a local non-ComfyUI TTS engine."""
    is_cancelled = cancel_requested or (lambda: False)
    command = resolve_engine_command(engine_id, models_dir)
    clone_config = _load_clone_config(clone_config_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    total = len(list(_iter_synthesis_chunks(manifest, chapter_filter)))
    done_start = count_done_chunks(manifest, chapter_filter, manifest_path=manifest_path)
    pending = collect_pending_chunks(
        manifest,
        chapter_filter,
        failed_only=failed_only,
        manifest_path=manifest_path,
    )
    if not pending:
        _emit(progress, f"All {total} chunks already synthesized. Nothing to do.")
        return SynthesisSummary(total=total, synthesized=0, skipped=done_start, failed=0)

    _emit(
        progress,
        f"{command.model_id}: {total} total, {done_start} already done, {len(pending)} to synthesize.",
    )

    done = done_start
    synthesized = 0
    failed = 0
    manifest_language = str(manifest.get("language") or "ru")
    for chapter_entry, chunk in pending:
        if is_cancelled():
            return SynthesisSummary(
                total=total,
                synthesized=synthesized,
                skipped=done_start,
                failed=failed,
                status="cancelled",
            )
        chapter_index = int(chapter_entry.get("chapter_index", 0))
        chunk_index = int(chunk.get("chunk_index", 0))
        voice_label = str(chunk.get("voice_label") or "narrator")
        voice_id = str(chunk.get("voice_id") or voice_label)
        text = _chunk_text(chunk, voice_label)
        language = str(chunk.get("language") or manifest_language)
        output_path = build_output_path(out_dir, chapter_index, chunk_index, voice_label)

        if not text.strip():
            chunk["synthesized"] = True
            chunk["audio_file"] = ""
            done += 1
            _emit(progress, f"PROGRESS {done}/{total}")
            save_manifest(manifest_path, manifest)
            continue

        _emit(
            progress,
            f"  Synthesizing ch{chapter_index + 1:03d}/chunk{chunk_index + 1:03d} "
            f"[{voice_label}/{voice_id}] {len(text)} chars -> {output_path.name}",
        )
        started = time.monotonic()
        try:
            voice_ref = _voice_reference_for_chunk(chunk, clone_config)
            run_engine_command(
                command,
                text=text,
                output_path=output_path,
                language=language,
                voice_id=voice_id,
                voice_label=voice_label,
                voice_ref=voice_ref,
                timeout=chunk_timeout,
                cancel_requested=cancel_requested,
            )
        except TTSEngineSynthesisCancelled:
            return SynthesisSummary(
                total=total,
                synthesized=synthesized,
                skipped=done_start,
                failed=failed,
                status="cancelled",
            )
        except Exception as exc:
            chunk["failed"] = True
            chunk["error"] = str(exc)
            failed += 1
            _emit(progress, f"  ERROR: {exc}")
            save_manifest(manifest_path, manifest)
            continue

        if not output_path.exists() or output_path.stat().st_size <= 0:
            message = f"{command.model_id} finished but did not create audio: {output_path}"
            chunk["failed"] = True
            chunk["error"] = message
            failed += 1
            _emit(progress, f"  ERROR: {message}")
            save_manifest(manifest_path, manifest)
            continue

        chunk["synthesized"] = True
        chunk["failed"] = False
        chunk["error"] = ""
        chunk["audio_file"] = _manifest_audio_file(output_path, manifest_path)
        _write_compatible_chunk_audio(chunk, output_path, manifest_path)
        chunk["tts_engine"] = engine_id
        done += 1
        synthesized += 1
        _emit(
            progress,
            f"    Done in {time.monotonic() - started:.1f}s -> {output_path.stat().st_size // 1024} KB",
        )
        _emit(progress, f"PROGRESS {done}/{total}")
        save_manifest(manifest_path, manifest)

    _emit(
        progress,
        f"Synthesis complete: {synthesized} new chunks synthesized "
        f"({done}/{total} total done, {failed} failed).",
    )
    return SynthesisSummary(total=total, synthesized=synthesized, skipped=done_start, failed=failed)


def resolve_engine_command(
    engine_id_or_model_id: str,
    models_dir: str | Path | None = None,
) -> TTSEngineCommand:
    """Resolve command template and local model path for an engine."""
    engine = get_tts_engine(engine_id_or_model_id)
    if engine is None:
        raise TTSEngineSynthesisError(f"Unknown TTS engine: {engine_id_or_model_id}")
    template = _engine_command_template(engine.engine_id)
    model_id = engine.primary_model_id
    model_path = tts_model_install_path(model_id, models_dir)
    return TTSEngineCommand(engine.engine_id, template, model_id, model_path)


def preflight_engine_command(
    engine_id_or_model_id: str,
    models_dir: str | Path | None = None,
    *,
    output_dir: str | Path | None = None,
    clone_config_path: str | Path | None = None,
) -> TTSEnginePreflight:
    """Check whether a local-command TTS engine can be launched."""
    command = resolve_engine_command(engine_id_or_model_id, models_dir)
    engine = get_tts_engine(command.engine_id)
    display_name = engine.display_name if engine else command.engine_id
    preview_values = _preflight_values(command)
    argv = _render_command(command.command_template, preview_values)
    executable = argv[0]
    executable_path = shutil.which(executable)
    env_name = _engine_env_name(command.engine_id)
    hint_template = INSTALL_HINTS.get(
        command.engine_id,
        "Install the engine CLI and make `{executable}` available on PATH, "
        "or set {env_name} to a working command template.",
    )
    checks = _preflight_checks(
        command,
        argv,
        executable_path,
        output_dir=Path(output_dir) if output_dir else None,
        clone_config_path=Path(clone_config_path) if clone_config_path else None,
    )
    ffmpeg_check = next((check for check in checks if check.name == "ffmpeg"), None)
    ffmpeg_path = ffmpeg_check.message if ffmpeg_check and ffmpeg_check.ok else None
    return TTSEnginePreflight(
        engine_id=command.engine_id,
        display_name=display_name,
        command_template=command.command_template,
        preview_command=shlex.join(argv),
        executable=executable,
        executable_path=executable_path,
        env_name=env_name,
        install_hint=hint_template.format(env_name=env_name, executable=executable),
        model_path=str(command.model_path),
        output_dir=str(output_dir) if output_dir else None,
        ffmpeg_path=ffmpeg_path,
        checks=checks,
    )


def run_engine_command(
    command: TTSEngineCommand,
    *,
    text: str,
    output_path: Path,
    language: str,
    voice_id: str,
    voice_label: str,
    voice_ref: dict[str, object],
    timeout: float,
    cancel_requested: CancelRequested | None = None,
) -> None:
    """Render a chunk by invoking the selected engine command."""
    is_cancelled = cancel_requested or (lambda: False)
    if is_cancelled():
        raise TTSEngineSynthesisCancelled("TTS engine synthesis cancelled before launch")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="books-to-audio-tts-") as temp_dir_text:
        temp_dir = Path(temp_dir_text)
        text_file = temp_dir / "text.txt"
        ref_text_file = temp_dir / "reference.txt"
        text_file.write_text(text, encoding="utf-8")
        ref_text = str(voice_ref.get("ref_text") or "")
        ref_text_file.write_text(ref_text, encoding="utf-8")
        values = {
            "text": text,
            "text_file": str(text_file),
            "output_file": str(output_path),
            "output_dir": str(output_path.parent),
            "output_name": output_path.name,
            "model_id": command.model_id,
            "model_path": str(command.model_path),
            "language": language,
            "voice_id": voice_id,
            "voice_label": voice_label,
            "ref_audio": str(voice_ref.get("ref_audio") or ""),
            "ref_text": ref_text,
            "ref_text_file": str(ref_text_file),
        }
        argv = _render_command(command.command_template, values)
        if cancel_requested is not None:
            _run_engine_command_cancellable(
                argv,
                command=command,
                timeout=timeout,
                cancel_requested=is_cancelled,
            )
            return
        try:
            result = subprocess.run(
                argv,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=max(1.0, float(timeout)),
            )
        except FileNotFoundError as exc:
            env_name = _engine_env_name(command.engine_id)
            hint_template = INSTALL_HINTS.get(
                command.engine_id,
                "Install the engine CLI or set {env_name} to a working command template.",
            )
            install_hint = hint_template.format(env_name=env_name, executable=argv[0])
            raise TTSEngineSynthesisError(
                f"TTS engine command was not found: {argv[0]}. "
                f"{install_hint} "
                f"Command template: {command.command_template}"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise TTSEngineSynthesisError(
                f"TTS engine command timed out after {timeout:.0f}s: {argv[0]}"
            ) from exc
        if result.returncode != 0:
            stderr = (result.stderr or result.stdout or "").strip()
            raise TTSEngineSynthesisError(
                f"TTS engine command failed with exit code {result.returncode}: {stderr}"
            )


def _run_engine_command_cancellable(
    argv: list[str],
    *,
    command: TTSEngineCommand,
    timeout: float,
    cancel_requested: CancelRequested,
) -> None:
    deadline = time.monotonic() + max(1.0, float(timeout))
    try:
        process = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        env_name = _engine_env_name(command.engine_id)
        hint_template = INSTALL_HINTS.get(
            command.engine_id,
            "Install the engine CLI or set {env_name} to a working command template.",
        )
        install_hint = hint_template.format(env_name=env_name, executable=argv[0])
        raise TTSEngineSynthesisError(
            f"TTS engine command was not found: {argv[0]}. "
            f"{install_hint} "
            f"Command template: {command.command_template}"
        ) from exc

    while process.poll() is None:
        if cancel_requested():
            _terminate_process(process)
            raise TTSEngineSynthesisCancelled("TTS engine synthesis cancelled")
        if time.monotonic() >= deadline:
            _terminate_process(process)
            raise TTSEngineSynthesisError(
                f"TTS engine command timed out after {timeout:.0f}s: {argv[0]}"
            )
        time.sleep(0.2)

    stdout, stderr = process.communicate()
    if process.returncode != 0:
        detail = (stderr or stdout or "").strip()
        raise TTSEngineSynthesisError(
            f"TTS engine command failed with exit code {process.returncode}: {detail}"
        )


def _terminate_process(process: subprocess.Popen[str]) -> None:
    process.terminate()
    try:
        process.wait(timeout=5.0)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5.0)


def _engine_command_template(engine_id: str) -> str:
    env_name = _engine_env_name(engine_id)
    override = os.environ.get(env_name)
    if override:
        return override
    try:
        return DEFAULT_COMMAND_TEMPLATES[engine_id]
    except KeyError as exc:
        raise TTSEngineSynthesisError(
            f"No command template is configured for TTS engine {engine_id}."
        ) from exc


def _engine_env_name(engine_id: str) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in engine_id.upper())
    return f"BOOKS_TO_AUDIO_TTS_{safe}_COMMAND"


def _render_command(template: str, values: dict[str, str]) -> list[str]:
    rendered: list[str] = []
    skip_previous_option = False
    for token in shlex.split(template):
        try:
            value = token.format(**values)
        except KeyError as exc:
            raise TTSEngineSynthesisError(f"Unknown command placeholder: {exc}") from exc
        if value == "":
            if rendered and rendered[-1].startswith("-"):
                rendered.pop()
            else:
                skip_previous_option = True
            continue
        if skip_previous_option and token.startswith("-"):
            skip_previous_option = False
            continue
        skip_previous_option = False
        rendered.append(value)
    if not rendered:
        raise TTSEngineSynthesisError("TTS engine command template rendered to an empty command.")
    return rendered


def _preflight_values(command: TTSEngineCommand) -> dict[str, str]:
    output_path = Path("<output_dir>") / "chapter_001_chunk_001_narrator.wav"
    return {
        "text": "<chunk_text>",
        "text_file": "<temp_text_file>",
        "output_file": str(output_path),
        "output_dir": "<output_dir>",
        "output_name": output_path.name,
        "model_id": command.model_id,
        "model_path": str(command.model_path),
        "language": "<language>",
        "voice_id": "<voice_id>",
        "voice_label": "<voice_label>",
        "ref_audio": "<reference_audio>",
        "ref_text": "<reference_text>",
        "ref_text_file": "<temp_reference_text_file>",
    }


def _preflight_checks(
    command: TTSEngineCommand,
    argv: list[str],
    executable_path: str | None,
    *,
    output_dir: Path | None,
    clone_config_path: Path | None,
) -> tuple[TTSEnginePreflightCheck, ...]:
    checks = [
        _check_executable(argv[0], executable_path),
        _check_template(command.command_template),
        _check_model_path(command.model_path),
        _check_output_dir(output_dir),
        _check_reference_inputs(command.command_template, clone_config_path),
        _check_ffmpeg(),
    ]
    return tuple(checks)


def _check_executable(executable: str, executable_path: str | None) -> TTSEnginePreflightCheck:
    if executable_path:
        return TTSEnginePreflightCheck(
            "executable",
            True,
            True,
            executable_path,
        )
    return TTSEnginePreflightCheck(
        "executable",
        False,
        True,
        f"{executable} was not found on PATH.",
    )


def _check_template(template: str) -> TTSEnginePreflightCheck:
    known = set(_preflight_values(TTSEngineCommand("", "", "", Path())).keys())
    fields = {
        field_name
        for _literal, field_name, _format_spec, _conversion in Formatter().parse(template)
        if field_name
    }
    unknown = sorted(field for field in fields if field not in known)
    has_text = bool(fields & {"text", "text_file"})
    has_output = bool(fields & {"output_file", "output_dir", "output_name"})
    problems: list[str] = []
    if unknown:
        problems.append(f"unknown placeholders: {', '.join(unknown)}")
    if not has_text:
        problems.append("missing a text placeholder")
    if not has_output:
        problems.append("missing an output placeholder")
    if problems:
        return TTSEnginePreflightCheck("template", False, True, "; ".join(problems))
    return TTSEnginePreflightCheck("template", True, True, "Command template placeholders are valid.")


def _check_model_path(model_path: Path) -> TTSEnginePreflightCheck:
    if model_path.exists():
        return TTSEnginePreflightCheck("model", True, True, str(model_path))
    return TTSEnginePreflightCheck(
        "model",
        False,
        True,
        f"Model path is missing: {model_path}",
    )


def _check_output_dir(output_dir: Path | None) -> TTSEnginePreflightCheck:
    if output_dir is None:
        return TTSEnginePreflightCheck(
            "output",
            True,
            False,
            "Output directory will be checked when a run starts.",
        )
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        probe = output_dir / ".books-to-audio-preflight"
        probe.write_text("", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        return TTSEnginePreflightCheck(
            "output",
            False,
            True,
            f"Output directory is not writable: {output_dir} ({exc})",
        )
    return TTSEnginePreflightCheck("output", True, True, str(output_dir))


def _check_reference_inputs(
    template: str,
    clone_config_path: Path | None,
) -> TTSEnginePreflightCheck:
    fields = {
        field_name
        for _literal, field_name, _format_spec, _conversion in Formatter().parse(template)
        if field_name
    }
    if not fields & {"ref_audio", "ref_text", "ref_text_file"}:
        return TTSEnginePreflightCheck(
            "reference",
            True,
            False,
            "Command template does not request reference audio/text.",
        )
    if clone_config_path is None:
        return TTSEnginePreflightCheck(
            "reference",
            True,
            False,
            "Reference audio/text is optional until a custom voice is selected.",
        )
    references = _load_clone_config(clone_config_path)
    missing: list[str] = []
    for key, entry in references.items():
        ref_audio = Path(str(entry.get("ref_audio") or ""))
        ref_text = str(entry.get("ref_text") or "").strip()
        if not ref_audio.exists():
            missing.append(f"{key}: missing reference audio {ref_audio}")
        if not ref_text:
            missing.append(f"{key}: missing reference text")
    if missing:
        return TTSEnginePreflightCheck("reference", False, True, "; ".join(missing))
    return TTSEnginePreflightCheck("reference", True, True, str(clone_config_path))


def _check_ffmpeg() -> TTSEnginePreflightCheck:
    configured = configured_ffmpeg_bin()
    candidate = str(configured or "ffmpeg")
    resolved = str(configured) if configured and Path(configured).exists() else shutil.which(candidate)
    if resolved:
        return TTSEnginePreflightCheck("ffmpeg", True, True, resolved)
    return TTSEnginePreflightCheck(
        "ffmpeg",
        False,
        True,
        f"ffmpeg was not found: {candidate}",
    )


def _load_clone_config(path: Path | None) -> dict[str, dict[str, object]]:
    if not path or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    return {str(key): value for key, value in data.items() if isinstance(value, dict)}


def _voice_reference_for_chunk(
    chunk: dict[str, Any],
    clone_config: dict[str, dict[str, object]],
) -> dict[str, object]:
    keys = [
        primary_voice_mapping_key(chunk),
        str(chunk.get("voice_id") or ""),
        str(chunk.get("voice_label") or ""),
    ]
    for key in keys:
        if key and key in clone_config:
            return clone_config[key]
    return {}


def _chunk_text(chunk: dict[str, Any], voice_label: str) -> str:
    return str(chunk.get("text") or chunk.get(voice_label) or "")


def _iter_synthesis_chunks(
    manifest: dict[str, Any],
    chapter_filter: int | None,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    from book_normalizer.comfyui.synthesis import iter_manifest_chunks

    return list(iter_manifest_chunks(manifest, chapter_filter))


def _manifest_audio_file(output_path: Path, manifest_path: Path) -> str:
    try:
        return output_path.resolve().relative_to(manifest_path.parent.resolve()).as_posix()
    except ValueError:
        return str(output_path)


def _write_compatible_chunk_audio(chunk: dict[str, Any], output_path: Path, manifest_path: Path) -> None:
    """Best-effort compatible MP3 sidecar for local-engine chunk audio."""
    try:
        compatible_path = export_compatible_mp3(
            output_path,
            ffmpeg=str(configured_ffmpeg_bin() or "ffmpeg"),
        )
    except Exception as exc:  # pragma: no cover - depends on local ffmpeg/runtime media
        logger.warning("Compatible chunk MP3 export failed for %s: %s", output_path, exc)
        chunk["compatible_audio_error"] = str(exc)
        return
    chunk["compatible_audio_file"] = _manifest_audio_file(compatible_path, manifest_path)
    chunk.pop("compatible_audio_error", None)


def _emit(progress: ProgressCallback | None, line: str) -> None:
    if progress:
        progress(line)
