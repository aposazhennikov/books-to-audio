# -*- coding: utf-8 -*-
"""Punctuation normalization for Russian text."""

from __future__ import annotations

import re

EM_DASH = "\u2014"
EN_DASH = "\u2013"
LEFT_QUOTE = "\u00ab"
RIGHT_QUOTE = "\u00bb"
LOW_QUOTE = "\u201e"
RIGHT_DOUBLE_QUOTE = "\u201c"
LEFT_DOUBLE_QUOTE = "\u201d"
ELLIPSIS = "\u2026"


def normalize_quotes(text: str) -> str:
    """
    Normalize quote characters to standard Russian typographic quotes.

    Converts straight quotes and various Unicode quote chars
    to the standard Russian quote style.
    """
    text = re.sub(r'(?<!\w)"([^"]+)"(?!\w)', LEFT_QUOTE + r"\1" + RIGHT_QUOTE, text)
    text = text.replace(RIGHT_DOUBLE_QUOTE, LEFT_QUOTE).replace(LEFT_DOUBLE_QUOTE, RIGHT_QUOTE)
    text = text.replace(LOW_QUOTE, LEFT_QUOTE)
    return text


def normalize_dashes(text: str) -> str:
    """
    Normalize various dash-like characters to proper em-dash usage.

    In Russian typography, em-dash is standard for dialogue
    and parenthetical clauses.
    """
    replacement = " " + EM_DASH + " "
    text = re.sub(r"\s--\s", replacement, text)
    text = re.sub(r"\s" + EN_DASH + r"\s", replacement, text)
    text = text.replace("--", EM_DASH)
    return text


def normalize_ellipsis(text: str) -> str:
    """Replace sequences of dots with a proper ellipsis character."""
    text = re.sub(r"\.{3,}", ELLIPSIS, text)
    return text


def adapt_punctuation_for_tts(text: str) -> str:
    """
    Adjust punctuation for better TTS output quality.

    - Replace em-dash used as sentence connector (not dialogue) with comma.
    - Replace ellipsis before a capital letter with period (clearer pause).
    - Strip leftover markdown formatting.
    """
    # Em-dash between clauses (not at line start = not dialogue).
    # Pattern: "word — word" mid-sentence -> "word, word".
    text = re.sub(
        r"(?<=[а-яёА-ЯЁ\d,.])\s*" + EM_DASH + r"\s*(?=[а-яё\d])",
        ", ",
        text,
    )

    # Ellipsis before a capital letter -> period for cleaner TTS pause.
    text = re.sub(r"…\s*(?=[А-ЯЁA-Z])", ". ", text)

    # Strip markdown bold/italic/heading markers.
    text = re.sub(r"\*{1,3}|_{1,3}", "", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

    return text
