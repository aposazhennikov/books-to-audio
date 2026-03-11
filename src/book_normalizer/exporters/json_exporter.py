"""JSON structure exporter for machine-readable book representation."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from book_normalizer.models.book import Book

logger = logging.getLogger(__name__)


class JsonExporter:
    """
    Export a Book as a structured JSON file.

    Produces book_structure.json with metadata, chapter list,
    and paragraph data for programmatic consumption.
    """

    def export(self, book: Book, output_dir: Path) -> Path:
        """Write the JSON structure file and return its path."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        structure = self._build_structure(book)
        json_path = output_dir / "book_structure.json"
        json_path.write_text(
            json.dumps(structure, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        logger.info("Wrote JSON structure to %s", json_path)
        book.add_audit("export", "json_export", f"path={json_path}")
        return json_path

    @staticmethod
    def _build_structure(book: Book) -> dict[str, Any]:
        """Build a serializable dictionary representing the book structure."""
        return {
            "id": book.id,
            "metadata": book.metadata.model_dump(),
            "created_at": book.created_at.isoformat(),
            "chapters": [
                {
                    "id": ch.id,
                    "title": ch.title,
                    "index": ch.index,
                    "paragraph_count": len(ch.paragraphs),
                    "char_count": len(ch.normalized_text or ch.raw_text),
                    "paragraphs": [
                        {
                            "id": p.id,
                            "index_in_chapter": p.index_in_chapter,
                            "raw_text_preview": p.raw_text[:120] + "…" if len(p.raw_text) > 120 else p.raw_text,
                            "normalized": bool(p.normalized_text),
                        }
                        for p in ch.paragraphs
                    ],
                }
                for ch in book.chapters
            ],
            "total_chapters": len(book.chapters),
            "total_paragraphs": sum(len(ch.paragraphs) for ch in book.chapters),
            "audit_trail": book.audit_trail,
        }
