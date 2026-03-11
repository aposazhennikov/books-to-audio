"""Loader factory that selects the appropriate loader for a given file."""

from __future__ import annotations

import logging
from pathlib import Path

from book_normalizer.loaders.base import BaseLoader
from book_normalizer.models.book import Book

logger = logging.getLogger(__name__)


class LoaderFactory:
    """
    Registry-based factory for book loaders.

    Loaders are registered at init time or dynamically via `register`.
    The factory picks the first loader whose `can_load` returns True.
    """

    def __init__(self, loaders: list[BaseLoader] | None = None) -> None:
        self._loaders: list[BaseLoader] = loaders or []

    def register(self, loader: BaseLoader) -> None:
        """Register an additional loader."""
        self._loaders.append(loader)

    def get_loader(self, path: Path) -> BaseLoader:
        """
        Find a loader capable of handling the given file.

        Raises:
            ValueError: If no registered loader supports the file format.
        """
        for loader in self._loaders:
            if loader.can_load(path):
                return loader
        supported = set()
        for loader in self._loaders:
            supported.update(loader.supported_extensions)
        raise ValueError(
            f"No loader found for '{path.suffix}'. "
            f"Supported extensions: {sorted(supported)}"
        )

    def load(self, path: Path) -> Book:
        """Load a book using the appropriate loader."""
        resolved = Path(path).resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"File not found: {resolved}")
        loader = self.get_loader(resolved)
        logger.info("Loading '%s' with %s", resolved.name, type(loader).__name__)
        return loader.load(resolved)

    @classmethod
    def default(cls) -> LoaderFactory:
        """
        Create a factory with all built-in loaders registered.

        Imports are deferred so that missing optional deps
        do not break the entire module at import time.
        """
        from book_normalizer.loaders.docx_loader import DocxLoader
        from book_normalizer.loaders.epub_loader import EpubLoader
        from book_normalizer.loaders.fb2_loader import Fb2Loader
        from book_normalizer.loaders.pdf_loader import PdfLoader
        from book_normalizer.loaders.txt_loader import TxtLoader

        return cls(loaders=[
            TxtLoader(),
            PdfLoader(),
            EpubLoader(),
            Fb2Loader(),
            DocxLoader(),
        ])
