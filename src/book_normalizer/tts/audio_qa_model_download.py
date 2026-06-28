"""Download local Hugging Face models used by audio QA gates."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from book_normalizer.tts.model_paths import default_comfyui_models_dir, looks_like_model_dir, model_basename

DEFAULT_LLM_AUDIO_QA_MODEL_ID = "Qwen/Qwen3-Omni-30B-A3B-Instruct"
QWEN3_ASR_MODEL_ID = "Qwen/Qwen3-ASR-1.7B"
FORCED_ALIGNER_MODEL_ID = "Qwen/Qwen3-ForcedAligner-0.6B-hf"
RUSSIAN_EMOTION_MODEL_ID = "Aniemore/wav2vec2-xlsr-53-russian-emotion-recognition"
AUDIO_QA_MODEL_SUBDIR = "audio_qa"

AUDIO_QA_MODEL_SETS = {
    "omni": (DEFAULT_LLM_AUDIO_QA_MODEL_ID,),
    "production": (
        DEFAULT_LLM_AUDIO_QA_MODEL_ID,
        QWEN3_ASR_MODEL_ID,
        FORCED_ALIGNER_MODEL_ID,
    ),
    "all": (
        DEFAULT_LLM_AUDIO_QA_MODEL_ID,
        QWEN3_ASR_MODEL_ID,
        FORCED_ALIGNER_MODEL_ID,
        RUSSIAN_EMOTION_MODEL_ID,
    ),
}

AUDIO_QA_MODEL_DOWNLOAD_WARNING = (
    "WARNING: Audio QA model download uses Hugging Face, can take a long time, "
    "and can consume tens of gigabytes for the Omni reviewer. Use a fast disk with enough space."
)


@dataclass(frozen=True)
class AudioQaModelInstallResult:
    """Result for one requested audio QA model repository."""

    model_id: str
    path: Path
    already_present: bool


class AudioQaModelDownloadError(RuntimeError):
    """Raised when Hugging Face audio QA model download cannot start or complete."""


def audio_qa_model_install_path(model_id: str, models_dir: str | Path | None = None) -> Path:
    """Return the local model folder used by audio QA components."""
    root = Path(models_dir).expanduser() if models_dir else default_comfyui_models_dir()
    return root / AUDIO_QA_MODEL_SUBDIR / model_basename(model_id)


def audio_qa_model_is_installed(model_id: str, models_dir: str | Path | None = None) -> bool:
    """Return True when the selected models dir already contains this model."""
    return looks_like_model_dir(audio_qa_model_install_path(model_id, models_dir))


def expand_audio_qa_model_ids(model_ids_or_sets: list[str] | tuple[str, ...]) -> list[str]:
    """Expand audio QA model-set aliases into unique Hugging Face model ids."""
    requested = model_ids_or_sets or ("production",)
    expanded: list[str] = []
    for item in requested:
        normalized = str(item or "").strip()
        if not normalized:
            continue
        candidates = AUDIO_QA_MODEL_SETS.get(normalized, (normalized,))
        for model_id in candidates:
            if model_id not in expanded:
                expanded.append(model_id)
    return expanded


def install_audio_qa_models(
    model_ids_or_sets: list[str] | tuple[str, ...],
    models_dir: str | Path | None = None,
    *,
    token: str | None = None,
    force: bool = False,
    progress: Callable[[str], None] | None = None,
) -> list[AudioQaModelInstallResult]:
    """Download requested Hugging Face audio QA models into the selected models dir."""
    requested = expand_audio_qa_model_ids(model_ids_or_sets)
    if not requested:
        raise AudioQaModelDownloadError("No audio QA models were selected for download.")

    results: list[AudioQaModelInstallResult] = []
    snapshot_download = None
    for model_id in requested:
        target_dir = audio_qa_model_install_path(model_id, models_dir)
        if not force and looks_like_model_dir(target_dir):
            _emit(progress, f"Already installed: {model_id} -> {target_dir}")
            results.append(AudioQaModelInstallResult(model_id, target_dir, True))
            continue

        if snapshot_download is None:
            try:
                from huggingface_hub import snapshot_download as hf_snapshot_download
            except ImportError as exc:  # pragma: no cover - depends on optional package
                raise AudioQaModelDownloadError(
                    "huggingface-hub is required to install audio QA models. "
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
            raise AudioQaModelDownloadError(f"Could not download {model_id}: {exc}") from exc
        if not looks_like_model_dir(target_dir):
            raise AudioQaModelDownloadError(
                f"Downloaded {model_id}, but {target_dir} does not look like a model folder."
            )
        _emit(progress, f"Installed: {model_id} -> {target_dir}")
        results.append(AudioQaModelInstallResult(model_id, target_dir, False))
    return results


def _emit(progress: Callable[[str], None] | None, message: str) -> None:
    if progress:
        progress(message)
