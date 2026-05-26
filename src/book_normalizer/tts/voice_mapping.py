"""Helpers for mapping book roles/characters to concrete TTS speakers."""

from __future__ import annotations

from typing import Any

from book_normalizer.chunking.manifest_v2 import role_for_voice_id

NEUTRAL_EMOTIONS = {"", "neutral", "calm"}


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
    if role in {"narrator", "male", "female", "unknown"}:
        return role

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
