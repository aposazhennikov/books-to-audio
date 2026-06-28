"""Helpers that verify and restore LLM segments against source text."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from book_normalizer.chunking.llm_segmenter_config import _DASH_CHARS, _OPENING_QUOTE_CHARS


def _segments_preserve_source(source_text: str, segments: list[dict[str, Any]]) -> bool:
    joined = " ".join(str(segment.get("text") or "") for segment in segments)
    return _canonical_for_preservation(source_text) == _canonical_for_preservation(joined)


def _reconcile_segments_to_source(
    source_text: str,
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]] | None:
    """Restore exact source punctuation around LLM-proposed segment boundaries."""
    source_canonical, source_map = _canonical_with_index_map(source_text)
    if not source_canonical:
        return None

    spans: list[tuple[int, int]] = []
    offset = 0
    previous_end = 0
    for segment in segments:
        segment_canonical, _segment_map = _canonical_with_index_map(str(segment.get("text") or ""))
        if not segment_canonical:
            return None
        if not source_canonical.startswith(segment_canonical, offset):
            return None

        start = source_map[offset]
        end = source_map[offset + len(segment_canonical) - 1] + 1
        start = _extend_segment_start(source_text, start, previous_end)
        end = _extend_segment_end(source_text, end)
        spans.append((start, end))
        previous_end = end
        offset += len(segment_canonical)

    if offset != len(source_canonical):
        return None

    reconciled: list[dict[str, Any]] = []
    for segment, (start, end) in zip(segments, spans, strict=True):
        restored = source_text[start:end].strip()
        if not restored:
            return None
        row = dict(segment)
        row["text"] = restored
        reconciled.append(row)
    return reconciled


def _reconcile_segments_to_source_with_gaps(
    source_text: str,
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]] | None:
    """
    Restore source text while preserving usable LLM role boundaries.

    LLMs sometimes drop short narrator clauses while still marking nearby dialogue
    correctly.  Instead of falling back for the entire window, keep matched LLM
    spans and insert unmatched source gaps as neutral narrator segments.
    """
    source_canonical, source_map = _canonical_with_index_map(source_text)
    if not source_canonical:
        return None

    rows: list[dict[str, Any]] = []
    offset = 0
    previous_end = 0
    matched_chars = 0
    for segment in segments:
        segment_text = str(segment.get("text") or "")
        segment_canonical, _segment_map = _canonical_with_index_map(segment_text)
        if not segment_canonical:
            continue

        match_offset = source_canonical.find(segment_canonical, offset)
        if match_offset < 0:
            continue

        start = source_map[match_offset]
        end = source_map[match_offset + len(segment_canonical) - 1] + 1
        start = _extend_segment_start(source_text, start, previous_end)
        end = _extend_segment_end(source_text, end)

        if start > previous_end:
            gap = source_text[previous_end:start].strip()
            if gap:
                rows.append(_source_gap_segment(gap, segment))

        restored = source_text[start:end].strip()
        if restored:
            row = dict(segment)
            row["text"] = restored
            rows.append(row)
            matched_chars += len(segment_canonical)
        offset = match_offset + len(segment_canonical)
        previous_end = end

    if previous_end < len(source_text):
        gap = source_text[previous_end:].strip()
        if gap:
            rows.append(_source_gap_segment(gap, segments[-1] if segments else {}))

    if not rows or matched_chars == 0:
        return None
    if matched_chars < max(12, len(source_canonical) // 10):
        return None
    if not _segments_preserve_source(source_text, rows):
        return None
    return rows


def _source_gap_segment(text: str, nearby_segment: dict[str, Any]) -> dict[str, Any]:
    return {
        "role": "narrator",
        "speaker": "",
        "character_description": "",
        "emotion": str(nearby_segment.get("emotion") or "neutral"),
        "section_kind": "narration",
        "text": text,
        "intonation": str(nearby_segment.get("intonation") or "calm"),
        "pause_after_ms": 0,
        "boundary_after": "",
    }


def _canonical_with_index_map(text: str) -> tuple[str, list[int]]:
    chars: list[str] = []
    indexes: list[int] = []
    for index, char in enumerate(text or ""):
        if char.isspace() or _is_match_ignored_char(char):
            continue
        chars.append(char)
        indexes.append(index)
    return "".join(chars), indexes


def _extend_segment_start(source_text: str, start: int, lower_bound: int) -> int:
    while start > lower_bound and _is_match_ignored_char(source_text[start - 1]):
        start -= 1

    probe = start
    while probe > lower_bound and source_text[probe - 1].isspace() and source_text[probe - 1] not in "\r\n":
        probe -= 1
    if probe > lower_bound and source_text[probe - 1] in _DASH_CHARS:
        return probe - 1
    return start


def _extend_segment_end(source_text: str, end: int) -> int:
    while end < len(source_text):
        if _is_match_ignored_char(source_text[end]):
            end += 1
            continue
        probe = end
        while probe < len(source_text) and source_text[probe].isspace() and source_text[probe] not in "\r\n":
            probe += 1
        if probe < len(source_text) and (
            source_text[probe] in _OPENING_QUOTE_CHARS
            or source_text[probe] in _DASH_CHARS
        ):
            break
        if probe < len(source_text) and _is_match_ignored_char(source_text[probe]):
            end = probe
            continue
        break
    return end


def _is_match_ignored_char(char: str) -> bool:
    return char in _DASH_CHARS or unicodedata.category(char).startswith("P")


def _canonical_for_preservation(text: str) -> str:
    return re.sub(r"\s+", "", text or "")
