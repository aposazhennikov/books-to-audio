"""Helpers for mapping book roles/characters to concrete TTS speakers."""

from __future__ import annotations

from hashlib import sha1
from typing import Any

from book_normalizer.chunking.manifest_v2 import role_for_voice_id
from book_normalizer.normalization.morphology import infer_person_gender

NEUTRAL_EMOTIONS = {"", "neutral", "calm"}

AUTO_BUILTIN_VOICES_BY_ROLE = {
    "narrator": ("narrator_calm", "narrator_wise", "narrator_energetic"),
    "male": (
        "male_young",
        "male_confident",
        "male_deep",
        "male_lively",
        "male_regional",
    ),
    "female": (
        "female_warm",
        "female_bright",
        "female_playful",
        "female_gentle",
    ),
}

EMOTION_BUILTIN_VOICE_BY_ROLE = {
    "narrator": {
        "excited": "narrator_energetic",
        "joyful": "narrator_energetic",
        "cheerful": "narrator_energetic",
        "wise": "narrator_wise",
    },
    "male": {
        "angry": "male_confident",
        "tense": "male_confident",
        "assertive": "male_confident",
        "sad": "male_deep",
        "whisper": "male_deep",
        "excited": "male_lively",
        "joyful": "male_lively",
        "cheerful": "male_lively",
    },
    "female": {
        "angry": "female_bright",
        "tense": "female_bright",
        "assertive": "female_bright",
        "sad": "female_gentle",
        "whisper": "female_gentle",
        "excited": "female_playful",
        "joyful": "female_playful",
        "cheerful": "female_playful",
    },
}


def segment_speaker(segment: dict[str, Any]) -> str:
    """Return the character display name stored by LLM/GUI manifests."""
    for key in ("speaker", "character", "role_display_name"):
        value = str(segment.get(key) or "").strip()
        if value:
            return value
    return ""


def segment_emotion(segment: dict[str, Any]) -> str:
    """Return the role/emotion variant label if it is specific enough."""
    value = str(
        segment.get("emotion")
        or segment.get("voice_tone")
        or segment.get("intonation")
        or "",
    ).strip()
    return "" if value.casefold() in NEUTRAL_EMOTIONS else value


def canonical_role_for_segment(segment: dict[str, Any]) -> str:
    """Return narrator/male/female/unknown from segment metadata."""
    role = str(segment.get("role") or "").strip().lower()
    if role in {"narrator", "male", "female"}:
        return role
    if role == "unknown":
        inferred = infer_person_gender(segment_speaker(segment))
        return inferred or role

    voice_label = str(segment.get("voice_label") or "").strip().lower()
    if voice_label == "men":
        return "male"
    if voice_label == "women":
        return "female"
    if voice_label == "narrator":
        return "narrator"

    return role_for_voice_id(
        str(segment.get("voice_id") or ""),
        fallback="narrator",
    )


def voice_mapping_candidates(segment: dict[str, Any]) -> list[str]:
    """Return keys to try when resolving a saved voice for one chunk.

    Most specific keys are first.  A character/emotion variant such as
    ``speaker:Маргарита|emotion:sad`` can override the plain character
    ``speaker:Маргарита``; both can override broad gender/narrator defaults.
    """
    candidates: list[str] = []

    def add(key: str) -> None:
        key = key.strip()
        if key and key not in candidates:
            candidates.append(key)

    speaker = segment_speaker(segment)
    emotion = segment_emotion(segment)
    if speaker:
        if emotion:
            add(f"speaker:{speaker}|emotion:{emotion}")
        add(f"speaker:{speaker}")

    section = str(segment.get("section_kind") or "").strip().lower()
    if section:
        add(f"section:{section}")

    role = canonical_role_for_segment(segment)
    if role:
        add(role)

    voice_label = str(segment.get("voice_label") or "").strip().lower()
    if voice_label:
        add(voice_label)

    add("__all__")
    return candidates


def primary_voice_mapping_key(segment: dict[str, Any]) -> str:
    """Return the best UI mapping key for a manifest chunk."""
    for key in voice_mapping_candidates(segment):
        if key != "__all__":
            return key
    return "narrator"


def auto_builtin_voice_id_for_segment(segment: dict[str, Any]) -> str:
    """Return a stable built-in voice preset for a segment.

    The GUI has many detected character names, but Qwen ships with a small
    built-in speaker set. This spreads named characters across that set while
    keeping every occurrence of the same speaker on the same preset.
    """

    role = canonical_role_for_segment(segment)
    if role == "unknown" and str(segment.get("section_kind") or "").strip().lower() == "dialogue":
        role = "male"
    if role not in AUTO_BUILTIN_VOICES_BY_ROLE:
        role = "narrator"

    voices = AUTO_BUILTIN_VOICES_BY_ROLE[role]
    speaker = segment_speaker(segment)
    if speaker and role in {"male", "female"}:
        return voices[_stable_index(f"{role}:{speaker}", len(voices))]

    emotion = segment_emotion(segment).casefold()
    if emotion:
        mapped = EMOTION_BUILTIN_VOICE_BY_ROLE.get(role, {}).get(emotion)
        if mapped:
            return mapped

    return voices[0]


def apply_auto_builtin_voice_ids(segments: list[dict[str, Any]]) -> None:
    """Mutate segment records with stable built-in voice assignments."""

    for segment in segments:
        segment["voice_id"] = auto_builtin_voice_id_for_segment(segment)


def _stable_index(value: str, modulo: int) -> int:
    digest = sha1(value.casefold().encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % modulo
