"""Source text and row normalization helpers for LLM segmentation."""

from __future__ import annotations

import json
import re
from typing import Any

from book_normalizer.chunking.llm_segmenter_fields import (
    _clean_intonation,
    _clean_optional,
    _clean_section_kind,
    _legacy_voice_role,
    _legacy_voice_text,
    _normalize_role,
)
from book_normalizer.chunking.splitter import DEFAULT_PARAGRAPH_PAUSE_MS, chunk_text
from book_normalizer.languages import get_book_language, normalize_book_language
from book_normalizer.prompts.loader import load_language_prompt, load_prompt


def _chapter_text(chapter: object) -> str:
    paragraphs = list(getattr(chapter, "paragraphs", []) or [])
    normalized: list[str] = []
    for para in paragraphs:
        text = _normalize_segment_source_text(
            str(getattr(para, "normalized_text", "") or getattr(para, "raw_text", ""))
        )
        if text:
            normalized.append(text)
    return "\n\n".join(normalized)

def _normalize_segment_source_text(text: str) -> str:
    """Collapse layout-only whitespace before LLM segmentation."""
    lines = [re.sub(r"[^\S\r\n]+", " ", line).strip() for line in str(text or "").splitlines()]
    return "\n".join(lines).strip()

def _build_windows(text: str, max_chars: int) -> list[str]:
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    if not paragraphs and text.strip():
        paragraphs = [text.strip()]
    windows: list[str] = []
    current: list[str] = []
    current_len = 0
    for paragraph in paragraphs:
        paragraph_parts = (
            chunk_text(paragraph, max_chunk_chars=max_chars)
            if len(paragraph) > max_chars
            else [paragraph]
        )
        for part in paragraph_parts:
            sep = 2 if current else 0
            if current and current_len + sep + len(part) > max_chars:
                windows.append("\n\n".join(current))
                current = [part]
                current_len = len(part)
            else:
                current.append(part)
                current_len += sep + len(part)
    if current:
        windows.append("\n\n".join(current))
    return windows

def _normalise_segments(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        raw_segments = data.get("segments", [])
    else:
        raw_segments = data
    if not isinstance(raw_segments, list):
        return []

    segments: list[dict[str, Any]] = []
    for item in raw_segments:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or _legacy_voice_text(item)).strip()
        if not text:
            continue
        role = _normalize_role(item.get("role") or item.get("voice") or _legacy_voice_role(item))
        segments.append(
            {
                "role": role,
                "speaker": _clean_optional(item.get("speaker") or item.get("character")),
                "character_description": _clean_optional(
                    item.get("character_description")
                    or item.get("role_description")
                    or item.get("description")
                ),
                "emotion": _clean_intonation(item.get("emotion") or item.get("intonation") or "calm"),
                "section_kind": _clean_section_kind(item.get("section_kind"), role),
                "text": text,
                "intonation": _clean_intonation(item.get("intonation") or item.get("voice_tone") or "calm"),
                "pause_after_ms": _safe_int(item.get("pause_after_ms")),
                "boundary_after": str(item.get("boundary_after") or ""),
            }
        )
    return segments

def _source_annotation_units(window_text: str, max_unit_chars: int) -> list[dict[str, Any]]:
    """Build immutable source units that the LLM may annotate but not rewrite."""

    parts: list[str] = []
    for paragraph in [part.strip() for part in window_text.split("\n\n") if part.strip()]:
        if len(paragraph) <= max_unit_chars:
            parts.append(paragraph)
            continue
        parts.extend(chunk_text(paragraph, max_chunk_chars=max_unit_chars) or [paragraph])
    if not parts and window_text.strip():
        parts = chunk_text(window_text.strip(), max_chunk_chars=max_unit_chars) or [window_text.strip()]
    return [{"segment_id": index, "text": text} for index, text in enumerate(parts, 1)]

