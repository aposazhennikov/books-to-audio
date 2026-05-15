"""Optional silero-stress adapter and stress mark conversion helpers."""

from __future__ import annotations

import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)

COMBINING_ACUTE = "\u0301"
VOWELS = frozenset("аеёиоуыэюяАЕЁИОУЫЭЮЯ")


def convert_external_stress_marks(text: str) -> str:
    """
    Convert external stress notation to U+0301 combining acute marks.

    Supported formats:
    - silero-stress / plus-before-vowel: ``зам+ок`` -> ``замо́к``.
    - apostrophe after a vowel: ``замо'к`` -> ``замо́к``.
    - apostrophe before a vowel: ``зам'ок`` -> ``замо́к``.
    """
    if not text:
        return text

    result: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        next_ch = text[i + 1] if i + 1 < len(text) else ""

        if ch == "+" and next_ch in VOWELS:
            result.append(next_ch)
            result.append(COMBINING_ACUTE)
            i += 2
            continue

        if ch in {"'", "’", "`", "´"}:
            if result and result[-1] in VOWELS:
                result.append(COMBINING_ACUTE)
                i += 1
                continue
            if next_ch in VOWELS:
                result.append(next_ch)
                result.append(COMBINING_ACUTE)
                i += 2
                continue

        result.append(ch)
        i += 1

    return "".join(result)


class SileroStressPredictor:
    """Lazy wrapper around silero-stress."""

    def __init__(self) -> None:
        self._accentor: Callable[[str], str] | None = None
        self._load_attempted = False

    def _load(self) -> Callable[[str], str] | None:
        if self._load_attempted:
            return self._accentor

        self._load_attempted = True
        try:
            from silero_stress import load_accentor
        except ImportError:
            logger.info("silero-stress is not installed; stress model fallback disabled.")
            return None

        try:
            self._accentor = load_accentor()
        except Exception as exc:  # pragma: no cover - depends on torch/model runtime
            logger.warning("Failed to initialize silero-stress accentor: %s", exc)
            self._accentor = None
        return self._accentor

    def accent_text(self, text: str) -> str | None:
        """Return text with U+0301 stress marks, or None if unavailable."""
        if not text:
            return text

        accentor = self._load()
        if accentor is None:
            return None

        try:
            accented = accentor(text)
        except Exception as exc:  # pragma: no cover - depends on torch/model runtime
            logger.warning("silero-stress accenting failed: %s", exc)
            return None

        if not isinstance(accented, str):
            return None
        return convert_external_stress_marks(accented)

