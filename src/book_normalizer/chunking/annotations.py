"""Detect chapter-level annotation and epigraph blocks for TTS."""

from __future__ import annotations

import re
from typing import Any

SPECIAL_SECTION_VOICE_ID = "narrator_wise"
SPECIAL_SECTION_KINDS = {"annotation", "epigraph"}

_ANNOTATION_MARK_RE = re.compile(
    r"^\s*(?:аннотаци[яи]|annotation|abstract|примечани[ея])\s*[:.\-—–]?\s*$",
    re.IGNORECASE,
)
_EPIGRAPH_SOURCE_RE = re.compile(
    r"(?:^|\s)(?:из|from)\s+[^.!?]{3,80}$",
    re.IGNORECASE,
)
_CHAPTER_PREFIX_RE = re.compile(
    r"^\s*(?:глава\s+(?:\d+|[ivxlcdm|]+|[а-яё-]+)|chapter\s+\S+|пролог|эпилог)\b",
    re.IGNORECASE,
)


def classify_chapter_paragraphs(paragraphs: list[str]) -> list[str]:
    """Return a section kind for each paragraph, or an empty string."""
    kinds = [""] * len(paragraphs)
    if not paragraphs:
        return kinds

    for index, text in enumerate(paragraphs):
        stripped = _clean_text(text)
        if not stripped:
            continue
        if _looks_like_epigraph(stripped, index=index, paragraphs=paragraphs):
            kinds[index] = "epigraph"
            continue
        if _ANNOTATION_MARK_RE.fullmatch(stripped):
            kinds[index] = "annotation"
            for follow in range(index + 1, min(len(paragraphs), index + 4)):
                candidate = _clean_text(paragraphs[follow])
                if not candidate or _looks_like_chapter_heading(candidate):
                    break
                if _looks_like_annotation_body(candidate):
                    kinds[follow] = "annotation"
                    continue
                break

    return kinds


def apply_special_section_marks(
    book: object,
    segments: list[dict[str, Any]],
    *,
    enabled: bool,
) -> None:
    """Mark segment rows that belong to annotation/epigraph paragraphs."""
    if not enabled or not segments:
        return

    targets_by_chapter: dict[int, list[tuple[str, str]]] = {}
    for chapter in getattr(book, "chapters", []):
        chapter_index = int(getattr(chapter, "index", 0) or 0)
        paragraphs = [
            str(getattr(para, "normalized_text", "") or getattr(para, "raw_text", ""))
            for para in getattr(chapter, "paragraphs", [])
        ]
        kinds = classify_chapter_paragraphs(paragraphs)
        targets_by_chapter[chapter_index] = [
            (kind, _normalize_match_text(text))
            for kind, text in zip(kinds, paragraphs, strict=False)
            if kind and _normalize_match_text(text)
        ]

    for segment in segments:
        if bool(segment.get("is_dialogue")):
            continue
        chapter_index = int(segment.get("chapter_index") or 0)
        segment_text = _normalize_match_text(str(segment.get("text") or ""))
        if not segment_text:
            continue
        for kind, target_text in targets_by_chapter.get(chapter_index, []):
            if _texts_overlap(segment_text, target_text):
                mark_segment_as_special_section(segment, kind)
                break


def mark_segment_as_special_section(segment: dict[str, Any], kind: str) -> None:
    """Mutate a segment dict so downstream voice mapping treats it specially."""
    kind = kind.strip().lower()
    if kind not in SPECIAL_SECTION_KINDS:
        return
    segment["role"] = "narrator"
    segment["is_dialogue"] = False
    segment["section_kind"] = kind
    segment["speaker"] = ""
    segment["voice_id"] = SPECIAL_SECTION_VOICE_ID
    segment.setdefault("intonation", "wise" if kind == "epigraph" else "calm")


def _looks_like_epigraph(text: str, *, index: int, paragraphs: list[str]) -> bool:
    if index > 2:
        return False
    if not _looks_like_short_front_matter(text):
        return False
    if _looks_like_chapter_heading(text) or _ANNOTATION_MARK_RE.fullmatch(text):
        return False
    next_text = _clean_text(paragraphs[index + 1]) if index + 1 < len(paragraphs) else ""
    if not _looks_like_chapter_heading(next_text):
        return False
    return bool(_EPIGRAPH_SOURCE_RE.search(text)) or "\n" in paragraphs[index]


def _looks_like_short_front_matter(text: str) -> bool:
    words = re.findall(r"[\w\u0400-\u04ff]+", text, flags=re.UNICODE)
    return 4 <= len(words) <= 28 and len(text) <= 220


def _looks_like_annotation_body(text: str) -> bool:
    if _looks_like_chapter_heading(text):
        return False
    words = re.findall(r"[\w\u0400-\u04ff]+", text, flags=re.UNICODE)
    return 5 <= len(words) <= 120


def _looks_like_chapter_heading(text: str) -> bool:
    first_line = text.splitlines()[0].strip() if text else ""
    return bool(_CHAPTER_PREFIX_RE.match(first_line))


def _clean_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", str(text or "").strip())


def _normalize_match_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").casefold()).strip()


def _texts_overlap(segment_text: str, target_text: str) -> bool:
    if segment_text in target_text or target_text in segment_text:
        return True
    if len(segment_text) < 24 or len(target_text) < 24:
        return False
    return segment_text[:80] in target_text or target_text[:80] in segment_text
