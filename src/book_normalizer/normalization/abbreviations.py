"""Expand common Russian abbreviations for TTS readability."""

from __future__ import annotations

import re

# Multi-word abbreviations (order matters: longer matches first).
_MULTI_WORD: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bт\.\s*е\.", re.IGNORECASE), "то есть"),
    (re.compile(r"\bт\.\s*д\.", re.IGNORECASE), "так далее"),
    (re.compile(r"\bт\.\s*п\.", re.IGNORECASE), "тому подобное"),
    (re.compile(r"\bт\.\s*н\.", re.IGNORECASE), "так называемый"),
    (re.compile(r"\bт\.\s*к\.", re.IGNORECASE), "так как"),
    (re.compile(r"\bи\s+т\.\s*д\.\s+и\s+т\.\s*п\.", re.IGNORECASE), "и так далее и тому подобное"),
]

# Context-sensitive single-letter abbreviations.
# "г." after a 4-digit number = "год", otherwise left as-is.
_YEAR_G = re.compile(r"(\d{4})\s*г\.")
_YEARS_GG = re.compile(r"(\d{4})\s*[-–—]\s*(\d{4})\s*гг\.")

# "в." after a Roman numeral or number = "века".
_CENTURY_V = re.compile(r"(\b[IVXLCDM]+|\d+)\s*в\.")

# Standalone abbreviations that are safe to expand unconditionally.
_SIMPLE: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bдр\."), "другие"),
    (re.compile(r"\bпр\."), "прочее"),
    (re.compile(r"\bсм\."), "смотри"),
    (re.compile(r"\bср\."), "сравни"),
    (re.compile(r"\bнапр\."), "например"),
    (re.compile(r"\bок\."), "около"),
]


def expand_abbreviations(text: str) -> str:
    """
    Replace common Russian abbreviations with their full forms.

    Designed for TTS pipelines where abbreviated text sounds unnatural.
    Multi-word abbreviations are expanded first to avoid partial matches.
    """
    # Compound abbreviation first (before individual parts get expanded).
    for pattern, replacement in _MULTI_WORD:
        text = pattern.sub(replacement, text)

    # Year: "1812 г." -> "1812 года".
    text = _YEARS_GG.sub(r"\1–\2 годов", text)
    text = _YEAR_G.sub(r"\1 года", text)

    # Century: "XVIII в." -> "XVIII века".
    text = _CENTURY_V.sub(r"\1 века", text)

    for pattern, replacement in _SIMPLE:
        text = pattern.sub(replacement, text)

    return text
