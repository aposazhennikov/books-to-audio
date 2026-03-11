"""Built-in stress dictionary and unified lookup for Russian words."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from book_normalizer.memory.stress_store import StressStore
from book_normalizer.models.memory import StressMemoryEntry

logger = logging.getLogger(__name__)

COMBINING_ACUTE = "\u0301"

_CYRILLIC_WORD_RE = re.compile(r"[а-яёА-ЯЁ]+", re.UNICODE)

VOWELS = frozenset("аеёиоуыэюяАЕЁИОУЫЭЮЯ")


def count_vowels(word: str) -> int:
    """Count the number of vowels (syllables) in a Russian word."""
    return sum(1 for ch in word if ch in VOWELS)


def is_russian_word(token: str) -> bool:
    """Check if a token is a pure Russian word."""
    return bool(_CYRILLIC_WORD_RE.fullmatch(token))


def strip_stress(word: str) -> str:
    """Remove all combining acute accent marks from a word."""
    return word.replace(COMBINING_ACUTE, "")


def apply_stress(word: str, vowel_index: int) -> str:
    """
    Apply a combining acute accent after the vowel at the given position.

    vowel_index is 0-based counting only vowels in the word.
    """
    vi = 0
    result: list[str] = []
    for ch in word:
        result.append(ch)
        if ch in VOWELS:
            if vi == vowel_index:
                result.append(COMBINING_ACUTE)
            vi += 1
    return "".join(result)


_BUILTIN_STRESS: dict[str, str] = {
    "молоко": "молоко" + COMBINING_ACUTE,
    "дорога": "доро" + COMBINING_ACUTE + "га",
    "город": "го" + COMBINING_ACUTE + "род",
    "голова": "голова" + COMBINING_ACUTE,
    "вода": "вода" + COMBINING_ACUTE,
    "река": "река" + COMBINING_ACUTE,
    "земля": "земля" + COMBINING_ACUTE,
    "книга": "кни" + COMBINING_ACUTE + "га",
    "слово": "сло" + COMBINING_ACUTE + "во",
    "время": "вре" + COMBINING_ACUTE + "мя",
    "место": "ме" + COMBINING_ACUTE + "сто",
    "дело": "де" + COMBINING_ACUTE + "ло",
    "глаза": "глаза" + COMBINING_ACUTE,
    "рука": "рука" + COMBINING_ACUTE,
    "нога": "нога" + COMBINING_ACUTE,
    "дверь": "две" + COMBINING_ACUTE + "рь",
    "окно": "окно" + COMBINING_ACUTE,
    "утро": "у" + COMBINING_ACUTE + "тро",
    "ночь": "но" + COMBINING_ACUTE + "чь",
    "день": "де" + COMBINING_ACUTE + "нь",
    "человек": "челове" + COMBINING_ACUTE + "к",
    "работа": "рабо" + COMBINING_ACUTE + "та",
    "жизнь": "жи" + COMBINING_ACUTE + "знь",
    "ребёнок": "ребё" + COMBINING_ACUTE + "нок",
    "страна": "страна" + COMBINING_ACUTE,
    "сторона": "сторона" + COMBINING_ACUTE,
    "деревня": "дере" + COMBINING_ACUTE + "вня",
    "дорого": "до" + COMBINING_ACUTE + "рого",
    "хорошо": "хорошо" + COMBINING_ACUTE,
    "далеко": "далеко" + COMBINING_ACUTE,
    "красиво": "краси" + COMBINING_ACUTE + "во",
    "понятно": "поня" + COMBINING_ACUTE + "тно",
    "сегодня": "сего" + COMBINING_ACUTE + "дня",
    "спасибо": "спаси" + COMBINING_ACUTE + "бо",
    "пожалуйста": "пожа" + COMBINING_ACUTE + "луйста",
    "здравствуйте": "здра" + COMBINING_ACUTE + "вствуйте",
    "обязательно": "обяза" + COMBINING_ACUTE + "тельно",
    "замок": "за" + COMBINING_ACUTE + "мок",
    "писать": "писа" + COMBINING_ACUTE + "ть",
    "читать": "чита" + COMBINING_ACUTE + "ть",
    "говорить": "говори" + COMBINING_ACUTE + "ть",
    "думать": "ду" + COMBINING_ACUTE + "мать",
    "знать": "зна" + COMBINING_ACUTE + "ть",
    "видеть": "ви" + COMBINING_ACUTE + "деть",
    "слышать": "слы" + COMBINING_ACUTE + "шать",
    "хотеть": "хоте" + COMBINING_ACUTE + "ть",
    "мочь": "мо" + COMBINING_ACUTE + "чь",
    "идти": "идти" + COMBINING_ACUTE,
    "стоять": "стоя" + COMBINING_ACUTE + "ть",
    "сидеть": "сиде" + COMBINING_ACUTE + "ть",
    "лежать": "лежа" + COMBINING_ACUTE + "ть",
    "бежать": "бежа" + COMBINING_ACUTE + "ть",
    "начать": "нача" + COMBINING_ACUTE + "ть",
    "понять": "поня" + COMBINING_ACUTE + "ть",
}


class StressDictionary:
    """
    Unified stress dictionary combining built-in entries with user StressStore.

    Lookup priority:
    1. User store (highest priority — user corrections override everything).
    2. Built-in dictionary.
    3. None if not found.

    Single-vowel words are auto-resolved (stress is unambiguous).
    """

    def __init__(self, store: StressStore | None = None) -> None:
        self._store = store
        self._builtin = dict(_BUILTIN_STRESS)

    @property
    def builtin_count(self) -> int:
        """Number of entries in the built-in dictionary."""
        return len(self._builtin)

    @property
    def user_count(self) -> int:
        """Number of entries in the user store."""
        if self._store is None:
            return 0
        return self._store.count()

    def lookup(self, word: str) -> str | None:
        """
        Look up the stressed form of a word.

        Returns the stressed form string (with combining acute)
        or None if the word is unknown.
        """
        normalized = word.lower().strip()
        if not normalized or not is_russian_word(normalized):
            return None

        if count_vowels(normalized) <= 1:
            return normalized

        if self._store:
            entry = self._store.lookup(normalized)
            if entry and entry.stressed_form:
                return entry.stressed_form

        return self._builtin.get(normalized)

    def is_known(self, word: str) -> bool:
        """Check if a word exists in any dictionary source."""
        return self.lookup(word) is not None

    def add_user_entry(self, word: str, stressed_form: str, confirmed: bool = True) -> None:
        """Add an entry to the user store."""
        if self._store is None:
            logger.warning("No user store configured; entry not persisted.")
            return
        entry = StressMemoryEntry(
            word=word,
            normalized_word=word.lower().strip(),
            stressed_form=stressed_form,
            confirmed=confirmed,
        )
        self._store.add(entry)
