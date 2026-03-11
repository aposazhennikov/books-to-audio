"""Tests for the PDF loader."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from book_normalizer.loaders.pdf_loader import PdfLoader


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
