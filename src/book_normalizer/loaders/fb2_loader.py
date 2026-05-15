"""Loader for FB2 (.fb2) book files using lxml XML parsing."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from book_normalizer.loaders.base import BaseLoader
from book_normalizer.models.book import Book, Chapter, Metadata, Paragraph

logger = logging.getLogger(__name__)

FB2_NS = "http://www.gribuser.ru/xml/fictionbook/2.0"
_NS = {"fb": FB2_NS}


class Fb2Loader(BaseLoader):
    """
    FB2 loader using lxml for XML parsing.

    FB2 is a well-structured XML format popular in Russian-language
    e-book distribution. The loader extracts metadata from
    <description> and text from <body>/<section> elements.
    """

    @property
    def supported_extensions(self) -> set[str]:
        return {".fb2"}

    def load(self, path: Path) -> Book:
        """Load an FB2 file and return a Book."""
        resolved = path.resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"File not found: {resolved}")

        try:
            from lxml import etree
        except ImportError as exc:
            raise ImportError(
                "lxml is required for FB2 loading. Install it: pip install lxml"
            ) from exc

        raw_bytes = resolved.read_bytes()
        tree = etree.fromstring(raw_bytes)

        metadata = self._extract_metadata(tree, resolved)
        chapters = self._extract_chapters(tree)

        if not chapters:
            full_text = self._extract_all_text(tree)
            paragraphs = self._split_paragraphs(full_text)
            chapters = [Chapter(title="Full Text", index=0, paragraphs=paragraphs)]

        book = Book(metadata=metadata, chapters=chapters)
        total_paras = sum(len(ch.paragraphs) for ch in chapters)
        book.add_audit(
            "loading", "fb2_loader",
            f"chapters={len(chapters)}, paragraphs={total_paras}",
        )
        return book

    @staticmethod
    def _extract_metadata(tree: object, path: Path) -> Metadata:
        """Extract metadata from FB2 <description>/<title-info>."""
        from lxml import etree

        def _find_text(parent: etree._Element, xpath: str) -> str:
            el = parent.find(xpath, namespaces=_NS)
            if el is not None and el.text:
                return el.text.strip()
            return ""

        title_info = tree.find(".//fb:description/fb:title-info", namespaces=_NS)

        title = ""
        author = ""
        language = "ru"
        year = ""

        if title_info is not None:
            book_title = title_info.find("fb:book-title", namespaces=_NS)
            if book_title is not None and book_title.text:
                title = book_title.text.strip()

            author_el = title_info.find("fb:author", namespaces=_NS)
            if author_el is not None:
                first = _find_text(author_el, "fb:first-name")
                last = _find_text(author_el, "fb:last-name")
                author = f"{first} {last}".strip()

            lang_el = title_info.find("fb:lang", namespaces=_NS)
            if lang_el is not None and lang_el.text:
                language = lang_el.text.strip()

            date_el = title_info.find("fb:date", namespaces=_NS)
            if date_el is not None:
                year = date_el.get("value", "") or (date_el.text or "").strip()

        return Metadata(
            title=title or "Untitled",
            author=author or "Unknown",
            language=language,
            year=year,
            source_path=str(path),
            source_format="fb2",
        )

    @classmethod
    def _extract_chapters(cls, tree: object) -> list[Chapter]:
        """Extract chapters from FB2 <body>/<section> elements."""

        body = tree.find(".//fb:body", namespaces=_NS)
        if body is None:
            return []

        sections = body.findall("fb:section", namespaces=_NS)
        if not sections:
            return []

        chapters: list[Chapter] = []
        for idx, section in enumerate(sections):
            title = cls._extract_section_title(section)
            paragraphs = cls._extract_section_paragraphs(section)
            paragraphs = cls._trim_leading_front_matter(paragraphs)

            if not paragraphs:
                continue

            chapters.append(
                Chapter(
                    title=title or f"Section {idx + 1}",
                    index=idx,
                    paragraphs=paragraphs,
                )
            )

        return chapters

    @staticmethod
    def _extract_section_title(section: object) -> str:
        """Extract title text from a <section>/<title> element."""

        title_el = section.find("fb:title", namespaces=_NS)
        if title_el is None:
            return ""

        parts: list[str] = []
        for p_el in title_el.findall("fb:p", namespaces=_NS):
            text = "".join(p_el.itertext()).strip()
            if text:
                parts.append(text)

        if not parts:
            text = "".join(title_el.itertext()).strip()
            return text

        return " ".join(parts)

    @classmethod
    def _extract_section_paragraphs(cls, section: object) -> list[Paragraph]:
        """Extract paragraphs from <p> elements within a section."""
        from lxml import etree

        paragraphs: list[Paragraph] = []
        idx = 0

        for elem in section:
            tag = etree.QName(elem.tag).localname if isinstance(elem.tag, str) else ""

            if tag == "p":
                text = "".join(elem.itertext()).strip()
                if text:
                    if cls._is_chapter_description_paragraph(paragraphs, elem, text):
                        continue
                    paragraphs.append(
                        Paragraph(raw_text=text, normalized_text="", index_in_chapter=idx)
                    )
                    idx += 1

            elif tag == "subtitle":
                text = "".join(elem.itertext()).strip()
                if text:
                    paragraphs.append(
                        Paragraph(raw_text=text, normalized_text="", index_in_chapter=idx)
                    )
                    idx += 1

            elif tag == "cite":
                cite_parts: list[str] = []
                for cite_elem in elem:
                    cite_tag = etree.QName(cite_elem.tag).localname if isinstance(cite_elem.tag, str) else ""
                    if cite_tag == "p":
                        cite_text = "".join(cite_elem.itertext()).strip()
                        if cite_text:
                            cite_parts.append(cite_text)
                    elif cite_tag == "text-author":
                        author_text = "".join(cite_elem.itertext()).strip()
                        if author_text:
                            cite_parts.append(author_text)

                if cite_parts:
                    combined_cite = "\n".join(cite_parts)
                    paragraphs.append(
                        Paragraph(raw_text=combined_cite, normalized_text="", index_in_chapter=idx)
                    )
                    idx += 1

            elif tag == "empty-line":
                continue

            elif tag == "section":
                sub_paras = cls._extract_section_paragraphs(elem)
                sub_title = cls._extract_section_title(elem)
                if sub_title:
                    paragraphs.append(
                        Paragraph(raw_text=sub_title, normalized_text="", index_in_chapter=idx)
                    )
                    idx += 1
                for p in sub_paras:
                    p.index_in_chapter = idx
                    paragraphs.append(p)
                    idx += 1

        return paragraphs

    @classmethod
    def _is_chapter_description_paragraph(
        cls,
        paragraphs: list[Paragraph],
        elem: object,
        text: str,
    ) -> bool:
        """Return true for FB2 bold one-line subtitles right after chapter headings."""
        if not paragraphs:
            return False
        if not cls._chapter_heading_key(paragraphs[-1].raw_text):
            return False
        if cls._chapter_heading_key(text):
            return False
        if not cls._is_strong_only_paragraph(elem):
            return False

        words = text.split()
        return 1 < len(words) <= 18 and len(text) <= 180

    @staticmethod
    def _is_strong_only_paragraph(elem: object) -> bool:
        """Return true when an FB2 paragraph only wraps text in <strong>."""
        from lxml import etree

        child_tags: list[str] = []
        for child in elem:
            if not isinstance(child.tag, str):
                continue
            child_tags.append(etree.QName(child.tag).localname)

        return bool(child_tags) and set(child_tags) == {"strong"}

    @classmethod
    def _trim_leading_front_matter(cls, paragraphs: list[Paragraph]) -> list[Paragraph]:
        """
        Drop generated FB2 front matter before the real first chapter.

        Some Calibre/Litmir FB2 files put annotation, a plain chapter list, and
        title-page lines into the first body section before repeating the same
        chapter headings again for the actual book text.  Keep the repeated
        heading onward so chapter detection sees the real book body.
        """
        if len(paragraphs) < 6:
            return paragraphs

        heading_indices: dict[str, list[int]] = {}
        for idx, para in enumerate(paragraphs):
            key = cls._chapter_heading_key(para.raw_text)
            if key:
                heading_indices.setdefault(key, []).append(idx)

        duplicate_starts = [
            indices[1]
            for indices in heading_indices.values()
            if len(indices) >= 2
        ]
        if not duplicate_starts:
            return paragraphs

        trim_at = min(duplicate_starts)
        if trim_at <= 0:
            return paragraphs

        leading = paragraphs[:trim_at]
        leading_heading_count = sum(
            1 for para in leading if cls._chapter_heading_key(para.raw_text)
        )
        has_front_marker = any(
            cls._looks_like_front_matter_marker(para.raw_text)
            for para in leading[:10]
        )
        if leading_heading_count < 3 and not has_front_marker:
            return paragraphs

        trimmed = paragraphs[trim_at:]
        for idx, para in enumerate(trimmed):
            para.index_in_chapter = idx
        return trimmed

    @staticmethod
    def _chapter_heading_key(text: str) -> str:
        """Return a normalized heading key for duplicate chapter-list detection."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(lines) != 1:
            return ""

        from book_normalizer.chaptering.patterns import match_chapter_heading

        line = lines[0]
        match = match_chapter_heading(line)
        if not match:
            return ""

        heading, _label = match
        return re.sub(r"\s+", " ", heading.casefold()).strip(" .,:;!?")

    @staticmethod
    def _looks_like_front_matter_marker(text: str) -> bool:
        """Return true for short labels commonly found in generated FB2 prefaces."""
        normalized = re.sub(r"\s+", " ", text.casefold()).strip(" .,:;!?")
        return normalized in {
            "annotation",
            "table of contents",
            "аннотация",
            "содержание",
            "оглавление",
        }

    @staticmethod
    def _extract_all_text(tree: object) -> str:
        """Fallback: extract all text from the entire FB2 body."""

        body = tree.find(".//fb:body", namespaces=_NS)
        if body is None:
            return ""

        parts: list[str] = []
        for p_el in body.iter(f"{{{FB2_NS}}}p"):
            text = "".join(p_el.itertext()).strip()
            if text:
                parts.append(text)
        return "\n\n".join(parts)

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
                Paragraph(raw_text=stripped, normalized_text="", index_in_chapter=idx)
            )
        return paragraphs
