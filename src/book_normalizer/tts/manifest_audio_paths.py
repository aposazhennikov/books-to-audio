"""Safe audio path resolution for v2 manifests."""

from __future__ import annotations

from pathlib import Path


class ManifestAudioPathError(ValueError):
    """Raised when a manifest audio_file path is missing or unsafe."""


def resolve_manifest_audio_path(audio_file: str, manifest_path: Path | None) -> Path:
    """Resolve a manifest audio_file path without falling back to cwd."""
    raw_audio_file = str(audio_file or "").strip()
    if not raw_audio_file:
        raise ManifestAudioPathError("Manifest audio_file is empty.")
    if manifest_path is None:
        raise ManifestAudioPathError(
            f"Cannot resolve manifest audio_file {raw_audio_file!r} without a manifest path."
        )

    manifest_dir = manifest_path.parent.resolve(strict=False)
    raw_path = Path(raw_audio_file)
    candidate = raw_path if raw_path.is_absolute() else manifest_dir / raw_path
    resolved = candidate.resolve(strict=False)

    try:
        resolved.relative_to(manifest_dir)
    except ValueError as exc:
        raise ManifestAudioPathError(
            f"Manifest audio_file {raw_audio_file!r} resolves outside manifest directory {manifest_dir}."
        ) from exc

    return resolved
