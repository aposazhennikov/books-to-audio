from __future__ import annotations

from book_normalizer.chunking.role_inventory import build_role_inventory


def test_role_inventory_sorts_characters_and_emotion_variants() -> None:
    inventory = build_role_inventory(
        [
            {
                "role": "female",
                "speaker": "Маргарита",
                "character_description": "Смелая, резкая, эмоциональная.",
                "is_dialogue": True,
                "emotion": "joyful",
                "text": "Да!",
            },
            {
                "role": "female",
                "speaker": "Маргарита",
                "is_dialogue": True,
                "emotion": "fearful",
                "text": "Что это?",
            },
            {
                "role": "male",
                "speaker": "Воланд",
                "is_dialogue": True,
                "emotion": "cold",
                "text": "Никогда и ничего не просите.",
            },
            {
                "role": "narrator",
                "section_kind": "preface",
                "is_dialogue": False,
                "intonation": "calm",
                "text": "Предисловие.",
            },
            {
                "role": "narrator",
                "is_dialogue": False,
                "intonation": "calm",
                "text": "Авторский текст.",
            },
        ],
        language="ru",
    )

    roles = inventory["roles"]
    assert [role["display_name"] for role in roles[:3]] == [
        "Маргарита",
        "Воланд",
        "Narrator",
    ]
    margarita = roles[0]
    assert margarita["direct_speech_count"] == 2
    assert margarita["description"] == "Смелая, резкая, эмоциональная."
    assert margarita["voice_variants"] == [
        {"voice_key": "Маргарита-joyful", "count": 1},
        {"voice_key": "Маргарита-fearful", "count": 1},
    ]
    assert inventory["total_direct_speech"] == 3
    assert any(role["display_name"] == "Preface" for role in roles)
