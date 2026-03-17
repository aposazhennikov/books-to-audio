"""Tests for the stress resolver module."""

from __future__ import annotations

from pathlib import Path

from book_normalizer.models.book import Book, Chapter, Paragraph, Segment
from book_normalizer.stress.dictionary import COMBINING_ACUTE, StressDictionary, is_russian_word
from book_normalizer.stress.resolver import StressResolver, _find_context_for_word


class TestFindContext:
    def test_finds_context(self) -> None:
        para = Paragraph(raw_text="", normalized_text="Это молоко вкусное. Ещё одно предложение.", index_in_chapter=0)
        ch = Chapter(title="Test", index=0, paragraphs=[para])
        book = Book(chapters=[ch])

        contexts = _find_context_for_word(book, "молоко")
        assert len(contexts) == 1
        assert "молоко" in contexts[0]
        # Should return at least a full sentence context.
        assert "Это молоко вкусное." in contexts[0]

    def test_no_match(self) -> None:
        para = Paragraph(raw_text="", normalized_text="Текст без нужного слова.", index_in_chapter=0)
        ch = Chapter(title="Test", index=0, paragraphs=[para])
        book = Book(chapters=[ch])

        contexts = _find_context_for_word(book, "промышленность")
        assert len(contexts) == 0


class TestResolverHelpers:
    def test_convert_apostrophe_to_acute(self) -> None:
        result = StressResolver._convert_apostrophe_to_acute("моло'ко")
        assert result == "моло" + COMBINING_ACUTE + "ко"

    def test_apostrophe_on_non_vowel(self) -> None:
        result = StressResolver._convert_apostrophe_to_acute("т'ест")
        assert COMBINING_ACUTE not in result
        assert "'" in result

    def test_update_book_segments(self, tmp_path: Path) -> None:
        from book_normalizer.memory.stress_store import StressStore
        from book_normalizer.models.memory import StressMemoryEntry

        store = StressStore(tmp_path / "stress.json")
        stressed_form = "промы" + COMBINING_ACUTE + "шленность"
        store.add(StressMemoryEntry(
            word="промышленность",
            normalized_word="промышленность",
            stressed_form=stressed_form,
        ))

        d = StressDictionary(store=store)
        resolver = StressResolver(dictionary=d)

        seg = Segment(text="промышленность", stress_form="")
        para = Paragraph(
            raw_text="промышленность",
            normalized_text="промышленность",
            segments=[seg],
            index_in_chapter=0,
        )
        ch = Chapter(title="Test", index=0, paragraphs=[para])
        book = Book(chapters=[ch])

        resolver._update_book_segments(book)
        assert seg.stress_form == stressed_form
