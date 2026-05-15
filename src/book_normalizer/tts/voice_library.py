"""Local library for reusable Qwen voice clone prompts."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VOICE_FILE_SUFFIX = ".voice.pt"
META_FILE_SUFFIX = ".voice.json"
VOICE_LIBRARY_VERSION = 1


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
        "ref_audio": ref_audio,
        "ref_audio_sha256": (
            _hash_file(ref_audio_path) if ref_audio_path.exists() else ""
        ),
        "ref_text": ref_text,
    }
    if extra:
        metadata.update(extra)
    return metadata


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
    )


def load_voice_prompt(prompt_path: Path, map_location: str | None = None) -> Any:
    """Load a saved Qwen voice clone prompt from disk."""
    import torch

    try:
        return torch.load(
            prompt_path,
            map_location=map_location,
            weights_only=False,
        )
    except TypeError:
        return torch.load(prompt_path, map_location=map_location)


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

        voice_id = sanitize_voice_id(str(metadata.get("id") or metadata_path.stem))
        prompt_file = str(metadata.get("prompt_file") or f"{voice_id}{VOICE_FILE_SUFFIX}")
        prompt_path = library_dir / prompt_file
        if not prompt_path.exists():
            fallback = metadata_path.with_suffix("").with_suffix(VOICE_FILE_SUFFIX)
            if fallback.exists():
                prompt_path = fallback
                voice_id = sanitize_voice_id(fallback.name.removesuffix(VOICE_FILE_SUFFIX))
            else:
                continue

        voices.append(
            SavedVoice(
                voice_id=voice_id,
                name=str(metadata.get("name") or voice_id),
                prompt_path=prompt_path,
                metadata_path=metadata_path,
                created_at=str(metadata.get("created_at") or ""),
                model=str(metadata.get("model") or ""),
                ref_audio=str(metadata.get("ref_audio") or ""),
                ref_audio_sha256=str(metadata.get("ref_audio_sha256") or ""),
                speech_rate=float(metadata.get("speech_rate") or 1.0),
            )
        )
    return sorted(voices, key=lambda item: item.name.lower())


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
            return voice.prompt_path
    raise FileNotFoundError(
        f"Saved voice '{value}' not found in {library_dir}."
    )
