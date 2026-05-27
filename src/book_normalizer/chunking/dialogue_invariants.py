"""Conservative structural checks for dialogue/narration chunk boundaries."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from book_normalizer.chunking.llm_segmenter import (
    _dash_starts_narrator_tag,
    _starts_with_direct_speech_marker,
    _take_quoted_speech,
)
from book_normalizer.languages import normalize_book_language


@dataclass(frozen=True)
class DialogueChunkIssue:
    """A likely dialogue boundary issue in a ready-to-synthesize chunk."""

    kind: str
    chapter_index: int
    chunk_index: int
    role: str
    text: str
    message: str


def audit_dialogue_chunk_boundaries(
    chunks: Iterable[dict[str, Any]],
    *,
    language: str = "ru",
) -> list[DialogueChunkIssue]:
    """Return conservative issues where a chunk likely mixes speech and tags."""

    code = normalize_book_language(language)
    issues: list[DialogueChunkIssue] = []
    for chunk in chunks:
        text = str(chunk.get("text") or "").strip()
        if not text:
            continue
        role = str(chunk.get("role") or chunk.get("voice") or "").strip().lower()
        section_kind = str(chunk.get("section_kind") or "").strip().lower()
        chapter_index = _safe_int(chunk.get("chapter_index"))
        chunk_index = _safe_int(chunk.get("chunk_index"))

        if _is_dialogue_chunk(role, section_kind) and _has_embedded_author_tag(text, code):
            issues.append(DialogueChunkIssue(
                kind="dialogue_contains_author_tag",
                chapter_index=chapter_index,
                chunk_index=chunk_index,
                role=role or "unknown",
                text=text,
                message="Direct-speech chunk still contains an inline author tag.",
            ))
            continue

        if _is_narration_chunk(role, section_kind) and _starts_with_direct_speech_marker(text, code):
            issues.append(DialogueChunkIssue(
                kind="narration_starts_with_direct_speech",
                chapter_index=chapter_index,
                chunk_index=chunk_index,
                role=role or "narrator",
                text=text,
                message="Narration chunk starts like a direct-speech chunk.",
            ))
            continue

        if _is_narration_chunk(role, section_kind) and _narrator_tag_contains_next_speech(text, code):
            issues.append(DialogueChunkIssue(
                kind="narration_contains_next_direct_speech",
                chapter_index=chapter_index,
                chunk_index=chunk_index,
                role=role or "narrator",
                text=text,
                message="Author-tag chunk appears to contain the following direct speech.",
            ))
    return issues


def _is_dialogue_chunk(role: str, section_kind: str) -> bool:
    return section_kind == "dialogue" or role in {"male", "female", "unknown"}


def _is_narration_chunk(role: str, section_kind: str) -> bool:
    return section_kind != "dialogue" and role in {"", "narrator"}


def _has_embedded_author_tag(text: str, language: str) -> bool:
    if _quoted_speech_has_author_tail(text, language):
        return True
    if not text.lstrip().startswith(("-", "—", "–")):
        return False
    return _dash_speech_has_author_tail(text, language)


def _dash_speech_has_author_tail(text: str, language: str) -> bool:
    stripped = text.strip()
    for index, char in enumerate(stripped[1:], start=1):
        if char not in "-—–":
            continue
        speech = stripped[:index].rstrip()
        tail = stripped[index:].strip()
        if not speech or not tail:
            continue
        if speech[-1:] in ",.!?…" and _dash_starts_narrator_tag(tail, language):
            return True
    return False


def _quoted_speech_has_author_tail(text: str, language: str) -> bool:
    stripped = text.lstrip()
    if not stripped or stripped[0] not in "\"“„«‹「『《〈":
        return False
    speech, tail = _take_quoted_speech(stripped)
    return bool(speech and tail and _dash_starts_narrator_tag(tail, language))


def _narrator_tag_contains_next_speech(text: str, language: str) -> bool:
    stripped = text.strip()
    if not _dash_starts_narrator_tag(stripped, language):
        return False
    for index, char in enumerate(stripped[1:], start=1):
        if char not in "-—–":
            continue
        previous = stripped[index - 1] if index > 0 else ""
        if previous and not (previous.isspace() or previous in ",.!?:…"):
            continue
        before = stripped[:index].rstrip()
        before_is_short_tag = len(before) <= 120 and _dash_starts_narrator_tag(before, language)
        if before and before[-1] not in ",.!?:…" and not before_is_short_tag:
            continue
        tail = stripped[index:].strip()
        after_dash = tail[1:].lstrip() if tail and tail[0] in "-—–" else tail
        if (
            after_dash
            and (after_dash[0].isupper() or after_dash[0] in "\"“„«‹「『《〈")
            and _starts_with_direct_speech_marker(tail, language)
        ):
            return True
    return False


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
