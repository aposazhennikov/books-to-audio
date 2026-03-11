"""Base JSON-backed persistent store with repository-style API."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class JsonStore:
    """
    Generic JSON-backed persistent store.

    Stores a list of Pydantic model instances as a JSON array.
    Supports load, save, append, and lookup operations.
    Thread-safety is NOT guaranteed — designed for single-user CLI usage.
    """

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        """Return the file path of this store."""
        return self._path

    @property
    def exists(self) -> bool:
        """Check whether the backing file exists."""
        return self._path.is_file()

    def load_raw(self) -> list[dict[str, Any]]:
        """Load raw dicts from the JSON file."""
        if not self._path.is_file():
            return []
        try:
            text = self._path.read_text(encoding="utf-8")
            data = json.loads(text)
            if isinstance(data, list):
                return data
            return []
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read store at %s: %s", self._path, exc)
            return []

    def save_raw(self, items: list[dict[str, Any]]) -> None:
        """Write raw dicts to the JSON file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(items, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def load_models(self, model_class: type[T]) -> list[T]:
        """Load and parse all entries as Pydantic model instances."""
        raw = self.load_raw()
        results: list[T] = []
        for item in raw:
            try:
                results.append(model_class.model_validate(item))
            except Exception as exc:
                logger.warning("Skipping invalid entry in %s: %s", self._path, exc)
        return results

    def save_models(self, items: list[T]) -> None:
        """Serialize Pydantic model instances and save to file."""
        raw = [item.model_dump(mode="json") for item in items]
        self.save_raw(raw)

    def append_model(self, item: T) -> None:
        """Load existing entries, append one, and save back."""
        raw = self.load_raw()
        raw.append(item.model_dump(mode="json"))
        self.save_raw(raw)

    def clear(self) -> None:
        """Remove all entries from the store."""
        self.save_raw([])
