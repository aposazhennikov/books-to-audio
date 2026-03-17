"""Voice presets for Qwen3-TTS CustomVoice — expanded speaker library.

Qwen3-TTS supports 9 built-in speakers. Each preset combines a speaker
timbre with a Russian-language instruct prompt to create a distinct voice
character for audiobook narration.
"""

from __future__ import annotations

from dataclasses import dataclass

PREVIEW_PHRASE_RU = (
    "Сергей сидел за столом и пил чай с малиновым вареньем. "
    "Состояние было весьма тоскливым."
)

PREVIEW_PHRASE_EN = (
    "The quick brown fox jumps over the lazy dog. "
    "Every morning brings new hope and opportunities."
)


@dataclass(frozen=True)
class VoicePreset:
    """Single voice preset definition."""

    id: str
    speaker: str
    instruct: str
    label_en: str
    label_ru: str
    category: str
    description_en: str
    description_ru: str


VOICE_PRESETS: list[VoicePreset] = [
    # ── Narrators ──
    VoicePreset(
        id="narrator_calm",
        speaker="Aiden",
        instruct=(
            "Спокойный, чёткий голос рассказчика. "
            "Читай размеренно, с правильными паузами и естественной интонацией. "
            "Не торопись."
        ),
        label_en="Narrator — Calm",
        label_ru="Диктор — Спокойный",
        category="narrator",
        description_en="Calm, steady narrator. Clear diction, measured pace.",
        description_ru="Спокойный диктор. Чёткая дикция, размеренный темп.",
    ),
    VoicePreset(
        id="narrator_energetic",
        speaker="Ryan",
        instruct=(
            "Энергичный, уверенный голос рассказчика. "
            "Читай бодро, с выразительной интонацией. "
            "Подчёркивай ключевые моменты."
        ),
        label_en="Narrator — Energetic",
        label_ru="Диктор — Энергичный",
        category="narrator",
        description_en="Dynamic narrator. Confident, expressive reading.",
        description_ru="Энергичный диктор. Уверенное, выразительное чтение.",
    ),
    VoicePreset(
        id="narrator_wise",
        speaker="Uncle_Fu",
        instruct=(
            "Мудрый, опытный голос рассказчика. "
            "Читай неторопливо, с глубиной и значительностью. "
            "Голос опытного человека."
        ),
        label_en="Narrator — Wise",
        label_ru="Диктор — Мудрый",
        category="narrator",
        description_en="Seasoned, wise narrator. Deep timbre, unhurried pace.",
        description_ru="Мудрый диктор. Глубокий тембр, неторопливый темп.",
    ),

    # ── Male voices ──
    VoicePreset(
        id="male_young",
        speaker="Ryan",
        instruct=(
            "Молодой мужской голос. "
            "Говори с эмоцией, соответствующей контексту диалога. "
            "Естественные интонации молодого человека."
        ),
        label_en="Male — Young",
        label_ru="Мужской — Молодой",
        category="male",
        description_en="Young dynamic male. Emotional, natural intonation.",
        description_ru="Молодой динамичный голос. Эмоциональная интонация.",
    ),
    VoicePreset(
        id="male_confident",
        speaker="Aiden",
        instruct=(
            "Уверенный мужской голос среднего возраста. "
            "Говори чётко и решительно. "
            "Спокойная уверенность."
        ),
        label_en="Male — Confident",
        label_ru="Мужской — Уверенный",
        category="male",
        description_en="Confident middle-aged male. Clear, decisive.",
        description_ru="Уверенный голос среднего возраста. Чёткий, решительный.",
    ),
    VoicePreset(
        id="male_deep",
        speaker="Uncle_Fu",
        instruct=(
            "Глубокий мужской голос. "
            "Говори с достоинством и весомостью. "
            "Баритон, неторопливая речь."
        ),
        label_en="Male — Deep",
        label_ru="Мужской — Глубокий",
        category="male",
        description_en="Deep baritone. Dignified, weighty speech.",
        description_ru="Глубокий баритон. Достойная, весомая речь.",
    ),
    VoicePreset(
        id="male_lively",
        speaker="Dylan",
        instruct=(
            "Живой, весёлый мужской голос. "
            "Говори бодро, с юмором и лёгкостью. "
            "Молодой и обаятельный."
        ),
        label_en="Male — Lively",
        label_ru="Мужской — Живой",
        category="male",
        description_en="Lively, cheerful male. Humorous, charming.",
        description_ru="Живой, весёлый голос. С юмором и лёгкостью.",
    ),
    VoicePreset(
        id="male_regional",
        speaker="Eric",
        instruct=(
            "Яркий мужской голос с характером. "
            "Говори экспрессивно, с выражением. "
            "Харизматичная речь."
        ),
        label_en="Male — Expressive",
        label_ru="Мужской — Экспрессивный",
        category="male",
        description_en="Expressive male with character. Charismatic speech.",
        description_ru="Экспрессивный голос с характером. Харизматичная речь.",
    ),

    # ── Female voices ──
    VoicePreset(
        id="female_warm",
        speaker="Serena",
        instruct=(
            "Мягкий, тёплый женский голос. "
            "Говори нежно, с теплотой и заботой. "
            "Естественные интонации."
        ),
        label_en="Female — Warm",
        label_ru="Женский — Тёплый",
        category="female",
        description_en="Warm, gentle female. Tender, caring intonation.",
        description_ru="Тёплый, мягкий голос. Нежная, заботливая интонация.",
    ),
    VoicePreset(
        id="female_bright",
        speaker="Vivian",
        instruct=(
            "Яркий, звонкий женский голос. "
            "Говори выразительно и энергично. "
            "Молодая, уверенная женщина."
        ),
        label_en="Female — Bright",
        label_ru="Женский — Яркий",
        category="female",
        description_en="Bright, clear female. Expressive, energetic.",
        description_ru="Яркий, звонкий голос. Выразительная, энергичная.",
    ),
    VoicePreset(
        id="female_playful",
        speaker="Ono_Anna",
        instruct=(
            "Игривый женский голос. "
            "Говори легко, с улыбкой в голосе. "
            "Кокетливая и весёлая."
        ),
        label_en="Female — Playful",
        label_ru="Женский — Игривый",
        category="female",
        description_en="Playful female. Light, smiling voice.",
        description_ru="Игривый голос. Лёгкая, улыбчивая речь.",
    ),
    VoicePreset(
        id="female_gentle",
        speaker="Sohee",
        instruct=(
            "Нежный, мелодичный женский голос. "
            "Говори спокойно и ласково. "
            "Мягкая, успокаивающая речь."
        ),
        label_en="Female — Gentle",
        label_ru="Женский — Нежный",
        category="female",
        description_en="Gentle, melodic female. Soft, soothing speech.",
        description_ru="Нежный, мелодичный голос. Мягкая, успокаивающая речь.",
    ),
]

PRESET_BY_ID: dict[str, VoicePreset] = {p.id: p for p in VOICE_PRESETS}

LEGACY_VOICE_MAP: dict[str, str] = {
    "narrator": "narrator_calm",
    "male": "male_young",
    "female": "female_warm",
}


def get_preset(voice_id: str) -> VoicePreset:
    """Get a voice preset by id, with fallback for legacy ids."""
    if voice_id in PRESET_BY_ID:
        return PRESET_BY_ID[voice_id]
    mapped = LEGACY_VOICE_MAP.get(voice_id)
    if mapped and mapped in PRESET_BY_ID:
        return PRESET_BY_ID[mapped]
    return PRESET_BY_ID["narrator_calm"]
