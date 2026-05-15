"""Tests for text chunking splitter."""


from book_normalizer.chunking.splitter import (
    chunk_chapter,
    chunk_text,
    split_into_sentences,
)


class TestSplitIntoSentences:
    """Tests for sentence splitting."""

    def test_simple_sentences(self) -> None:
        """Simple period-separated sentences are split correctly."""
        result = split_into_sentences("Первое предложение. Второе предложение.")
        assert len(result) == 2

    def test_exclamation_and_question(self) -> None:
        """Sentences ending with ! and ? are split."""
        result = split_into_sentences("Привет! Как дела? Нормально.")
        assert len(result) == 3

    def test_ellipsis(self) -> None:
        """Ellipsis acts as sentence boundary."""
        result = split_into_sentences("Он думал… Потом ушёл.")
        assert len(result) == 2

    def test_empty_text(self) -> None:
        """Empty text returns empty list."""
        assert split_into_sentences("") == []
        assert split_into_sentences("   ") == []


class TestChunkText:
    """Tests for text chunking."""

    def test_short_text_single_chunk(self) -> None:
        """Text shorter than max_chunk_chars stays as one chunk."""
        text = "Короткий текст."
        chunks = chunk_text(text, max_chunk_chars=900)
        assert len(chunks) == 1
        assert chunks[0] == "Короткий текст."

    def test_long_text_split_at_sentences(self) -> None:
        """Long text is split at sentence boundaries."""
        sentences = ["Предложение номер один." for _ in range(20)]
        text = " ".join(sentences)
        chunks = chunk_text(text, max_chunk_chars=200)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 250

    def test_no_chunk_exceeds_limit_significantly(self) -> None:
        """No chunk exceeds the limit by more than one sentence."""
        text = "А. Б. В. Г. Д. Е. Ж. З. И. К."
        chunks = chunk_text(text, max_chunk_chars=10)
        assert len(chunks) >= 3

    def test_empty_text(self) -> None:
        """Empty text returns empty list."""
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_tiny_limit_splits_long_sentence_on_words(self) -> None:
        """A tiny chunk limit does not cut through words."""
        text = "alpha beta gamma delta epsilon zeta eta theta iota."
        chunks = chunk_text(text, max_chunk_chars=18)

        assert len(chunks) > 1
        assert " ".join(chunks) == text
        assert all(len(chunk) <= 18 for chunk in chunks)

    def test_single_long_word_is_not_cut(self) -> None:
        """A word longer than the limit is kept intact."""
        text = "supercalifragilistic expialidocious."
        chunks = chunk_text(text, max_chunk_chars=10)

        assert "supercalifragilistic" in chunks
        assert " ".join(chunks) == text


class TestChunkChapter:
    """Tests for chapter-level chunking."""

    def test_small_chapter_single_chunk(self) -> None:
        """Small chapter stays as one chunk."""
        text = "Первый абзац.\n\nВторой абзац."
        chunks = chunk_chapter(text, chapter_index=0, max_chunk_chars=900)
        assert len(chunks) == 1
        assert chunks[0].chapter_index == 0
        assert chunks[0].index == 0

    def test_large_chapter_multiple_chunks(self) -> None:
        """Large chapter is split into multiple chunks."""
        paragraphs = [f"Параграф номер {i}. " * 10 for i in range(30)]
        text = "\n\n".join(paragraphs)
        chunks = chunk_chapter(text, chapter_index=2, max_chunk_chars=200)
        assert len(chunks) > 1
        assert all(c.chapter_index == 2 for c in chunks)
        indices = [c.index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_paragraph_boundaries_respected(self) -> None:
        """Short paragraphs are grouped together, not split mid-paragraph."""
        text = "Абзац один.\n\nАбзац два.\n\nАбзац три."
        chunks = chunk_chapter(text, chapter_index=0, max_chunk_chars=900)
        assert len(chunks) == 1
        assert "\n\n" in chunks[0].text
