"""Local library for reusable Qwen voice clone prompts."""

from __future__ import annotations

import hashlib
import json
import os
import pickle
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VOICE_FILE_SUFFIX = ".voice.pt"
META_FILE_SUFFIX = ".voice.json"
VOICE_LIBRARY_VERSION = 1


class UnsafeVoicePromptError(RuntimeError):
    """Raised when a saved voice prompt cannot be loaded safely."""


@dataclass(frozen=True)
class SavedVoice:
    """Metadata for one saved reusable voice prompt."""

    voice_id: str
    name: str
    prompt_path: Path
    metadata_path: Path
    created_at: str = ""
    model: str = ""
    ref_audio: str = ""
    ref_audio_sha256: str = ""
    speech_rate: float = 1.0
    description: str = ""
    ref_text: str = ""
    preview_audio: str = ""
    source: str = "local"
    comfyui_speaker: str = ""


def default_voice_library_dir() -> Path:
    """Return the shared project-local voice library directory."""
    return Path(__file__).resolve().parents[3] / "output" / "voices"


def normalize_voice_library_dir(library_dir: str | Path) -> Path:
    """Return an absolute host path for a voice library directory."""
    path_text = str(library_dir).strip()
    if os.name == "nt" and path_text.startswith("/mnt/") and len(path_text) > 6:
        drive = path_text[5]
        rest = path_text[6:].lstrip("/")
        path_text = f"{drive.upper()}:/{rest}"

    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = default_voice_library_dir().parents[1] / path
    return path


def sanitize_voice_id(name: str) -> str:
    """Create a filesystem-safe id for a saved voice."""
    value = name.strip().lower()
    value = re.sub(r"\s+", "_", value)
    value = re.sub(r"[^\w.-]+", "_", value, flags=re.UNICODE)
    value = re.sub(r"_+", "_", value).strip("._-")
    return value or "voice"


def voice_paths(library_dir: Path, name: str) -> tuple[Path, Path, str]:
    """Return prompt path, metadata path, and sanitized voice id."""
    library_dir = normalize_voice_library_dir(library_dir)
    voice_id = sanitize_voice_id(name)
    return (
        library_dir / f"{voice_id}{VOICE_FILE_SUFFIX}",
        library_dir / f"{voice_id}{META_FILE_SUFFIX}",
        voice_id,
    )


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _metadata_path_for_prompt(prompt_path: Path) -> Path:
    if prompt_path.name.endswith(VOICE_FILE_SUFFIX):
        stem = prompt_path.name.removesuffix(VOICE_FILE_SUFFIX)
        return prompt_path.with_name(f"{stem}{META_FILE_SUFFIX}")
    return prompt_path.with_suffix(META_FILE_SUFFIX)


def _verify_prompt_sidecar_hash(prompt_path: Path) -> None:
    metadata_path = _metadata_path_for_prompt(prompt_path)
    if not metadata_path.exists():
        return
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    if not isinstance(metadata, dict):
        return

    expected_sha256 = str(metadata.get("prompt_sha256") or "").strip().lower()
    if expected_sha256 and _hash_file(prompt_path) != expected_sha256:
        raise UnsafeVoicePromptError(
            f"Saved voice prompt hash mismatch for {prompt_path}. "
            "The .voice.pt file does not match its .voice.json sidecar."
        )


