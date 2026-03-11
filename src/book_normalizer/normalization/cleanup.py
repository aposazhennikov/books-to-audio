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

    Counts line occurrences; if a line appears more than `min_occurrences`
    times, it is likely a repeating header or footer.
    """
    lines = text.split("\n")
    line_counts: dict[str, int] = {}
    for line in lines:
        stripped = line.strip()
        if stripped and len(stripped) < 100:
            line_counts[stripped] = line_counts.get(stripped, 0) + 1

    repeated = {line for line, count in line_counts.items() if count >= min_occurrences}
    if not repeated:
        return text

    cleaned_lines: list[str] = []
    for line in lines:
        if line.strip() not in repeated:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)
