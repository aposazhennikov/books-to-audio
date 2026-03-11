"""Abstract base class for all book format loaders."""

from __future__ import annotations

import abc
from pathlib import Path

from book_normalizer.models.book import Book


class BaseLoader(abc.ABC):
    """
    Abstract loader interface.

    Every concrete loader must implement `supported_extensions` and `load`.
    The factory uses `can_load` to pick the right loader for a given file.
    """

    @property
    @abc.abstractmethod
    def supported_extensions(self) -> set[str]:
        """Return the set of file extensions this loader handles (e.g. {'.txt'})."""

    def can_load(self, path: Path) -> bool:
        """Check whether this loader can handle the given file path."""
        return path.suffix.lower() in self.supported_extensions

    @abc.abstractmethod
    def load(self, path: Path) -> Book:
        """
        Load a book from the given file path.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file content cannot be parsed.
        """
