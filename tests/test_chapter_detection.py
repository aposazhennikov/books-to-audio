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
            ("Глава V", "chapter_roman"),
            ("Глава XIV", "chapter_roman"),
            ("Глава III", "chapter_roman"),
            ("Глава |", "chapter_roman"),
            ("Глава Il", "chapter_roman"),
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
            "Глава I Сержант гвардии 7",
            "Глава XIV Суд 124",
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

    def test_footnote_numbers_not_treated_as_chapters(self) -> None:
        """Numbered footnotes with restarting numbering must not create chapters."""
        book = self._make_book_with_paragraphs([
            "Глава первая",
            "Текст первой главы.",
            "1 Примечание к первой главе с пояснением",
            "2 Еще одно примечание с подробностями",
            "Глава вторая",
            "Текст второй главы.",
            "1 Примечание к второй главе с пояснением",
            "2 Повторное примечание нового раздела текста",
            "Глава третья",
            "Текст третьей главы.",
            "1 Примечание к третьей главе с пояснением",
        ])
        detector = ChapterDetector()
        result = detector.detect_and_split(book)
        assert len(result.chapters) == 3
        for ch in result.chapters:
            assert "Глава" in ch.title

    def test_sequential_numeric_headings_are_kept(self) -> None:
        """Legitimate numbered chapters (monotonic) must still be detected."""
        book = self._make_book_with_paragraphs([
            "1. Введение в тематику данного исследования",
            "Текст введения.",
            "Ещё текст.",
            "2. Методология проведения научного исследования",
            "Текст методологии.",
            "Ещё текст.",
            "3. Результаты проведенного исследования",
            "Текст результатов.",
        ])
        detector = ChapterDetector()
        result = detector.detect_and_split(book)
        assert len(result.chapters) == 3

    def test_mixed_real_chapters_and_many_footnotes(self) -> None:
        """Simulate Pushkin-like layout: real Глава + scattered footnotes."""
        paras = [
            "Глава первая",
            "Текст.",
        ]
        for fn_num in [1, 2, 3, 4]:
            paras.append(f"{fn_num} Примечание с достаточно длинным текстом")
        paras += [
            "Глава вторая",
            "Текст.",
        ]
        for fn_num in [1, 2, 3]:
            paras.append(f"{fn_num} Примечание с достаточно длинным текстом")
        paras += [
            "Глава третья",
            "Текст.",
        ]
        for fn_num in [1, 2]:
            paras.append(f"{fn_num} Примечание с достаточно длинным текстом")
        book = self._make_book_with_paragraphs(paras)
        detector = ChapterDetector()
        result = detector.detect_and_split(book)
        assert len(result.chapters) == 3
        for ch in result.chapters:
            assert "Глава" in ch.title

    def test_recover_ocr_damaged_chapter_numeral(self) -> None:
        """OCR-damaged numeral after 'Глава' is recovered when other chapters exist."""
        book = self._make_book_with_paragraphs([
            "Глава I",
            "Текст первой главы.",
            "Ещё текст.",
            "Глава Il",
            "Текст второй главы.",
            "Ещё текст.",
            "Глава III",
            "Текст третьей главы.",
            "Ещё текст.",
            "Глава [М",
            "Текст четвёртой главы.",
            "Ещё текст.",
            "Глава V",
            "Текст пятой главы.",
        ])
        detector = ChapterDetector()
        result = detector.detect_and_split(book)
        assert len(result.chapters) == 5
        titles = [ch.title for ch in result.chapters]
        assert any("4" in t or "[М" in t for t in titles)

    def test_recover_various_ocr_artifacts(self) -> None:
        """Different OCR artifacts after 'Глава' are all recovered."""
        book = self._make_book_with_paragraphs([
            "Глава I",
            "Текст.",
            "Ещё текст.",
            "Глава (II",
            "Текст.",
            "Ещё текст.",
            "Глава III",
            "Текст.",
            "Ещё текст.",
            "Глава 1У",
            "Текст.",
            "Ещё текст.",
            "Глава V",
            "Текст.",
        ])
        detector = ChapterDetector()
        result = detector.detect_and_split(book)
        assert len(result.chapters) == 5

    def test_no_recovery_without_enough_confirmed_chapters(self) -> None:
        """Orphan 'Глава' lines are NOT recovered when < 3 confirmed hits."""
        book = self._make_book_with_paragraphs([
            "Глава первая",
            "Текст.",
            "Глава [М",
            "Текст.",
        ])
        detector = ChapterDetector()
        result = detector.detect_and_split(book)
        titles = [ch.title for ch in result.chapters]
        assert not any("[М" in t for t in titles)

    def test_long_glava_line_not_recovered(self) -> None:
        """Long OCR-like line starting with 'Глава' is not adopted as orphan."""
        book = self._make_book_with_paragraphs([
            "Глава первая",
            "Текст.",
            "Ещё текст.",
            "Глава вторая",
            "Текст.",
            "Ещё текст.",
            "Глава третья",
            "Текст.",
            "Глава [номер четыре со всеми действующими лицами произведения",
            "Текст.",
        ])
        detector = ChapterDetector()
        result = detector.detect_and_split(book)
        assert len(result.chapters) == 3
        titles = [ch.title for ch in result.chapters]
        assert not any("четыре" in t for t in titles)

    def test_toc_entry_not_recovered_as_orphan(self) -> None:
        """TOC line like 'Глава I Сержант гвардии 7' is not adopted."""
        book = self._make_book_with_paragraphs([
            "Глава первая",
            "Текст.",
            "Ещё текст.",
            "Глава вторая",
            "Текст.",
            "Ещё текст.",
            "Глава третья",
            "Текст.",
            "Глава I Сержант гвардии 7",
            "Текст.",
        ])
        detector = ChapterDetector()
        result = detector.detect_and_split(book)
        assert len(result.chapters) == 3
        titles = [ch.title for ch in result.chapters]
        assert not any("Сержант" in t for t in titles)
