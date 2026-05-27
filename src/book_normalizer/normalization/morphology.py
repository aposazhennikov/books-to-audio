"""Optional pymorphy3 helpers for conservative rule-based context checks."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

_PLURAL_HEAD_POS = frozenset({"NOUN", "ADJF", "ADJS", "PRTF", "PRTS", "NPRO", "NUMR"})


@lru_cache(maxsize=1)
def _get_morph_analyzer() -> Any | None:
    """Return a cached pymorphy3 analyzer, or None when the dependency is absent."""
    try:
        from pymorphy3 import MorphAnalyzer
    except ImportError:
        return None

    try:
        return MorphAnalyzer()
    except Exception as exc:  # pragma: no cover - defensive against bad dictionaries
        logger.warning("Failed to initialize pymorphy3 MorphAnalyzer: %s", exc)
        return None


def parse_word(word: str) -> list[Any]:
    """Parse a word with pymorphy3 if available."""
    analyzer = _get_morph_analyzer()
    if analyzer is None:
        return []
    try:
        return list(analyzer.parse(word))
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("pymorphy3 failed to parse %r: %s", word, exc)
        return []


def is_likely_plural_head(word: str) -> bool:
    """
    Return True when a word is likely a plural noun/modifier head.

    This is intentionally conservative and is used to avoid changing
    ``все люди`` into ``всё люди``.
    """
    for parse in parse_word(word)[:3]:
        tag = getattr(parse, "tag", None)
        if tag is None:
            continue
        pos = getattr(tag, "POS", None)
        if pos in _PLURAL_HEAD_POS and "plur" in tag:
            return True
    return False


def infer_person_gender(word: str) -> str:
    """Infer ``male``/``female`` for a singular Russian person noun or name."""

    cleaned = str(word or "").strip().split()[0] if str(word or "").strip() else ""
    if not cleaned:
        return ""
    if cleaned[:1].isupper() and cleaned.casefold().endswith(
        ("очка", "ечка", "онька", "енька", "ушка", "юша")
    ):
        return "female"
    for parse in parse_word(cleaned)[:3]:
        tag = getattr(parse, "tag", None)
        if tag is None:
            continue
        pos = getattr(tag, "POS", None)
        if pos != "NOUN" or "sing" not in tag or "plur" in tag:
            continue
        if "Name" not in tag and "anim" not in tag:
            continue
        if "masc" in tag:
            return "male"
        if "femn" in tag:
            return "female"
    return ""
