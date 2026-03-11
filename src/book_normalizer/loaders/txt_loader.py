"""Loader for plain-text (.txt) book files."""

from __future__ import annotations

import logging
from pathlib import Path

from book_normalizer.loaders.base import BaseLoader
from book_normalizer.models.book import Book, Metadata, Paragraph, Chapter
from book_normalizer.normalization.cleanup import remove_repeated_headers

logger = logging.getLogger(__name__)

_ENCODINGS_TO_TRY = ("utf-8", "cp1251", "cp866", "koi8-r", "latin-1")


class TxtLoader(BaseLoader):
    """
    Plain-text loader with automatic encoding detection.

    Tries common Russian encodings in order and picks the first
    that decodes without errors.
    """

    @property
    def supported_extensions(self) -> set[str]:
        return {".txt"}

    def load(self, path: Path) -> Book:
        """Load a plain-text file and return a Book with a single synthetic chapter."""
        resolved = path.resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"File not found: {resolved}")

        text = self._read_with_encoding_fallback(resolved)
        logger.info("Loaded %d characters from '%s'", len(text), resolved.name)

        # Remove repeated headers/footers before splitting into paragraphs.
        text = remove_repeated_headers(text, min_occurrences=3)

        paragraphs = self._split_paragraphs(text)

        chapter = Chapter(
            title="Full Text",
            index=0,
            paragraphs=paragraphs,
            source_span_start=0,
            source_span_end=len(text),
        )

        metadata = Metadata(
            source_path=str(resolved),
            source_format="txt",
        )

        book = Book(metadata=metadata, chapters=[chapter])
        book.add_audit("loading", "txt_loader", f"chars={len(text)}, paragraphs={len(paragraphs)}")
        return book

    @staticmethod
    def _read_with_encoding_fallback(path: Path) -> str:
        """Try multiple encodings and return decoded text."""
        for enc in _ENCODINGS_TO_TRY:
            try:
                return path.read_text(encoding=enc)
            except (UnicodeDecodeError, UnicodeError):
                continue
        raise ValueError(f"Unable to decode '{path}' with any of: {_ENCODINGS_TO_TRY}")

    @staticmethod
    def _split_paragraphs(text: str) -> list[Paragraph]:
        """
        Split text into paragraphs by double-newline boundaries.

        Single newlines within a paragraph are preserved as-is at this stage;
        normalization will handle line-wrap repair later.
        """
        raw_blocks = text.split("\n\n")
        paragraphs: list[Paragraph] = []
        for idx, block in enumerate(raw_blocks):
            stripped = block.strip()
            if not stripped:
                continue
            paragraphs.append(
                Paragraph(
                    raw_text=stripped,
                    normalized_text="",
                    index_in_chapter=idx,
                )
            )
        return paragraphs
