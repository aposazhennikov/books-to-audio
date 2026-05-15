"""Tests for GUI normalization worker helpers."""

from __future__ import annotations

import pytest

from book_normalizer.config import OcrMode
from book_normalizer.gui.workers.normalize_worker import (
    _effective_pdf_extraction_mode,
    _ensure_pdf_selection_is_usable,
)


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
