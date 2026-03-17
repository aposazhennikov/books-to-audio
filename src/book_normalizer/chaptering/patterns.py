"""Configurable regex patterns for Russian chapter heading detection."""

from __future__ import annotations

import re

# Compiled chapter-heading patterns ordered from most specific to most generic.
# Each pattern is a tuple of (compiled_regex, human_label).
CHAPTER_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # "Глава 1", "Глава 12", "ГЛАВА 1".
    (re.compile(r"^\s*[Гг][Лл][Аа][Вв][Аа]\s+\d+", re.MULTILINE), "chapter_numeric"),
    # "Глава первая", "Глава двадцатая".
    (
        re.compile(
            r"^\s*[Гг][Лл][Аа][Вв][Аа]\s+"
            r"[А-Яа-яЁё]+",
            re.MULTILINE,
        ),
        "chapter_word",
    ),
    # "Глава V", "Глава XIV", "Глава |", "Глава Il" — Latin Roman numerals
    # including frequent OCR variants (l for I, | for I).
    # The $ anchor rejects TOC lines like "Глава I Title 7".
    (re.compile(r"^\s*[Гг][Лл][Аа][Вв][Аа]\s+[IVXLCDMl|]+\s*$", re.MULTILINE), "chapter_roman"),
    # "Часть I", "Часть 2", "ЧАСТЬ III".
    (re.compile(r"^\s*[Чч][Аа][Сс][Тт][Ьь]\s+[IVXLCDM\d]+", re.MULTILINE), "part"),
    # "1. Title", "1.1 Title", "1.1. Title" — numeric headings.
    (re.compile(r"^\s*\d+(?:\.\d+)*\.?\s+[А-ЯЁA-Z][А-Яа-яЁёA-Za-z\s]{10,}$", re.MULTILINE), "numeric_heading"),
    # "Введение", "Заключение", "Послесловие" — common standalone headings.
    (
        re.compile(
            r"^\s*(?:[Вв]ведение|[Зз]аключение|[Пп]ослесловие|[Пп]редисловие)\s*$",
            re.MULTILINE,
        ),
        "intro_conclusion",
    ),
    # "Пролог", "Эпилог", "ПРОЛОГ".
    (
        re.compile(
            r"^\s*(?:[Пп][Рр][Оо][Лл][Оо][Гг]|[Ээ][Пп][Ии][Лл][Оо][Гг])\s*$",
            re.MULTILINE,
        ),
        "prologue_epilogue",
    ),
    # "I", "II", "III", "IV" — standalone Roman numerals (at least II to avoid false positives).
    (re.compile(r"^\s*(?:I{2,3}|IV|VI{0,3}|IX|XI{0,3}|XI?V|XX?)\s*$", re.MULTILINE), "roman_numeral"),
]


def match_chapter_heading(line: str) -> tuple[str, str] | None:
    """
    Check if a line matches any known chapter heading pattern.

    Returns (matched_text, pattern_label) or None if no match.
    """
    stripped = line.strip()
    if not stripped:
        return None
    for pattern, label in CHAPTER_PATTERNS:
        m = pattern.match(stripped)
        if m:
            return (stripped, label)
    return None
