"""Tests for normalization pipeline and individual stages."""

from __future__ import annotations

from book_normalizer.models.book import Book, Chapter, Paragraph
from book_normalizer.normalization.cleanup import remove_page_numbers, remove_repeated_headers
from book_normalizer.normalization.paragraphs import collapse_empty_lines
from book_normalizer.normalization.pipeline import NormalizationPipeline
from book_normalizer.normalization.punctuation import normalize_dashes, normalize_ellipsis, normalize_quotes
from book_normalizer.normalization.whitespace import normalize_whitespace, repair_broken_lines


class TestWhitespace:
    def test_collapse_multiple_spaces(self) -> None:
        assert normalize_whitespace("Привет    мир") == "Привет мир"

    def test_remove_nbsp(self) -> None:
        assert normalize_whitespace("Привет\u00a0мир") == "Привет мир"

    def test_remove_zero_width(self) -> None:
        assert normalize_whitespace("Текст\u200bтекст") == "Тексттекст"

    def test_strip_trailing_spaces(self) -> None:
        result = normalize_whitespace("Текст   \nЕщё   ")
        assert "   " not in result


class TestRepairBrokenLines:
    def test_joins_broken_word(self) -> None:
        result = repair_broken_lines("прекрас\nный")
        assert result == "прекрас ный"

    def test_preserves_paragraph_breaks(self) -> None:
        text = "Конец абзаца.\n\nНовый абзац."
        result = repair_broken_lines(text)
        assert "\n\n" in result


class TestPunctuation:
    def test_normalize_straight_quotes(self) -> None:
        result = normalize_quotes('"текст"')
        assert result == "«текст»"

    def test_normalize_dashes(self) -> None:
        assert "—" in normalize_dashes("слово -- слово")
        assert "—" in normalize_dashes("слово – слово")

    def test_normalize_ellipsis(self) -> None:
        assert normalize_ellipsis("текст...") == "текст…"
        assert normalize_ellipsis("текст....") == "текст…"


class TestCleanup:
    def test_remove_page_numbers(self) -> None:
        text = "Текст.\n123\nЕщё текст."
        result = remove_page_numbers(text)
        assert "123" not in result
        assert "Текст." in result

    def test_remove_repeated_headers(self) -> None:
        text = "Заголовок\nТекст.\nЗаголовок\nЕщё.\nЗаголовок\nКонец."
        result = remove_repeated_headers(text, min_occurrences=3)
        assert "Заголовок" not in result


class TestCollapseEmptyLines:
    def test_triple_newlines_collapsed(self) -> None:
        result = collapse_empty_lines("A\n\n\n\nB")
        assert result == "A\n\nB"


class TestNormalizationPipeline:
    def test_normalize_text(self) -> None:
        pipeline = NormalizationPipeline()
        result = pipeline.normalize_text("Привет    мир...  ")
        assert "  " not in result
        assert "…" in result

    def test_normalize_book(self) -> None:
        para = Paragraph(raw_text="Текст   с   пробелами...", index_in_chapter=0)
        ch = Chapter(title="Test", index=0, paragraphs=[para])
        book = Book(chapters=[ch])

        pipeline = NormalizationPipeline()
        pipeline.normalize_book(book)

        assert para.normalized_text
        assert "   " not in para.normalized_text

    def test_custom_stage(self) -> None:
        pipeline = NormalizationPipeline(stages=[])
        pipeline.add_stage("upper", str.upper)
        assert pipeline.normalize_text("hello") == "HELLO"
