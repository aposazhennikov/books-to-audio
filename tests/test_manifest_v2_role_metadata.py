from __future__ import annotations

from book_normalizer.chunking.manifest_v2 import chunks_to_manifest, flatten_manifest


def test_v2_manifest_preserves_role_metadata_for_voice_mapping() -> None:
    manifest = chunks_to_manifest(
        [
            {
                "chapter_index": 0,
                "chunk_index": 0,
                "role": "female",
                "voice_id": "female_warm",
                "speaker": "Маргарита",
                "character_description": "Смелая.",
                "emotion": "joyful",
                "section_kind": "dialogue",
                "text": "Я здесь.",
            }
        ],
        book_title="Book",
        language="ru",
    ).to_record()

    chunk = flatten_manifest(manifest)[0]

    assert chunk["speaker"] == "Маргарита"
    assert chunk["character_description"] == "Смелая."
    assert chunk["emotion"] == "joyful"
    assert chunk["section_kind"] == "dialogue"
