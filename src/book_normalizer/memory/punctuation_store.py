"""Persistent store for punctuation correction decisions."""

from __future__ import annotations

import logging
from pathlib import Path

from book_normalizer.memory.store import JsonStore
from book_normalizer.models.memory import PunctuationMemoryEntry

logger = logging.getLogger(__name__)


class PunctuationStore:
    """
    Repository for punctuation correction decisions.

    Lookups are done by exact original fragment match.
    """

    def __init__(self, path: Path) -> None:
        self._store = JsonStore(path)
        self._cache: dict[str, PunctuationMemoryEntry] | None = None

    def _ensure_loaded(self) -> dict[str, PunctuationMemoryEntry]:
        """Lazy-load entries into an in-memory lookup cache."""
        if self._cache is None:
            entries = self._store.load_models(PunctuationMemoryEntry)
            self._cache = {e.original: e for e in entries}
        return self._cache

    def lookup(self, original: str) -> PunctuationMemoryEntry | None:
        """Find a stored punctuation decision for the given original fragment."""
        cache = self._ensure_loaded()
        return cache.get(original)

    def has(self, original: str) -> bool:
        """Check if a decision exists for the given original."""
        return self.lookup(original) is not None

    def add(self, entry: PunctuationMemoryEntry) -> None:
        """Add or update a punctuation entry."""
        cache = self._ensure_loaded()
        cache[entry.original] = entry
        self._save()

    def all_entries(self) -> list[PunctuationMemoryEntry]:
        """Return all stored punctuation entries."""
        return list(self._ensure_loaded().values())

    def count(self) -> int:
        """Return the number of stored punctuation decisions."""
        return len(self._ensure_loaded())

    def _save(self) -> None:
        """Persist current state to disk."""
        if self._cache is not None:
            self._store.save_models(list(self._cache.values()))
