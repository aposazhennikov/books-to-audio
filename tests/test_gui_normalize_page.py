from __future__ import annotations

import os

import pytest

from tests.gui.helpers import assert_layout_sane, render_widget

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from book_normalizer.gui.i18n import SUPPORTED_LANGUAGES, set_language
from book_normalizer.models.book import Book, Chapter, Paragraph

QtWidgets = pytest.importorskip("PyQt6.QtWidgets")
QtCore = pytest.importorskip("PyQt6.QtCore")
QApplication = QtWidgets.QApplication
normalize_page = pytest.importorskip("book_normalizer.gui.pages.normalize_page")
_book_preview_lines = normalize_page._book_preview_lines
NormalizePage = normalize_page.NormalizePage


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_book_preview_default_is_not_truncated() -> None:
    book = Book(chapters=[
        Chapter(
            title="Long Chapter",
            index=0,
            paragraphs=[
                Paragraph(raw_text=f"Paragraph {idx}", normalized_text=f"Paragraph {idx}")
                for idx in range(35)
            ],
        ),
    ])

    raw_lines, norm_lines = _book_preview_lines(book)

    assert "Paragraph 34" in raw_lines
    assert norm_lines == raw_lines


def test_normalize_page_hides_ocr_help_until_pdf_selected(qapp) -> None:
    page = NormalizePage()

    assert page._ocr_mode_label_wrap.isHidden()
    assert page._ocr_dpi_label_wrap.isHidden()
    assert page._ocr_psm_label_wrap.isHidden()

    page._selected_path = "book.fb2"
    page._update_ocr_visibility()

    assert page._ocr_mode_label_wrap.isHidden()
    assert page._ocr_dpi_label_wrap.isHidden()
    assert page._ocr_psm_label_wrap.isHidden()
    assert not page._ocr_not_applicable_label.isHidden()

    page._selected_path = "book.pdf"
    page._update_ocr_visibility()

    assert not page._ocr_mode_label_wrap.isHidden()
    assert not page._ocr_dpi_label_wrap.isHidden()
    assert not page._ocr_psm_label_wrap.isHidden()
    assert page._ocr_not_applicable_label.isHidden()

    page.deleteLater()


def test_normalize_page_defaults_book_language_to_russian(qapp) -> None:
    page = NormalizePage()

    assert page._book_language.currentData() == "ru"
    assert [
        page._book_language.itemData(index)
        for index in range(page._book_language.count())
    ] == ["ru", "en", "zh", "kk", "uz"]

    page.deleteLater()


