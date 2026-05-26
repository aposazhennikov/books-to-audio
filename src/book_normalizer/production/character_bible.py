"""Build a stable character bible from segment or chunk manifests."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from hashlib import sha1
from pathlib import Path
from typing import Any

from book_normalizer.chunking.manifest_v2 import ensure_v2_manifest
from book_normalizer.tts.voice_mapping import canonical_role_for_segment

CHARACTER_BIBLE_VERSION = 1
DEFAULT_CHARACTER_BIBLE_NAME = "character_bible.json"

GENERIC_SPEAKERS = {
    "",
    "male character",
    "female character",
    "unknown",
    "narrator",
    "men",
    "women",
    "male",
    "female",
}

_RU_SPEAKER_AFTER_VERB_RE = re.compile(
    r"\b(?:сказал|сказала|ответил|ответила|спросил|спросила|крикнул|крикнула|"
    r"прошептал|прошептала|произнёс|произнес|произнесла|воскликнул|"
    r"воскликнула|добавил|добавила|заметил|заметила|возразил|возразила)\s+"
    r"(?P<speaker>[А-ЯЁ][А-ЯЁа-яё-]{1,40})",
    re.IGNORECASE,
)

_EN_SPEAKER_RE = re.compile(
    r"\b(?:(?:said|asked|replied|shouted|whispered|cried|muttered)\s+"
    r"(?P<after>[A-Z][A-Za-z'-]{1,40})|"
    r"(?P<before>[A-Z][A-Za-z'-]{1,40})\s+"
    r"(?:said|asked|replied|shouted|whispered|cried|muttered))\b"
)


@dataclass
class CharacterProfile:
    """One canonical character or narration role."""

    character_id: str
    display_name: str
    role: str = "unknown"
    aliases: set[str] = field(default_factory=set)
    description: str = ""
    direct_speech_count: int = 0
    segment_count: int = 0
    chapter_indexes: set[int] = field(default_factory=set)
    emotion_counts: Counter[str] = field(default_factory=Counter)
    sample_lines: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def add_segment(self, segment: dict[str, Any]) -> None:
        """Merge one segment/chunk into the profile."""
        self.segment_count += 1
        self.chapter_indexes.add(int(segment.get("chapter_index") or 0))
        if _is_direct_speech(segment):
            self.direct_speech_count += 1

        speaker = _clean_speaker(segment.get("speaker"))
        if speaker:
            self.aliases.add(speaker)

        emotion = _clean_label(segment.get("emotion") or segment.get("intonation") or segment.get("voice_tone"))
        if emotion:
            self.emotion_counts[emotion] += 1

        description = _clean_text(
            segment.get("character_description")
            or segment.get("role_description")
            or segment.get("description")
        )
        if description and not self.description:
            self.description = description

        text = _clean_text(segment.get("text"))
        if text and len(self.sample_lines) < 6:
            self.sample_lines.append(text[:220])

    def finalize(self) -> None:
        """Compute derived confidence and stable aliases."""
        self.aliases.add(self.display_name)
        if self.display_name == "Narrator":
            self.confidence = 1.0
            return
        evidence = 0.0
        if self.direct_speech_count:
            evidence += 0.35
        if self.segment_count >= 2:
            evidence += 0.20
        if self.description:
            evidence += 0.15
        if len(self.aliases) >= 2:
            evidence += 0.10
        if self.emotion_counts:
            evidence += 0.10
        if self.chapter_indexes:
            evidence += min(0.10, len(self.chapter_indexes) * 0.03)
        self.confidence = round(min(0.98, max(0.25, evidence)), 3)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the profile for JSON reports."""
        emotions = [
            {"emotion": emotion, "count": count}
            for emotion, count in self.emotion_counts.most_common()
        ]
        return {
            "character_id": self.character_id,
            "display_name": self.display_name,
            "role": self.role,
            "aliases": sorted(self.aliases, key=str.casefold),
            "description": self.description,
            "direct_speech_count": self.direct_speech_count,
            "segment_count": self.segment_count,
            "chapter_indexes": sorted(self.chapter_indexes),
            "emotions": emotions,
            "sample_lines": self.sample_lines,
            "confidence": self.confidence,
        }


