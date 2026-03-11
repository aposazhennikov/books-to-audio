"""Persistent store for spelling/OCR correction decisions."""

from __future__ import annotations

import logging
from pathlib import Path

from book_normalizer.memory.store import JsonStore
from book_normalizer.models.memory import CorrectionMemoryEntry

logger = logging.getLogger(__name__)


class CorrectionStore:
    """
    Repository for spelling/OCR correction decisions.

    Lookups are done by exact original fragment match.
    This allows auto-applying previously confirmed corrections
    when the same fragment appears in future books.
    """

    def __init__(self, path: Path) -> None:
        self._store = JsonStore(path)
        self._cache: dict[str, CorrectionMemoryEntry] | None = None

    def _ensure_loaded(self) -> dict[str, CorrectionMemoryEntry]:
        """Lazy-load entries into an in-memory lookup cache."""
        if self._cache is None:
            entries = self._store.load_models(CorrectionMemoryEntry)
            self._cache = {e.original: e for e in entries}
        return self._cache

    def lookup(self, original: str) -> CorrectionMemoryEntry | None:
        """Find a stored correction for the given original fragment."""
        cache = self._ensure_loaded()
        return cache.get(original)

    def has(self, original: str) -> bool:
        """Check if a correction exists for the given original."""
        return self.lookup(original) is not None

    def add(self, entry: CorrectionMemoryEntry) -> None:
        """Add or update a correction entry."""
        cache = self._ensure_loaded()
        cache[entry.original] = entry
        self._save()

    def remove(self, original: str) -> bool:
        """Remove a correction entry. Returns True if found."""
        cache = self._ensure_loaded()
        if original in cache:
            del cache[original]
            self._save()
            return True
        return False

    def all_entries(self) -> list[CorrectionMemoryEntry]:
        """Return all stored correction entries."""
        return list(self._ensure_loaded().values())

    def count(self) -> int:
        """Return the number of stored corrections."""
        return len(self._ensure_loaded())

    def _save(self) -> None:
        """Persist current state to disk."""
        if self._cache is not None:
            self._store.save_models(list(self._cache.values()))
