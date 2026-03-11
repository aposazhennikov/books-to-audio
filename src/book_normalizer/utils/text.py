"""Text utility helpers."""

from __future__ import annotations


def truncate(text: str, max_len: int = 80) -> str:
    """Truncate text to max_len with ellipsis if needed."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def count_words(text: str) -> int:
    """Count whitespace-delimited words in text."""
    return len(text.split())
