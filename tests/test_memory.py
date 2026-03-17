"""Tests for memory model structures."""

from __future__ import annotations

from book_normalizer.models.memory import (
    CorrectionMemoryEntry,
    PunctuationMemoryEntry,
    StressMemoryEntry,
)


class TestStressMemoryEntry:
    def test_creation(self) -> None:
        entry = StressMemoryEntry(word="замок", stressed_form="за́мок")
        assert entry.word == "замок"
        assert entry.stressed_form == "за́мок"
        assert not entry.confirmed

    def test_serialization(self) -> None:
        entry = StressMemoryEntry(word="молоко", stressed_form="молоко́", confirmed=True)
        data = entry.model_dump()
        assert data["word"] == "молоко"
        assert data["confirmed"] is True


class TestCorrectionMemoryEntry:
    def test_creation(self) -> None:
        entry = CorrectionMemoryEntry(
            original="тесь",
            replacement="тест",
            issue_type="spelling",
            token="тесь",
            normalized_token="тесь",
            auto_apply_safe=True,
        )
        assert entry.original == "тесь"
        assert entry.replacement == "тест"


class TestPunctuationMemoryEntry:
    def test_creation(self) -> None:
        entry = PunctuationMemoryEntry(original="тест,тест", replacement="тест, тест")
        assert entry.replacement == "тест, тест"
