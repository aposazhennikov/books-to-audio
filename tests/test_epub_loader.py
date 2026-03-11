"""Tests for the EPUB loader."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from book_normalizer.loaders.epub_loader import EpubLoader


class TestEpubLoader:
    def test_supported_extensions(self) -> None:
        loader = EpubLoader()
        assert ".epub" in loader.supported_extensions

    def test_can_load(self, tmp_path: Path) -> None:
        loader = EpubLoader()
        assert loader.can_load(tmp_path / "book.epub")
        assert not loader.can_load(tmp_path / "book.txt")

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        loader = EpubLoader()
        with pytest.raises(FileNotFoundError):
            loader.load(tmp_path / "missing.epub")

    def test_html_to_text(self) -> None:
        html = "<p>First paragraph.</p><p>Second paragraph.</p>"
        result = EpubLoader._html_to_text(html)
        assert "First paragraph." in result
        assert "Second paragraph." in result

    def test_html_to_text_with_br(self) -> None:
        html = "Line one<br/>Line two"
        result = EpubLoader._html_to_text(html)
        assert "Line one\nLine two" == result

    def test_html_to_text_strips_tags(self) -> None:
        html = "<div><strong>Bold</strong> and <em>italic</em></div>"
        result = EpubLoader._html_to_text(html)
        assert "Bold and italic" in result
        assert "<strong>" not in result

    def test_extract_title_from_html(self) -> None:
        html = "<h1>Chapter Title</h1><p>Body text.</p>"
        title = EpubLoader._extract_title_from_html(html)
        assert title == "Chapter Title"

    def test_extract_title_from_h2(self) -> None:
        html = "<h2>Second Level</h2><p>Text.</p>"
        title = EpubLoader._extract_title_from_html(html)
        assert title == "Second Level"

    def test_extract_title_no_heading(self) -> None:
        html = "<p>No heading here.</p>"
        title = EpubLoader._extract_title_from_html(html)
        assert title == ""

    def test_html_entity_decoding(self) -> None:
        html = "<p>Hello&nbsp;World &amp; Friends</p>"
        result = EpubLoader._html_to_text(html)
        assert "Hello World & Friends" in result

    def test_split_paragraphs(self) -> None:
        text = "First.\n\nSecond.\n\nThird."
        result = EpubLoader._split_paragraphs(text)
        assert len(result) == 3
        assert result[0].raw_text == "First."
        assert result[2].raw_text == "Third."
