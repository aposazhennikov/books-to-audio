from __future__ import annotations

from pathlib import Path

import pytest

from book_normalizer.tts.manifest_audio_paths import (
    ManifestAudioPathError,
    resolve_manifest_audio_path,
)


def test_resolve_manifest_audio_path_accepts_relative_inside_manifest_dir(tmp_path: Path) -> None:
    manifest_path = tmp_path / "book" / "chunks_manifest_v2.json"
    audio_path = manifest_path.parent / "audio_chunks" / "chapter_001" / "chunk.wav"

    resolved = resolve_manifest_audio_path(
        "audio_chunks/chapter_001/chunk.wav",
        manifest_path,
    )

    assert resolved == audio_path.resolve(strict=False)


def test_resolve_manifest_audio_path_accepts_absolute_inside_manifest_dir(tmp_path: Path) -> None:
    manifest_path = tmp_path / "book" / "chunks_manifest_v2.json"
    audio_path = manifest_path.parent / "audio_chunks" / "chapter_001" / "chunk.wav"

    resolved = resolve_manifest_audio_path(str(audio_path), manifest_path)

    assert resolved == audio_path.resolve(strict=False)


def test_resolve_manifest_audio_path_rejects_relative_escape(tmp_path: Path) -> None:
    manifest_path = tmp_path / "book" / "chunks_manifest_v2.json"

    with pytest.raises(ManifestAudioPathError, match="outside manifest directory"):
        resolve_manifest_audio_path("../outside.wav", manifest_path)


def test_resolve_manifest_audio_path_rejects_absolute_outside_manifest_dir(tmp_path: Path) -> None:
    manifest_path = tmp_path / "book" / "chunks_manifest_v2.json"
    outside_path = tmp_path / "outside.wav"

    with pytest.raises(ManifestAudioPathError, match="outside manifest directory"):
        resolve_manifest_audio_path(str(outside_path), manifest_path)


def test_resolve_manifest_audio_path_rejects_relative_without_manifest_path() -> None:
    with pytest.raises(ManifestAudioPathError, match="without a manifest path"):
        resolve_manifest_audio_path("audio_chunks/chunk.wav", None)
