from __future__ import annotations

import json
import os
import wave
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tests.gui.helpers import assert_layout_sane, render_widget
from tests.gui.helpers import qapp as make_qapp

QtCore = pytest.importorskip("PyQt6.QtCore")
QtWidgets = pytest.importorskip("PyQt6.QtWidgets")
assembly_page = pytest.importorskip("book_normalizer.gui.pages.assembly_page")
AssemblyPage = assembly_page.AssemblyPage
AssemblyWorker = assembly_page.AssemblyWorker


@pytest.fixture
def qapp():
    return make_qapp()


def _write_wav(path: Path, *, frames: int = 240, sample_rate: int = 24000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x01\x00" * frames)


def _run_worker(worker: object) -> tuple[list[str], list[str], list[str]]:
    progress: list[str] = []
    finished: list[str] = []
    errors: list[str] = []
    worker.progress.connect(progress.append)
    worker.finished.connect(finished.append)
    worker.error.connect(errors.append)
    worker.run()
    return progress, finished, errors


def test_assembly_worker_uses_manifest_api_without_subprocess(tmp_path: Path) -> None:
    source = Path("src/book_normalizer/gui/pages/assembly_page.py").read_text(
        encoding="utf-8"
    )
    assert "subprocess" not in source
    assert "--audio-dir" not in source

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
                                "text": "Hello.",
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
    worker = AssemblyWorker(
        audio_dir=tmp_path / "audio_chunks",
        output_dir=tmp_path,
        pause_same=0,
        pause_change=0,
        manifest_path=manifest_path,
    )

    progress, finished, errors = _run_worker(worker)

    assert errors == []
    assert progress
    assert len(finished) == 1
    assert "chapter_001.wav" in finished[0]
    assert "1 chunks ->" in finished[0]
    assert (tmp_path / "chapter_001.wav").exists()


def test_assembly_worker_supports_legacy_synthesis_manifest(tmp_path: Path) -> None:
    output_dir = tmp_path / "book"
    wav_path = output_dir / "audio_chunks" / "chapter_001" / "chunk_001_narrator.wav"
    _write_wav(wav_path)
    (output_dir / "synthesis_manifest.json").write_text(
        json.dumps(
            [
                {
                    "chapter_index": 0,
                    "chunk_index": 0,
                    "voice_id": "narrator",
                    "role": "narrator",
                    "text_len": 6,
                    "file": "audio_chunks/chapter_001/chunk_001_narrator.wav",
                }
            ]
        ),
        encoding="utf-8",
    )
    worker = AssemblyWorker(
        audio_dir=output_dir / "audio_chunks",
        output_dir=output_dir,
        pause_same=0,
        pause_change=0,
    )

    _progress, finished, errors = _run_worker(worker)

    assert errors == []
    assert len(finished) == 1
    assert "chapter_001" in finished[0]
    assert (output_dir / "audio_chapters" / "chapter_001.wav").exists()
    assert (output_dir / "full_book.wav").exists()


def test_assembly_worker_reports_no_wav_for_empty_legacy_folder(tmp_path: Path) -> None:
    output_dir = tmp_path / "empty"
    worker = AssemblyWorker(
        audio_dir=output_dir / "audio_chunks",
        output_dir=output_dir,
        pause_same=0,
        pause_change=0,
    )

    _progress, finished, errors = _run_worker(worker)

    assert errors == []
    assert finished == [f"No WAV chunks in {output_dir / 'audio_chunks'}"]


def test_assembly_page_uses_light_compact_numeric_controls(qapp) -> None:
    page = AssemblyPage()
    render_widget(page, 760, 520, scale=1.45)

    assert_layout_sane(page)
    assert "rgba(15,23,42" not in page._dir_label.styleSheet()
    assert "rgba(226,232,240" not in page._output_label.styleSheet()
    for spin in (page._pause_same, page._pause_change):
        assert spin.alignment() & QtCore.Qt.AlignmentFlag.AlignHCenter
        assert spin.alignment() & QtCore.Qt.AlignmentFlag.AlignVCenter
        assert spin.lineEdit().alignment() & QtCore.Qt.AlignmentFlag.AlignHCenter
        assert spin.lineEdit().alignment() & QtCore.Qt.AlignmentFlag.AlignVCenter
        assert spin.buttonSymbols() == QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons
        assert spin.width() <= 128
        assert spin.height() == 38

    page.close()
    page.deleteLater()
