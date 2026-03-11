"""Tests for the TXT loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from book_normalizer.loaders.txt_loader import TxtLoader


class TestTxtLoader:
    def test_supported_extensions(self) -> None:
        loader = TxtLoader()
        assert ".txt" in loader.supported_extensions

    def test_can_load(self, tmp_path: Path) -> None:
        loader = TxtLoader()
        assert loader.can_load(tmp_path / "book.txt")
        assert not loader.can_load(tmp_path / "book.pdf")

    def test_load_simple_file(self, tmp_txt_file: Path) -> None:
        loader = TxtLoader()
        book = loader.load(tmp_txt_file)
        assert book.metadata.source_format == "txt"
        assert len(book.chapters) == 1
        assert len(book.chapters[0].paragraphs) > 0

    def test_load_preserves_text(self, tmp_path: Path) -> None:
        content = "Привет, мир!\n\nЭто тестовый текст."
        f = tmp_path / "simple.txt"
        f.write_text(content, encoding="utf-8")

        loader = TxtLoader()
        book = loader.load(f)
        paragraphs = book.chapters[0].paragraphs
        assert len(paragraphs) == 2
        assert paragraphs[0].raw_text == "Привет, мир!"
        assert paragraphs[1].raw_text == "Это тестовый текст."

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        loader = TxtLoader()
        with pytest.raises(FileNotFoundError):
            loader.load(tmp_path / "nonexistent.txt")

    def test_load_cp1251_file(self, tmp_path: Path) -> None:
        content = "Тест кириллицы в cp1251."
        f = tmp_path / "cp1251.txt"
        f.write_bytes(content.encode("cp1251"))

        loader = TxtLoader()
        book = loader.load(f)
        assert "Тест кириллицы" in book.chapters[0].paragraphs[0].raw_text

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")

        loader = TxtLoader()
        book = loader.load(f)
        assert len(book.chapters[0].paragraphs) == 0

    def test_audit_trail_recorded(self, tmp_txt_file: Path) -> None:
        loader = TxtLoader()
        book = loader.load(tmp_txt_file)
        assert len(book.audit_trail) >= 1
        assert book.audit_trail[0]["stage"] == "loading"
