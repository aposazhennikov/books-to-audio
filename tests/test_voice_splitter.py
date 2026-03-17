"""Tests for voice-annotated chunking."""

from __future__ import annotations

import pytest

from book_normalizer.chunking.voice_splitter import (
    chunk_annotated_book,
    chunk_annotated_chapter,
)
from book_normalizer.dialogue.models import (
    AnnotatedChapter,
    AnnotatedParagraph,
    DialogueLine,
    SpeakerRole,
    VoiceAnnotatedChunk,
)


def _line(text: str, role: SpeakerRole, is_dialogue: bool) -> DialogueLine:
    return DialogueLine(
        text=text, role=role, is_dialogue=is_dialogue,
        paragraph_id="p0", line_index=0,
    )


def _chapter(lines: list[DialogueLine], index: int = 0) -> AnnotatedChapter:
    para = AnnotatedParagraph(paragraph_id="p0", chapter_index=index, lines=lines)
    return AnnotatedChapter(
        chapter_index=index, chapter_title=f"Ch{index}", paragraphs=[para]
    )


class TestVoiceAnnotatedChunking:

    def test_single_narrator_chunk(self) -> None:
        ch = _chapter([
            _line("Short narration.", SpeakerRole.NARRATOR, False),
        ])
        chunks = chunk_annotated_chapter(ch)
        assert len(chunks) == 1
        assert chunks[0].role == SpeakerRole.NARRATOR
        assert chunks[0].voice_id == "narrator"

    def test_dialogue_creates_separate_chunks(self) -> None:
        ch = _chapter([
            _line("\u041d\u0430\u0440\u0440\u0430\u0442\u043e\u0440.", SpeakerRole.NARRATOR, False),
            _line("\u041f\u0440\u0438\u0432\u0435\u0442!", SpeakerRole.MALE, True),
            _line("\u0417\u0434\u0440\u0430\u0432\u0441\u0442\u0432\u0443\u0439\u0442\u0435!", SpeakerRole.FEMALE, True),
        ])
        chunks = chunk_annotated_chapter(ch)
        assert len(chunks) == 3
        assert chunks[0].role == SpeakerRole.NARRATOR
        assert chunks[1].role == SpeakerRole.MALE
        assert chunks[1].voice_id == "male"
        assert chunks[2].role == SpeakerRole.FEMALE
        assert chunks[2].voice_id == "female"

    def test_consecutive_same_role_merged(self) -> None:
        ch = _chapter([
            _line("First sentence.", SpeakerRole.NARRATOR, False),
            _line("Second sentence.", SpeakerRole.NARRATOR, False),
        ])
        chunks = chunk_annotated_chapter(ch)
        assert len(chunks) == 1
        assert "First" in chunks[0].text
        assert "Second" in chunks[0].text

    def test_long_text_split_into_sub_chunks(self) -> None:
        long_text = "\u041f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u0438\u0435 \u043d\u043e\u043c\u0435\u0440 \u043e\u0434\u0438\u043d. " * 200
        ch = _chapter([
            _line(long_text, SpeakerRole.NARRATOR, False),
        ])
        chunks = chunk_annotated_chapter(ch, max_chunk_chars=100)
        assert len(chunks) > 1
        for c in chunks:
            assert c.role == SpeakerRole.NARRATOR

    def test_unknown_role_mapped_to_narrator(self) -> None:
        ch = _chapter([
            _line("Something.", SpeakerRole.UNKNOWN, True),
        ])
        chunks = chunk_annotated_chapter(ch)
        assert chunks[0].role == SpeakerRole.NARRATOR

    def test_chunk_indices_sequential(self) -> None:
        ch = _chapter([
            _line("\u041d\u0430\u0440\u0440\u0430\u0446\u0438\u044f.", SpeakerRole.NARRATOR, False),
            _line("\u0420\u0435\u043f\u043b\u0438\u043a\u0430.", SpeakerRole.MALE, True),
            _line("\u0415\u0449\u0451 \u043d\u0430\u0440\u0440\u0430\u0446\u0438\u044f.", SpeakerRole.NARRATOR, False),
        ])
        chunks = chunk_annotated_chapter(ch)
        for i, c in enumerate(chunks):
            assert c.index == i

    def test_empty_chapter(self) -> None:
        ch = AnnotatedChapter(chapter_index=0, chapter_title="", paragraphs=[])
        assert chunk_annotated_chapter(ch) == []

    def test_chapter_index_preserved(self) -> None:
        ch = _chapter([
            _line("Text.", SpeakerRole.NARRATOR, False),
        ], index=5)
        chunks = chunk_annotated_chapter(ch)
        assert chunks[0].chapter_index == 5


class TestChunkAnnotatedBook:

    def test_multiple_chapters(self) -> None:
        ch0 = _chapter([
            _line("\u0413\u043b\u0430\u0432\u0430 1.", SpeakerRole.NARRATOR, False),
        ], index=0)
        ch1 = _chapter([
            _line("\u0413\u043b\u0430\u0432\u0430 2.", SpeakerRole.NARRATOR, False),
            _line("\u0414\u0438\u0430\u043b\u043e\u0433.", SpeakerRole.MALE, True),
        ], index=1)
        result = chunk_annotated_book([ch0, ch1])
        assert 0 in result
        assert 1 in result
        assert len(result[0]) == 1
        assert len(result[1]) == 2

    def test_empty_list(self) -> None:
        result = chunk_annotated_book([])
        assert result == {}
