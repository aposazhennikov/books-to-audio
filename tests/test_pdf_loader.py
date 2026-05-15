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
    _looks_like_toc,
    _postprocess_ocr_text,
    _prepare_ocr_page_images,
    _should_keep_ocr_text,
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


class TestOcrImagePreparation:
    def test_prepare_ocr_page_images_splits_landscape_spread(self) -> None:
        pil_image = pytest.importorskip("PIL.Image")

        img = pil_image.new("L", (1000, 600), 255)
        for x0 in (120, 620):
            for y in range(120, 480, 18):
                for x in range(x0, x0 + 260):
                    img.putpixel((x, y), 0)

        segments = _prepare_ocr_page_images(img)

        assert len(segments) == 2
        assert all(segment.size[0] < img.size[0] for segment in segments)

    def test_postprocess_ocr_text_drops_noise_and_joins_hyphenation(self) -> None:
        raw = "' \\\\ . p .\nСОДЕРЖА-\nЩАЯ ГЛУБОКОЕ\nисследование предмета"

        cleaned = _postprocess_ocr_text(raw)

        assert "p ." not in cleaned
        assert "СОДЕРЖАЩАЯ ГЛУБОКОЕ исследование предмета" in cleaned

    def test_should_keep_ocr_text_rejects_toc_blocks(self) -> None:
        toc = (
            "Содержание\n"
            "ГЛАВА ПЕРВАЯ ................................ 3\n"
            "ГЛАВА ВТОРАЯ ................................ 7\n"
            "ГЛАВА ТРЕТЬЯ ................................ 10\n"
        )

        assert _looks_like_toc(toc) is True
        assert _should_keep_ocr_text(toc) is False
