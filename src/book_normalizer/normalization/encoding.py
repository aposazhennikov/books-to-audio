"""Encoding-related normalization for garbled or mixed-encoding text."""

from __future__ import annotations

import re

_MOJIBAKE_REPLACEMENTS: list[tuple[str, str]] = [
    ("\u0410\u0402", "\u0410"),
    ("\u00c3\u0192", "\u0410"),
    ("\u0432\u0402\u201c", "\u2014"),
    ("\u0432\u0402\u201d", "\u2014"),
    ("\u0432\u0402\u0153", "\u00ab"),
    ("\u0432\u0402\u045e", "\u00bb"),
]


def fix_common_mojibake(text: str) -> str:
    """
    Attempt to fix common mojibake patterns from double-encoding.

    These patterns arise when UTF-8 Russian text is decoded as CP1252
    and then re-encoded. Only safe, high-confidence replacements are applied.
    """
    for bad, good in _MOJIBAKE_REPLACEMENTS:
        text = text.replace(bad, good)
    return text


def normalize_encoding_artifacts(text: str) -> str:
    """
    Remove or replace encoding artifacts commonly found in extracted text.

    Targets replacement characters, unusual control sequences,
    and stray byte-order marks embedded within text.
    """
    text = text.replace("\ufffd", "")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = text.replace("\ufeff", "")
    return text
