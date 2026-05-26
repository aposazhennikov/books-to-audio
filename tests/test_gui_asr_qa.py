from __future__ import annotations

import json
import os
import wave
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tests.gui.helpers import qapp as make_qapp

pytest.importorskip("PyQt6.QtCore")
pytest.importorskip("PyQt6.QtWidgets")

from book_normalizer.gui.pages.synthesis_page import SynthesisPage
from book_normalizer.gui.workers.tts_worker import AsrQaWorker
from book_normalizer.tts.asr_qa import AsrTranscript


@pytest.fixture
def qapp():
    return make_qapp()


class FakeFasterWhisperBackend:
    name = "fake"

    def __init__(self, model: str, **_kwargs: object) -> None:
        self.model = model

    def transcribe(self, audio_path: Path, *, language: str | None = None) -> AsrTranscript:
        return AsrTranscript(text="hello world", language="en", confidence=0.97)


def _write_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b"\x01\x00" * 24000)


def _write_manifest(path: Path, wav_path: Path) -> None:
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


def test_asr_qa_worker_writes_report_and_manifest(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import book_normalizer.tts.asr_qa as asr_qa

    monkeypatch.setattr(asr_qa, "FasterWhisperBackend", FakeFasterWhisperBackend)
    wav_path = tmp_path / "audio_chunks" / "chapter_001" / "chunk_001_narrator.wav"
    _write_wav(wav_path)
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    _write_manifest(manifest_path, wav_path)
    worker = AsrQaWorker(manifest_path, model="unit")
    finished: list[tuple[str, str, int, int, int]] = []
    errors: list[str] = []
    worker.finished.connect(lambda *args: finished.append(args))
    worker.error.connect(errors.append)

    worker.run()

    assert errors == []
    assert finished[0][1] == "passed"
    assert (tmp_path / "asr_qa_report.json").exists()
    assert (tmp_path / "asr_qa_report.diff.txt").exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["chapters"][0]["chunks"][0]["asr_qa"]["status"] == "passed"


def test_synthesis_page_filters_asr_warning_chunks(qapp, tmp_path: Path) -> None:
    wav_path = tmp_path / "audio_chunks" / "chapter_001" / "chunk_001_narrator.wav"
    _write_wav(wav_path)
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    data = {
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
                        "text": "Good chunk.",
                        "synthesized": True,
                        "audio_file": str(wav_path),
                        "asr_qa": {"schema_version": 1, "status": "passed"},
                    },
                    {
                        "chunk_index": 1,
                        "voice": "narrator",
                        "voice_id": "narrator_calm",
                        "text": "Needs review.",
                        "synthesized": True,
                        "audio_file": str(wav_path),
                        "asr_qa": {"schema_version": 1, "status": "warning"},
                    },
                ],
            }
        ],
    }
    manifest_path.write_text(json.dumps(data), encoding="utf-8")
    page = SynthesisPage()
    page.set_manifest(manifest_path, tmp_path)

    idx = page._asr_filter_combo.findData("bad")
    page._asr_filter_combo.setCurrentIndex(idx)
    page._refresh_test_chapter_combo()

    assert page._test_chunk_combo.count() == 1
    assert page._test_chunk_combo.currentData() == (0, 1)
    page._select_first_asr_issue()
    assert page._test_chunk_combo.currentData() == (0, 1)
    page.close()
    page.deleteLater()
