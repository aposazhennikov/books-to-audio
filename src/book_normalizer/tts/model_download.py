"""Download and verify local TTS model folders."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from book_normalizer.tts.engines import (
    COSYVOICE_3,
    F5_TTS,
    FISH_SPEECH_15,
    QWEN3_TTS_BASE_06B,
    QWEN3_TTS_BASE_17B,
    QWEN3_TTS_CUSTOM_VOICE_06B,
    QWEN3_TTS_CUSTOM_VOICE_17B,
    QWEN3_TTS_TOKENIZER,
    QWEN3_TTS_VOICE_DESIGN_17B,
    TTS_ENGINES,
    XTTS_V2,
    tts_model_ids_for_engine,
)
from book_normalizer.tts.model_paths import (
    default_comfyui_models_dir,
    looks_like_model_dir,
    model_basename,
)

DEFAULT_TTS_MODEL_ID = QWEN3_TTS_CUSTOM_VOICE_17B
VOICE_CLONE_MODEL_ID = QWEN3_TTS_BASE_17B
TTS_MODEL_SUBDIR = "audio_encoders"

KNOWN_TTS_MODEL_IDS = (
    QWEN3_TTS_CUSTOM_VOICE_17B,
    QWEN3_TTS_CUSTOM_VOICE_06B,
    QWEN3_TTS_BASE_17B,
    QWEN3_TTS_BASE_06B,
    QWEN3_TTS_VOICE_DESIGN_17B,
    QWEN3_TTS_TOKENIZER,
    FISH_SPEECH_15,
    F5_TTS,
    XTTS_V2,
    COSYVOICE_3,
)

MODEL_DOWNLOAD_WARNING = (
    "WARNING: TTS model download uses Hugging Face, can take a long time, "
    "and can consume many gigabytes of disk space and network traffic. "
    "Make sure the selected models folder is on a fast disk with enough free space."
)


@dataclass(frozen=True)
class TTSModelInstallResult:
    """Result for one requested model repository."""

    model_id: str
    path: Path
    already_present: bool


class TTSModelDownloadError(RuntimeError):
    """Raised when Hugging Face model download cannot start or complete."""


def tts_model_install_path(model_id: str, models_dir: str | Path | None = None) -> Path:
    """Return the local ComfyUI-compatible folder for a Hugging Face model id."""
    root = Path(models_dir).expanduser() if models_dir else default_comfyui_models_dir()
    return root / TTS_MODEL_SUBDIR / model_basename(model_id)


def tts_model_is_installed(model_id: str, models_dir: str | Path | None = None) -> bool:
    """Return True when the selected models dir already contains this model."""
    return looks_like_model_dir(tts_model_install_path(model_id, models_dir))


def expand_tts_model_ids(
    model_ids: list[str] | tuple[str, ...],
    *,
    include_tokenizer: bool = True,
) -> list[str]:
    """Return a deduplicated model list, optionally adding the Qwen tokenizer."""
    expanded: list[str] = []
    for model_or_engine_id in model_ids:
        engine_models = tts_model_ids_for_engine(model_or_engine_id)
        candidates = engine_models or (str(model_or_engine_id or "").strip(),)
        for model_id in candidates:
            normalized = str(model_id or "").strip()
            if not normalized:
                continue
            if normalized not in expanded:
                expanded.append(normalized)

    needs_qwen_tokenizer = any(
        model_id.startswith("Qwen/Qwen3-TTS-12Hz-") for model_id in expanded
    )
    if include_tokenizer and needs_qwen_tokenizer and QWEN3_TTS_TOKENIZER not in expanded:
        expanded.append(QWEN3_TTS_TOKENIZER)

    return expanded


def default_tts_model_ids() -> list[str]:
    """Return model ids downloaded by the default installer scenario."""
    defaults = [engine.engine_id for engine in TTS_ENGINES if engine.default]
    return expand_tts_model_ids(defaults)


def all_supported_tts_model_ids() -> list[str]:
    """Return model ids for every selectable TTS engine."""
    supported: list[str] = []
    for engine in TTS_ENGINES:
        for model_id in engine.model_ids:
            if model_id not in supported:
                supported.append(model_id)
    return supported


def _expand_legacy_tts_model_ids(
    model_ids: list[str] | tuple[str, ...],
    *,
    include_tokenizer: bool = True,
) -> list[str]:
    """Compatibility helper kept for older tests/imports during refactors."""
    expanded: list[str] = []
    for model_id in model_ids:
        normalized = str(model_id or "").strip()
        if not normalized:
            continue
        if normalized not in expanded:
            expanded.append(normalized)

    if include_tokenizer and expanded and QWEN3_TTS_TOKENIZER not in expanded:
        expanded.append(QWEN3_TTS_TOKENIZER)

    return expanded


def missing_tts_model_ids(
    model_ids: list[str] | tuple[str, ...],
    models_dir: str | Path | None = None,
    *,
    include_tokenizer: bool = True,
) -> list[str]:
    """Return model ids absent from the selected local model directory."""
    return [
        model_id
        for model_id in expand_tts_model_ids(model_ids, include_tokenizer=include_tokenizer)
        if not tts_model_is_installed(model_id, models_dir)
    ]


def install_tts_models(
    model_ids: list[str] | tuple[str, ...],
    models_dir: str | Path | None = None,
    *,
    token: str | None = None,
    force: bool = False,
    include_tokenizer: bool = True,
    progress: Callable[[str], None] | None = None,
) -> list[TTSModelInstallResult]:
    """Download requested Hugging Face TTS models into the selected models dir."""
    requested = expand_tts_model_ids(model_ids, include_tokenizer=include_tokenizer)
    if not requested:
        raise TTSModelDownloadError("No TTS models were selected for download.")

    results: list[TTSModelInstallResult] = []
    snapshot_download = None
    for model_id in requested:
        target_dir = tts_model_install_path(model_id, models_dir)
        if not force and looks_like_model_dir(target_dir):
            _emit(progress, f"Already installed: {model_id} -> {target_dir}")
            results.append(
                TTSModelInstallResult(
                    model_id=model_id,
                    path=target_dir,
                    already_present=True,
                )
            )
            continue

        if snapshot_download is None:
            try:
                from huggingface_hub import snapshot_download as hf_snapshot_download
            except ImportError as exc:  # pragma: no cover - depends on optional package
                raise TTSModelDownloadError(
                    "huggingface-hub is required to install TTS models. "
                    "Run install.py again or install it with: pip install huggingface-hub"
                ) from exc
            snapshot_download = hf_snapshot_download

        target_dir.mkdir(parents=True, exist_ok=True)
        _emit(progress, f"Downloading {model_id} -> {target_dir}")
        try:
            snapshot_download(
                repo_id=model_id,
                repo_type="model",
                local_dir=str(target_dir),
                token=token or None,
            )
        except Exception as exc:  # pragma: no cover - network/service dependent
            raise TTSModelDownloadError(f"Could not download {model_id}: {exc}") from exc

        if not looks_like_model_dir(target_dir):
            raise TTSModelDownloadError(
                f"Downloaded {model_id}, but {target_dir} does not look like a model folder."
            )

        _emit(progress, f"Installed: {model_id} -> {target_dir}")
        results.append(
            TTSModelInstallResult(
                model_id=model_id,
                path=target_dir,
                already_present=False,
            )
        )

    return results


def _emit(progress: Callable[[str], None] | None, message: str) -> None:
    if progress:
        progress(message)
