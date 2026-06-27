"""Tests for multi-work structure detection."""

from __future__ import annotations

from book_normalizer.chaptering.detector import ChapterDetector
from book_normalizer.chaptering.patterns import match_chapter_heading, match_work_heading
from book_normalizer.models.book import Book, Chapter, Paragraph


def _book(texts: list[str]) -> Book:
    paragraphs = [
        Paragraph(raw_text=text, index_in_chapter=index)
        for index, text in enumerate(texts)
    ]
    return Book(chapters=[Chapter(title="Full Text", index=0, paragraphs=paragraphs)])


def test_multibook_repeated_chapter_numbers_are_preserved() -> None:
    """Repeated chapter names across detected works must not be deduplicated."""
    book = _book([
        "Книга первая",
        "Глава 1",
        "Текст первой книги, первой главы.",
        "Глава 2",
        "Текст первой книги, второй главы.",
        "Книга вторая",
        "Глава 1",
        "Текст второй книги, первой главы.",
        "Глава 2",
        "Текст второй книги, второй главы.",
    ])

    result = ChapterDetector().detect_and_split(book)

    assert len(result.chapters) == 4
    assert [chapter.work_title for chapter in result.chapters] == [
        "Книга первая",
        "Книга первая",
        "Книга вторая",
        "Книга вторая",
    ]
    assert result.chapters[0].title == "Книга первая - Глава 1"
    assert result.chapters[2].title == "Книга вторая - Глава 1"
    assert result.metadata.extra["structure"]["work_count"] == 2
    assert result.metadata.extra["structure"]["needs_review"] is True


def test_multibook_without_chapters_creates_one_section_per_work() -> None:
    """A collection can contain works without explicit chapters."""
    book = _book([
        "Book One",
        "A standalone novella without chapter headings.",
        "More text from the first novella.",
        "Book Two",
        "Another standalone novella without chapter headings.",
        "More text from the second novella.",
    ])

    result = ChapterDetector().detect_and_split(book)

    assert len(result.chapters) == 2
    assert result.chapters[0].title == "Book One"
    assert result.chapters[1].title == "Book Two"
    assert result.chapters[0].work_title == "Book One"
    assert result.chapters[1].work_title == "Book Two"


def test_supported_language_heading_patterns() -> None:
    assert match_chapter_heading("Chapter One") is not None
    assert match_chapter_heading("Chapter IV") is not None
    assert match_chapter_heading("第一章") is not None
    assert match_chapter_heading("Bob 1") is not None
    assert match_chapter_heading("Тарау 1") is not None
    assert match_work_heading("Book Two") is not None
    assert match_work_heading("第二部") is not None
