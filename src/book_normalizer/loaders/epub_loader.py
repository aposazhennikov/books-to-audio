"""Loader for EPUB (.epub) book files using ebooklib."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from book_normalizer.loaders.base import BaseLoader
from book_normalizer.models.book import Book, Chapter, Metadata, Paragraph

logger = logging.getLogger(__name__)


class EpubLoader(BaseLoader):
    """
    EPUB loader built on top of ebooklib.

    Extracts text from HTML content items, strips tags,
    and builds a Book with chapters derived from spine order.
    """

    @property
    def supported_extensions(self) -> set[str]:
        return {".epub"}

    def load(self, path: Path) -> Book:
        """Load an EPUB file and return a Book."""
        resolved = path.resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"File not found: {resolved}")

        try:
            from ebooklib import epub
        except ImportError as exc:
            raise ImportError(
                "ebooklib is required for EPUB loading. Install it: pip install ebooklib"
            ) from exc

        epub_book = epub.read_epub(str(resolved), options={"ignore_ncx": True})

        metadata = self._extract_metadata(epub_book, resolved)
        chapters = self._extract_chapters(epub_book)

        total_paras = sum(len(ch.paragraphs) for ch in chapters)
        if total_paras == 0:
            # Fail loudly instead of silently exporting an empty book.
            raise ValueError(f"EPUB extraction produced no paragraphs for '{resolved}'.")

        book = Book(metadata=metadata, chapters=chapters)
        book.add_audit(
            "loading",
            "epub_loader",
            f"chapters={len(chapters)}, paragraphs={total_paras}",
        )
        return book

    @staticmethod
    def _extract_metadata(epub_book: object, path: Path) -> Metadata:
        """Extract metadata from EPUB Dublin Core fields."""
        from ebooklib import epub

        def _get_dc(book: epub.EpubBook, field: str) -> str:
            values = book.get_metadata("DC", field)
            if values:
                val = values[0]
                if isinstance(val, tuple):
                    return str(val[0])
                return str(val)
            return ""

        return Metadata(
            title=_get_dc(epub_book, "title") or "Untitled",
            author=_get_dc(epub_book, "creator") or "Unknown",
            language=_get_dc(epub_book, "language") or "ru",
            publisher=_get_dc(epub_book, "publisher"),
            year=_get_dc(epub_book, "date"),
            source_path=str(path),
            source_format="epub",
        )

    @classmethod
    def _extract_chapters(cls, epub_book: object) -> list[Chapter]:
        """Extract chapters from EPUB document items in a robust, spine-aware order."""
        from ebooklib import epub

        chapters: list[Chapter] = []

        # Collect all document items first. Some ebooklib versions expose ITEM_DOCUMENT,
        # others require using the numeric type code (9).
        item_document_type = getattr(epub, "ITEM_DOCUMENT", 9)
        doc_items = list(epub_book.get_items_of_type(item_document_type))

        # Also include items whose type is 0 (regular HTML chapters in some EPUBs),
        # while avoiding duplicates by id.
        seen_ids: set[str] = {getattr(it, "get_id", lambda: "")() for it in doc_items}
        for item in epub_book.get_items():
            item_type = getattr(item, "get_type", lambda: None)()
            item_id = getattr(item, "get_id", lambda: "")()
            if item_type == 0 and item_id and item_id not in seen_ids:
                doc_items.append(item)
                seen_ids.add(item_id)

        id_to_item = {item.get_id(): item for item in doc_items}

        # Build reading order from spine when available, then append remaining docs.
        ordered_ids: list[str] = []
        spine = getattr(epub_book, "spine", []) or []
        for entry in spine:
            item_id = entry[0] if isinstance(entry, tuple) else entry
            if item_id in id_to_item and item_id not in ordered_ids:
                ordered_ids.append(item_id)

        for item in doc_items:
            item_id = item.get_id()
            if item_id not in ordered_ids:
                ordered_ids.append(item_id)

        for item_id in ordered_ids:
            item = id_to_item.get(item_id)
            if not item:
                continue

            content = item.get_content()
            if not content:
                continue

            try:
                html_text = content.decode("utf-8", errors="replace")
            except Exception:
                continue

            title = cls._extract_title_from_html(html_text)
            plain_text = cls._html_to_text(html_text)
            if not plain_text.strip():
                continue

            paragraphs = cls._split_paragraphs(plain_text)
            if not paragraphs:
                # Fallback: treat whole block as a single paragraph if non-empty.
                paragraphs = [
                    Paragraph(raw_text=plain_text.strip(), normalized_text="", index_in_chapter=0)
                ]

            chapter_title = title or f"Section {len(chapters) + 1}"

            # If the first paragraph duplicates the title text, drop it.
            if title and paragraphs and paragraphs[0].raw_text.strip() == title.strip():
                paragraphs = [
                    Paragraph(
                        raw_text=p.raw_text,
                        normalized_text=p.normalized_text,
                        index_in_chapter=idx,
                    )
                    for idx, p in enumerate(paragraphs[1:])
                ]

            chapters.append(
                Chapter(
                    title=chapter_title,
                    index=len(chapters),
                    paragraphs=paragraphs,
                )
            )

        return chapters

    @staticmethod
    def _extract_title_from_html(html: str) -> str:
        """Try to extract a heading from HTML content."""
        for tag in ("h1", "h2", "h3"):
            match = re.search(
                rf"<{tag}[^>]*>(.*?)</{tag}>",
                html,
                re.IGNORECASE | re.DOTALL,
            )
            if match:
                text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
                if text:
                    return text
        return ""

    @staticmethod
    def _html_to_text(html: str) -> str:
        """Convert HTML to plain text preserving paragraph boundaries."""
        text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
        text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</div>", "\n\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</h[1-6]>", "\n\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"&nbsp;", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"&amp;", "&", text, flags=re.IGNORECASE)
        text = re.sub(r"&lt;", "<", text, flags=re.IGNORECASE)
        text = re.sub(r"&gt;", ">", text, flags=re.IGNORECASE)
        text = re.sub(r"&quot;", '"', text, flags=re.IGNORECASE)
        text = re.sub(r"&#\d+;", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _split_paragraphs(text: str) -> list[Paragraph]:
        """Split text into paragraphs by double-newline boundaries."""
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
