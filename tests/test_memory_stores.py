"""Tests for persistent memory stores."""

from __future__ import annotations

from pathlib import Path

from book_normalizer.memory.correction_store import CorrectionStore
from book_normalizer.memory.punctuation_store import PunctuationStore
from book_normalizer.memory.store import JsonStore
from book_normalizer.memory.stress_store import StressStore
from book_normalizer.models.memory import (
    CorrectionMemoryEntry,
    PunctuationMemoryEntry,
    StressMemoryEntry,
)


class TestJsonStore:
    def test_save_and_load_raw(self, tmp_path: Path) -> None:
        store = JsonStore(tmp_path / "test.json")
        data = [{"key": "value"}, {"key": "value2"}]
        store.save_raw(data)
        assert store.load_raw() == data

    def test_load_nonexistent(self, tmp_path: Path) -> None:
        store = JsonStore(tmp_path / "missing.json")
        assert store.load_raw() == []

    def test_exists_property(self, tmp_path: Path) -> None:
        store = JsonStore(tmp_path / "test.json")
        assert not store.exists
        store.save_raw([])
        assert store.exists

    def test_save_and_load_models(self, tmp_path: Path) -> None:
        store = JsonStore(tmp_path / "test.json")
        entries = [
            CorrectionMemoryEntry(original="abc", replacement="def"),
            CorrectionMemoryEntry(original="ghi", replacement="jkl"),
        ]
        store.save_models(entries)
        loaded = store.load_models(CorrectionMemoryEntry)
        assert len(loaded) == 2
        assert loaded[0].original == "abc"
        assert loaded[1].replacement == "jkl"

    def test_append_model(self, tmp_path: Path) -> None:
        store = JsonStore(tmp_path / "test.json")
        e1 = CorrectionMemoryEntry(original="a", replacement="b")
        e2 = CorrectionMemoryEntry(original="c", replacement="d")
        store.append_model(e1)
        store.append_model(e2)
        loaded = store.load_models(CorrectionMemoryEntry)
        assert len(loaded) == 2

    def test_clear(self, tmp_path: Path) -> None:
        store = JsonStore(tmp_path / "test.json")
        store.save_raw([{"x": 1}])
        store.clear()
        assert store.load_raw() == []

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        store = JsonStore(tmp_path / "nested" / "deep" / "test.json")
        store.save_raw([{"ok": True}])
        assert store.exists


class TestCorrectionStore:
    def test_add_and_lookup(self, tmp_path: Path) -> None:
        store = CorrectionStore(tmp_path / "corrections.json")
        entry = CorrectionMemoryEntry(original="тесь", replacement="тест", confirmed=True)
        store.add(entry)
        assert store.has("тесь")
        assert store.lookup("тесь").replacement == "тест"

    def test_lookup_missing(self, tmp_path: Path) -> None:
        store = CorrectionStore(tmp_path / "corrections.json")
        assert store.lookup("missing") is None

    def test_count(self, tmp_path: Path) -> None:
        store = CorrectionStore(tmp_path / "corrections.json")
        store.add(CorrectionMemoryEntry(original="a", replacement="b"))
        store.add(CorrectionMemoryEntry(original="c", replacement="d"))
        assert store.count() == 2

    def test_persistence(self, tmp_path: Path) -> None:
        path = tmp_path / "corrections.json"
        store1 = CorrectionStore(path)
        store1.add(CorrectionMemoryEntry(original="x", replacement="y", confirmed=True))

        store2 = CorrectionStore(path)
        assert store2.has("x")
        assert store2.lookup("x").confirmed is True

    def test_remove(self, tmp_path: Path) -> None:
        store = CorrectionStore(tmp_path / "corrections.json")
        store.add(CorrectionMemoryEntry(original="a", replacement="b"))
        assert store.remove("a") is True
        assert not store.has("a")
        assert store.remove("missing") is False

    def test_all_entries(self, tmp_path: Path) -> None:
        store = CorrectionStore(tmp_path / "corrections.json")
        store.add(CorrectionMemoryEntry(original="a", replacement="b"))
        store.add(CorrectionMemoryEntry(original="c", replacement="d"))
        entries = store.all_entries()
        assert len(entries) == 2


class TestPunctuationStore:
    def test_add_and_lookup(self, tmp_path: Path) -> None:
        store = PunctuationStore(tmp_path / "punct.json")
        entry = PunctuationMemoryEntry(original="тест,тест", replacement="тест, тест", confirmed=True)
        store.add(entry)
        assert store.has("тест,тест")
        assert store.lookup("тест,тест").replacement == "тест, тест"

    def test_count(self, tmp_path: Path) -> None:
        store = PunctuationStore(tmp_path / "punct.json")
        store.add(PunctuationMemoryEntry(original="a", replacement="b"))
        assert store.count() == 1


class TestStressStore:
    def test_add_and_lookup(self, tmp_path: Path) -> None:
        store = StressStore(tmp_path / "stress.json")
        entry = StressMemoryEntry(word="замок", normalized_word="замок", stressed_form="за\u0301мок")
        store.add(entry)
        assert store.has("замок")
        assert store.has("ЗАМОК")
        assert store.lookup("замок").stressed_form == "за\u0301мок"

    def test_lookup_case_insensitive(self, tmp_path: Path) -> None:
        store = StressStore(tmp_path / "stress.json")
        store.add(StressMemoryEntry(word="Молоко", normalized_word="молоко", stressed_form="молоко\u0301"))
        assert store.has("молоко")
        assert store.has("Молоко")

    def test_persistence(self, tmp_path: Path) -> None:
        path = tmp_path / "stress.json"
        store1 = StressStore(path)
        store1.add(StressMemoryEntry(word="слово", normalized_word="слово", stressed_form="сло\u0301во"))

        store2 = StressStore(path)
        assert store2.has("слово")