def load_manifest_rows(path: Path) -> list[dict[str, Any]]:
    """Load flat segment/chunk rows from a supported manifest JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return rows_from_manifest(data)


def rows_from_manifest(data: object) -> list[dict[str, Any]]:
    """Return flat rows from v2 chunks, GUI segment lists, or simple row dicts."""
    if isinstance(data, list):
        return [dict(item) for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        raise ValueError("Character bible input must be a JSON object or list.")

    if "chapters" in data:
        manifest = ensure_v2_manifest(data).to_record()
        rows: list[dict[str, Any]] = []
        for chapter in manifest.get("chapters", []):
            if not isinstance(chapter, dict):
                continue
            for chunk in chapter.get("chunks", []):
                if isinstance(chunk, dict):
                    rows.append({"chapter_title": chapter.get("chapter_title", ""), **chunk})
        return rows

    if isinstance(data.get("segments"), list):
        return [dict(item) for item in data["segments"] if isinstance(item, dict)]
    if isinstance(data.get("rows"), list):
        return [dict(item) for item in data["rows"] if isinstance(item, dict)]
    raise ValueError("Unsupported character bible input shape.")


def build_character_bible(
    rows: list[dict[str, Any]],
    *,
    book_title: str = "",
    language: str = "ru",
) -> dict[str, Any]:
    """Build a character bible from flat segment/chunk rows."""
    profiles: dict[str, CharacterProfile] = {}
    unresolved: list[dict[str, Any]] = []
    evidence_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        normalized = _normalize_row(row)
        name = _character_name_for_row(normalized, language=language)
        if name:
            evidence_by_name[_name_key(name)].append(normalized | {"_display_name": name})
        elif _is_direct_speech(normalized):
            unresolved.append(_unresolved_record(normalized, reason="speaker_not_proven"))
        else:
            evidence_by_name[_name_key("Narrator")].append(normalized | {"_display_name": "Narrator"})

    for key, items in evidence_by_name.items():
        display_name = _best_display_name(items)
        character_id = _character_id(display_name, key)
        role = _role_for_items(items)
        profile = CharacterProfile(
            character_id=character_id,
            display_name=display_name,
            role=role,
        )
        for item in items:
            profile.add_segment(item)
        profile.finalize()
        profiles[key] = profile

    characters = sorted(
        (profile.to_dict() for profile in profiles.values()),
        key=lambda item: (
            item["display_name"] != "Narrator",
            -int(item["direct_speech_count"]),
            -int(item["segment_count"]),
            str(item["display_name"]).casefold(),
        ),
    )
    return {
        "version": CHARACTER_BIBLE_VERSION,
        "book_title": book_title,
        "language": language,
        "total_rows": len(rows),
        "total_characters": len(characters),
        "total_direct_speech": sum(int(item["direct_speech_count"]) for item in characters),
        "characters": characters,
        "unresolved_dialogue": unresolved,
        "summary": {
            "unresolved_dialogue": len(unresolved),
            "high_confidence_characters": sum(1 for item in characters if float(item["confidence"]) >= 0.70),
            "generic_dialogue_rows": sum(1 for item in unresolved if item.get("reason") == "speaker_not_proven"),
        },
    }


def write_character_bible(path: Path, bible: dict[str, Any]) -> Path:
    """Write a character bible JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bible, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def apply_character_bible_to_manifest(
    manifest: dict[str, Any],
    bible: dict[str, Any],
) -> dict[str, Any]:
    """Attach character ids and canonical speaker names to v2 manifest chunks."""
    record = ensure_v2_manifest(manifest).to_record()
    by_name: dict[str, dict[str, Any]] = {}
    for character in bible.get("characters", []):
        if not isinstance(character, dict):
            continue
        for alias in character.get("aliases", []):
            by_name[_name_key(str(alias))] = character
        by_name[_name_key(str(character.get("display_name") or ""))] = character

    for chapter in record.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        for chunk in chapter.get("chunks", []):
            if not isinstance(chunk, dict):
                continue
            name = _character_name_for_row(chunk, language=str(record.get("language") or "ru"))
            if not name and not _is_direct_speech(chunk):
                name = "Narrator"
            character = by_name.get(_name_key(name or ""))
            if not character:
                continue
            chunk["character_id"] = str(character.get("character_id") or "")
            chunk["canonical_speaker"] = str(character.get("display_name") or name)
            chunk["character_confidence"] = float(character.get("confidence") or 0.0)
    return record


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    role = canonical_role_for_segment(row)
    normalized.setdefault("role", role)
    normalized.setdefault("voice", role)
    if "is_dialogue" not in normalized:
        normalized["is_dialogue"] = role in {"male", "female", "unknown"} or str(
            normalized.get("section_kind") or ""
        ).lower() == "dialogue"
    return normalized


