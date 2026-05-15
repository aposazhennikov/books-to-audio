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

# Stray OCR artifacts: single low-comma, guillemets, backticks in Cyrillic context.
_STRAY_PUNCT_IN_CYR = re.compile(
    r"(?<=[а-яёА-ЯЁ])['\u2018\u2019`\u201A\u201B\u2039\u203A‹›](?=\s|[а-яёА-ЯЁ]|$)"
)

# Spurious period inside a word: "за. столом" -> "за столом".
_PERIOD_INSIDE_WORD = re.compile(
    r"(?<=[а-яёА-ЯЁ])\.\s(?=[а-яё])"
)

# Lone garbage characters surrounded by whitespace in Cyrillic text.
_LONE_GARBAGE = re.compile(
    r"(?<=\s)[=<>|#№\u2021\u2020\u00A7\u00B6]+(?=\s)"
)

# Two or more stray single characters separated by spaces (OCR junk).
_SCATTERED_CHARS = re.compile(
    r"\b([а-яёА-ЯЁa-zA-Z])\s+([а-яёА-ЯЁa-zA-Z])\s+([а-яёА-ЯЁa-zA-Z])\b"
)


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


_TRAILING_JUNK = re.compile(
    r"\s+[а-яёА-ЯЁa-zA-Z.,;:!?\-]{1,3}\s*$"
)

_LEADING_COMMA_PERIOD = re.compile(
    r"^[‚,.:;]\s*"
)

_MULTI_SPACE = re.compile(r" {3,}")

_BROKEN_HYPHEN = re.compile(
    r"([а-яёА-ЯЁ])-\s*\n\s*([а-яё])"
)

_STRAY_LINE_PATTERN = re.compile(
    r"^[\s\W]{0,4}[а-яёА-ЯЁa-zA-Z]{1,2}[\s\W]{0,4}$"
)


def fix_ocr_artifacts(text: str) -> str:
    """Remove common OCR artifacts from Cyrillic text.

    Handles stray apostrophes/backticks, spurious periods inside words,
    lone garbage symbols, low-comma quotation marks, trailing junk characters,
    broken hyphenated words across lines, and scattered single-char noise
    typical of Tesseract misrecognition on Russian scans.
    """
    text = _STRAY_PUNCT_IN_CYR.sub("", text)
    text = _PERIOD_INSIDE_WORD.sub(" ", text)
    text = _LONE_GARBAGE.sub("", text)

    # Rejoin words broken by hyphenation across lines.
    text = _BROKEN_HYPHEN.sub(r"\1\2", text)

    # Remove excess whitespace (3+ spaces -> single space).
    text = _MULTI_SPACE.sub(" ", text)

    lines = text.split("\n")
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()

        # Skip empty lines (preserve one blank).
        if not stripped:
            if not cleaned or cleaned[-1].strip():
                cleaned.append("")
            continue

        # Skip lines that are just 1-2 stray characters (OCR noise).
        if _STRAY_LINE_PATTERN.match(stripped):
            if not stripped.isdigit() and stripped not in ("—", "«", "»", "—,"):
                continue

        # Remove leading stray comma/period from OCR.
        stripped = _LEADING_COMMA_PERIOD.sub("", stripped)

        # Remove trailing junk chars (1-3 random letters at line end).
        stripped = _TRAILING_JUNK.sub("", stripped)

        if stripped:
            cleaned.append(stripped)

    text = "\n".join(cleaned)
    return text
