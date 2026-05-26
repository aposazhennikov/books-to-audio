"""Strict helpers for the v2 TTS chunk manifest contract."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from book_normalizer.languages import (
    DEFAULT_BOOK_LANGUAGE,
    normalize_book_language,
    qwen_tts_language,
)

MANIFEST_VERSION = 2
DEFAULT_MANIFEST_NAME = "chunks_manifest_v2.json"

VOICE_LABEL_BY_ROLE = {
    "narrator": "narrator",
    "male": "men",
    "female": "women",
    "men": "men",
    "women": "women",
    "unknown": "narrator",
}

VOICE_BY_LABEL = {
    "narrator": "narrator",
    "men": "male",
    "women": "female",
}

VOICE_ID_BY_LABEL = {
    "narrator": "narrator_calm",
    "men": "male_young",
    "women": "female_warm",
}


class ManifestV2Error(ValueError):
    """Raised when a manifest is not a valid v2 manifest."""


class ManifestChunkV2(BaseModel):
    """One TTS chunk in a v2 manifest."""

    chapter_index: int = 0
    chunk_index: int = 0
    voice_label: str = ""
    voice: str = "narrator"
    voice_id: str = ""
    voice_tone: str = "neutral"
    text: str = ""
    narrator: str | None = None
    men: str | None = None
    women: str | None = None
    synthesized: bool = False
    failed: bool = False
    error: str = ""
    audio_file: str | None = None
    pause_after_ms: int = 0
    boundary_after: str = ""
    speaker: str = ""
    character_description: str = ""
    emotion: str = ""
    section_kind: str = ""
    deleted: bool = False
    excluded_from_tts: bool = False

    @field_validator("voice_label")
    @classmethod
    def _valid_voice_label(cls, value: str) -> str:
        normalized = (value or "").strip()
        if not normalized:
            return ""
        if normalized not in VOICE_BY_LABEL:
            raise ManifestV2Error(
                f"Invalid v2 voice_label {value!r}; expected one of {sorted(VOICE_BY_LABEL)}."
            )
        return normalized

    def model_post_init(self, _context: Any) -> None:
        if self.voice_label not in VOICE_BY_LABEL:
            self.voice_label = role_to_voice_label(self.voice, self.voice_id)
        self.voice = VOICE_BY_LABEL[self.voice_label]
        if not self.voice_id:
            self.voice_id = VOICE_ID_BY_LABEL[self.voice_label]
        if not self.text:
            self.text = str(getattr(self, self.voice_label) or "")
        setattr(self, self.voice_label, self.text)

    def reset_audio_state(self) -> None:
        """Mark the chunk as needing synthesis after text/voice changes."""
        self.synthesized = False
        self.failed = False
        self.error = ""
        self.audio_file = None

    def to_record(self) -> dict[str, Any]:
        """Return a clean JSON record, preserving the voice-label text field."""
        record = self.model_dump()
        record[self.voice_label] = self.text
        return record


class ManifestChapterV2(BaseModel):
    """A chapter entry in a v2 manifest."""

    chapter_index: int = 0
    chapter_title: str = ""
    chunks: list[ManifestChunkV2] = Field(default_factory=list)

    def model_post_init(self, _context: Any) -> None:
        if not self.chapter_title:
            self.chapter_title = f"Chapter {self.chapter_index + 1}"
        renumber_chunks(self)

    def to_record(self) -> dict[str, Any]:
        return {
            "chapter_index": self.chapter_index,
            "chapter_title": self.chapter_title,
            "chunks": [chunk.to_record() for chunk in self.chunks],
        }


class ManifestV2(BaseModel):
    """Top-level v2 manifest model."""

    version: int = MANIFEST_VERSION
    book_title: str = ""
    language: str = DEFAULT_BOOK_LANGUAGE
    tts_language: str = qwen_tts_language(DEFAULT_BOOK_LANGUAGE)
    chunker: str = "gui"
    model: str = ""
    max_chunk_chars: int | None = None
    chapters: list[ManifestChapterV2] = Field(default_factory=list)

    @field_validator("version")
    @classmethod
    def _version_must_be_v2(cls, value: int) -> int:
        if value != MANIFEST_VERSION:
            raise ManifestV2Error(
                f"Only {DEFAULT_MANIFEST_NAME} version 2 is supported; got version {value!r}."
            )
        return value

    @field_validator("language")
    @classmethod
    def _normalize_language(cls, value: str) -> str:
        return normalize_book_language(value)

    def to_record(self) -> dict[str, Any]:
        language = normalize_book_language(self.language)
        record: dict[str, Any] = {
            "version": MANIFEST_VERSION,
            "book_title": self.book_title,
            "language": language,
            "tts_language": qwen_tts_language(language),
            "chunker": self.chunker,
            "chapters": [chapter.to_record() for chapter in self.chapters],
        }
        if self.model:
            record["model"] = self.model
        if self.max_chunk_chars is not None:
            record["max_chunk_chars"] = self.max_chunk_chars
        return record


def role_for_voice_id(voice_id: str, fallback: str = "narrator") -> str:
    """Infer the canonical role from a voice preset id."""
    normalized = (voice_id or "").strip().lower()
    if normalized.startswith("male_") or normalized in {"male", "men"}:
        return "male"
    if normalized.startswith("female_") or normalized in {"female", "women"}:
        return "female"
    if normalized.startswith("narrator_") or normalized == "narrator":
        return "narrator"
    if fallback == "":
        return ""
    return fallback if fallback in VOICE_LABEL_BY_ROLE else "narrator"


def role_to_voice_label(role: str, voice_id: str = "") -> str:
    """Return the v2 voice label for a role/voice preset pair."""
    inferred_role = role_for_voice_id(voice_id, fallback="")
    if inferred_role in {"male", "female", "narrator"}:
        return VOICE_LABEL_BY_ROLE[inferred_role]
    normalized = (role or "").strip().lower()
    return VOICE_LABEL_BY_ROLE.get(normalized, "narrator")


def ensure_v2_manifest(data: object) -> ManifestV2:
    """Validate and return a strict v2 manifest model."""
    if isinstance(data, list):
        raise ManifestV2Error(
            f"v1 list manifests are no longer supported; generate/use {DEFAULT_MANIFEST_NAME}."
        )
    if not isinstance(data, dict):
        raise ManifestV2Error(f"{DEFAULT_MANIFEST_NAME} must be a JSON object.")
    if data.get("version", 1) != MANIFEST_VERSION:
        raise ManifestV2Error(
            f"Only {DEFAULT_MANIFEST_NAME} version 2 is supported; got version {data.get('version', 1)!r}."
        )
    return ManifestV2.model_validate(data)


def load_manifest(path: Path) -> ManifestV2:
    """Load and validate a v2 manifest from disk."""
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")
    return ensure_v2_manifest(json.loads(path.read_text(encoding="utf-8")))


def save_manifest(path: Path, manifest: ManifestV2 | dict[str, Any]) -> None:
    """Atomically save a v2 manifest."""
    model = manifest if isinstance(manifest, ManifestV2) else ensure_v2_manifest(manifest)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(model.to_record(), ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def iter_chunk_pairs(
    manifest: ManifestV2 | dict[str, Any],
    chapter_filter: int | None = None,
) -> Iterator[tuple[ManifestChapterV2, ManifestChunkV2]]:
    """Yield chapter/chunk pairs, optionally filtered by 1-based chapter."""
    model = manifest if isinstance(manifest, ManifestV2) else ensure_v2_manifest(manifest)
    for chapter in model.chapters:
        if chapter_filter is not None and chapter.chapter_index != chapter_filter - 1:
            continue
        for chunk in chapter.chunks:
            yield chapter, chunk


def flatten_manifest(
    manifest: ManifestV2 | dict[str, Any],
    chapter_filter: int | None = None,
) -> list[dict[str, Any]]:
    """Return flat v2 chunk records with chapter indexes included."""
    return [
        {"chapter_index": chapter.chapter_index, **chunk.to_record()}
        for chapter, chunk in iter_chunk_pairs(manifest, chapter_filter)
    ]


def chunk_is_excluded(chunk: dict[str, Any]) -> bool:
    """Return true when a chunk is intentionally omitted from TTS output."""
    return bool(chunk.get("deleted") or chunk.get("excluded_from_tts"))


def chunks_to_manifest(
    chunks: Iterable[dict[str, Any]],
    *,
    book_title: str,
    language: str = DEFAULT_BOOK_LANGUAGE,
    chunker: str = "gui",
    model: str = "",
    max_chunk_chars: int | None = None,
) -> ManifestV2:
    """Build a v2 manifest from flat chunk dictionaries."""
    chapters: dict[int, ManifestChapterV2] = {}
    per_chapter_index: dict[int, int] = defaultdict(int)
    manifest_language = normalize_book_language(language)
    for raw_chunk in chunks:
        if language == DEFAULT_BOOK_LANGUAGE and raw_chunk.get("language"):
            manifest_language = normalize_book_language(str(raw_chunk.get("language")))
        chapter_index = int(raw_chunk.get("chapter_index", 0))
        chapter = chapters.setdefault(
            chapter_index,
            ManifestChapterV2(chapter_index=chapter_index),
        )
        voice_id = str(raw_chunk.get("voice_id") or "")
        voice_label = str(raw_chunk.get("voice_label") or "").strip()
        if voice_label not in VOICE_BY_LABEL:
            voice_label = role_to_voice_label(str(raw_chunk.get("role", "narrator")), voice_id)

        chunk_index = int(raw_chunk.get("chunk_index", per_chapter_index[chapter_index]))
        per_chapter_index[chapter_index] = max(per_chapter_index[chapter_index], chunk_index + 1)
        text = str(raw_chunk.get("text") or raw_chunk.get(voice_label) or "")
        chapter.chunks.append(
            ManifestChunkV2(
                chapter_index=chapter_index,
                chunk_index=chunk_index,
                voice_label=voice_label,
                voice_id=voice_id or VOICE_ID_BY_LABEL[voice_label],
                voice_tone=str(raw_chunk.get("voice_tone") or raw_chunk.get("intonation") or "neutral"),
                text=text,
                synthesized=bool(raw_chunk.get("synthesized", False)),
                failed=bool(raw_chunk.get("failed", False)),
                error=str(raw_chunk.get("error") or ""),
                audio_file=raw_chunk.get("audio_file"),
                pause_after_ms=int(raw_chunk.get("pause_after_ms") or 0),
                boundary_after=str(raw_chunk.get("boundary_after") or ""),
                speaker=str(raw_chunk.get("speaker") or ""),
                character_description=str(raw_chunk.get("character_description") or ""),
                emotion=str(raw_chunk.get("emotion") or ""),
                section_kind=str(raw_chunk.get("section_kind") or ""),
                deleted=bool(raw_chunk.get("deleted", False)),
                excluded_from_tts=bool(raw_chunk.get("excluded_from_tts", False)),
            )
        )

    return ManifestV2(
        book_title=book_title,
        language=manifest_language,
        tts_language=qwen_tts_language(manifest_language),
        chunker=chunker,
        model=model,
        max_chunk_chars=max_chunk_chars,
        chapters=[chapters[index] for index in sorted(chapters)],
    )


def find_chunk(
    manifest: ManifestV2,
    chapter_index: int,
    chunk_index: int,
) -> tuple[ManifestChapterV2, int, ManifestChunkV2] | None:
    """Find a mutable chunk by zero-based chapter/chunk indexes."""
    for chapter in manifest.chapters:
        if chapter.chapter_index != chapter_index:
            continue
        for index, chunk in enumerate(chapter.chunks):
            if chunk.chunk_index == chunk_index:
                return chapter, index, chunk
    return None


def update_chunk_text(
    manifest: ManifestV2,
    chapter_index: int,
    chunk_index: int,
    text: str,
) -> bool:
    """Update one chunk's text and reset its synthesis state."""
    found = find_chunk(manifest, chapter_index, chunk_index)
    if found is None:
        return False
    _chapter, _index, chunk = found
    chunk.text = text
    setattr(chunk, chunk.voice_label, text)
    chunk.reset_audio_state()
    return True