def _character_name_for_row(row: dict[str, Any], *, language: str) -> str:
    speaker = _clean_speaker(row.get("speaker") or row.get("character") or row.get("role_display_name"))
    if _is_specific_speaker(speaker):
        return speaker

    inferred = _infer_speaker_from_text(_clean_text(row.get("text")), language=language)
    if inferred:
        return inferred
    if not _is_direct_speech(row):
        return "Narrator"
    return ""


def _infer_speaker_from_text(text: str, *, language: str) -> str:
    if not text:
        return ""
    if language == "en":
        match = _EN_SPEAKER_RE.search(text)
        return _clean_speaker(match.group("after") or match.group("before")) if match else ""
    match = _RU_SPEAKER_AFTER_VERB_RE.search(text)
    return _clean_speaker(match.group("speaker")) if match else ""


def _best_display_name(items: list[dict[str, Any]]) -> str:
    names = Counter(str(item.get("_display_name") or "").strip() for item in items)
    names.pop("", None)
    if not names:
        return "Narrator"
    return names.most_common(1)[0][0]


def _role_for_items(items: list[dict[str, Any]]) -> str:
    roles = Counter(canonical_role_for_segment(item) for item in items)
    roles.pop("", None)
    if not roles:
        return "narrator"
    if "narrator" in roles and len(roles) == 1:
        return "narrator"
    for role, _count in roles.most_common():
        if role != "narrator":
            return role
    return roles.most_common(1)[0][0]


def _unresolved_record(row: dict[str, Any], *, reason: str) -> dict[str, Any]:
    return {
        "reason": reason,
        "chapter_index": int(row.get("chapter_index") or 0),
        "chunk_index": int(row.get("chunk_index") or row.get("segment_index") or 0),
        "role": canonical_role_for_segment(row),
        "emotion": _clean_label(row.get("emotion") or row.get("intonation") or row.get("voice_tone")),
        "text": _clean_text(row.get("text"))[:260],
    }


def _is_direct_speech(row: dict[str, Any]) -> bool:
    if "is_dialogue" in row:
        return bool(row.get("is_dialogue"))
    role = canonical_role_for_segment(row)
    if role in {"male", "female", "unknown"}:
        return True
    return str(row.get("section_kind") or "").strip().lower() == "dialogue"


def _is_specific_speaker(value: str) -> bool:
    return bool(value and value.casefold() not in GENERIC_SPEAKERS)


def _character_id(display_name: str, key: str) -> str:
    slug = re.sub(r"[^\w]+", "_", display_name.casefold(), flags=re.UNICODE).strip("_")
    slug = slug or "character"
    digest = sha1(key.encode("utf-8")).hexdigest()[:8]
    return f"char_{slug}_{digest}"


def _name_key(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip().casefold()


def _clean_speaker(value: Any) -> str:
    return re.sub(r"^[\s,.;:!?—–-]+|[\s,.;:!?—–-]+$", "", _clean_text(value))


def _clean_label(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()[:80]


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
