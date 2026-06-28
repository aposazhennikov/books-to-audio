"""Tests for voice-annotated chunking."""

from __future__ import annotations

from book_normalizer.chunking.annotations import classify_chapter_paragraphs
from book_normalizer.chunking.dialogue_invariants import audit_dialogue_chunk_boundaries
from book_normalizer.chunking.splitter import (
    DEFAULT_CHAPTER_PAUSE_MS,
    DEFAULT_PARAGRAPH_PAUSE_MS,
)
from book_normalizer.chunking.voice_splitter import (
    build_chunks_from_segments,
    chunk_annotated_book,
    chunk_annotated_chapter,
    extract_segments_chapter,
)
from book_normalizer.dialogue.models import (
    AnnotatedChapter,
    AnnotatedParagraph,
    DialogueLine,
    SpeakerRole,
)
from book_normalizer.models.book import Paragraph


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
            _line(
                "\u0417\u0434\u0440\u0430\u0432\u0441\u0442\u0432\u0443\u0439\u0442\u0435!",
                SpeakerRole.FEMALE,
                True,
            ),
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
        sentence = (
            "\u041f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u0438\u0435 "
            "\u043d\u043e\u043c\u0435\u0440 "
            "\u043e\u0434\u0438\u043d. "
        )
        long_text = sentence * 200
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

    def test_unknown_dialogue_stays_separate_from_narration(self) -> None:
        ch = _chapter([
            _line("Narration.", SpeakerRole.NARRATOR, False),
            _line("Manual speech.", SpeakerRole.UNKNOWN, True),
            _line("More narration.", SpeakerRole.NARRATOR, False),
        ])

        segments = extract_segments_chapter(ch)
        chunks = chunk_annotated_chapter(ch)

        assert len(segments) == 3
        assert segments[1].is_dialogue
        assert segments[1].role == SpeakerRole.UNKNOWN
        assert len(chunks) == 3

    def test_segment_builder_preserves_unknown_dialogue_role(self) -> None:
        segments = [
            {
                "chapter_index": 0,
                "segment_index": 0,
                "language": "ru",
                "role": "unknown",
                "voice_id": "narrator_calm",
                "section_kind": "dialogue",
                "text": "- Кто здесь?",
                "intonation": "tense",
            },
        ]

        chunks = build_chunks_from_segments(segments)

        assert chunks[0]["role"] == "unknown"
        assert chunks[0]["section_kind"] == "dialogue"

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

    def test_segments_keep_paragraph_and_chapter_pause_metadata(self) -> None:
        ch = AnnotatedChapter(
            chapter_index=0,
            chapter_title="Ch0",
            paragraphs=[
                AnnotatedParagraph(
                    paragraph_id="p0",
                    chapter_index=0,
                    lines=[
                        DialogueLine(
                            text="First paragraph.",
                            role=SpeakerRole.NARRATOR,
                            paragraph_id="p0",
                            line_index=0,
                            is_dialogue=False,
                        ),
                    ],
                ),
                AnnotatedParagraph(
                    paragraph_id="p1",
                    chapter_index=0,
                    lines=[
                        DialogueLine(
                            text="Second paragraph.",
                            role=SpeakerRole.NARRATOR,
                            paragraph_id="p1",
                            line_index=0,
                            is_dialogue=False,
                        ),
                    ],
                ),
            ],
        )

        segments = extract_segments_chapter(ch)

        assert len(segments) == 2
        assert segments[0].boundary_after == "paragraph"
        assert segments[0].pause_after_ms == DEFAULT_PARAGRAPH_PAUSE_MS
        assert segments[1].boundary_after == "chapter"
        assert segments[1].pause_after_ms == DEFAULT_CHAPTER_PAUSE_MS

    def test_extract_segments_marks_leading_epigraph(self) -> None:
        ch = AnnotatedChapter(
            chapter_index=0,
            chapter_title="Глава первая",
            paragraphs=[
                AnnotatedParagraph(
                    paragraph_id="p0",
                    chapter_index=0,
                    lines=[
                        DialogueLine(
                            text="Веревка есть вервие простое. Из учебного наставления для палачей",
                            role=SpeakerRole.NARRATOR,
                            paragraph_id="p0",
                            line_index=0,
                            is_dialogue=False,
                        ),
                    ],
                ),
                AnnotatedParagraph(
                    paragraph_id="p1",
                    chapter_index=0,
                    lines=[
                        DialogueLine(
                            text="Глава первая, повествующая в общем-то ни о чем",
                            role=SpeakerRole.NARRATOR,
                            paragraph_id="p1",
                            line_index=0,
                            is_dialogue=False,
                        ),
                    ],
                ),
                AnnotatedParagraph(
                    paragraph_id="p2",
                    chapter_index=0,
                    lines=[
                        DialogueLine(
                            text="Сергей сидел за столом.",
                            role=SpeakerRole.NARRATOR,
                            paragraph_id="p2",
                            line_index=0,
                            is_dialogue=False,
                        ),
                    ],
                ),
            ],
        )

        segments = extract_segments_chapter(ch, detect_special_sections=True)

        assert segments[0].section_kind == "epigraph"
        assert segments[0].voice_id == "narrator_wise"
        assert segments[1].section_kind == ""

    def test_classify_epigraph_accepts_paragraph_objects_and_ocr_noise(self) -> None:
        paragraphs = [
            Paragraph(
                raw_text=". . - у . Краткость - родная сестра таланта "
                "и сводная сестра безработицы. Из библии для чиновников"
            ),
            Paragraph(raw_text="ГЛАВА ТРЕТЬЯ"),
            Paragraph(raw_text="СОБЫТИЯ В КОТОРОЙ РАЗВИВАЮТСЯ ВО СНЕ"),
        ]

        assert classify_chapter_paragraphs(paragraphs)[:2] == ["epigraph", ""]


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