def build_voice_metadata(
    *,
    name: str,
    prompt_path: Path,
    metadata_path: Path,
    ref_audio: str,
    ref_text: str,
    model: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build JSON metadata for a saved voice prompt."""
    voice_id = sanitize_voice_id(name)
    ref_audio_path = Path(ref_audio)
    metadata: dict[str, Any] = {
        "version": VOICE_LIBRARY_VERSION,
        "id": voice_id,
        "name": name.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "prompt_file": prompt_path.name,
        "metadata_file": metadata_path.name,
        "prompt_sha256": (
            _hash_file(prompt_path) if prompt_path.exists() else ""
        ),
        "ref_audio": ref_audio,
        "ref_audio_sha256": (
            _hash_file(ref_audio_path) if ref_audio_path.exists() else ""
        ),
        "ref_text": ref_text,
    }
    if extra:
        metadata.update(extra)
    return metadata


def save_comfyui_voice_metadata(
    *,
    library_dir: Path,
    name: str,
    ref_audio: str,
    ref_text: str,
    model: str = "",
    speech_rate: float = 1.0,
    description: str = "",
    overwrite: bool = True,
) -> SavedVoice:
    """Persist metadata for a ComfyUI-saved voice in the shared library."""
    library_dir = normalize_voice_library_dir(library_dir)
    voice_id = sanitize_voice_id(name)
    metadata_path = library_dir / f"{voice_id}{META_FILE_SUFFIX}"
    if metadata_path.exists() and not overwrite:
        raise FileExistsError(
            f"Saved voice '{voice_id}' already exists in {library_dir}."
        )

    library_dir.mkdir(parents=True, exist_ok=True)
    ref_audio_path = Path(ref_audio)
    metadata: dict[str, Any] = {
        "version": VOICE_LIBRARY_VERSION,
        "id": voice_id,
        "name": name.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "source": "comfyui",
        "comfyui_speaker": name.strip(),
        "ref_audio": ref_audio,
        "preview_audio": ref_audio,
        "ref_audio_sha256": (
            _hash_file(ref_audio_path) if ref_audio_path.exists() else ""
        ),
        "ref_text": ref_text,
        "description": description or ref_text.strip(),
        "speech_rate": speech_rate,
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return _saved_voice_from_metadata(
        metadata,
        metadata_path,
        library_dir / f"{voice_id}{VOICE_FILE_SUFFIX}",
    )


def save_voice_prompt(
    prompt: Any,
    *,
    library_dir: Path,
    name: str,
    ref_audio: str,
    ref_text: str,
    model: str,
    overwrite: bool = False,
    extra: dict[str, Any] | None = None,
) -> SavedVoice:
    """Persist a Qwen ``voice_clone_prompt`` and sidecar metadata."""
    import torch

    library_dir = normalize_voice_library_dir(library_dir)
    prompt_path, metadata_path, voice_id = voice_paths(library_dir, name)
    if not overwrite and (prompt_path.exists() or metadata_path.exists()):
        raise FileExistsError(
            f"Saved voice '{voice_id}' already exists in {library_dir}."
        )

    library_dir.mkdir(parents=True, exist_ok=True)
    torch.save(prompt, prompt_path)
    metadata = build_voice_metadata(
        name=name,
        prompt_path=prompt_path,
        metadata_path=metadata_path,
        ref_audio=ref_audio,
        ref_text=ref_text,
        model=model,
        extra=extra,
    )
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return SavedVoice(
        voice_id=voice_id,
        name=str(metadata.get("name") or voice_id),
        prompt_path=prompt_path,
        metadata_path=metadata_path,
        created_at=str(metadata.get("created_at") or ""),
        model=str(metadata.get("model") or ""),
        ref_audio=str(metadata.get("ref_audio") or ""),
        ref_audio_sha256=str(metadata.get("ref_audio_sha256") or ""),
        speech_rate=float(metadata.get("speech_rate") or 1.0),
        description=str(metadata.get("description") or ""),
        ref_text=str(metadata.get("ref_text") or ""),
        preview_audio=str(metadata.get("preview_audio") or metadata.get("ref_audio") or ""),
        source=str(metadata.get("source") or "local"),
        comfyui_speaker=str(metadata.get("comfyui_speaker") or ""),
    )


def load_voice_prompt(prompt_path: Path, map_location: str | None = None) -> Any:
    """Load a saved Qwen voice clone prompt from disk."""
    import torch

    _verify_prompt_sidecar_hash(prompt_path)
    try:
        return torch.load(
            prompt_path,
            map_location=map_location,
            weights_only=True,
        )
    except TypeError as exc:
        raise UnsafeVoicePromptError(
            "This PyTorch build does not support torch.load(weights_only=True). "
            "Refusing to load .voice.pt with unrestricted pickle semantics; "
            "upgrade PyTorch or regenerate the voice prompt in this environment."
        ) from exc
    except pickle.UnpicklingError as exc:
        raise UnsafeVoicePromptError(
            f"Saved voice prompt {prompt_path} cannot be loaded safely. "
            "Use only prompts created by this app, or regenerate the voice prompt "
            "from trusted reference audio."
        ) from exc


def list_saved_voices(library_dir: Path) -> list[SavedVoice]:
    """Return saved voices with valid metadata and prompt files."""
    library_dir = normalize_voice_library_dir(library_dir)
    if not library_dir.exists():
        return []

    voices: list[SavedVoice] = []
    for metadata_path in sorted(library_dir.glob(f"*{META_FILE_SUFFIX}")):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(metadata, dict):
            continue

        voice_id = sanitize_voice_id(
            str(metadata.get("id") or metadata_path.stem.removesuffix(".voice"))
        )
        prompt_file = str(metadata.get("prompt_file") or "")
        prompt_path = library_dir / (prompt_file or f"{voice_id}{VOICE_FILE_SUFFIX}")
        if not prompt_path.exists():
            fallback = metadata_path.with_suffix("").with_suffix(VOICE_FILE_SUFFIX)
            if fallback.exists():
                prompt_path = fallback
                voice_id = sanitize_voice_id(fallback.name.removesuffix(VOICE_FILE_SUFFIX))
            elif not _metadata_is_comfyui_voice(metadata):
                continue

        metadata["id"] = voice_id
        voices.append(_saved_voice_from_metadata(metadata, metadata_path, prompt_path))
    return sorted(voices, key=lambda item: item.name.lower())


def _metadata_is_comfyui_voice(metadata: dict[str, Any]) -> bool:
    """Return true for metadata that points to a ComfyUI saved speaker."""
    return (
        str(metadata.get("source") or "").strip().lower() == "comfyui"
        or bool(str(metadata.get("comfyui_speaker") or "").strip())
    )


def _saved_voice_from_metadata(
    metadata: dict[str, Any],
    metadata_path: Path,
    prompt_path: Path,
) -> SavedVoice:
    """Convert one sidecar JSON dict into a SavedVoice object."""
    voice_id = sanitize_voice_id(str(metadata.get("id") or metadata_path.stem))
    ref_audio = str(metadata.get("ref_audio") or "")
    preview_audio = str(metadata.get("preview_audio") or ref_audio)
    return SavedVoice(
        voice_id=voice_id,
        name=str(metadata.get("name") or voice_id),
        prompt_path=prompt_path,
        metadata_path=metadata_path,
        created_at=str(metadata.get("created_at") or ""),
        model=str(metadata.get("model") or ""),
        ref_audio=ref_audio,
        ref_audio_sha256=str(metadata.get("ref_audio_sha256") or ""),
        speech_rate=float(metadata.get("speech_rate") or 1.0),
        description=str(metadata.get("description") or ""),
        ref_text=str(metadata.get("ref_text") or ""),
        preview_audio=preview_audio,
        source=str(metadata.get("source") or ("comfyui" if _metadata_is_comfyui_voice(metadata) else "local")),
        comfyui_speaker=str(metadata.get("comfyui_speaker") or ""),
    )


def resolve_saved_voice_path(name_or_path: str, library_dir: Path) -> Path:
    """Resolve a saved voice id/name/path to the underlying ``.voice.pt`` file."""
    library_dir = normalize_voice_library_dir(library_dir)
    value = name_or_path.strip()
    if not value:
        raise ValueError("Saved voice name is empty.")

    direct = Path(value)
    if direct.exists():
        return direct

    voice_id = sanitize_voice_id(value)
    candidate = library_dir / f"{voice_id}{VOICE_FILE_SUFFIX}"
    if candidate.exists():
        return candidate

    for voice in list_saved_voices(library_dir):
        if value in {voice.voice_id, voice.name}:
            if voice.prompt_path.exists():
                return voice.prompt_path
            break
    raise FileNotFoundError(
        f"Saved voice '{value}' not found in {library_dir}."
    )
