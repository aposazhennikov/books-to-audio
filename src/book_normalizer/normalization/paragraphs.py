"""Paragraph-level normalization utilities."""

from __future__ import annotations

import re


def collapse_empty_lines(text: str) -> str:
    """Replace runs of 3+ empty lines with exactly two (paragraph boundary)."""
    return re.sub(r"\n{3,}", "\n\n", text)


def strip_paragraph_indents(text: str) -> str:
    """Remove leading indentation that some extractors add to every paragraph."""
    return re.sub(r"^[ \t]+", "", text, flags=re.MULTILINE)
