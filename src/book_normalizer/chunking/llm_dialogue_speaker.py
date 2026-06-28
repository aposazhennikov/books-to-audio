"""Speaker inference helpers for repaired dialogue segments."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from book_normalizer.chunking.llm_dialogue_markers import (
    _contains_ru_attribution_word,
    _dash_starts_narrator_tag,
    _looks_like_direct_speech,
    _opening_quote_starts_direct_speech,
    _starts_with_direct_speech_marker,
    _take_quoted_speech,
)
from book_normalizer.chunking.llm_segmenter_config import (
    _CLOSING_QUOTE_BY_OPENING,
    _EN_FEMALE_ATTRIBUTION_RE,
    _EN_MALE_ATTRIBUTION_RE,
    _EN_SPEAKER_RE,
    _KK_ATTRIBUTION_RE,
    _KK_SPEAKER_TOKEN,
    _OPENING_QUOTE_CHARS,
    _RU_BAD_SPEAKER_TOKENS,
    _RU_FEMALE_ATTRIBUTION,
    _RU_FEMALE_ATTRIBUTION_RE,
    _RU_MALE_ATTRIBUTION,
    _RU_MALE_ATTRIBUTION_RE,
    _RU_SPEAKER_TOKEN,
    _SYSTEM_SECTION_KINDS,
    _UZ_ATTRIBUTION_RE,
    _UZ_SPEAKER_TOKEN,
    _ZH_BAD_SPEAKER_TOKENS,
    _ZH_FEMALE_ATTRIBUTION_RE,
    _ZH_MALE_ATTRIBUTION_RE,
    _ZH_SPEAKER_RE,
)
from book_normalizer.chunking.llm_segmenter_fields import _clean_optional
from book_normalizer.languages import normalize_book_language
from book_normalizer.normalization.morphology import infer_person_gender, is_definitely_not_person_reference

_RU_COMMON_PERSON_NOUN_GENDERS = {
    "барон": "male",
    "граф": "male",
    "князь": "male",
    "маркиз": "male",
    "мужчина": "male",
    "парень": "male",
    "старик": "male",
    "цыган": "male",
    "баронесса": "female",
    "графиня": "female",
    "девушка": "female",
    "женщина": "female",
    "княгиня": "female",
    "маркиза": "female",
    "старуха": "female",
    "цыганка": "female",
}
_RU_INANIMATE_SPEAKER_SUFFIXES = (
    "ание",
    "ение",
    "тие",
    "ство",
    "ость",
    "ное",
    "ское",
    "цкое",
    "гое",
)


def _repair_dialogue_metadata(
    *,
    role: str,
    speaker: str,
    section_kind: str,
    character_description: str,
    text: str,
    language: str,
    recent_dialogue_speakers: list[tuple[str, str]],
    force_narration: bool = False,
    force_dialogue: bool = False,
) -> tuple[str, str, str, str]:
    if section_kind in _SYSTEM_SECTION_KINDS:
        return role, speaker, section_kind, character_description
    if force_narration:
        return "narrator", "", "narration", ""
    if force_dialogue:
        if not section_kind or section_kind == "narration":
            section_kind = "dialogue"
        return role, speaker, section_kind, character_description

    if (
        role in {"male", "female", "unknown"}
        and section_kind == "dialogue"
        and not _looks_like_direct_speech(text, language)
        and (not speaker or _dialogue_markup_looks_like_narration(text, language))
    ):
        return "narrator", "", "narration", ""

    if (
        role == "narrator"
        and section_kind == "narration"
        and not speaker
        and _dash_starts_narrator_tag(text, language)
    ):
        return "narrator", "", "narration", ""

    if (
        section_kind == "dialogue"
        and language == "ru"
        and _dash_starts_narrator_tag(text, language)
        and _contains_ru_attribution_word(text)
    ):
        return "narrator", "", "narration", ""

    if not _has_direct_speech_marker(text, language):
        return role, speaker, section_kind, character_description

    inferred_speaker, inferred_role = _infer_dialogue_speaker(text, language)
    if inferred_speaker:
        speaker = speaker or inferred_speaker
    if inferred_role in {"male", "female"}:
        role = inferred_role
    if speaker:
        speaker_role = infer_person_gender(speaker)
        if speaker_role in {"male", "female"}:
            role = speaker_role

    if not speaker:
        speaker, known_role = _alternate_dialogue_speaker(recent_dialogue_speakers, role)
        if known_role in {"male", "female"} and role == "narrator":
            role = known_role

    if role == "narrator":
        role = "unknown"

    if not section_kind or section_kind == "narration":
        section_kind = "dialogue"
    if speaker and not character_description:
        character_description = "Direct-speech character inferred from local dialogue context."
    return role, speaker, section_kind, character_description

def _has_direct_speech_marker(text: str, language: str) -> bool:
    return _starts_with_direct_speech_marker(text, language)

def _dialogue_markup_looks_like_narration(text: str, language: str) -> bool:
    """Return true when LLM speaker markup contradicts the text shape."""
    stripped = str(text or "").strip()
    if not stripped:
        return False
    if stripped[0] in _OPENING_QUOTE_CHARS:
        quote = stripped[0]
        close_quote = _CLOSING_QUOTE_BY_OPENING.get(quote, quote)
        if stripped.find(close_quote, 1) < 0:
            return False
        speech, tail = _take_quoted_speech(stripped)
        if not tail and re.search(r"[.!?…][»\"'”’]?[.!?…]?\s*$", speech):
            return False
        return not _opening_quote_starts_direct_speech(stripped, language)
    if normalize_book_language(language) == "ru":
        return stripped[0].islower()
    return False

def _infer_dialogue_speaker(text: str, language: str) -> tuple[str, str]:
    language = normalize_book_language(language)
    if language == "ru":
        return _infer_ru_dialogue_speaker(text)
    if language == "en":
        return _infer_en_dialogue_speaker(text)
    if language == "zh":
        return _infer_zh_dialogue_speaker(text)
    if language == "kk":
        return _infer_regex_dialogue_speaker(text, _KK_ATTRIBUTION_RE, _clean_cyrillic_speaker)
    if language == "uz":
        return _infer_regex_dialogue_speaker(text, _UZ_ATTRIBUTION_RE, _clean_latin_speaker)
    return "", ""

def _infer_ru_dialogue_speaker(text: str) -> tuple[str, str]:
    candidates: list[tuple[int, str, str]] = []
    for regex, role in (
        (_RU_MALE_ATTRIBUTION_RE, "male"),
        (_RU_FEMALE_ATTRIBUTION_RE, "female"),
    ):
        for match in regex.finditer(text):
            speaker = _clean_ru_speaker(match.group("speaker"))
            if speaker:
                candidates.append((match.start(), speaker, role))
    for verbs, role in (
        (_RU_MALE_ATTRIBUTION, "male"),
        (_RU_FEMALE_ATTRIBUTION, "female"),
    ):
        speaker_before = re.compile(
            rf"\b(?P<speaker>{_RU_SPEAKER_TOKEN})\b"
            rf"(?:\s+[А-ЯЁа-яё-]{{1,30}}){{0,4}}\s+\b(?:{'|'.join(verbs)})\b",
            re.IGNORECASE,
        )
        for match in speaker_before.finditer(text):
            speaker = _clean_ru_speaker(match.group("speaker"))
            if speaker:
                candidates.append((match.start(), speaker, role))
    if candidates:
        _position, speaker, role = max(candidates, key=lambda item: item[0])
        return speaker, role
    if _text_has_ru_gendered_attribution(text, _RU_MALE_ATTRIBUTION):
        return "", "male"
    if _text_has_ru_gendered_attribution(text, _RU_FEMALE_ATTRIBUTION):
        return "", "female"
    pronoun_role = _infer_ru_pronoun_attribution_role(text)
    if pronoun_role:
        return "", pronoun_role
    return "", ""

def _infer_ru_pronoun_attribution_role(text: str) -> str:
    probe = text.casefold()
    if re.search(r"\b[а-яё]{3,}ла(?:сь)?\s+она\b|\bона\s+[а-яё]{3,}ла(?:сь)?\b", probe):
        return "female"
    if re.search(r"\b[а-яё]{3,}л(?:ся)?\s+он\b|\bон\s+[а-яё]{3,}л(?:ся)?\b", probe):
        return "male"

    if re.search(r"\b[а-яё]{3,}ла(?:сь)?\s+я\b", probe):
        return "female"
    if re.search(r"\b[а-яё]{3,}л(?:ся)?\s+я\b", probe):
        return "male"
    if re.search(r"\bя\s+(?:[а-яё]+\s+){0,3}[а-яё]{3,}ла(?:сь)?\b", probe):
        return "female"
    if re.search(r"\bя\s+(?:[а-яё]+\s+){0,3}[а-яё]{3,}л(?:ся)?\b", probe):
        return "male"
    return ""

def _infer_en_dialogue_speaker(text: str) -> tuple[str, str]:
    role = ""
    if _EN_MALE_ATTRIBUTION_RE.search(text or ""):
        role = "male"
    elif _EN_FEMALE_ATTRIBUTION_RE.search(text or ""):
        role = "female"
    match = _EN_SPEAKER_RE.search(text or "")
    if not match:
        return "", role
    speaker = _clean_optional(match.group("after") or match.group("before"))
    return speaker, role or ("unknown" if speaker else "")

def _infer_zh_dialogue_speaker(text: str) -> tuple[str, str]:
    role = ""
    if _ZH_MALE_ATTRIBUTION_RE.search(text or ""):
        role = "male"
    elif _ZH_FEMALE_ATTRIBUTION_RE.search(text or ""):
        role = "female"
    for match in _ZH_SPEAKER_RE.finditer(text or ""):
        speaker = _clean_zh_speaker(match.group("speaker"))
        if speaker:
            return speaker, role or "unknown"
    return "", role

def _infer_regex_dialogue_speaker(
    text: str,
    regex: re.Pattern[str],
    cleaner: Callable[[str], str],
) -> tuple[str, str]:
    for match in regex.finditer(text or ""):
        speaker = cleaner(match.group("speaker"))
        if speaker:
            return speaker, "unknown"
    return "", ""

def _clean_ru_speaker(value: str) -> str:
    speaker = re.sub(r"^[\s,.;:!?—–-]+|[\s,.;:!?—–-]+$", "", value or "")
    if not speaker:
        return ""
    if speaker.casefold() in _RU_BAD_SPEAKER_TOKENS:
        return ""
    if not re.fullmatch(_RU_SPEAKER_TOKEN, speaker):
        return ""
    speaker_gender = _infer_ru_speaker_gender_fallback(speaker)
    if _looks_like_ru_inanimate_speaker(speaker) and not speaker_gender:
        return ""
    if is_definitely_not_person_reference(speaker) and not speaker_gender:
        return ""
    if speaker[0].islower() and not speaker_gender:
        return ""
    if speaker[0].islower():
        speaker = speaker[0].upper() + speaker[1:]
    return _clean_optional(speaker)

def _infer_ru_speaker_gender_fallback(speaker: str) -> str:
    gender = infer_person_gender(speaker)
    if gender:
        return gender
    return _RU_COMMON_PERSON_NOUN_GENDERS.get(speaker.casefold(), "")

def _looks_like_ru_inanimate_speaker(speaker: str) -> bool:
    lowered = speaker.casefold()
    if lowered in _RU_COMMON_PERSON_NOUN_GENDERS:
        return False
    return lowered.endswith(_RU_INANIMATE_SPEAKER_SUFFIXES)

def _clean_speaker(value: Any, language: str) -> str:
    speaker = _clean_optional(value)
    if not speaker:
        return ""
    if normalize_book_language(language) != "ru":
        return speaker
    if len(speaker.split()) != 1:
        return speaker
    if not re.search(r"[А-ЯЁа-яё]", speaker):
        return speaker
    return _clean_ru_speaker(speaker)

def _clean_cyrillic_speaker(value: str) -> str:
    speaker = re.sub(r"^[\s,.;:!?—–-]+|[\s,.;:!?—–-]+$", "", value or "")
    if not re.fullmatch(_KK_SPEAKER_TOKEN, speaker or ""):
        return ""
    return _clean_optional(speaker)

def _clean_latin_speaker(value: str) -> str:
    speaker = re.sub(r"^[\s,.;:!?—–-]+|[\s,.;:!?—–-]+$", "", value or "")
    if not re.fullmatch(_UZ_SPEAKER_TOKEN, speaker or ""):
        return ""
    return _clean_optional(speaker)

def _clean_zh_speaker(value: str) -> str:
    speaker = re.sub(
        r"^[\s，。！？、；：“”‘’「」『』《》〈〉]+|[\s，。！？、；：“”‘’「」『』《》〈〉]+$",
        "",
        value or "",
    )
    if not speaker or speaker in _ZH_BAD_SPEAKER_TOKENS:
        return ""
    if not re.fullmatch(r"[\u3400-\u9fff]{1,12}", speaker):
        return ""
    return _clean_optional(speaker)

def _text_has_ru_gendered_attribution(text: str, verbs: tuple[str, ...]) -> bool:
    return bool(re.search(rf"\b(?:{'|'.join(verbs)})\b", text or "", re.IGNORECASE))

def _alternate_dialogue_speaker(
    recent_dialogue_speakers: list[tuple[str, str]],
    role: str,
) -> tuple[str, str]:
    if not recent_dialogue_speakers:
        return "", ""
    previous_speaker, _previous_role = recent_dialogue_speakers[-1]
    for speaker, speaker_role in reversed(recent_dialogue_speakers[:-1]):
        if speaker and speaker != previous_speaker:
            if role in {"male", "female"} and speaker_role not in {role, "unknown"}:
                continue
            return speaker, speaker_role
    return "", ""

def _narration_continuation_speaker(
    text: str,
    *,
    language: str,
    recent_dialogue_speakers: list[tuple[str, str]],
) -> tuple[str, str] | None:
    """Infer who keeps speaking after an adjacent author tag."""

    if normalize_book_language(language) != "ru":
        return None
    if not recent_dialogue_speakers or not _contains_ru_attribution_word(text):
        return None
    speaker, role = _infer_ru_dialogue_speaker(text)
    if speaker:
        return speaker, role if role in {"male", "female"} else infer_person_gender(speaker)
    if _dash_starts_narrator_tag(text, "ru"):
        return recent_dialogue_speakers[-1]
    return None

def _remember_dialogue_speaker(
    recent_dialogue_speakers: list[tuple[str, str]],
    *,
    speaker: str,
    role: str,
) -> None:
    if not speaker:
        return
    normalized_role = role if role in {"male", "female"} else "unknown"
    record = (speaker, normalized_role)
    if recent_dialogue_speakers and recent_dialogue_speakers[-1] == record:
        return
    recent_dialogue_speakers.append(record)
    del recent_dialogue_speakers[:-8]
