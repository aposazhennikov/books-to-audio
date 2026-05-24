from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from book_normalizer.models.book import Book, Chapter, Metadata, Paragraph

QtWidgets = pytest.importorskip("PyQt6.QtWidgets")
QtCore = pytest.importorskip("PyQt6.QtCore")
QApplication = QtWidgets.QApplication
roles_page = pytest.importorskip("book_normalizer.gui.pages.roles_page")
RolesPage = roles_page.RolesPage


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


class _Signal:
    def __init__(self) -> None:
        self.callbacks = []

    def connect(self, callback):  # noqa: ANN001
        self.callbacks.append(callback)

    def emit(self, *args):  # noqa: ANN002
        for callback in self.callbacks:
            callback(*args)


def _sample_book() -> Book:
    return Book(
        metadata=Metadata(language="ru"),
        chapters=[
            Chapter(
                index=0,
                paragraphs=[
                    Paragraph(raw_text="Привет.", normalized_text="Привет."),
                ],
            )
        ],
    )


def test_roles_page_runs_llm_segments_and_writes_inventory(
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
                            "language": "ru",
                            "role": "female",
                            "speaker": "Маргарита",
                            "character_description": "Смелая.",
                            "is_dialogue": True,
                            "emotion": "joyful",
                            "intonation": "joyful",
                            "text": "Привет.",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            self.finished.emit(str(manifest_path))

    monkeypatch.setattr(roles_page, "ExportSegmentsWorker", _FakeWorker)
    page = RolesPage()
    qtbot.addWidget(page)
    page.set_book(_sample_book(), tmp_path)

    emitted: list[tuple[str, str]] = []
    page.segments_ready.connect(lambda segments, roles: emitted.append((segments, roles)))
    qtbot.mouseClick(page._btn_extract, QtCore.Qt.MouseButton.LeftButton)

    assert captured["speaker_mode"] == "llm"
    assert captured["output_dir"] == tmp_path
    assert emitted == [
        (
            str(tmp_path / "segments_manifest.json"),
            str(tmp_path / "roles_manifest.json"),
        )
    ]
    inventory = json.loads((tmp_path / "roles_manifest.json").read_text(encoding="utf-8"))
    assert inventory["roles"][0]["display_name"] == "Маргарита"
    assert page._table.rowCount() == 1

    page.deleteLater()


def test_roles_page_labels_llm_fields_and_shows_endpoint_start(qapp) -> None:
    page = RolesPage()

    assert page._llm_endpoint_label.text()
    assert page._llm_model_label.text()
    assert page._llm_endpoint.cursorPosition() == 0
    assert page._llm_model.cursorPosition() == 0
    assert page._llm_endpoint.maximumWidth() <= 260
    assert page._btn_extract.maximumWidth() <= 340

    page.deleteLater()
