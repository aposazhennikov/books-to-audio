"""Tests for GUI normalization worker helpers."""

from __future__ import annotations

import pytest

from book_normalizer.config import OcrMode
from book_normalizer.gui.workers.normalize_worker import (
    NormalizeWorker,
    _apply_selected_book_language,
    _effective_pdf_extraction_mode,
    _ensure_pdf_selection_is_usable,
)
from book_normalizer.llm.model_router import FALLBACK_QWEN3_MODEL, PRIMARY_QWEN3_MODEL
from book_normalizer.models.book import Book, Chapter, Metadata, Paragraph


def test_gui_pdf_auto_falls_back_without_tesseract() -> None:
    mode = _effective_pdf_extraction_mode(
        OcrMode.AUTO,
        tesseract_available=False,
    )

    assert mode == OcrMode.OFF


def test_gui_pdf_compare_falls_back_without_tesseract() -> None:
    mode = _effective_pdf_extraction_mode(
        OcrMode.COMPARE,
        tesseract_available=False,
    )

    assert mode == OcrMode.OFF


def test_gui_pdf_force_requires_tesseract() -> None:
    with pytest.raises(RuntimeError, match="Tesseract"):
        _effective_pdf_extraction_mode(
            OcrMode.FORCE,
            tesseract_available=False,
        )


def test_gui_pdf_keeps_requested_mode_when_tesseract_available() -> None:
    assert (
        _effective_pdf_extraction_mode(
            OcrMode.FORCE,
            tesseract_available=True,
        )
        == OcrMode.FORCE
    )


def test_gui_pdf_rejects_broken_native_without_tesseract() -> None:
    with pytest.raises(RuntimeError, match="Tesseract"):
        _ensure_pdf_selection_is_usable(
            OcrMode.AUTO,
            {"native_unreadable": True, "ocr_unreadable": True},
            tesseract_available=False,
        )


def test_gui_pdf_rejects_unreadable_ocr_when_native_is_broken() -> None:
    with pytest.raises(RuntimeError, match="OCR"):
        _ensure_pdf_selection_is_usable(
            OcrMode.AUTO,
            {"native_unreadable": True, "ocr_unreadable": True},
            tesseract_available=True,
        )


def test_apply_selected_book_language_overrides_loader_metadata() -> None:
    book = Book(metadata=Metadata(language="ru"))

    result = _apply_selected_book_language(book, "en-US")

    assert result is book
    assert book.metadata.language == "en"
    assert book.audit_trail[-1]["details"] == "language=en"


def test_llm_normalize_marks_book_for_smart_voice_markup(tmp_path, monkeypatch) -> None:
    captured: dict = {}

    class _FakeNormalizer:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def normalize_book(self, book, progress_callback=None):  # noqa: ANN001
            if progress_callback is not None:
                progress_callback(1, 1, 1, 0)
            return (1, 0)

    monkeypatch.setattr("book_normalizer.normalization.llm_normalizer.LlmNormalizer", _FakeNormalizer)
    book = Book(
        metadata=Metadata(language="uz"),
        chapters=[
            Chapter(
                index=0,
                paragraphs=[Paragraph(raw_text="Salom.", normalized_text="Salom.", index_in_chapter=0)],
            ),
        ],
    )
    worker = NormalizeWorker(
        input_path=tmp_path / "book.txt",
        llm_model="gemma3:4b",
        book_language="uz",
    )

    result = worker._llm_normalize_with_progress(book)

    assert result is book
    assert captured["language"] == "uz"
    assert captured["model"] == "gemma3:4b"
    assert book.metadata.extra["llm_processing_enabled"] is True
    assert book.metadata.extra["llm_language"] == "uz"
    assert book.metadata.extra["llm_model_candidates"] == [
        PRIMARY_QWEN3_MODEL,
        FALLBACK_QWEN3_MODEL,
    ]
