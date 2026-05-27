from __future__ import annotations

import pytest

from book_normalizer.chunking.dialogue_invariants import (
    assert_dialogue_chunk_boundaries,
    audit_dialogue_chunk_boundaries,
    audit_dialogue_speaker_assignments,
)


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


def test_boundary_assertion_rejects_manifest_issues() -> None:
    manifest = {
        "version": 2,
        "language": "ru",
        "chapters": [
            {
                "chapter_index": 0,
                "chunks": [
                    {
                        "chunk_index": 0,
                        "voice": "male",
                        "voice_id": "male_young",
                        "section_kind": "dialogue",
                        "text": "- Что случилось? - спросил он.",
                    }
                ],
            }
        ],
    }

    with pytest.raises(ValueError, match="Dialogue chunk boundary audit failed"):
        assert_dialogue_chunk_boundaries(manifest, language="ru")


def test_speaker_audit_warns_about_dialogue_on_narrator_voice() -> None:
    issues = audit_dialogue_speaker_assignments([
        {
            "chapter_index": 0,
            "chunk_index": 3,
            "role": "unknown",
            "voice_id": "narrator_calm",
            "section_kind": "dialogue",
            "speaker": "",
            "text": "- Кто здесь?",
        }
    ])

    assert [issue.kind for issue in issues] == ["dialogue_uses_narrator_voice"]
    assert issues[0].chapter_index == 0
    assert issues[0].chunk_index == 3


def test_speaker_audit_warns_about_role_voice_mismatch() -> None:
    issues = audit_dialogue_speaker_assignments([
        {
            "role": "female",
            "voice_id": "male_young",
            "section_kind": "dialogue",
            "speaker": "Анна",
            "text": "- Я тут.",
        }
    ])

    assert [issue.kind for issue in issues] == ["dialogue_role_voice_mismatch"]


def test_speaker_audit_warns_about_non_person_speaker_token() -> None:
    issues = audit_dialogue_speaker_assignments([
        {
            "role": "male",
            "voice_id": "male_young",
            "section_kind": "dialogue",
            "speaker": "Кто",
            "text": "- Я тут.",
        }
    ])

    assert [issue.kind for issue in issues] == ["dialogue_speaker_not_person"]


def test_speaker_audit_accepts_named_character_voice() -> None:
    issues = audit_dialogue_speaker_assignments([
        {
            "role": "male",
            "voice_id": "male_deep",
            "section_kind": "dialogue",
            "speaker": "Сергей",
            "text": "- Я тут.",
        }
    ])

    assert issues == []