class TestBuildChunksFromSegments:

    def test_chunk_index_resets_per_chapter(self) -> None:
        segments = [
            {
                "chapter_index": 0,
                "voice_id": "narrator_calm",
                "intonation": "neutral",
                "role": "narrator",
                "text": "Chapter one.",
            },
            {
                "chapter_index": 1,
                "voice_id": "narrator_calm",
                "intonation": "neutral",
                "role": "narrator",
                "text": "Chapter two.",
            },
        ]

        chunks = build_chunks_from_segments(segments)

        assert [chunk["chapter_index"] for chunk in chunks] == [0, 1]
        assert [chunk["chunk_index"] for chunk in chunks] == [0, 0]

    def test_role_is_inferred_from_assigned_voice_id(self) -> None:
        segments = [
            {
                "chapter_index": 0,
                "voice_id": "male_young",
                "intonation": "neutral",
                "role": "narrator",
                "text": "Manually assigned dialogue.",
            },
        ]

        chunks = build_chunks_from_segments(segments)

        assert chunks[0]["role"] == "male"

    def test_dialogue_section_with_narrator_voice_gets_character_voice(self) -> None:
        segments = [
            {
                "chapter_index": 0,
                "language": "ru",
                "voice_id": "narrator_calm",
                "intonation": "questioning",
                "role": "narrator",
                "section_kind": "dialogue",
                "text": "А вы кто? — спросил",
            },
        ]

        chunks = build_chunks_from_segments(segments)

        assert chunks[0]["role"] in {"male", "female", "unknown"}
        assert chunks[0]["voice_id"] != "narrator_calm"

    def test_character_metadata_prevents_wrong_dialogue_merge(self) -> None:
        segments = [
            {
                "chapter_index": 0,
                "voice_id": "female_warm",
                "intonation": "joyful",
                "role": "female",
                "speaker": "Маргарита",
                "character_description": "Смелая.",
                "emotion": "joyful",
                "section_kind": "dialogue",
                "text": "Я здесь.",
            },
            {
                "chapter_index": 0,
                "voice_id": "female_warm",
                "intonation": "joyful",
                "role": "female",
                "speaker": "Аннушка",
                "character_description": "Бытовая и резкая.",
                "emotion": "joyful",
                "section_kind": "dialogue",
                "text": "И я тоже.",
            },
        ]

        chunks = build_chunks_from_segments(segments)

        assert [chunk["speaker"] for chunk in chunks] == ["Маргарита", "Аннушка"]
        assert [chunk["text"] for chunk in chunks] == ["Я здесь.", "И я тоже."]

    def test_paragraph_pause_flushes_same_voice_chunks(self) -> None:
        segments = [
            {
                "chapter_index": 0,
                "voice_id": "narrator_calm",
                "intonation": "neutral",
                "role": "narrator",
                "text": "First paragraph.",
                "pause_after_ms": DEFAULT_PARAGRAPH_PAUSE_MS,
                "boundary_after": "paragraph",
            },
            {
                "chapter_index": 0,
                "voice_id": "narrator_calm",
                "intonation": "neutral",
                "role": "narrator",
                "text": "Second paragraph.",
            },
        ]

        chunks = build_chunks_from_segments(segments)

        assert len(chunks) == 2
        assert chunks[0]["pause_after_ms"] == DEFAULT_PARAGRAPH_PAUSE_MS
        assert chunks[0]["boundary_after"] == "paragraph"

    def test_repaired_narrator_chunks_are_coalesced_after_dialogue_demotion(self) -> None:
        segments = [
            {
                "chapter_index": 0,
                "language": "ru",
                "voice_id": "male_young",
                "intonation": "calm",
                "role": "male",
                "section_kind": "dialogue",
                "text": (
                    "Но благостный Осирис сказал, что от наколдованной водки он косеет, "
                    "а Гор,"
                ),
            },
            {
                "chapter_index": 0,
                "language": "ru",
                "voice_id": "narrator_calm",
                "intonation": "calm",
                "role": "narrator",
                "section_kind": "narration",
                "text": "- он указал перстом на великолепного бога - блюёт.",
            },
        ]

        chunks = build_chunks_from_segments(segments)

        assert len(chunks) == 1
        assert chunks[0]["role"] == "narrator"
        assert chunks[0]["voice_id"] == "narrator_calm"
        assert chunks[0]["text"] == (
            "Но благостный Осирис сказал, что от наколдованной водки он косеет, "
            "а Гор, - он указал перстом на великолепного бога - блюёт."
        )

    def test_build_chunks_repairs_stale_llm_dialogue_boundaries(self) -> None:
        segments = [
            {
                "chapter_index": 0,
                "language": "ru",
                "voice_id": "narrator_calm",
                "role": "narrator",
                "section_kind": "narration",
                "intonation": "calm",
                "text": "И тут вновь появился злой бог Сет. «",
            },
            {
                "chapter_index": 0,
                "language": "ru",
                "voice_id": "male_young",
                "role": "male",
                "section_kind": "dialogue",
                "intonation": "tense",
                "text": "Что-то сдохло?» - спросил потянув носом воздух.",
            },
            {
                "chapter_index": 0,
                "language": "ru",
                "voice_id": "male_young",
                "role": "male",
                "section_kind": "dialogue",
                "intonation": "tense",
                "text": "Но увидев сию деву, бог явственно вздрогнул.",
            },
        ]

        chunks = build_chunks_from_segments(segments)

        assert [chunk["text"] for chunk in chunks] == [
            "И тут вновь появился злой бог Сет.",
            "«Что-то сдохло?»",
            "- спросил потянув носом воздух.",
            "Но увидев сию деву, бог явственно вздрогнул.",
        ]
        assert [chunk["voice_id"] for chunk in chunks] == [
            "narrator_calm",
            "male_confident",
            "narrator_calm",
            "narrator_calm",
        ]

    def test_build_chunks_repairs_boundaries_after_text_subchunking(self) -> None:
        segments = [
            {
                "chapter_index": 0,
                "language": "ru",
                "voice_id": "male_young",
                "role": "male",
                "section_kind": "dialogue",
                "intonation": "calm",
                "text": "«Неужели это работает?» — подумал Сергей. «Проверим позже,, решил маркиз.",
            },
        ]

        chunks = build_chunks_from_segments(segments, max_chunk_chars=120)

        assert [chunk["text"] for chunk in chunks] == [
            "«Неужели это работает?»",
            "— подумал Сергей.",
            "«Проверим позже,,",
            "решил маркиз.",
        ]
        assert [chunk["role"] for chunk in chunks] == ["male", "narrator", "male", "narrator"]
        assert [chunk["chunk_index"] for chunk in chunks] == [0, 1, 2, 3]

    def test_build_chunks_refreshes_default_character_voice_ids(self) -> None:
        segments = [
            {
                "chapter_index": 0,
                "voice_id": "male_young",
                "role": "male",
                "speaker": "Drovosek",
                "intonation": "calm",
                "text": "First line.",
            },
            {
                "chapter_index": 0,
                "voice_id": "male_young",
                "role": "male",
                "speaker": "Voin",
                "intonation": "calm",
                "text": "Second line.",
            },
        ]

        chunks = build_chunks_from_segments(segments)

        assert [chunk["voice_id"] for chunk in chunks] == [
            "male_confident",
            "male_young",
        ]

    def test_build_chunks_splits_quoted_inner_thought_from_author_tag(self) -> None:
        segments = [
            {
                "chapter_index": 0,
                "language": "ru",
                "voice_id": "male_young",
                "role": "male",
                "section_kind": "inner_thought",
                "intonation": "tense",
                "text": "«Действительно, — подумал Сергей».",
            },
        ]

        chunks = build_chunks_from_segments(segments, max_chunk_chars=600)

        assert audit_dialogue_chunk_boundaries(chunks, language="ru") == []
        assert [chunk["role"] for chunk in chunks] == ["male", "narrator"]
        assert chunks[0]["section_kind"] == "inner_thought"
        assert chunks[1]["section_kind"] == "narration"
        assert chunks[0]["text"] == "«Действительно,"
        assert chunks[1]["text"] == "— подумал Сергей»."

    def test_build_chunks_splits_inner_thought_continuation_after_author_tag(self) -> None:
        segments = [
            {
                "chapter_index": 0,
                "language": "ru",
                "voice_id": "male_young",
                "role": "male",
                "section_kind": "inner_thought",
                "intonation": "tense",
                "text": "«Действительно, — подумал Сергей, — все идет наперекосяк».",
            },
        ]

        chunks = build_chunks_from_segments(segments, max_chunk_chars=600)

        assert audit_dialogue_chunk_boundaries(chunks, language="ru") == []
        assert [chunk["role"] for chunk in chunks] == ["male", "narrator", "male"]
        assert [chunk["section_kind"] for chunk in chunks] == [
            "inner_thought",
            "narration",
            "inner_thought",
        ]
        assert chunks[0]["text"] == "«Действительно,"
        assert chunks[1]["text"] == "— подумал Сергей,"
        assert chunks[2]["text"] == "— все идет наперекосяк»."
