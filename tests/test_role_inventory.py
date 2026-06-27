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


def test_role_inventory_recovers_direct_speech_from_role_metadata() -> None:
    inventory = build_role_inventory(
        [
            {
                "role": "female",
                "speaker": "\u041c\u0430\u0440\u0433\u0430\u0440\u0438\u0442\u0430",
                "section_kind": "dialogue",
                "is_dialogue": False,
                "text": "\u0414\u0430!",
            },
            {
                "role": "narrator",
                "speaker": "\u041c\u0430\u0440\u0433\u0430\u0440\u0438\u0442\u0430",
                "section_kind": "narration",
                "is_dialogue": False,
                "text": "\u0441\u043a\u0430\u0437\u0430\u043b\u0430 \u043e\u043d\u0430.",
            },
        ],
        language="ru",
    )

    roles = inventory["roles"]
    margarita = next(
        role
        for role in roles
        if role["display_name"] == "\u041c\u0430\u0440\u0433\u0430\u0440\u0438\u0442\u0430"
    )
    assert margarita["direct_speech_count"] == 1
    assert inventory["total_direct_speech"] == 1
