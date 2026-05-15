"""Tests for the PDF loader."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from book_normalizer.config import OcrMode
from book_normalizer.loaders.pdf_loader import (
    PdfLoader,
    PdfOcrCompareResult,
    PdfTextVariant,
    extract_pdf_with_ocr_mode,
    select_pdf_text_for_mode,
)


class TestPdfLoader:
    def test_supported_extensions(self) -> None:
        loader = PdfLoader()
        assert ".pdf" in loader.supported_extensions

    def test_can_load(self, tmp_path: Path) -> None:
        loader = PdfLoader()
        assert loader.can_load(tmp_path / "book.pdf")
        assert not loader.can_load(tmp_path / "book.txt")

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        loader = PdfLoader()
        with pytest.raises(FileNotFoundError):
            loader.load(tmp_path / "missing.pdf")

    @patch("book_normalizer.loaders.pdf_loader.PdfLoader._extract_text")
    def test_load_with_mocked_extraction(self, mock_extract: MagicMock, tmp_path: Path) -> None:
        mock_extract.return_value = "Первый абзац.\n\nВторой абзац."

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy")

        loader = PdfLoader()
        book = loader.load(pdf_file)

        assert book.metadata.source_format == "pdf"
        assert len(book.chapters[0].paragraphs) == 2
        assert book.chapters[0].paragraphs[0].raw_text == "Первый абзац."

    @patch("book_normalizer.loaders.pdf_loader.PdfLoader._extract_text")
    def test_audit_trail(self, mock_extract: MagicMock, tmp_path: Path) -> None:
        mock_extract.return_value = "Текст."
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy")

        loader = PdfLoader()
        book = loader.load(pdf_file)
        assert any(r["stage"] == "loading" for r in book.audit_trail)


class TestOcrModeSelection:
    def test_extract_pdf_with_ocr_mode_off_returns_only_native(self, tmp_path: Path) -> None:
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy")

        with patch.object(PdfLoader, "_extract_text", return_value="native text"):
            result = extract_pdf_with_ocr_mode(pdf_file, OcrMode.OFF)

        assert result.native.text == "native text"
        assert result.ocr is None

    def test_select_pdf_text_for_mode_off_uses_native(self) -> None:
        compare = PdfOcrCompareResult(
            native=PdfTextVariant(kind="native", text="native"),
            ocr=PdfTextVariant(kind="ocr", text="ocr"),
        )
        chosen, stats = select_pdf_text_for_mode(compare, OcrMode.OFF)
        assert chosen.kind == "native"
        assert stats["selected"] == "native"

    def test_select_pdf_text_for_mode_force_uses_ocr(self) -> None:
        compare = PdfOcrCompareResult(
            native=PdfTextVariant(kind="native", text="native"),
            ocr=PdfTextVariant(kind="ocr", text="ocr"),
        )
        chosen, stats = select_pdf_text_for_mode(compare, OcrMode.FORCE)
        assert chosen.kind == "ocr"
        assert stats["selected"] == "ocr"

    def test_select_pdf_text_for_mode_auto_falls_back_when_native_empty(self) -> None:
        compare = PdfOcrCompareResult(
            native=PdfTextVariant(kind="native", text="   "),
            ocr=PdfTextVariant(kind="ocr", text="Распознанный русский текст"),
        )
        chosen, stats = select_pdf_text_for_mode(compare, OcrMode.AUTO)
        assert chosen.kind == "ocr"
        assert stats["selected"] == "ocr"
        assert stats["ocr_unreadable"] is False

    def test_select_pdf_text_for_mode_auto_does_not_use_unreadable_ocr(self) -> None:
        compare = PdfOcrCompareResult(
            native=PdfTextVariant(kind="native", text="Co,11;ep'l\\:aHne rJIABA"),
            ocr=PdfTextVariant(kind="ocr", text="lorem ipsum OCR garbage"),
        )

        chosen, stats = select_pdf_text_for_mode(compare, OcrMode.AUTO)

        assert chosen.kind == "native"
        assert stats["native_unreadable"] is True
        assert stats["ocr_unreadable"] is True
        assert stats["reason"] == "auto_mode_no_readable_ocr"

    def test_select_pdf_text_for_mode_auto_prefers_native_when_not_empty(self) -> None:
        compare = PdfOcrCompareResult(
            native=PdfTextVariant(kind="native", text="Родной текст на русском языке"),
            ocr=PdfTextVariant(kind="ocr", text="Текст после распознавания"),
        )
        chosen, stats = select_pdf_text_for_mode(compare, OcrMode.AUTO)
        assert chosen.kind == "native"
        assert stats["selected"] == "native"
        assert stats["native_unreadable"] is False

    def test_select_pdf_text_for_mode_marks_broken_native_when_ocr_unavailable(self) -> None:
        compare = PdfOcrCompareResult(
            native=PdfTextVariant(kind="native", text="Co,11;ep'l\\:aHne rJIABA llEPBMI"),
            ocr=None,
        )

        chosen, stats = select_pdf_text_for_mode(compare, OcrMode.AUTO)

        assert chosen.kind == "native"
        assert stats["native_unreadable"] is True
        assert stats["reason"] == "ocr_unavailable_native_unreadable"
