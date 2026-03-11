"""Tests for chapter detection and splitting."""

from __future__ import annotations

import pytest

from book_normalizer.chaptering.detector import ChapterDetector
from book_normalizer.chaptering.patterns import match_chapter_heading
from book_normalizer.models.book import Book, Chapter, Paragraph


class TestChapterPatterns:
    @pytest.mark.parametrize(
        "line,expected_label",
        [
            ("Глава 1", "chapter_numeric"),
            ("Глава 12", "chapter_numeric"),
            ("ГЛАВА 3", "chapter_numeric"),
            ("глава 5", "chapter_numeric"),
            ("Глава первая", "chapter_word"),
            ("Глава двадцатая", "chapter_word"),
            ("Часть I", "part"),
            ("Часть 2", "part"),
            ("ЧАСТЬ III", "part"),
            ("Пролог", "prologue_epilogue"),
            ("ПРОЛОГ", "prologue_epilogue"),
            ("Эпилог", "prologue_epilogue"),
            ("эпилог", "prologue_epilogue"),
        ],
    )
    def test_known_patterns_match(self, line: str, expected_label: str) -> None:
        result = match_chapter_heading(line)
        assert result is not None, f"Expected match for '{line}'"
        _, label = result
        assert label == expected_label

    @pytest.mark.parametrize(
        "line",
        [
            "Обычный текст абзаца.",
            "Он сказал: «Глава была интересной».",
            "123",
            "",
            "   ",
        ],
    )
    def test_non_headings_do_not_match(self, line: str) -> None:
        assert match_chapter_heading(line) is None


class TestChapterDetector:
    def _make_book_with_paragraphs(self, texts: list[str]) -> Book:
        """Create a book with a single chapter containing given paragraph texts."""
        paragraphs = [
            Paragraph(raw_text=text, index_in_chapter=i)
            for i, text in enumerate(texts)
        ]
        chapter = Chapter(title="Full Text", index=0, paragraphs=paragraphs)
        return Book(chapters=[chapter])

    def test_detects_two_chapters(self) -> None:
        book = self._make_book_with_paragraphs([
            "Глава 1",
            "Текст первой главы.",
            "Продолжение первой главы.",
            "Глава 2",
            "Текст второй главы.",
        ])
        detector = ChapterDetector()
        result = detector.detect_and_split(book)
        assert len(result.chapters) == 2
        assert result.chapters[0].title == "Глава 1"
        assert result.chapters[1].title == "Глава 2"

    def test_no_headings_single_chapter(self) -> None:
        book = self._make_book_with_paragraphs([
            "Обычный текст.",
            "Ещё текст.",
        ])
        detector = ChapterDetector()
        result = detector.detect_and_split(book)
        assert len(result.chapters) == 1

    def test_preamble_before_first_heading(self) -> None:
        book = self._make_book_with_paragraphs([
            "Это предисловие автора.",
            "Глава 1",
            "Текст главы.",
        ])
        detector = ChapterDetector()
        result = detector.detect_and_split(book)
        assert len(result.chapters) == 2
        assert result.chapters[0].title == "Preamble"
        assert result.chapters[1].title == "Глава 1"

    def test_prologue_detection(self) -> None:
        book = self._make_book_with_paragraphs([
            "Пролог",
            "Текст пролога.",
            "Глава 1",
            "Текст главы.",
        ])
        detector = ChapterDetector()
        result = detector.detect_and_split(book)
        assert len(result.chapters) == 2
        assert result.chapters[0].title == "Пролог"

    def test_empty_book(self) -> None:
        book = Book(chapters=[])
        detector = ChapterDetector()
        result = detector.detect_and_split(book)
        assert len(result.chapters) == 0

    def test_chapters_are_reindexed(self) -> None:
        book = self._make_book_with_paragraphs([
            "Глава 1",
            "Текст.",
            "Глава 2",
            "Текст.",
            "Глава 3",
            "Текст.",
        ])
        detector = ChapterDetector()
        result = detector.detect_and_split(book)
        for i, ch in enumerate(result.chapters):
            assert ch.index == i
