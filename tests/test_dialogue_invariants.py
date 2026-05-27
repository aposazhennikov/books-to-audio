from __future__ import annotations

from book_normalizer.chunking.dialogue_invariants import audit_dialogue_chunk_boundaries


def test_audit_accepts_clean_dialogue_and_narration_chunks() -> None:
    chunks = [
        {
            "chapter_index": 0,
            "chunk_index": 0,
            "role": "male",
            "section_kind": "dialogue",
            "text": "- Что это?",
        },
        {
            "chapter_index": 0,
            "chunk_index": 1,
            "role": "narrator",
            "section_kind": "narration",
            "text": "- спросил он, наконец, дрогнувшим голосом.",
        },
        {
            "chapter_index": 0,
            "chunk_index": 2,
            "role": "narrator",
            "section_kind": "narration",
            "text": "Название «Вольфшанце» — волчье логово осталось в памяти.",
        },
    ]

    assert audit_dialogue_chunk_boundaries(chunks, language="ru") == []


def test_audit_flags_dialogue_chunk_with_author_tag() -> None:
    issues = audit_dialogue_chunk_boundaries([
        {
            "chapter_index": 1,
            "chunk_index": 2,
            "role": "male",
            "section_kind": "dialogue",
            "text": "- Что это? - спросил он.",
        },
    ])

    assert [issue.kind for issue in issues] == ["dialogue_contains_author_tag"]
    assert issues[0].chapter_index == 1
    assert issues[0].chunk_index == 2


def test_audit_flags_narration_chunk_that_starts_with_direct_speech() -> None:
    issues = audit_dialogue_chunk_boundaries([
        {
            "role": "narrator",
            "section_kind": "narration",
            "text": "- Взрывайтесь немедленно!",
        },
    ])

    assert [issue.kind for issue in issues] == ["narration_starts_with_direct_speech"]


def test_audit_flags_author_tag_with_next_direct_speech() -> None:
    issues = audit_dialogue_chunk_boundaries([
        {
            "role": "narrator",
            "section_kind": "narration",
            "text": "- признался - Ой, как все запущено,",
        },
    ])

    assert [issue.kind for issue in issues] == ["narration_contains_next_direct_speech"]


def test_audit_does_not_flag_speech_with_attribution_word_inside_phrase() -> None:
    issues = audit_dialogue_chunk_boundaries([
        {
            "role": "female",
            "section_kind": "dialogue",
            "text": "- Я сказала руки за голову!",
        },
    ])

    assert issues == []
