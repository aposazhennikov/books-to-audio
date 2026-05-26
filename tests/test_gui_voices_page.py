from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from book_normalizer.gui.i18n import set_language
from book_normalizer.llm.model_router import PRIMARY_QWEN3_MODEL
from book_normalizer.models.book import Book, Chapter, Metadata, Paragraph
from tests.gui.helpers import render_widget

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
    page._build_tts_chunks()

    chunks_path = tmp_path / "chunks_manifest_v2.json"
    assert built_paths == [str(chunks_path)]
    manifest = json.loads(chunks_path.read_text(encoding="utf-8"))
    assert manifest["language"] == "en"
    assert manifest["chapters"][0]["chunks"][0]["text"] == "Edited line."


def test_voices_page_uses_compact_centered_chunk_size_field(qapp) -> None:
    page = VoicesPage()

    assert page._chunk_size.alignment() & QtCore.Qt.AlignmentFlag.AlignHCenter
    assert page._chunk_size.alignment() & QtCore.Qt.AlignmentFlag.AlignVCenter
    assert page._chunk_size.lineEdit().alignment() & QtCore.Qt.AlignmentFlag.AlignHCenter
    assert page._chunk_size.lineEdit().alignment() & QtCore.Qt.AlignmentFlag.AlignVCenter
    assert page._chunk_size.buttonSymbols() == QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons
    assert 38 <= page._chunk_size.height() <= 42
    assert page._chunk_size.width() <= 160

    page.deleteLater()


def test_chunk_page_internal_tabs_are_chunk_focused(qapp) -> None:
    set_language("ru")
    page = VoicesPage()
    render_widget(page, 1180, 760, scale=1.0)

    assert page._top_tabs.tabText(0) == "Ревью чанков"
    assert page._top_tabs.tabText(1) == "Пресеты голосов"
    assert page._speaker_mode_label.text() == "Источник сегментов:"
    assert page._speaker_mode.currentText() == "Правила: быстрое разбиение"
    assert page._btn_detect.text() == "Пересобрать сегменты"
    assert "локальный черновик" in page._speaker_mode_hint.text()
    assert "\n" not in page._speaker_mode_hint.text()
    assert page._speaker_mode_hint.text().endswith("кавычкам.")
    assert "реплик" not in page._speaker_mode_hint.text()
    assert "Библиотека голосов" not in {
        page._top_tabs.tabText(0),
        page._top_tabs.tabText(1),
        page._preview_title.text(),
    }

    page.deleteLater()


def test_chunk_page_inline_mode_hints_are_short_and_translated(qapp) -> None:
    page = VoicesPage()

    for code in ("ru", "en", "zh", "kk", "uz"):
        set_language(code)
        page.retranslate()
        for mode in ("heuristic", "llm", "manual"):
            page._speaker_mode.setCurrentIndex(page._speaker_mode.findData(mode))
            hint = page._speaker_mode_hint.text()
            assert hint.strip()
            assert "\n" not in hint
            assert len(hint) <= 90
            assert "??" not in hint
            assert "wsl" not in hint.lower()

    page.deleteLater()
    set_language("ru")


