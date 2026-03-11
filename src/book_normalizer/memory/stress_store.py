"""Persistent store for stress/accent decisions."""

from __future__ import annotations

import logging
from pathlib import Path

from book_normalizer.memory.store import JsonStore
from book_normalizer.models.memory import StressMemoryEntry

logger = logging.getLogger(__name__)


class StressStore:
    """
    Repository for stress dictionary entries.

    Lookups are done by normalized_word (lowercase) first,
    falling back to exact word match. This store will be
    fully utilized in Phase 4.
    """

    def __init__(self, path: Path) -> None:
        self._store = JsonStore(path)
        self._cache: dict[str, StressMemoryEntry] | None = None

    def _ensure_loaded(self) -> dict[str, StressMemoryEntry]:
        """Lazy-load entries keyed by normalized_word."""
        if self._cache is None:
            entries = self._store.load_models(StressMemoryEntry)
            self._cache = {}
            for e in entries:
                key = e.normalized_word or e.word.lower()
                self._cache[key] = e
        return self._cache

    def lookup(self, word: str) -> StressMemoryEntry | None:
        """Find a stored stress entry for the given word."""
        cache = self._ensure_loaded()
        normalized = word.lower().strip()
        return cache.get(normalized)

    def has(self, word: str) -> bool:
        """Check if a stress entry exists for the given word."""
        return self.lookup(word) is not None

    def add(self, entry: StressMemoryEntry) -> None:
        """Add or update a stress entry."""
        cache = self._ensure_loaded()
        key = entry.normalized_word or entry.word.lower()
        cache[key] = entry
        self._save()

    def all_entries(self) -> list[StressMemoryEntry]:
        """Return all stored stress entries."""
        return list(self._ensure_loaded().values())

    def count(self) -> int:
        """Return the number of stored stress entries."""
        return len(self._ensure_loaded())

    def _save(self) -> None:
        """Persist current state to disk."""
        if self._cache is not None:
            self._store.save_models(list(self._cache.values()))
