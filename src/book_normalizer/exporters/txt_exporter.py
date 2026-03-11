"""Plain-text exporter for full book and per-chapter files."""

from __future__ import annotations

import logging
from pathlib import Path

from book_normalizer.models.book import Book

logger = logging.getLogger(__name__)


class TxtExporter:
    """
    Export a Book as plain UTF-8 text files.

    Produces:
    - 000_full_book.txt with concatenated normalized text.
    - NNN_chapter_NN.txt for each chapter.
    """

    def export(self, book: Book, output_dir: Path) -> list[Path]:
        """
        Write text files to output_dir and return the list of created paths.

        Creates the directory if it does not exist.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        created: list[Path] = []

        full_path = output_dir / "000_full_book.txt"
        full_text = self._build_full_text(book)
        full_path.write_text(full_text, encoding="utf-8")
        created.append(full_path)
        logger.info("Wrote full book text to %s (%d chars)", full_path, len(full_text))

        for chapter in book.chapters:
            chapter_num = chapter.index + 1
            filename = f"{chapter_num:03d}_chapter_{chapter_num:02d}.txt"
            chapter_path = output_dir / filename
            chapter_text = chapter.normalized_text or chapter.raw_text
            chapter_path.write_text(chapter_text, encoding="utf-8")
            created.append(chapter_path)
            logger.debug("Wrote chapter '%s' to %s", chapter.title, chapter_path)

        book.add_audit("export", "txt_export", f"files={len(created)}")
        return created

    @staticmethod
    def _build_full_text(book: Book) -> str:
        """Build the full normalized text with chapter separators."""
        parts: list[str] = []
        for chapter in book.chapters:
            if chapter.title:
                parts.append(f"{'=' * 60}")
                parts.append(chapter.title)
                parts.append(f"{'=' * 60}")
                parts.append("")
            text = chapter.normalized_text or chapter.raw_text
            parts.append(text)
            parts.append("")
        return "\n".join(parts)