def test_voice_table_hides_empty_editor_and_compacts_columns(qapp) -> None:
    page = VoicesPage()
    render_widget(page, 760, 520, scale=1.45)

    table = page._voice_table
    assert table._editor_tabs.isHidden()
    assert table._chapter_nav_panel.isHidden()
    assert table._preset_toolbar_panel.isHidden()
    assert table._quick_apply_panel.isHidden()
    assert table._table.horizontalScrollBarPolicy() == QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert table._table.verticalScrollBarPolicy() == QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
    assert table._segment_editor.verticalScrollBarPolicy() == QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
    assert table._full_text_editor.verticalScrollBarPolicy() == QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
    for column in (0, 1, 2, 6, 7, 8):
        assert table._table.isColumnHidden(column)

    table.set_segments(
        [
            {
                "segment_index": index,
                "chapter_index": index // 6,
                "role": "narrator",
                "voice_id": "narrator_calm",
                "intonation": "calm",
                "text": f"Editable segment {index}.",
            }
            for index in range(18)
        ]
    )
    render_widget(page, 760, 520, scale=1.45)

    assert table._editor_tabs.isVisible()
    assert table._chapter_nav_panel.isVisible()
    assert table._preset_toolbar_panel.isVisible()
    assert table._quick_apply_panel.isVisible()
    assert table._table.verticalScrollBar().maximum() > 0
    assert table._table.verticalScrollBar().isVisible()
    assert table._btn_prev_segment.isVisible()
    assert table._btn_next_segment.isVisible()
    assert table._table.viewport().height() >= table._table.verticalHeader().defaultSectionSize()
    role_combo = table._table.cellWidget(0, 4)
    voice_combo = table._table.cellWidget(0, 5)
    assert role_combo is not None
    assert voice_combo is not None
    assert role_combo.geometry().bottom() <= table._table.viewport().rect().bottom()
    assert voice_combo.geometry().bottom() <= table._table.viewport().rect().bottom()
    assert not table._table.isColumnHidden(3)
    assert not table._table.isColumnHidden(4)
    assert not table._table.isColumnHidden(5)

    page.deleteLater()


def test_voice_table_exposes_editable_character_roles(qapp, qtbot) -> None:
    page = VoicesPage()
    qtbot.addWidget(page)
    page._voice_table.set_segments(
        [
            {
                "segment_index": 0,
                "chapter_index": 0,
                "role": "female",
                "speaker": "Маргарита",
                "character_description": "Решительная.",
                "emotion": "sad",
                "voice_id": "female_warm",
                "intonation": "sad",
                "text": "Я вернусь.",
            },
        ]
    )

    role_combo = page._voice_table._table.cellWidget(0, 4)
    assert isinstance(role_combo, QtWidgets.QComboBox)
    assert role_combo.isEditable()
    assert role_combo.currentText() == "Маргарита"

    role_combo.setCurrentText("Маргарита-Грустная")
    role_combo.lineEdit().editingFinished.emit()

    segment = page._voice_table.get_segments()[0]
    assert segment["role"] == "female"
    assert segment["speaker"] == "Маргарита-Грустная"
    assert segment["character"] == "Маргарита-Грустная"
    assert segment["role_display_name"] == "Маргарита-Грустная"
    page.deleteLater()


def test_voice_table_voice_changes_keep_llm_character_role(qapp, qtbot) -> None:
    page = VoicesPage()
    qtbot.addWidget(page)
    page._voice_table.set_segments(
        [
            {
                "segment_index": 0,
                "chapter_index": 0,
                "role": "female",
                "speaker": "Маргарита",
                "character": "Маргарита",
                "role_display_name": "Маргарита",
                "is_dialogue": True,
                "voice_id": "female_warm",
                "intonation": "sad",
                "text": "Я вернусь.",
            },
        ]
    )

    voice_combo = page._voice_table._table.cellWidget(0, 5)
    assert isinstance(voice_combo, QtWidgets.QComboBox)
    voice_combo.setCurrentIndex(voice_combo.findData("narrator_calm"))

    segment = page._voice_table.get_segments()[0]
    assert segment["voice_id"] == "narrator_calm"
    assert segment["role"] == "female"
    assert segment["speaker"] == "Маргарита"
    assert segment["character"] == "Маргарита"
    assert segment["role_display_name"] == "Маргарита"
    assert segment["is_dialogue"] is True
    page.deleteLater()


def test_voice_preview_tab_hides_scrollbar_but_keeps_content_scrollable(qapp) -> None:
    page = VoicesPage()
    page._top_tabs.setCurrentIndex(1)
    render_widget(page, 760, 520, scale=1.45)

    scroll = page.findChild(QtWidgets.QScrollArea, "voicePreviewScroll")
    assert scroll is not None
    assert scroll.verticalScrollBarPolicy() == QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert scroll.horizontalScrollBarPolicy() == QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert not scroll.verticalScrollBar().isVisible()
    assert not scroll.horizontalScrollBar().isVisible()
    assert page._voice_preview._phrase_input.verticalScrollBarPolicy() == QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert page._voice_preview._phrase_input.horizontalScrollBarPolicy() == QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert scroll.widget() is page._voice_preview
    assert scroll.verticalScrollBar().maximum() > 0
    assert scroll.widget().sizeHint().height() > scroll.viewport().height()

    page.deleteLater()


