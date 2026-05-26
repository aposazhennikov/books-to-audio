from __future__ import annotations

import json
import wave
from pathlib import Path

from click.testing import CliRunner

import book_normalizer.cli as cli
from book_normalizer.tts.asr_qa import AsrTranscript


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
