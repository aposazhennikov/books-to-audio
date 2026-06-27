"""Source text and row normalization helpers for LLM segmentation."""

from __future__ import annotations

import json
import re
from typing import Any

from book_normalizer.chunking.llm_segmenter_config import _SYSTEM_PROMPTS
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
    return _SYSTEM_PROMPTS.get(code, _SYSTEM_PROMPTS["ru"])

def _user_prompt_for_window(
    *,
    language: str,
    chapter_index: int,
    window_index: int,
    window_text: str,
    previous_issues: list[str] | None = None,
) -> str:
    retry_guard = ""
    if previous_issues:
        retry_guard = (
            "\nPREVIOUS_OUTPUT_FAILED_VALIDATION:\n"
            + json.dumps({"issues": previous_issues[:6]}, ensure_ascii=False)
            + "\nThe next answer must preserve input.text exactly. "
            "If dialogue boundaries are uncertain, return fewer larger segments."
        )
    return (
        "Input is JSON. Segment only input.text. "
        "Preserve quoted dialogue, apostrophes, punctuation, and word order. "
        "The ordered concatenation of all segment.text values must reproduce "
        "input.text exactly after whitespace normalization.\n"
        "INPUT_JSON:\n"
        + json.dumps(
            {
                "language": get_book_language(language).english_name,
                "chapter": chapter_index + 1,
                "window": window_index + 1,
                "text": window_text,
            },
            ensure_ascii=False,
        )
        + retry_guard
    )