def split_chunk_text(
    manifest: ManifestV2,
    chapter_index: int,
    chunk_index: int,
    split_at: int,
) -> bool:
    """Split one chunk at a text cursor offset."""
    found = find_chunk(manifest, chapter_index, chunk_index)
    if found is None:
        return False
    chapter, index, chunk = found
    left = chunk.text[:split_at].strip()
    right = chunk.text[split_at:].strip()
    if not left or not right:
        return False

    next_chunk = ManifestChunkV2.model_validate(chunk.to_record())
    chunk.text = left
    setattr(chunk, chunk.voice_label, left)
    chunk.pause_after_ms = 0
    chunk.boundary_after = ""
    chunk.reset_audio_state()

    next_chunk.text = right
    setattr(next_chunk, next_chunk.voice_label, right)
    next_chunk.reset_audio_state()
    chapter.chunks.insert(index + 1, next_chunk)
    renumber_chunks(chapter)
    return True


def merge_chunk_with_next(
    manifest: ManifestV2,
    chapter_index: int,
    chunk_index: int,
) -> bool:
    """Merge one chunk with its immediate next chunk."""
    found = find_chunk(manifest, chapter_index, chunk_index)
    if found is None:
        return False
    chapter, index, chunk = found
    if index + 1 >= len(chapter.chunks):
        return False
    next_chunk = chapter.chunks[index + 1]
    chunk.text = " ".join(part for part in (chunk.text.strip(), next_chunk.text.strip()) if part)
    setattr(chunk, chunk.voice_label, chunk.text)
    if next_chunk.pause_after_ms:
        chunk.pause_after_ms = next_chunk.pause_after_ms
    if next_chunk.boundary_after:
        chunk.boundary_after = next_chunk.boundary_after
    chunk.reset_audio_state()
    del chapter.chunks[index + 1]
    renumber_chunks(chapter)
    return True


def renumber_chunks(chapter: ManifestChapterV2) -> None:
    """Keep chunk indexes contiguous inside a chapter."""
    for index, chunk in enumerate(chapter.chunks):
        chunk.chapter_index = chapter.chapter_index
        chunk.chunk_index = index
