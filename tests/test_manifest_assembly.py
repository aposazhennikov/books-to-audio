"""Tests for v2 manifest-based audio assembly."""

from __future__ import annotations

import wave
from pathlib import Path

from book_normalizer.tts.manifest_assembly import assemble_from_manifest


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
    )

    assert results[0].chunks == 2
    out = tmp_path / "chapter_001.wav"
    assert out.exists()
    with wave.open(str(out), "rb") as wav:
        # 100 + 100 frames plus 100ms pause at 24kHz.
        assert wav.getnframes() == 2600


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

    results = assemble_from_manifest(manifest, tmp_path, strict_missing=False)

    assert results[0].skipped is True
    assert results[0].missing == 1