def _normalise_annotations(
    data: Any,
    source_units: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Join model metadata to local source text by id, ignoring any model text."""

    if isinstance(data, dict):
        raw_segments = data.get("segments", [])
    else:
        raw_segments = data
    if not isinstance(raw_segments, list):
        raw_segments = []

    by_id: dict[int, dict[str, Any]] = {}
    for item in raw_segments:
        if not isinstance(item, dict):
            continue
        segment_id = _safe_int(item.get("segment_id"), default=0)
        if segment_id > 0:
            by_id[segment_id] = item
    if not by_id:
        return []

    segments: list[dict[str, Any]] = []
    for unit in source_units:
        segment_id = _safe_int(unit.get("segment_id"), default=0)
        text = str(unit.get("text") or "").strip()
        if not text:
            continue
        item = by_id.get(segment_id, {})
        role = _normalize_role(item.get("role") or item.get("voice") or _legacy_voice_role(item))
        segments.append(
            {
                "role": role,
                "speaker": _clean_optional(item.get("speaker") or item.get("character")),
                "character_description": _clean_optional(
                    item.get("character_description")
                    or item.get("role_description")
                    or item.get("description")
                ),
                "emotion": _clean_intonation(item.get("emotion") or item.get("intonation") or "calm"),
                "section_kind": _clean_section_kind(item.get("section_kind"), role),
                "text": text,
                "intonation": _clean_intonation(item.get("intonation") or item.get("voice_tone") or "calm"),
                "pause_after_ms": _safe_int(item.get("pause_after_ms")),
                "boundary_after": str(item.get("boundary_after") or ""),
            }
        )
    return segments

def _source_fallback_segments(window_text: str) -> list[dict[str, Any]]:
    """Preserve a failed LLM window as a safe narrator segment."""
    return [
        {
            "role": "narrator",
            "speaker": "",
            "character_description": "",
            "emotion": "neutral",
            "section_kind": "narration",
            "text": window_text,
            "intonation": "calm",
            "pause_after_ms": 0,
            "boundary_after": "",
        }
    ]

def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def apply_paragraph_boundary_pauses(rows: list[dict[str, Any]]) -> None:
    """Ensure rows that already mark paragraph boundaries carry a pause."""

    for row in rows:
        if row.get("boundary_after") == "paragraph":
            row["pause_after_ms"] = max(
                _safe_int(row.get("pause_after_ms")),
                DEFAULT_PARAGRAPH_PAUSE_MS,
            )

def _system_prompt_for_language(language: str | None) -> str:
    code = normalize_book_language(language)
    return load_language_prompt("chunking", "voice_role_annotation_system", code)

def _user_prompt_for_window(
    *,
    language: str,
    chapter_index: int,
    window_index: int,
    window_text: str,
    previous_issues: list[str] | None = None,
) -> str:
    return _user_prompt_for_annotations(
        language=language,
        chapter_index=chapter_index,
        window_index=window_index,
        source_units=_source_annotation_units(window_text, max_unit_chars=1200),
        previous_issues=previous_issues,
    )

def _user_prompt_for_annotations(
    *,
    language: str,
    chapter_index: int,
    window_index: int,
    source_units: list[dict[str, Any]],
    previous_issues: list[str] | None = None,
) -> str:
    retry_guard = ""
    if previous_issues:
        retry_guard = (
            "\nPREVIOUS_OUTPUT_FAILED_VALIDATION:\n"
            + json.dumps({"issues": previous_issues[:6]}, ensure_ascii=False)
            + "\nReturn metadata for each existing segment_id only. Do not add any text field."
        )
    return (
        load_prompt("chunking/voice_role_annotation_user.txt")
        .replace(
            "{{INPUT_JSON}}",
            json.dumps(
                {
                    "language": get_book_language(language).english_name,
                    "chapter": chapter_index + 1,
                    "window": window_index + 1,
                    "source_segments": source_units,
                },
                ensure_ascii=False,
            ),
        )
        .replace("{{RETRY_GUARD}}", retry_guard)
    )
