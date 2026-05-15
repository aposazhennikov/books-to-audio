"""Cleanup transformations for common extraction artifacts."""

from __future__ import annotations

import re


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
        if stripped and len(stripped) < 100:
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
