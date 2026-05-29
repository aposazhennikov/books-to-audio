from __future__ import annotations

import math
import wave
from pathlib import Path

from book_normalizer.tts.artifact_qa import (
    annotate_manifest_with_artifacts,
    run_artifact_qa,
)
from book_normalizer.tts.audio_smoothing import smooth_wav_silence
from book_normalizer.tts.quality_gate import split_problem_chunks_for_retry


def _write_wav(path: Path, samples: list[int], *, sample_rate: int = 8000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = b"".join(int(sample).to_bytes(2, "little", signed=True) for sample in samples)
        wav.writeframes(frames)


def _manifest(audio_path: Path, *, text: str = "hello world") -> dict:
    return {
        "version": 2,
        "language": "en",
        "chapters": [
            {
                "chapter_index": 0,
                "chunks": [
                    {
                        "chapter_index": 0,
                        "chunk_index": 0,
                        "voice_label": "narrator",
                        "text": text,
                        "synthesized": True,
                        "audio_file": str(audio_path),
                    }
                ],
            }
        ],
    }


def test_artifact_qa_detects_clipping_and_resets_bad_chunk(tmp_path: Path) -> None:
    audio_path = tmp_path / "chunk.wav"
    _write_wav(audio_path, [32767] * 8000)
    manifest = _manifest(audio_path)

    result = run_artifact_qa(manifest, manifest_path=tmp_path / "chunks_manifest_v2.json")
    annotate_manifest_with_artifacts(
        manifest,
        result,
        reset_bad_chunks=True,
        max_resynthesis_attempts=2,
    )

    chunk = manifest["chapters"][0]["chunks"][0]
    assert result.status == "failed"
    assert "clipping" in chunk["artifact_qa"]["issues"]
    assert chunk["failed"] is True
    assert chunk["synthesized"] is False
    assert chunk["audio_file"] is None
    assert chunk["resynthesis_attempt"] == 1
    assert str(audio_path) in chunk["rejected_audio_files"]


def test_artifact_qa_detects_silence(tmp_path: Path) -> None:
    audio_path = tmp_path / "silent.wav"
    _write_wav(audio_path, [0] * 8000)

    result = run_artifact_qa(_manifest(audio_path), manifest_path=tmp_path / "chunks_manifest_v2.json")

    chunk = result.chunks[0]
    assert chunk.status == "failed"
    assert {issue.kind for issue in chunk.issues} >= {"mostly_silent"}


def test_artifact_qa_detects_repeated_audio_windows(tmp_path: Path) -> None:
    audio_path = tmp_path / "repeat.wav"
    window = [
        int(math.sin(index / 8.0) * 5000)
        for index in range(800)
    ]
    _write_wav(audio_path, window * 12)

    result = run_artifact_qa(_manifest(audio_path), manifest_path=tmp_path / "chunks_manifest_v2.json")

    chunk = result.chunks[0]
    assert chunk.status == "failed"
    assert "repeated_audio" in {issue.kind for issue in chunk.issues}


def test_silence_smoothing_compresses_long_internal_gap(tmp_path: Path) -> None:
    audio_path = tmp_path / "gap.wav"
    tone = [int(math.sin(index / 8.0) * 5000) for index in range(800)]
    _write_wav(audio_path, tone + [0] * 16_000 + tone, sample_rate=8000)

    result = smooth_wav_silence(audio_path)

    assert result.changed is True
    assert result.max_silence_ms >= 1900
    assert result.removed_silence_ms >= 1400
    with wave.open(str(audio_path), "rb") as wav:
        assert wav.getnframes() < 800 + 16_000 + 800


def test_artifact_qa_warns_about_excessive_silence_gap(tmp_path: Path) -> None:
    audio_path = tmp_path / "gap.wav"
    tone = [int(math.sin(index / 8.0) * 5000) for index in range(800)]
    _write_wav(audio_path, tone + [0] * 16_000 + tone, sample_rate=8000)

    result = run_artifact_qa(_manifest(audio_path), manifest_path=tmp_path / "chunks_manifest_v2.json")

    chunk = result.chunks[0]
    assert chunk.status in {"warning", "failed"}
    assert "excessive_silence_gap" in {issue.kind for issue in chunk.issues}


def test_split_problem_chunks_for_retry_splits_repeated_long_chunk() -> None:
    text = (
        "This is a long sentence that can be split cleanly. "
        "This second half should become another chunk after repeated audio."
    ) * 3
    manifest = {
        "version": 2,
        "chapters": [
            {
                "chapter_index": 0,
                "chunks": [
                    {
                        "chapter_index": 0,
                        "chunk_index": 0,
                        "voice_label": "narrator",
                        "text": text,
                        "narrator": text,
                        "synthesized": False,
                        "failed": True,
                        "audio_file": None,
                        "resynthesis_attempt": 2,
                        "resynthesis_reason": "artifact_qa: repeated_audio",
                        "artifact_qa": {"status": "failed", "issues": ["repeated_audio"]},
                    }
                ],
            }
        ],
    }

    split_count = split_problem_chunks_for_retry(manifest)

    chunks = manifest["chapters"][0]["chunks"]
    assert split_count == 1
    assert len(chunks) == 2
    assert chunks[0]["chunk_index"] == 0
    assert chunks[1]["chunk_index"] == 1
    assert chunks[0]["text"]
    assert chunks[1]["text"]
    assert chunks[0]["resynthesis_split_count"] == 1
    assert chunks[1]["resynthesis_split_count"] == 1
