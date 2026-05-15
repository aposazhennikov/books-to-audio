"""Resolve TTS model names against a shared ComfyUI models directory."""

from __future__ import annotations

import os
from pathlib import Path

MODEL_DIR_ENV_VARS = ("BOOKS_TO_AUDIO_MODELS_DIR", "COMFYUI_MODELS_DIR")
MODEL_SUBDIRS = (
    "audio_encoders",
    "",
    "checkpoints",
    "text_encoders",
    "diffusion_models",
    "unet",
)


def default_comfyui_models_dir() -> Path:
    """Return the default shared ComfyUI models directory for this platform."""
    if os.name == "nt":
        return Path("D:/ComfyUI-external/models")
    return Path("/mnt/d/ComfyUI-external/models")


def candidate_model_roots(models_dir: str | Path | None = None) -> list[Path]:
    """Return model root candidates in priority order."""
    roots: list[Path] = []
    if models_dir:
        roots.append(Path(models_dir).expanduser())

    for env_name in MODEL_DIR_ENV_VARS:
        value = os.environ.get(env_name)
        if value:
            roots.append(Path(value).expanduser())

    roots.append(default_comfyui_models_dir())

    deduped: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root)
        if key not in seen:
            deduped.append(root)
            seen.add(key)
    return deduped


def resolve_model_path(
    model_name: str,
    models_dir: str | Path | None = None,
) -> str:
    """Resolve a HuggingFace model id to a local ComfyUI model folder if present.

    For example, ``Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice`` resolves to
    ``D:/ComfyUI-external/models/audio_encoders/Qwen3-TTS-12Hz-1.7B-CustomVoice``
    on Windows or ``/mnt/d/ComfyUI-external/models/audio_encoders/...`` in WSL.
    If no local folder is found, the original model name is returned so
    ``from_pretrained`` can keep its normal HuggingFace behavior.
    """
    model_name = str(model_name).strip()
    if not model_name:
        return model_name

    direct_path = Path(model_name).expanduser()
    if _looks_like_model_dir(direct_path):
        return str(direct_path)

    basename = _model_basename(model_name)
    for root in candidate_model_roots(models_dir):
        for subdir in MODEL_SUBDIRS:
            candidate = root / subdir / basename if subdir else root / basename
            if _looks_like_model_dir(candidate):
                return str(candidate)

    return model_name


def describe_model_resolution(
    model_name: str,
    models_dir: str | Path | None = None,
) -> tuple[str, bool]:
    """Return ``(resolved_name, is_local)`` for status/log output."""
    resolved = resolve_model_path(model_name, models_dir=models_dir)
    return resolved, _looks_like_model_dir(Path(resolved))


def _model_basename(model_name: str) -> str:
    """Return the likely local folder name for a model id or path."""
    normalized = model_name.replace("\\", "/").rstrip("/")
    return normalized.rsplit("/", 1)[-1]


def _looks_like_model_dir(path: Path) -> bool:
    """Return True when a directory looks loadable by ``from_pretrained``."""
    try:
        return path.is_dir() and (path / "config.json").is_file()
    except OSError:
        return False
