"""Expand numeric literals to Russian words for TTS readability."""

from __future__ import annotations

import re

from num2words import num2words

# Ordinal suffix patterns: "17-й", "2-го", "1-му", "3-м", "5-я".
_ORDINAL_RE = re.compile(
    r"\b(\d+)-(?:й|го|му|м|я|ю|ой|ей|ых|ое|ая|ые|ом|ем|ым|им)\b"
)

# Standalone numbers: "17", "1812" surrounded by non-digit context.
# Avoid matching numbers that are part of larger tokens (like filenames).
_STANDALONE_NUM_RE = re.compile(r"(?<!\S)(\d{1,6})(?!\S|\d)")

# Year pattern: already handled by abbreviations.py ("1812 года"),
# but bare 4-digit numbers in text still need expansion.
_FOUR_DIGIT_YEAR_CONTEXT = re.compile(
    r"(?:в|до|после|около|к|с|от)\s+(\d{4})\b"
)


def _safe_num2words(n: int, **kwargs: str) -> str:
    """Wrapper around num2words that handles edge cases."""
    try:
        return num2words(n, lang="ru", **kwargs)
    except (ValueError, OverflowError):
        return str(n)


def _expand_ordinal(match: re.Match[str]) -> str:
    """Expand ordinal number like '17-й' -> 'семнадцатый'."""
    n = int(match.group(1))
    suffix = match.group(0).split("-", 1)[1]

    to_param = "ordinal"
    # Feminine forms.
    if suffix in ("я", "ю", "ой", "ей", "ая"):
        # num2words doesn't have gender support; use default ordinal.
        pass
    return _safe_num2words(n, to=to_param)


def _expand_standalone(match: re.Match[str]) -> str:
    """Expand a standalone number to cardinal words."""
    n = int(match.group(1))
    if n == 0:
        return match.group(0)
    return _safe_num2words(n)


def expand_numbers(text: str) -> str:
    """
    Replace numeric literals in Russian text with their word equivalents.

    Handles ordinals ('17-й' -> 'семнадцатый'), cardinals ('17' -> 'семнадцать'),
    and avoids touching numbers that are part of structured data.
    """
    # Ordinals first (before stripping the suffix).
    text = _ORDINAL_RE.sub(_expand_ordinal, text)

    # Standalone numbers.
    text = _STANDALONE_NUM_RE.sub(_expand_standalone, text)

    return text
