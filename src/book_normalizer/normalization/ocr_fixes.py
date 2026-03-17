"""Automatic OCR artifact fixes for the normalization pipeline."""

from __future__ import annotations

import re

# Latin characters that look identical to Cyrillic and can be safely replaced.
_LATIN_TO_CYRILLIC: dict[str, str] = {
    "a": "\u0430", "A": "\u0410",
    "e": "\u0435", "E": "\u0415",
    "o": "\u043e", "O": "\u041e",
    "p": "\u0440", "P": "\u0420",
    "c": "\u0441", "C": "\u0421",
    "x": "\u0445", "X": "\u0425",
    "H": "\u041d",
    "K": "\u041a",
    "M": "\u041c",
    "T": "\u0422",
    "B": "\u0412",
    "y": "\u0443",
}

_MAPPABLE_LATIN = set(_LATIN_TO_CYRILLIC.keys())
_HAS_CYRILLIC = re.compile(r"[а-яёА-ЯЁ]")
_HAS_LATIN = re.compile(r"[a-zA-Z]")
_ONLY_LATIN = re.compile(r"^[a-zA-Z]+$")
_WORD_RE = re.compile(r"\S+")

# Maximum length for a purely Latin word to be auto-corrected.
_MAX_AUTOFIX_LEN = 5


def _transliterate(word: str) -> str:
    """Replace Latin lookalikes with Cyrillic equivalents."""
    return "".join(_LATIN_TO_CYRILLIC.get(ch, ch) for ch in word)


def _all_chars_mappable(word: str) -> bool:
    """Check if every Latin letter in the word has a Cyrillic equivalent."""
    return all(ch in _MAPPABLE_LATIN for ch in word if ch.isalpha())


def fix_mixed_script(text: str) -> str:
    """
    Fix OCR-induced Latin characters in Cyrillic text.

    Two strategies:
    1. Mixed-script words (both Cyrillic and Latin) — replace Latin chars.
    2. Short purely-Latin words (<=5 chars) where ALL letters have Cyrillic
       lookalikes AND the surrounding text is Cyrillic — replace the whole word.
       This catches 'Ha'->'На', 'OH'->'ОН', 'HO'->'НО' etc.
    """
    words = _WORD_RE.findall(text)
    offsets = list(_WORD_RE.finditer(text))

    if not offsets:
        return text

    # Determine which words are Cyrillic for context checks.
    is_cyrillic = [bool(_HAS_CYRILLIC.search(w)) for w in words]

    result_parts: list[str] = []
    prev_end = 0

    for i, m in enumerate(offsets):
        result_parts.append(text[prev_end:m.start()])
        word = m.group(0)

        if _HAS_CYRILLIC.search(word) and _HAS_LATIN.search(word):
            result_parts.append(_transliterate(word))
        elif (
            _ONLY_LATIN.match(word)
            and len(word) <= _MAX_AUTOFIX_LEN
            and _all_chars_mappable(word)
            and _has_cyrillic_context(is_cyrillic, i)
        ):
            result_parts.append(_transliterate(word))
        else:
            result_parts.append(word)

        prev_end = m.end()

    result_parts.append(text[prev_end:])
    return "".join(result_parts)


def _has_cyrillic_context(is_cyrillic: list[bool], idx: int) -> bool:
    """Check if neighboring words (within 2 positions) contain Cyrillic."""
    for offset in (-1, 1, -2, 2):
        neighbor = idx + offset
        if 0 <= neighbor < len(is_cyrillic) and is_cyrillic[neighbor]:
            return True
    return False
