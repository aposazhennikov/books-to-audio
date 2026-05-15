from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from book_normalizer.models.book import Book, Chapter, Paragraph

QtWidgets = pytest.importorskip("PyQt6.QtWidgets")
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
