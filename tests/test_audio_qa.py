"""Tests for synthesized audio QA checks."""

from __future__ import annotations

import wave
from pathlib import Path

from book_normalizer.tts.audio_qa import run_audio_qa


def _write_wav(path: Path, frames: bytes, sample_rate: int = 24000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(frames)


def test_audio_qa_reports_missing_audio_file(tmp_path: Path) -> None:
    manifest = {
        "version": 2,
        "chapters": [
            {
                "chapter_index": 0,
                "chunks": [
                    {
                        "chunk_index": 0,
                        "synthesized": True,
                        "audio_file": str(tmp_path / "x.wav"),
                    }
                ],
            }
        ],
    }

    result = run_audio_qa(manifest)

    assert any(issue.kind == "missing_audio_file" for issue in result.issues)


def test_audio_qa_detects_silence(tmp_path: Path) -> None:
    wav_path = tmp_path / "silent.wav"
    _write_wav(wav_path, b"\x00\x00" * 24000)
    manifest = {
        "version": 2,
        "chapters": [
            {
                "chapter_index": 0,
                "chunks": [
                    {
                        "chunk_index": 0,
                        "synthesized": True,
                        "audio_file": str(wav_path),
                        "text": "короткий текст",
                    }
                ],
            }
        ],
    }

    result = run_audio_qa(manifest)

    assert result.checked_files == 1
    assert any(issue.kind == "mostly_silent" for issue in result.issues)


def test_audio_qa_passes_basic_non_silent_file(tmp_path: Path) -> None:
    wav_path = tmp_path / "ok.wav"
    _write_wav(wav_path, b"\x10\x00" * 24000)
    manifest = {
        "version": 2,
        "chapters": [
            {
                "chapter_index": 0,
                "chunks": [
                    {
                        "chunk_index": 0,
                        "synthesized": True,
                        "audio_file": str(wav_path),
                        "text": "Это небольшой фрагмент текста для проверки длительности.",
                    }
                ],
            }
        ],
    }

    result = run_audio_qa(manifest, min_seconds_per_100_chars=0.1)

    assert result.checked_files == 1
    assert not any(issue.severity == "error" for issue in result.issues)
