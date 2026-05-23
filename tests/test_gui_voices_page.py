from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from book_normalizer.llm.model_router import PRIMARY_QWEN3_MODEL
from book_normalizer.models.book import Book, Chapter, Metadata, Paragraph

QtWidgets = pytest.importorskip("PyQt6.QtWidgets")
QtCore = pytest.importorskip("PyQt6.QtCore")
QApplication = QtWidgets.QApplication
voices_page = pytest.importorskip("book_normalizer.gui.pages.voices_page")
VoicesPage = voices_page.VoicesPage


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_voices_page_defaults_to_llm_when_normalization_used(qapp, tmp_path) -> None:
    book = Book(
        metadata=Metadata(
            language="kk",
            extra={
                "llm_processing_enabled": True,
                "llm_model_candidates": [PRIMARY_QWEN3_MODEL, "fallback"],
            },
        ),
    )
    page = VoicesPage()

    page.set_book(book, tmp_path)

    assert page._speaker_mode.currentData() == "llm"
    assert page._llm_model.text() == PRIMARY_QWEN3_MODEL
    page.deleteLater()


class _Signal:
    def __init__(self) -> None:
        self.callbacks = []

    def connect(self, callback):  # noqa: ANN001
        self.callbacks.append(callback)

    def emit(self, *args):  # noqa: ANN002
        for callback in self.callbacks:
            callback(*args)


def _sample_book(language: str = "en") -> Book:
    return Book(
        metadata=Metadata(language=language),
        chapters=[
            Chapter(
                index=0,
                paragraphs=[
                    Paragraph(
                        raw_text="Hello there.",
                        normalized_text="Hello there.",
                        index_in_chapter=0,
                    ),
                ],
            )
        ],
    )


def test_voices_page_detect_save_and_build_buttons_use_real_manifest_flow(
    qapp,
    qtbot,
    tmp_path: Path,
    monkeypatch,
) -> None:
    captured: dict = {}

    class _FakeWorker:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.progress = _Signal()
            self.finished = _Signal()
            self.error = _Signal()

        def start(self) -> None:
            manifest_path = captured["output_dir"] / "segments_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    [
                        {
                            "segment_index": 0,
                            "chapter_index": 0,
                            "language": "en",
                            "is_dialogue": False,
                            "role": "narrator",
                            "voice_id": "narrator_calm",
                            "intonation": "calm",
                            "text": "Hello there.",
                            "pause_after_ms": 1500,
                            "boundary_after": "chapter",
                        }
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            self.finished.emit(str(manifest_path))

    monkeypatch.setattr(voices_page, "ExportSegmentsWorker", _FakeWorker)
    page = VoicesPage()
    qtbot.addWidget(page)
    page.set_book(_sample_book("en"), tmp_path)

    qtbot.mouseClick(page._btn_detect, QtCore.Qt.MouseButton.LeftButton)

    assert captured["speaker_mode"] == "heuristic"
    assert page._manifest_path == tmp_path / "segments_manifest.json"
    assert page._voice_table.get_segments()[0]["text"] == "Hello there."
    assert page._btn_save.isEnabled()
    assert page._btn_build.isEnabled()

    page._voice_table._segment_editor.setPlainText("Edited line.")
    qtbot.mouseClick(page._btn_save, QtCore.Qt.MouseButton.LeftButton)
    saved = json.loads((tmp_path / "segments_manifest.json").read_text(encoding="utf-8"))
    assert saved[0]["text"] == "Edited line."

    built_paths: list[str] = []
    page.chunks_built.connect(built_paths.append)
    qtbot.mouseClick(page._btn_build, QtCore.Qt.MouseButton.LeftButton)

    chunks_path = tmp_path / "chunks_manifest_v2.json"
    assert built_paths == [str(chunks_path)]
    manifest = json.loads(chunks_path.read_text(encoding="utf-8"))
    assert manifest["language"] == "en"
    assert manifest["chapters"][0]["chunks"][0]["text"] == "Edited line."
