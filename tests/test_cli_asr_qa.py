from __future__ import annotations

import json
import wave
from pathlib import Path

from click.testing import CliRunner

import book_normalizer.cli as cli
from book_normalizer.tts.asr_qa import AsrTranscript
from book_normalizer.tts.perceptual_qa import (
    PerceptualChunkResult,
    PerceptualQaResult,
)


class FakeFasterWhisperBackend:
    name = "fake-whisper"

    def __init__(self, model: str, **_kwargs: object) -> None:
        self.model = model

    def transcribe(self, audio_path: Path, *, language: str | None = None) -> AsrTranscript:
        return AsrTranscript(
            text="hello world",
            language="en",
            confidence=0.99,
            segments=[{"start": 0, "end": 1, "text": "hello world"}],
            duration_seconds=1.0,
        )


def _write_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b"\x01\x00" * 24000)


def test_audio_qa_cli_runs_asr_writes_report_and_manifest(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import book_normalizer.tts.asr_qa as asr_qa

    monkeypatch.setattr(asr_qa, "FasterWhisperBackend", FakeFasterWhisperBackend)
    wav_path = tmp_path / "audio_chunks" / "chapter_001" / "chunk_001_narrator.wav"
    _write_wav(wav_path)
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": 2,
                "language": "en",
                "chapters": [
                    {
                        "chapter_index": 0,
                        "chunks": [
                            {
                                "chunk_index": 0,
                                "voice": "narrator",
                                "voice_id": "narrator_calm",
                                "text": "Hello world.",
                                "synthesized": True,
                                "audio_file": str(wav_path),
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    report_path = tmp_path / "qa.json"

    result = CliRunner().invoke(
        cli.main,
        [
            "audio-qa",
            str(manifest_path),
            "--asr",
            "--asr-model",
            "unit-small",
            "--report",
            str(report_path),
        ],
    )

    assert result.exit_code == 0, result.output
    report = json.loads(report_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    asr_block = manifest["chapters"][0]["chunks"][0]["asr_qa"]
    assert report["asr_qa"]["backend"] == "fake-whisper"
    assert report["asr_qa"]["status"] == "passed"
    assert asr_block["model"] == "unit-small"
    assert asr_block["status"] == "passed"
    assert manifest["chapters"][0]["chunks"][0]["synthesized"] is True


def test_audio_qa_cli_reset_bad_chunks_makes_failed_only_retry_possible(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import book_normalizer.tts.asr_qa as asr_qa

    monkeypatch.setattr(asr_qa, "FasterWhisperBackend", FakeFasterWhisperBackend)
    wav_path = tmp_path / "audio_chunks" / "chapter_001" / "chunk_001_narrator.wav"
    _write_wav(wav_path)
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest_path.write_text(
        json.dumps(
            {
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
                                "text": "Completely different expected text.",
                                "synthesized": True,
                                "audio_file": str(wav_path),
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli.main,
        [
            "audio-qa",
            str(manifest_path),
            "--asr",
            "--reset-bad-chunks",
            "--max-resynth-attempts",
            "2",
        ],
    )

    assert result.exit_code == 0, result.output
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    chunk = manifest["chapters"][0]["chunks"][0]
    assert chunk["asr_qa"]["status"] == "failed"
    assert chunk["failed"] is True
    assert chunk["synthesized"] is False
    assert chunk["audio_file"] is None
    assert chunk["resynthesis_attempt"] == 1
    assert str(wav_path) in chunk["rejected_audio_files"]


def test_audio_qa_cli_runs_perceptual_writes_report_and_manifest(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import book_normalizer.tts.perceptual_qa as perceptual_qa

    def fake_run_perceptual_qa(*_args, **_kwargs):  # noqa: ANN002
        chunk = PerceptualChunkResult(
            chapter_index=0,
            chunk_index=0,
            audio_file=str(wav_path),
            status="passed",
            scores={
                "nisqa-v2": {
                    "mos": 4.1,
                    "noisiness": 4.0,
                    "discontinuity": 4.0,
                    "coloration": 3.9,
                    "loudness": 4.2,
                },
                "mosnet": {"mos": 3.8},
            },
        )
        return PerceptualQaResult(
            backends=["nisqa-v2", "mosnet"],
            created_at="2026-01-01T00:00:00+00:00",
            chunks=[chunk],
        )

    monkeypatch.setattr(perceptual_qa, "run_perceptual_qa", fake_run_perceptual_qa)
    wav_path = tmp_path / "audio_chunks" / "chapter_001" / "chunk_001_narrator.wav"
    _write_wav(wav_path)
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest_path.write_text(
        json.dumps(
            {
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
                                "text": "Hello world.",
                                "synthesized": True,
                                "audio_file": str(wav_path),
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    report_path = tmp_path / "qa.json"

    result = CliRunner().invoke(
        cli.main,
        [
            "audio-qa",
            str(manifest_path),
            "--perceptual",
            "--report",
            str(report_path),
        ],
    )

    assert result.exit_code == 0, result.output
    report = json.loads(report_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    block = manifest["chapters"][0]["chunks"][0]["perceptual_qa"]
    assert report["perceptual_qa"]["status"] == "passed"
    assert block["scores"]["nisqa-v2"]["mos"] == 4.1
    assert block["scores"]["mosnet"]["mos"] == 3.8
