"""Configurable regex patterns for multilingual structure detection."""

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
    # English: "Chapter 1", "Chapter One", "CHAPTER IV".
    (
        re.compile(
            r"^\s*chapter\s+(?:\d+|[ivxlcdm]+|one|two|three|four|five|six|seven|eight|nine|ten|"
            r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
            r"twenty)(?:\b|[.:])",
            re.IGNORECASE,
        ),
        "chapter_en",
    ),
    (
        re.compile(r"^\s*(?:prologue|epilogue|introduction|foreword|afterword)\s*$", re.IGNORECASE),
        "intro_conclusion_en",
    ),
    (
        re.compile(
            "^\\s*(?:\u0422\u0430\u0440\u0430\u0443|\u0442\u0430\u0440\u0430\u0443|"
            "\u0411\u04e9\u043b\u0456\u043c|\u0431\u04e9\u043b\u0456\u043c)\\s+"
            "(?:\\d+|[IVXLCDMivxlcdm]+|[\u0400-\u04ff]+)(?:\\b|[.:])"
        ),
        "chapter_kk",
    ),
    (
        re.compile(
            "^\\s*(?:bob|bo['`\u02bc]?lim)\\s+(?:\\d+|[ivxlcdm]+|[a-z\u02bc'`-]+)(?:\\b|[.:])",
            re.IGNORECASE,
        ),
        "chapter_uz",
    ),
    (
        re.compile("^\\s*\u7b2c[\\d\u4e00-\u9fff]{1,8}[\u7ae0\u56de\u8282]\\s*.*$"),
        "chapter_zh",
    ),
    (
        re.compile("^\\s*(?:\u5e8f\u7ae0|\u524d\u8a00|\u540e\u8bb0|\u7ed3\u8bed)\\s*$"),
        "intro_conclusion_zh",
    ),
]


WORK_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            "^\\s*(?:\u041a\u043d\u0438\u0433\u0430|\u043a\u043d\u0438\u0433\u0430|"
            "\u041a\u0456\u0442\u0430\u043f|\u043a\u0456\u0442\u0430\u043f|"
            "\u0422\u043e\u043c|\u0442\u043e\u043c)\\s+"
            "(?:\\d+|[IVXLCDMivxlcdm]+|[\u0400-\u04ff]+)(?:\\b|[.:]).{0,90}$"
        ),
        "work_cyrillic",
    ),
    (
        re.compile(
            r"^\s*(?:book|volume|vol\.)\s+"
            r"(?:\d+|[ivxlcdm]+|one|two|three|four|five|six|seven|eight|nine|ten|"
            r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
            r"twenty)(?:\b|[.:]).{0,90}$",
            re.IGNORECASE,
        ),
        "work_en",
    ),
    (
        re.compile(
            "^\\s*(?:kitob|tom)\\s+(?:\\d+|[ivxlcdm]+|[a-z\u02bc'`-]+)(?:\\b|[.:]).{0,90}$",
            re.IGNORECASE,
        ),
        "work_uz",
    ),
    (
        re.compile("^\\s*\u7b2c[\\d\u4e00-\u9fff]{1,8}[\u90e8\u5377\u518c]\\s*.*$"),
        "work_zh",
    ),
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


def match_work_heading(line: str) -> tuple[str, str] | None:
    """
    Check if a line looks like a top-level book, work, or volume boundary.

    The detector uses these boundaries to preserve omnibus files,
    trilogies, and collected editions before it searches for chapters.
    """
    stripped = line.strip()
    if not stripped or len(stripped) > 140:
        return None
    for pattern, label in WORK_PATTERNS:
        m = pattern.match(stripped)
        if m:
            return (stripped, label)
    return None
