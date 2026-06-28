"""Field normalization helpers for LLM segmentation rows."""

from __future__ import annotations

import re
from typing import Any

from book_normalizer.chunking.llm_segmenter_config import _DASH_CHARS, _QUOTE_CHARS, VOICE_LABEL_TO_ROLE


def _legacy_voice_text(item: dict[str, Any]) -> str:
    for key in ("narrator", "men", "women", "male", "female"):
        if key in item:
            return str(item[key])
    return ""

def _legacy_voice_role(item: dict[str, Any]) -> str:
    for key in ("narrator", "men", "women", "male", "female"):
        if key in item:
            return key
    return "narrator"

def _normalize_role(value: Any) -> str:
    role = str(value or "narrator").strip().lower()
    return VOICE_LABEL_TO_ROLE.get(role, "narrator")

def _clean_intonation(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "calm")).strip().lower()
    return text[:80] or "calm"

def _clean_optional(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:180]

def _clean_section_kind(value: Any, role: str) -> str:
    text = re.sub(r"\s+", "_", str(value or "").strip().lower())
    allowed = {
        "narration",
        "dialogue",
        "inner_thought",
        "annotation",
        "preface",
        "epilogue",
        "chapter_title",
    }
    if text in allowed:
        return text
    return "dialogue" if role in {"male", "female", "unknown"} else "narration"

def _is_dialogue_segment(
    *,
    role: str,
    section_kind: str,
    speaker: str,
    text: str,
) -> bool:
    """Detect direct speech even when the LLM cannot prove speaker gender."""
    if role == "narrator" and section_kind in {"narration", "inner_thought"} and not speaker:
        return False
    if section_kind == "inner_thought":
        return False
    if role in {"male", "female", "unknown"} or section_kind == "dialogue" or speaker:
        return True
    stripped = text.lstrip()
    return bool(stripped and (stripped[0] in _QUOTE_CHARS or stripped[0] in _DASH_CHARS))

