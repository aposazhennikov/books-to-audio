"""Hybrid chapter detector for splitting a Book into chapters."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from book_normalizer.chaptering.patterns import match_chapter_heading
from book_normalizer.models.book import Book, Chapter, Paragraph

logger = logging.getLogger(__name__)


@dataclass
class _HeadingHit:
    """Internal representation of a detected chapter heading."""

    paragraph_index: int
    heading_text: str
    pattern_label: str


class ChapterDetector:
    """
    Detect chapter boundaries and re-split a Book into chapters.

    Strategy:
    1. Scan all paragraphs of the first (synthetic) chapter for heading patterns.
    2. If headings found, split at those boundaries.
    3. If nothing found, keep the entire text as one chapter.

    The detector operates on the raw_text of paragraphs.
    """

    def __init__(self, min_chapter_paragraphs: int = 2) -> None:
        self._min_chapter_paragraphs = min_chapter_paragraphs

    def detect_and_split(self, book: Book) -> Book:
        """
        Re-split the book into chapters based on detected headings.

        Returns a new Book with updated chapters list.
        The original book object is not mutated.
        """
        all_paragraphs = self._collect_all_paragraphs(book)
        if not all_paragraphs:
            logger.warning("Book has no paragraphs; returning as-is.")
            return book

        hits = self._find_headings(all_paragraphs)

        if not hits:
            logger.info("No chapter headings detected; book will have a single chapter.")
            book.add_audit("chaptering", "no_headings", "Single chapter retained.")
            return book

        chapters = self._split_at_headings(all_paragraphs, hits)
        logger.info("Detected %d chapters.", len(chapters))

        new_book = book.model_copy(deep=True)
        new_book.chapters = chapters
        new_book.add_audit("chaptering", "split", f"chapters={len(chapters)}")
        return new_book

    @staticmethod
    def _collect_all_paragraphs(book: Book) -> list[Paragraph]:
        """Flatten all paragraphs from all chapters into one list."""
        result: list[Paragraph] = []
        for ch in book.chapters:
            result.extend(ch.paragraphs)
        return result

    @staticmethod
    def _find_headings(paragraphs: list[Paragraph]) -> list[_HeadingHit]:
        """Scan paragraphs for lines that match chapter heading patterns."""
        hits: list[_HeadingHit] = []
        for idx, para in enumerate(paragraphs):
            text = para.raw_text.strip()
            if not text:
                continue
            first_line = text.split("\n", maxsplit=1)[0]
            result = match_chapter_heading(first_line)
            if result:
                heading_text, label = result
                hits.append(_HeadingHit(paragraph_index=idx, heading_text=heading_text, pattern_label=label))
        return hits

    def _split_at_headings(
        self,
        paragraphs: list[Paragraph],
        hits: list[_HeadingHit],
    ) -> list[Chapter]:
        """Split paragraph list into chapters at heading boundaries."""
        chapters: list[Chapter] = []

        if hits[0].paragraph_index > 0:
            preamble_paras = paragraphs[: hits[0].paragraph_index]
            if preamble_paras:
                self._reindex_paragraphs(preamble_paras)
                chapters.append(
                    Chapter(
                        title="Preamble",
                        index=0,
                        paragraphs=preamble_paras,
                    )
                )

        for i, hit in enumerate(hits):
            start = hit.paragraph_index
            end = hits[i + 1].paragraph_index if i + 1 < len(hits) else len(paragraphs)
            chapter_paras = paragraphs[start + 1 : end]

            # Skip empty chapters (e.g., from table of contents).
            if not chapter_paras:
                continue

            self._reindex_paragraphs(chapter_paras)

            chapters.append(
                Chapter(
                    title=hit.heading_text,
                    index=len(chapters),
                    paragraphs=chapter_paras,
                )
            )

        # Filter out chapters with no meaningful content and reindex.
        chapters = [ch for ch in chapters if self._has_meaningful_content(ch)]
        for idx, ch in enumerate(chapters):
            ch.index = idx

        return chapters

    @staticmethod
    def _has_meaningful_content(chapter: Chapter) -> bool:
        """Check if chapter has meaningful content (not just separators/whitespace)."""
        if not chapter.paragraphs:
            return False

        # Count total text length excluding whitespace and common separators.
        total_chars = 0
        for para in chapter.paragraphs:
            text = para.raw_text.strip()
            # Skip paragraphs that are only separators.
            if text and text not in ("---", "***", "—", "–", "•"):
                total_chars += len(text)

        # Consider chapter meaningful if it has at least 20 chars of actual content.
        return total_chars >= 20

    @staticmethod
    def _reindex_paragraphs(paragraphs: list[Paragraph]) -> None:
        """Re-assign sequential index_in_chapter values."""
        for idx, para in enumerate(paragraphs):
            para.index_in_chapter = idx
