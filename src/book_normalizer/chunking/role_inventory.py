"""Role inventory derived from voice segment manifests."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

SYSTEM_ROLE_NAMES = {
    "annotation": "Annotation",
    "preface": "Preface",
    "epilogue": "Epilogue",
    "chapter_title": "Chapter title",
}


@dataclass
class RoleProfile:
    """A character/system role prepared for audiobook casting."""

    role_id: str
    display_name: str
    category: str
    description: str = ""
    direct_speech_count: int = 0
    segment_count: int = 0
    emotion_counts: Counter[str] = field(default_factory=Counter)

    def to_dict(self) -> dict[str, Any]:
        emotions = [
            {"emotion": emotion, "count": count}
            for emotion, count in self.emotion_counts.most_common()
        ]
        return {
            "role_id": self.role_id,
            "display_name": self.display_name,
            "category": self.category,
            "description": self.description,
            "direct_speech_count": self.direct_speech_count,
            "segment_count": self.segment_count,
            "emotions": emotions,
            "voice_variants": [
                {
                    "voice_key": f"{self.display_name}-{item['emotion']}",
                    "count": item["count"],
                }
                for item in emotions
            ],
        }


def build_role_inventory(
    segments: list[dict[str, Any]],
    *,
    language: str = "ru",
) -> dict[str, Any]:
    """Build a sorted role inventory from segment-manifest rows."""

    profiles: dict[str, RoleProfile] = {}
    total_direct = 0
    for segment in segments:
        display_name, category = _role_name_and_category(segment)
        role_id = _role_id(display_name)
        profile = profiles.get(role_id)
        if profile is None:
            profile = RoleProfile(
                role_id=role_id,
                display_name=display_name,
                category=category,
                description=_description_for(segment, display_name, category),
            )
            profiles[role_id] = profile

        profile.segment_count += 1
        if _is_direct_speech(segment):
            profile.direct_speech_count += 1
            total_direct += 1
        emotion = _emotion_for(segment)
        if emotion:
            profile.emotion_counts[emotion] += 1
        description = _description_for(segment, display_name, category)
        if description and not profile.description:
            profile.description = description

    roles = sorted(
        profiles.values(),
        key=lambda profile: (
            -profile.direct_speech_count,
            -profile.segment_count,
            profile.category != "dialogue",
            profile.display_name.casefold(),
        ),
    )
    return {
        "language": language,
        "total_segments": len(segments),
        "total_direct_speech": total_direct,
        "roles": [profile.to_dict() for profile in roles],
    }


def _role_name_and_category(segment: dict[str, Any]) -> tuple[str, str]:
    section_kind = str(segment.get("section_kind") or "").strip().lower()
    if section_kind in SYSTEM_ROLE_NAMES:
        return SYSTEM_ROLE_NAMES[section_kind], "system"

    speaker = (
        segment.get("speaker")
        or segment.get("character")
        or segment.get("role_display_name")
        or ""
    )
    speaker_text = str(speaker).strip()
    if speaker_text:
        return speaker_text, "dialogue" if _is_direct_speech(segment) else "narration"

    role = str(segment.get("role") or "narrator").strip().lower()
    if role == "male":
        return "Male character", "dialogue"
    if role == "female":
        return "Female character", "dialogue"
    return "Narrator", "narration"


def _description_for(segment: dict[str, Any], display_name: str, category: str) -> str:
    for key in ("character_description", "role_description", "description"):
        value = str(segment.get(key) or "").strip()
        if value:
            return value
    if category == "system":
        return f"System narration block for {display_name.lower()}."
    if category == "dialogue":
        return "Direct-speech role detected in the book."
    return "Narrator and authorial prose."


def _is_direct_speech(segment: dict[str, Any]) -> bool:
    if "is_dialogue" in segment:
        return bool(segment.get("is_dialogue"))
    return str(segment.get("role") or "").strip().lower() in {"male", "female"}


def _emotion_for(segment: dict[str, Any]) -> str:
    value = segment.get("emotion") or segment.get("intonation") or ""
    return re.sub(r"\s+", " ", str(value).strip().lower())[:80]


def _role_id(display_name: str) -> str:
    slug = re.sub(r"[^\w]+", "_", display_name.strip().casefold(), flags=re.UNICODE)
    slug = slug.strip("_")
    return slug or "role"
