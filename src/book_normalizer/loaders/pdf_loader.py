"""Loader for PDF (.pdf) book files using PyMuPDF."""

from __future__ import annotations

import logging
from pathlib import Path

from book_normalizer.loaders.base import BaseLoader
from book_normalizer.models.book import Book, Chapter, Metadata, Paragraph
from book_normalizer.normalization.cleanup import remove_repeated_headers

logger = logging.getLogger(__name__)


class PdfLoader(BaseLoader):
    """
    PDF loader built on top of PyMuPDF (fitz).

    Extracts text page by page, concatenates, and builds
    a Book with a single synthetic chapter.
    """

    @property
    def supported_extensions(self) -> set[str]:
        return {".pdf"}

    def load(self, path: Path) -> Book:
        """Load a PDF file and return a Book."""
        resolved = path.resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"File not found: {resolved}")

        try:
            import fitz  # PyMuPDF.
        except ImportError as exc:
            raise ImportError(
                "PyMuPDF is required for PDF loading. Install it: pip install PyMuPDF"
            ) from exc

        text = self._extract_text(resolved)
        logger.info("Extracted %d characters from '%s'", len(text), resolved.name)

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
            source_format="pdf",
        )

        book = Book(metadata=metadata, chapters=[chapter])
        book.add_audit("loading", "pdf_loader", f"chars={len(text)}, paragraphs={len(paragraphs)}")
        return book

    @staticmethod
    def _extract_text(path: Path) -> str:
        """Extract full text from all pages of a PDF."""
        import fitz  # PyMuPDF.

        pages: list[str] = []
        with fitz.open(str(path)) as doc:
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text("text")
                if page_text:
                    pages.append(page_text)

        return "\n\n".join(pages)

    @staticmethod
    def _split_paragraphs(text: str) -> list[Paragraph]:
        """Split extracted text into paragraphs by double-newline boundaries."""
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
