"""Cleanup transformations for common extraction artifacts."""

from __future__ import annotations

import re

from book_normalizer.chaptering.patterns import match_chapter_heading, match_work_heading

_URL_RE = re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE)
_PUBLISHER_BOILERPLATE_PHRASES = (
    "скачали книгу",
    "бесплатной электронной библиотеке",
    "все книги автора",
    "эта же книга в других форматах",
    "приятного чтения",
    "книга подготовлена",
    "литературного агентства",
    "royallib",
    "sesame",
)
_LEADING_BOILERPLATE_RE = re.compile(
    r"^\s*(?:приятного\s+чтения|спасибо,\s+что\s+скачали\s+книгу)[.!…:;,\s]*",
    re.IGNORECASE,
)


def _is_structure_heading_line(text: str) -> bool:
    """Return true for book/chapter boundaries that must not be treated as headers."""
    stripped = text.strip()
    if not stripped:
        return False
    return bool(match_chapter_heading(stripped) or match_work_heading(stripped))


def is_likely_publisher_boilerplate(text: str) -> bool:
    """Return true for library/publisher boilerplate that should not be voiced."""
    normalized = re.sub(r"\s+", " ", text.strip().casefold())
    if not normalized:
        return False

    phrase_hits = sum(
        1 for phrase in _PUBLISHER_BOILERPLATE_PHRASES if phrase in normalized
    )
    has_url = bool(_URL_RE.search(normalized))
    if has_url and phrase_hits:
        return True
    if phrase_hits >= 2:
        return True

    url_chars = sum(len(match.group(0)) for match in _URL_RE.finditer(normalized))
    return has_url and url_chars / max(len(normalized), 1) > 0.35


def remove_publisher_boilerplate(text: str) -> str:
    """Remove library/publisher front matter that should not be voiced."""
    cleaned_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append("")
            continue
        if is_likely_publisher_boilerplate(stripped):
            continue

        stripped = _LEADING_BOILERPLATE_RE.sub("", stripped).strip()
        if stripped and not is_likely_publisher_boilerplate(stripped):
            cleaned_lines.append(stripped)

    return "\n".join(cleaned_lines).strip()


def remove_page_numbers(text: str) -> str:
    """
    Remove standalone page numbers that appear on their own line.

    Targets lines that consist solely of a number (possibly with
    surrounding whitespace), which is a common PDF extraction artifact.
    """
    return re.sub(r"^\s*\d{1,4}\s*$", "", text, flags=re.MULTILINE)


def remove_repeated_headers(text: str, min_occurrences: int = 3) -> str:
    """
    Remove repeated header/footer lines that appear across pages.

    Counts line occurrences and patterns (lines with numbers replaced by #).
    If a line or pattern appears more than `min_occurrences` times,
    it is likely a repeating header or footer.
    """
    lines = text.split("\n")
    line_counts: dict[str, int] = {}
    pattern_counts: dict[str, int] = {}

    for line in lines:
        stripped = line.strip()
        if stripped and len(stripped) < 100 and not _is_structure_heading_line(stripped):
            # Count exact line.
            line_counts[stripped] = line_counts.get(stripped, 0) + 1

            # Count pattern with numbers replaced by #.
            pattern = re.sub(r"\d+", "#", stripped)
            if pattern != stripped:  # Only if line contains numbers.
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

    # Find repeated exact lines.
    repeated = {line for line, count in line_counts.items() if count >= min_occurrences}

    # Find repeated patterns (e.g., "Page #" appears many times).
    repeated_patterns = {
        pattern for pattern, count in pattern_counts.items() if count >= min_occurrences
    }

    if not repeated and not repeated_patterns:
        return text

    cleaned_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if _is_structure_heading_line(stripped):
            cleaned_lines.append(line)
            continue
        # Skip if exact match or pattern match.
        if stripped in repeated:
            continue
        pattern = re.sub(r"\d+", "#", stripped)
        if pattern in repeated_patterns:
            continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


# Inline footnote pattern: a line starting with 1-2 digits followed by
# a lowercase letter and short explanatory text (< 100 chars total).
_INLINE_FOOTNOTE_RE = re.compile(
    r"^\s*\d{1,2}\s+[а-яё].*$", re.MULTILINE
)

# Superscript-style footnote markers in running text: "[1]", "[2]".
_BRACKET_FOOTNOTE_REF = re.compile(r"\[\d{1,2}\]")


def remove_inline_footnotes(text: str) -> str:
    """
    Remove inline footnotes that were merged into running text by OCR.

    Targets two patterns:
    1. Standalone short lines like '1 чтобы стать учителем (франц.).'
    2. Bracketed references like '[1]' or '[2]' within sentences.
    """
    lines = text.split("\n")
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()
        if (
            stripped
            and len(stripped) < 100
            and _INLINE_FOOTNOTE_RE.match(stripped)
            and not re.match(r"^\s*\d{1,2}\s+[А-ЯЁA-Z]", stripped)
        ):
            continue
        cleaned.append(line)
    result = "\n".join(cleaned)
    result = _BRACKET_FOOTNOTE_REF.sub("", result)
    return result
