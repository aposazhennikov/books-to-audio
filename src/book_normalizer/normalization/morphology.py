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
    parses = parse_word(cleaned)
    for parse in parses[:3]:
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
    if _looks_like_capitalized_inflected_male_name(cleaned, parses):
        return "male"
    if _looks_like_capitalized_male_name(cleaned, parses):
        return "male"
    return ""


def is_definitely_not_person_reference(word: str) -> bool:
    """Return true for tokens that should not be accepted as speaker names."""

    cleaned = str(word or "").strip().split()[0] if str(word or "").strip() else ""
    if not cleaned:
        return False
    parses = parse_word(cleaned)
    if not parses:
        return False
    if _has_person_name_parse(parses):
        return False
    first_tag = getattr(parses[0], "tag", None)
    if first_tag is None:
        return False
    first_pos = getattr(first_tag, "POS", None)
    if first_pos in {
        "NPRO",
        "ADVB",
        "PREP",
        "CONJ",
        "PRCL",
        "INTJ",
        "GRND",
        "INFN",
        "ADJF",
        "ADJS",
        "PRTF",
        "PRTS",
    }:
        return True
    if first_pos == "VERB":
        return True
    first_score = float(getattr(parses[0], "score", 0.0))
    return bool(first_pos == "NOUN" and "inan" in first_tag and first_score >= 0.58)


def _has_person_name_parse(parses: list[Any]) -> bool:
    for parse in parses[:5]:
        tag = getattr(parse, "tag", None)
        if tag is not None and ("Name" in tag or "Surn" in tag):
            return True
    return False


def _looks_like_capitalized_inflected_male_name(word: str, parses: list[Any]) -> bool:
    """Return true for capitalized masculine names in non-nominative cases."""

    if not word[:1].isupper() or not parses:
        return False
    first_tag = getattr(parses[0], "tag", None)
    if first_tag is None:
        return False
    first_score = float(getattr(parses[0], "score", 0.0))
    return bool(
        getattr(first_tag, "POS", None) == "NOUN"
        and "masc" in first_tag
        and "sing" in first_tag
        and "nomn" not in first_tag
        and "accs" not in first_tag
        and first_score >= 0.8
    )


def _looks_like_capitalized_male_name(word: str, parses: list[Any]) -> bool:
    """Return true for unknown/proper-looking masculine names absent from dictionaries."""

    if not word[:1].isupper() or not word.replace("-", "").isalpha():
        return False
    lowered = word.casefold()
    if not lowered.endswith((
        "б", "в", "г", "д", "ж", "з", "к", "л", "м", "н", "п", "р", "с", "т", "ф", "х", "ц", "ч", "ш", "щ", "й",
    )):
        return False
    first_tag = getattr(parses[0], "tag", None) if parses else None
    first_score = float(getattr(parses[0], "score", 0.0)) if parses else 0.0
    if first_tag is not None:
        first_pos = getattr(first_tag, "POS", None)
        if first_pos in {"INFN", "GRND", "ADVB", "CONJ", "PRCL", "PREP"}:
            return False
        if first_pos == "NOUN" and "inan" in first_tag and first_score >= 0.58:
            return False
    return True
