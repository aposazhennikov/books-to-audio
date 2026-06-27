"""Text utility helpers."""

from __future__ import annotations

_MOJIBAKE_MARKERS = (
    "\u00d0",
    "\u00d1",
    "\u00c2",
    "\u00e2\u20ac",
    "\u00e2\u20ac\u2122",
    "\u00e2\u20ac\u0153",
    "\u00e2\u20ac\u009d",
    "\u00e2\u20ac\u201d",
    "\u00e2\u20ac\u201c",
)


def truncate(text: str, max_len: int = 80) -> str:
    """Truncate text to max_len with ellipsis if needed."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def count_words(text: str) -> int:
    """Count whitespace-delimited words in text."""
    return len(text.split())


def repair_utf8_mojibake(text: str) -> str:
    """
    Repair text decoded as Latin-1/CP1252 while the original bytes were UTF-8.

    Some PDF text layers expose Russian UTF-8 bytes that PyMuPDF/pdfminer surface
    as strings like ``Ð‘. Ðœ.`` instead of ``Б. М.``. Leaving that form in place
    breaks chapter detection, annotations, dialogue attribution, and TTS prosody.
    """
    if not text:
        return text

    original_score = _text_quality_score(text)
    best = text
    best_score = original_score

    for encoding in ("latin1", "cp1252"):
        candidate = _decode_utf8_roundtrip(text, encoding)
        if candidate is None:
            continue
        score = _text_quality_score(candidate)
        if score > best_score:
            best = candidate
            best_score = score

    if best is text:
        return text

    # Require a material improvement so ordinary multilingual text is untouched.
    min_gain = max(12, min(500, len(text) // 200))
    if best_score < original_score + min_gain:
        return text
    return best


def _decode_utf8_roundtrip(text: str, encoding: str) -> str | None:
    try:
        return text.encode(encoding).decode("utf-8")
    except UnicodeError:
        return None


def _text_quality_score(text: str) -> int:
    cyrillic = sum(1 for ch in text if "\u0400" <= ch <= "\u04ff")
    latin = sum(1 for ch in text if ("A" <= ch <= "Z") or ("a" <= ch <= "z"))
    markers = sum(text.count(marker) for marker in _MOJIBAKE_MARKERS)
    replacement = text.count("\ufffd")

    # Cyrillic is expected for the default Russian pipeline; Latin is neutral.
    # Mojibake marker characters are strong evidence that extraction is broken.
    return cyrillic * 4 + latin - markers * 18 - replacement * 30
