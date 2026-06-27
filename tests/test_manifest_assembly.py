"""Tests for v2 manifest-based audio assembly."""

from __future__ import annotations

import json
import wave
from pathlib import Path

import pytest

from book_normalizer.tts.manifest_assembly import assemble_from_manifest, load_manifest_v2


def _write_wav(path: Path, frames: int = 1200, sample_rate: int = 24000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x01\x00" * frames)


def test_assemble_from_manifest_preserves_manifest_order(tmp_path: Path) -> None:
    wav1 = tmp_path / "audio_chunks" / "chapter_001" / "chunk_001_narrator.wav"
    wav2 = tmp_path / "audio_chunks" / "chapter_001" / "chunk_002_men.wav"
    _write_wav(wav1, frames=100)
    _write_wav(wav2, frames=100)
    manifest = {
        "version": 2,
        "chapters": [
            {
                "chapter_index": 0,
                "chunks": [
                    {"chunk_index": 0, "voice": "narrator", "synthesized": True, "audio_file": str(wav1)},
                    {"chunk_index": 1, "voice": "male", "synthesized": True, "audio_file": str(wav2)},
                ],
            }
        ],
    }

    results = assemble_from_manifest(
        manifest,
        tmp_path,
        pause_same_voice_ms=0,
        pause_voice_change_ms=100,
        manifest_path=tmp_path / "chunks_manifest_v2.json",
    )

    assert results[0].chunks == 2
    out = tmp_path / "chapter_001.wav"
    assert out.exists()
    with wave.open(str(out), "rb") as wav:
        # 100 + 100 frames plus 100ms pause at 24kHz.
        assert wav.getnframes() == 2600


def test_assemble_from_loaded_manifest_resolves_relative_audio_from_manifest_dir(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "book"
    wav_path = project_dir / "audio_chunks" / "chapter_001" / "chunk_001_narrator.wav"
    _write_wav(wav_path, frames=100)
    manifest_path = project_dir / "chunks_manifest_v2.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "version": 2,
                "chapters": [
                    {
                        "chapter_index": 0,
                        "chunks": [
                            {
                                "chunk_index": 0,
                                "voice": "narrator",
                                "synthesized": True,
                                "audio_file": "audio_chunks/chapter_001/chunk_001_narrator.wav",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    manifest = load_manifest_v2(manifest_path)
    results = assemble_from_manifest(manifest, tmp_path / "assembled", pause_same_voice_ms=0)

    assert results[0].chunks == 1
    assert results[0].missing == 0
    assert (tmp_path / "assembled" / "chapter_001.wav").exists()


def test_assemble_from_manifest_skips_missing_files_when_not_strict(tmp_path: Path) -> None:
    manifest = {
        "version": 2,
        "chapters": [
            {
                "chapter_index": 0,
                "chunks": [
                    {
                        "chunk_index": 0,
                        "voice": "narrator",
                        "synthesized": True,
                        "audio_file": str(tmp_path / "missing.wav"),
                    },
                ],
            }
        ],
    }

    results = assemble_from_manifest(
        manifest,
        tmp_path,
        strict_missing=False,
        manifest_path=tmp_path / "chunks_manifest_v2.json",
    )

    assert results[0].skipped is True
    assert results[0].missing == 1


def test_assemble_from_manifest_skips_excluded_chunks_even_with_stale_audio(
    tmp_path: Path,
) -> None:
    keep = tmp_path / "audio_chunks" / "chapter_001" / "chunk_001_narrator.wav"
    deleted = tmp_path / "audio_chunks" / "chapter_001" / "chunk_002_narrator.wav"
    _write_wav(keep, frames=100)
    _write_wav(deleted, frames=100)
    manifest = {
        "version": 2,
        "chapters": [
            {
                "chapter_index": 0,
                "chunks": [
                    {
                        "chunk_index": 0,
                        "voice": "narrator",
                        "synthesized": True,
                        "audio_file": str(keep),
                    },
                    {
                        "chunk_index": 1,
                        "voice": "narrator",
                        "synthesized": True,
                        "audio_file": str(deleted),
                        "deleted": True,
                        "excluded_from_tts": True,
                    },
                ],
            }
        ],
    }

    results = assemble_from_manifest(
        manifest,
        tmp_path,
        pause_same_voice_ms=0,
        manifest_path=tmp_path / "chunks_manifest_v2.json",
    )

    assert results[0].chunks == 1
    with wave.open(str(tmp_path / "chapter_001.wav"), "rb") as wav:
        assert wav.getnframes() == 100


def test_assemble_from_manifest_writes_compatible_chapter_sidecar(
    tmp_path: Path,
    monkeypatch,
) -> None:
    wav_path = tmp_path / "audio_chunks" / "chapter_001" / "chunk_001_narrator.wav"
    _write_wav(wav_path, frames=100)
    manifest = {
        "version": 2,
        "chapters": [
            {
                "chapter_index": 0,
                "chunks": [
                    {"chunk_index": 0, "voice": "narrator", "synthesized": True, "audio_file": str(wav_path)},
                ],
            }
        ],
    }

    def fake_export(source: Path, output=None, **_kwargs):  # noqa: ANN001, ANN202
        target = output or source.with_suffix(".MP3")
        target.write_bytes(b"mp3")
        return target

    monkeypatch.setattr("book_normalizer.tts.manifest_assembly.export_compatible_mp3", fake_export)

    results = assemble_from_manifest(
        manifest,
        tmp_path,
        pause_same_voice_ms=0,
        manifest_path=tmp_path / "chunks_manifest_v2.json",
    )

    assert results[0].compatible_output_path == tmp_path / "chapter_001.MP3"
    assert (tmp_path / "chapter_001.MP3").read_bytes() == b"mp3"


def test_assemble_from_manifest_fails_on_audio_path_escape(tmp_path: Path) -> None:
    manifest = {
        "version": 2,
        "chapters": [
            {
                "chapter_index": 0,
                "chunks": [
                    {
                        "chunk_index": 0,
                        "voice": "narrator",
                        "synthesized": True,
                        "audio_file": "../outside.wav",
                    },
                ],
            }
        ],
    }

    with pytest.raises(ValueError, match="Unsafe manifest audio_file"):
        assemble_from_manifest(
            manifest,
            tmp_path,
            manifest_path=tmp_path / "book" / "chunks_manifest_v2.json",
        )