def test_normalize_page_passes_selected_book_language_to_worker(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    captured: dict = {}

    class _Signal:
        def connect(self, _callback):  # noqa: ANN001
            return None

    class _FakeWorker:
        progress = _Signal()
        progress_pct = _Signal()
        finished = _Signal()
        error = _Signal()

        def __init__(self, **kwargs):
            captured.update(kwargs)

        def start(self) -> None:
            return None

    monkeypatch.setattr(normalize_page, "NormalizeWorker", _FakeWorker)

    book_path = tmp_path / "book.txt"
    book_path.write_text("Hello world.", encoding="utf-8")
    page = NormalizePage()
    page._selected_path = str(book_path)
    page._path_label.setText(str(book_path))
    page._btn_run.setEnabled(True)
    page._book_language.setCurrentIndex(page._book_language.findData("en"))
    page._ocr_psm.setCurrentIndex(page._ocr_psm.findData(11))

    page._run_normalization()

    assert captured["input_path"] == book_path
    assert captured["book_language"] == "en"
    assert captured["ocr_psm"] == 11
    page.deleteLater()


def test_normalize_page_run_button_starts_worker(qapp, qtbot, tmp_path, monkeypatch) -> None:
    captured: dict = {}

    class _Signal:
        def __init__(self) -> None:
            self.callbacks = []

        def connect(self, callback):  # noqa: ANN001
            self.callbacks.append(callback)

        def emit(self, *args):  # noqa: ANN002
            for callback in self.callbacks:
                callback(*args)

    class _FakeWorker:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.progress = _Signal()
            self.progress_pct = _Signal()
            self.finished = _Signal()
            self.error = _Signal()

        def start(self) -> None:
            book = Book(
                chapters=[
                    Chapter(
                        index=0,
                        paragraphs=[
                            Paragraph(
                                raw_text="Hello.",
                                normalized_text="Hello.",
                                index_in_chapter=0,
                            ),
                        ],
                    )
                ],
            )
            self.finished.emit(book)

    monkeypatch.setattr(normalize_page, "NormalizeWorker", _FakeWorker)
    book_path = tmp_path / "book.txt"
    book_path.write_text("Hello.", encoding="utf-8")
    page = NormalizePage()
    qtbot.addWidget(page)
    page._selected_path = str(book_path)
    page._path_label.setText(str(book_path))
    page._btn_run.setEnabled(True)
    page._book_language.setCurrentIndex(page._book_language.findData("en"))

    qtbot.mouseClick(page._btn_run, QtCore.Qt.MouseButton.LeftButton)

    assert captured["input_path"] == book_path
    assert captured["book_language"] == "en"
    assert page._book is not None
    assert page._raw_text.toPlainText() == "Hello."


def test_normalize_page_hides_llm_field_help_until_enabled(qapp) -> None:
    page = NormalizePage()

    assert page._llm_endpoint_label_wrap.isHidden()
    assert page._llm_model_label_wrap.isHidden()

    page._llm_normalize.setChecked(True)

    assert not page._llm_endpoint_label_wrap.isHidden()
    assert not page._llm_model_label_wrap.isHidden()

    page._llm_normalize.setChecked(False)

    assert page._llm_endpoint_label_wrap.isHidden()
    assert page._llm_model_label_wrap.isHidden()

    page.deleteLater()


def test_normalize_page_uses_readable_psm_options_and_centered_dpi(qapp) -> None:
    set_language("en")
    page = NormalizePage()

    assert page._ocr_dpi.alignment() & QtCore.Qt.AlignmentFlag.AlignHCenter
    assert page._ocr_dpi.alignment() & QtCore.Qt.AlignmentFlag.AlignVCenter
    assert page._ocr_dpi.lineEdit().alignment() & QtCore.Qt.AlignmentFlag.AlignHCenter
    assert page._ocr_dpi.lineEdit().alignment() & QtCore.Qt.AlignmentFlag.AlignVCenter
    assert page._ocr_dpi.buttonSymbols() == QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons
    assert page._ocr_dpi.height() == 38
    assert page._ocr_dpi.width() <= 160
    assert [
        page._ocr_psm.itemData(index)
        for index in range(page._ocr_psm.count())
    ] == [3, 4, 6, 11, 13]
    current_text = page._ocr_psm.itemText(page._ocr_psm.findData(6)).lower()
    assert "6" in current_text
    assert "cropped text" in current_text
    assert "main body block" in current_text
    psm_help = page._ocr_psm.toolTip().lower()
    assert "book page" in psm_help
    assert "do not use for full pages" in psm_help
    assert page._raw_label.text() == "Original text"
    assert page._norm_label.text() == "After normalization"

    page.deleteLater()
    set_language("ru")

    ru_page = NormalizePage()
    ru_texts = [
        ru_page._ocr_psm.itemText(index)
        for index in range(ru_page._ocr_psm.count())
    ]
    assert any("Книжная страница" in text for text in ru_texts)
    assert any("Фрагменты" in text for text in ru_texts)
    assert "не использовать для полной страницы" in ru_page._ocr_psm.toolTip()
    ru_page.deleteLater()


def test_normalize_page_retranslates_psm_options_for_all_languages(qapp) -> None:
    for code, _label in SUPPORTED_LANGUAGES:
        set_language(code)
        page = NormalizePage()
        page.retranslate()

        texts = [page._ocr_psm.itemText(index) for index in range(page._ocr_psm.count())]
        assert [page._ocr_psm.itemData(index) for index in range(page._ocr_psm.count())] == [
            3,
            4,
            6,
            11,
            13,
        ]
        assert all(text.strip() for text in texts)
        assert all("??" not in text for text in texts)
        assert "??" not in page._ocr_psm.toolTip()
        assert "\ufffd" not in page._ocr_psm.toolTip()
        assert page._ocr_psm.currentData() == 6
        page.deleteLater()

    set_language("ru")


def test_normalize_page_allows_manual_normalized_text_edits(qapp, qtbot) -> None:
    page = NormalizePage()
    qtbot.addWidget(page)
    book = Book(
        chapters=[
            Chapter(
                title="Chapter",
                index=0,
                paragraphs=[
                    Paragraph(raw_text="Raw one.", normalized_text="Norm one."),
                    Paragraph(raw_text="Raw two.", normalized_text="Norm two."),
                ],
            )
        ]
    )

    page._on_finished(book)
    assert not page._norm_text.isReadOnly()
    assert page._btn_apply_norm_edits.isEnabled()

    page._norm_text.setPlainText("=== Chapter ===\n\nEdited one.\n\nEdited two.")
    qtbot.mouseClick(page._btn_apply_norm_edits, QtCore.Qt.MouseButton.LeftButton)

    assert book.chapters[0].paragraphs[0].normalized_text == "Edited one."
    assert book.chapters[0].paragraphs[1].normalized_text == "Edited two."

    page.deleteLater()


def test_normalize_page_pdf_layout_stays_sane_at_small_size(qapp) -> None:
    page = NormalizePage()
    page._selected_path = "book.pdf"
    page._update_ocr_visibility()

    render_widget(page, 760, 520, scale=1.0)
    assert_layout_sane(page)
    assert not page.findChildren(QtWidgets.QSplitter)
    for editor in (page._raw_text, page._norm_text):
        assert editor.horizontalScrollBarPolicy() == QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        assert editor.verticalScrollBarPolicy() == QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        assert not editor.horizontalScrollBar().isVisible()
        assert not editor.verticalScrollBar().isVisible()

    page.deleteLater()


def test_book_preview_continues_after_short_preamble() -> None:
    book = Book(chapters=[
        Chapter(
            title="Preamble",
            index=0,
            paragraphs=[
                Paragraph(raw_text="Верёвка есть вервие простое.", normalized_text="Верёвка есть вервие простое."),
            ],
        ),
        Chapter(
            title="ГЛАВА 1",
            index=1,
            paragraphs=[
                Paragraph(raw_text="Сергей сидел за столом.", normalized_text="Сергей сидел за столом."),
                Paragraph(raw_text="Гроза началась.", normalized_text="Гроза началась."),
            ],
        ),
    ])

    raw_lines, norm_lines = _book_preview_lines(book, limit=3)

    assert "Preamble" in raw_lines[0]
    assert "Верёвка есть вервие простое." in raw_lines
    assert "=== ГЛАВА 1 ===" in raw_lines
    assert "Сергей сидел за столом." in raw_lines
    assert norm_lines == raw_lines
