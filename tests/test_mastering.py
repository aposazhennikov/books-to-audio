from __future__ import annotations

import json
import wave
from pathlib import Path

import pytest

from book_normalizer.tts.mastering import master_manifest


def _write_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(b"\x01\x00" * 8000)


def _manifest(path: Path, wav_path: Path, *, status: str = "passed") -> None:
    path.write_text(
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
                                "artifact_qa": {"status": status},
                                "asr_qa": {"status": status},
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_master_manifest_blocks_non_passed_chunks(tmp_path: Path) -> None:
    wav_path = tmp_path / "audio_chunks" / "chapter_001" / "chunk_001_narrator.wav"
    _write_wav(wav_path)
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    _manifest(manifest_path, wav_path, status="warning")

    with pytest.raises(ValueError, match="Mastering blocked"):
        master_manifest(manifest_path, output_dir=tmp_path, output_format="mp3")


def test_master_manifest_runs_ffmpeg_and_writes_report(tmp_path: Path, monkeypatch) -> None:
    wav_path = tmp_path / "audio_chunks" / "chapter_001" / "chunk_001_narrator.wav"
    _write_wav(wav_path)
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    _manifest(manifest_path, wav_path)
    commands: list[list[str]] = []

    def fake_run(command, **_kwargs):  # noqa: ANN001, ANN202
        commands.append(command)
        Path(command[-1]).write_bytes(b"mastered")

    monkeypatch.setattr("book_normalizer.tts.mastering.subprocess.run", fake_run)

    result = master_manifest(
        manifest_path,
        output_dir=tmp_path,
        output_format="both",
        ffmpeg_bin="ffmpeg-test",
    )

    assert len(result.files) == 2
    assert commands[0][0] == "ffmpeg-test"
    assert "-af" in commands[0]
    assert "loudnorm=I=-18:TP=-1.5:LRA=11" in commands[0][commands[0].index("-af") + 1]
    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert len(report["files"]) == 2