def test_voice_table_filters_chapters_and_restores_deleted_segments(qapp, qtbot) -> None:
    page = VoicesPage()
    qtbot.addWidget(page)
    page._voice_table.set_segments(
        [
            {
                "segment_index": 0,
                "chapter_index": 0,
                "role": "narrator",
                "voice_id": "narrator_calm",
                "intonation": "calm",
                "text": "Keep me.",
            },
            {
                "segment_index": 1,
                "chapter_index": 1,
                "role": "narrator",
                "voice_id": "narrator_calm",
                "intonation": "calm",
                "text": "Delete me.",
            },
        ]
    )

    assert page._voice_table._chapter_filter.count() == 3
    page._voice_table._chapter_filter.setCurrentIndex(
        page._voice_table._chapter_filter.findData(1)
    )
    assert page._voice_table._table.rowCount() == 2
    assert page._voice_table._table.isRowHidden(0)
    assert not page._voice_table._table.isRowHidden(1)
    assert page._voice_table._table.item(1, 3).text() == "Delete me."
    assert page._voice_table._current_row() == 1

    qtbot.mouseClick(page._voice_table._btn_segment_delete, QtCore.Qt.MouseButton.LeftButton)
    assert page._voice_table.get_segments()[1]["deleted"] is True
    assert [seg["text"] for seg in page._voice_table.get_active_segments()] == ["Keep me."]

    qtbot.mouseClick(page._voice_table._btn_segment_restore, QtCore.Qt.MouseButton.LeftButton)
    assert page._voice_table.get_segments()[1]["deleted"] is False
    assert len(page._voice_table.get_active_segments()) == 2

    page.deleteLater()


def test_voice_table_chapter_filter_reuses_existing_rows(qapp, qtbot) -> None:
    page = VoicesPage()
    qtbot.addWidget(page)
    segments = [
        {
            "segment_index": index,
            "chapter_index": index // 40,
            "role": "narrator",
            "voice_id": "narrator_calm",
            "intonation": "calm",
            "text": f"Segment {index}.",
        }
        for index in range(120)
    ]
    page._voice_table.set_segments(segments)
    original_widget = page._voice_table._table.cellWidget(0, 5)

    page._voice_table._chapter_filter.setCurrentIndex(
        page._voice_table._chapter_filter.findData(1)
    )

    assert page._voice_table._table.rowCount() == len(segments)
    assert page._voice_table._table.cellWidget(0, 5) is original_widget
    assert page._voice_table._table.isRowHidden(0)
    assert not page._voice_table._table.isRowHidden(40)
    assert page._voice_table._current_row() == 40

    page.deleteLater()


def test_voices_page_builds_chunks_without_deleted_segments(qapp, qtbot, tmp_path) -> None:
    page = VoicesPage()
    qtbot.addWidget(page)
    page.set_book(_sample_book("en"), tmp_path)
    page._voice_table.set_segments(
        [
            {
                "segment_index": 0,
                "chapter_index": 0,
                "language": "en",
                "role": "narrator",
                "speaker": "Author",
                "voice_id": "narrator_calm",
                "intonation": "calm",
                "text": "Useful text.",
            },
            {
                "segment_index": 1,
                "chapter_index": 0,
                "language": "en",
                "role": "narrator",
                "voice_id": "narrator_calm",
                "intonation": "calm",
                "text": "Publisher junk.",
                "deleted": True,
                "excluded_from_tts": True,
            },
        ]
    )

    page._build_tts_chunks()

    manifest = json.loads((tmp_path / "chunks_manifest_v2.json").read_text(encoding="utf-8"))
    chunk = manifest["chapters"][0]["chunks"][0]
    chunk_text = chunk["text"]
    assert chunk_text == "Useful text."
    assert chunk["speaker"] == "Author"
