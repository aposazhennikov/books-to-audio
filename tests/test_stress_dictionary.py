"""Tests for the stress dictionary module."""

from __future__ import annotations

from pathlib import Path

from book_normalizer.memory.stress_store import StressStore
from book_normalizer.models.memory import StressMemoryEntry
from book_normalizer.stress.dictionary import (
    COMBINING_ACUTE,
    StressDictionary,
    apply_stress,
    count_vowels,
    is_russian_word,
    strip_stress,
)


class TestHelpers:
    def test_count_vowels(self) -> None:
        assert count_vowels("молоко") == 3
        assert count_vowels("дом") == 1
        assert count_vowels("стр") == 0
        assert count_vowels("") == 0

    def test_is_russian_word(self) -> None:
        assert is_russian_word("слово")
        assert is_russian_word("СЛОВО")
        assert is_russian_word("Ёж")
        assert not is_russian_word("word")
        assert not is_russian_word("сло2во")
        assert not is_russian_word("123")
        assert not is_russian_word("")

    def test_strip_stress(self) -> None:
        stressed = "молоко" + COMBINING_ACUTE
        assert strip_stress(stressed) == "молоко"
        assert strip_stress("простой") == "простой"

    def test_apply_stress(self) -> None:
        result = apply_stress("молоко", 2)
        assert COMBINING_ACUTE in result
        assert result == "молоко" + COMBINING_ACUTE

        result = apply_stress("молоко", 0)
        assert result.startswith("мо" + COMBINING_ACUTE)

        result = apply_stress("молоко", 1)
        assert "ло" + COMBINING_ACUTE in result


class TestStressDictionary:
    def test_builtin_lookup(self) -> None:
        d = StressDictionary()
        result = d.lookup("молоко")
        assert result is not None
        assert COMBINING_ACUTE in result

    def test_builtin_count(self) -> None:
        d = StressDictionary()
        assert d.builtin_count > 30

    def test_single_vowel_auto_resolved(self) -> None:
        d = StressDictionary()
        assert d.lookup("дом") == "дом"
        assert d.lookup("кот") == "кот"

    def test_unknown_word(self) -> None:
        d = StressDictionary()
        assert d.lookup("промышленность") is None

    def test_non_russian_returns_none(self) -> None:
        d = StressDictionary()
        assert d.lookup("hello") is None
        assert d.lookup("") is None

    def test_is_known(self) -> None:
        d = StressDictionary()
        assert d.is_known("молоко")
        assert d.is_known("дом")
        assert not d.is_known("промышленность")

    def test_user_store_overrides_builtin(self, tmp_path: Path) -> None:
        store = StressStore(tmp_path / "stress.json")
        custom_form = "мо" + COMBINING_ACUTE + "локо"
        store.add(StressMemoryEntry(
            word="молоко",
            normalized_word="молоко",
            stressed_form=custom_form,
            confirmed=True,
        ))

        d = StressDictionary(store=store)
        result = d.lookup("молоко")
        assert result == custom_form

    def test_add_user_entry(self, tmp_path: Path) -> None:
        store = StressStore(tmp_path / "stress.json")
        d = StressDictionary(store=store)

        stressed = "промы" + COMBINING_ACUTE + "шленность"
        d.add_user_entry("промышленность", stressed)
        assert d.is_known("промышленность")
        assert d.lookup("промышленность") == stressed

    def test_user_count(self, tmp_path: Path) -> None:
        store = StressStore(tmp_path / "stress.json")
        d = StressDictionary(store=store)
        assert d.user_count == 0
        d.add_user_entry("тест", "те" + COMBINING_ACUTE + "ст")
        assert d.user_count == 1

    def test_case_insensitive_lookup(self) -> None:
        d = StressDictionary()
        assert d.lookup("Молоко") is not None
        assert d.lookup("МОЛОКО") is not None
