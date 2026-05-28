from __future__ import annotations

from book_normalizer.tts.voice_mapping import (
    AUTO_BUILTIN_VOICES_BY_ROLE,
    apply_auto_builtin_voice_ids,
    auto_builtin_voice_id_for_segment,
    canonical_role_for_segment,
)


def test_auto_builtin_voice_mapping_spreads_named_male_characters() -> None:
    names = ["Drovosek", "Golem", "Lev", "Voin", "Set", "Otec"]
    voice_ids = [
        auto_builtin_voice_id_for_segment({"role": "male", "speaker": name})
        for name in names
    ]

    assert len(set(voice_ids)) > 1
    assert set(voice_ids) <= set(AUTO_BUILTIN_VOICES_BY_ROLE["male"])
    assert auto_builtin_voice_id_for_segment({"role": "male", "speaker": "Set"}) == (
        auto_builtin_voice_id_for_segment({"role": "male", "speaker": "Set"})
    )


def test_auto_builtin_voice_mapping_spreads_named_female_characters() -> None:
    names = ["Pandora", "Woman", "Margarita", "Anna", "Alice"]
    voice_ids = [
        auto_builtin_voice_id_for_segment({"role": "female", "speaker": name})
        for name in names
    ]

    assert len(set(voice_ids)) > 1
    assert set(voice_ids) <= set(AUTO_BUILTIN_VOICES_BY_ROLE["female"])


def test_auto_builtin_voice_mapping_uses_emotion_for_unnamed_dialogue() -> None:
    assert auto_builtin_voice_id_for_segment({"role": "male", "emotion": "tense"}) == (
        "male_confident"
    )
    assert auto_builtin_voice_id_for_segment({"role": "female", "emotion": "whisper"}) == (
        "female_gentle"
    )
    assert auto_builtin_voice_id_for_segment({"role": "narrator"}) == "narrator_calm"


def test_unknown_dialogue_uses_character_voice_not_narrator() -> None:
    segment = {"role": "unknown", "section_kind": "dialogue", "text": "- Кто здесь?"}

    assert canonical_role_for_segment(segment) == "unknown"
    assert auto_builtin_voice_id_for_segment(segment).startswith("male_")


def test_unknown_russian_named_speaker_gets_character_voice() -> None:
    male = {"role": "unknown", "section_kind": "dialogue", "speaker": "Сергей"}
    dictionary_gap_male = {"role": "unknown", "section_kind": "dialogue", "speaker": "Мерлин"}
    inflected_male = {"role": "unknown", "section_kind": "dialogue", "speaker": "Агамемнону"}
    common_gender_named_male = {"role": "unknown", "section_kind": "dialogue", "speaker": "Страшила"}
    foreign_i_male = {"role": "unknown", "section_kind": "dialogue", "speaker": "Перси"}
    foreign_o_male = {"role": "unknown", "section_kind": "dialogue", "speaker": "Белскудо"}
    female = {"role": "unknown", "section_kind": "dialogue", "speaker": "женщина"}
    diminutive = {"role": "unknown", "section_kind": "dialogue", "speaker": "Лизочка"}
    inanimate = {"role": "unknown", "section_kind": "dialogue", "speaker": "Предмет"}

    assert canonical_role_for_segment(male) == "male"
    assert canonical_role_for_segment(dictionary_gap_male) == "male"
    assert canonical_role_for_segment(inflected_male) == "male"
    assert canonical_role_for_segment(common_gender_named_male) == "male"
    assert canonical_role_for_segment(foreign_i_male) == "male"
    assert canonical_role_for_segment(foreign_o_male) == "male"
    assert canonical_role_for_segment(female) == "female"
    assert canonical_role_for_segment(diminutive) == "female"
    assert canonical_role_for_segment(inanimate) == "unknown"
    assert auto_builtin_voice_id_for_segment(male).startswith("male_")
    assert auto_builtin_voice_id_for_segment(common_gender_named_male).startswith("male_")
    assert auto_builtin_voice_id_for_segment(foreign_i_male).startswith("male_")
    assert auto_builtin_voice_id_for_segment(foreign_o_male).startswith("male_")
    assert auto_builtin_voice_id_for_segment(female).startswith("female_")
    assert auto_builtin_voice_id_for_segment(diminutive).startswith("female_")


def test_apply_auto_builtin_voice_ids_mutates_segments() -> None:
    segments = [
        {"role": "male", "speaker": "Drovosek", "voice_id": "male_young"},
        {"role": "female", "speaker": "Pandora", "voice_id": "female_warm"},
    ]

    apply_auto_builtin_voice_ids(segments)

    assert segments[0]["voice_id"] == auto_builtin_voice_id_for_segment(segments[0])
    assert segments[1]["voice_id"] == auto_builtin_voice_id_for_segment(segments[1])
