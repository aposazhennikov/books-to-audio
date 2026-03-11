"""Tests for the stress annotator."""

from __future__ import annotations

from pathlib import Path

from book_normalizer.models.book import Book, Chapter, Paragraph
from book_normalizer.stress.annotator import StressAnnotator
from book_normalizer.stress.dictionary import COMBINING_ACUTE, StressDictionary


def _make_book(text: str) -> Book:
    """Create a minimal book with a single paragraph."""
    para = Paragraph(raw_text=text, normalized_text=text, index_in_chapter=0)
    ch = Chapter(title="Test", index=0, paragraphs=[para])
    return Book(chapters=[ch])


class TestStressAnnotator:
    def test_annotate_known_words(self) -> None:
        book = _make_book("молоко и вода")
        d = StressDictionary()
        annotator = StressAnnotator(d)
        result = annotator.annotate_book(book)

        assert result.total_words == 3
        assert result.known_words >= 2
        assert result.single_vowel_words >= 1

    def test_segments_created(self) -> None:
        book = _make_book("молоко и вода")
        d = StressDictionary()
        annotator = StressAnnotator(d)
        annotator.annotate_book(book)

        para = book.chapters[0].paragraphs[0]
        assert len(para.segments) > 0

    def test_known_word_has_stress_form(self) -> None:
        book = _make_book("молоко")
        d = StressDictionary()
        annotator = StressAnnotator(d)
        annotator.annotate_book(book)

        para = book.chapters[0].paragraphs[0]
        word_segs = [s for s in para.segments if s.text == "молоко"]
        assert len(word_segs) == 1
        assert COMBINING_ACUTE in word_segs[0].stress_form

    def test_unknown_word_empty_stress(self) -> None:
        book = _make_book("промышленность")
        d = StressDictionary()
        annotator = StressAnnotator(d)
        result = annotator.annotate_book(book)

        assert result.unknown_words == 1
        assert "промышленность" in result.unknown_word_set

        para = book.chapters[0].paragraphs[0]
        word_segs = [s for s in para.segments if s.text == "промышленность"]
        assert word_segs[0].stress_form == ""

    def test_single_vowel_word(self) -> None:
        book = _make_book("кот")
        d = StressDictionary()
        annotator = StressAnnotator(d)
        result = annotator.annotate_book(book)

        assert result.single_vowel_words == 1
        para = book.chapters[0].paragraphs[0]
        word_segs = [s for s in para.segments if s.text == "кот"]
        assert word_segs[0].stress_form == "кот"

    def test_punctuation_preserved(self) -> None:
        book = _make_book("молоко, вода.")
        d = StressDictionary()
        annotator = StressAnnotator(d)
        annotator.annotate_book(book)

        para = book.chapters[0].paragraphs[0]
        texts = [s.text for s in para.segments]
        assert "," in "".join(texts)
        assert "." in "".join(texts)

    def test_reassemble_text(self) -> None:
        book = _make_book("молоко и вода")
        d = StressDictionary()
        annotator = StressAnnotator(d)
        annotator.annotate_book(book)

        para = book.chapters[0].paragraphs[0]
        reassembled = StressAnnotator.reassemble_text(para, use_stress=False)
        assert reassembled == "молоко и вода"

    def test_reassemble_with_stress(self) -> None:
        book = _make_book("молоко")
        d = StressDictionary()
        annotator = StressAnnotator(d)
        annotator.annotate_book(book)

        para = book.chapters[0].paragraphs[0]
        stressed = StressAnnotator.reassemble_text(para, use_stress=True)
        assert COMBINING_ACUTE in stressed

    def test_empty_paragraph(self) -> None:
        book = _make_book("")
        d = StressDictionary()
        annotator = StressAnnotator(d)
        result = annotator.annotate_book(book)
        assert result.total_words == 0

    def test_audit_trail(self) -> None:
        book = _make_book("молоко")
        d = StressDictionary()
        annotator = StressAnnotator(d)
        annotator.annotate_book(book)
        assert any(r["stage"] == "stress" for r in book.audit_trail)

    def test_multiple_chapters(self) -> None:
        p1 = Paragraph(raw_text="молоко", normalized_text="молоко", index_in_chapter=0)
        p2 = Paragraph(raw_text="вода", normalized_text="вода", index_in_chapter=0)
        ch1 = Chapter(title="Ch1", index=0, paragraphs=[p1])
        ch2 = Chapter(title="Ch2", index=1, paragraphs=[p2])
        book = Book(chapters=[ch1, ch2])

        d = StressDictionary()
        annotator = StressAnnotator(d)
        result = annotator.annotate_book(book)
        assert result.total_words == 2
        assert result.known_words == 2
