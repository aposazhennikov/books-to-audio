"""Hybrid chapter detector for splitting a Book into chapters."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from book_normalizer.chaptering.patterns import match_chapter_heading
from book_normalizer.chaptering.toc_parser import extract_main_titles, find_toc_section, parse_toc_entries
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

        # First try: scan for chapter headings in text.
        hits = self._find_headings(all_paragraphs)

        # Recover orphaned "Глава" lines with OCR-damaged numerals.
        hits = self._recover_orphan_glava_headings(all_paragraphs, hits)

        # Second try: if no headings or very few (<= 2), try parsing TOC.
        if len(hits) <= 2:
            full_text = "\n\n".join(p.raw_text for p in all_paragraphs)
            toc_range = find_toc_section(full_text)

            if toc_range:
                start, end = toc_range
                toc_text = full_text[start:end]
                toc_entries = parse_toc_entries(toc_text)

                if toc_entries:
                    # Extract main chapter titles from TOC.
                    # Try level=0 first (e.g., "1.", "2."), then level=1 if too few.
                    main_titles = extract_main_titles(toc_entries, max_level=0)

                    if len(main_titles) < 5:
                        # Not enough main chapters, include sub-chapters (level=1).
                        main_titles = extract_main_titles(toc_entries, max_level=1)

                    logger.info("Found %d chapters in TOC (level 0-1).", len(main_titles))

                    # Try to find these titles in text.
                    toc_hits = self._find_toc_based_headings(all_paragraphs, main_titles)

                    # Use TOC hits if we found more chapters than pattern matching.
                    if len(toc_hits) > len(hits):
                        logger.info("Using TOC-based chapters (%d) instead of pattern-based (%d).", len(toc_hits), len(hits))
                        hits = toc_hits

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

        # Remove duplicate headings (keep only the last occurrence).
        # This handles cases where TOC entries duplicate actual chapter headings.
        seen_titles: dict[str, int] = {}
        for i, hit in enumerate(hits):
            normalized_title = hit.heading_text.strip().upper()
            if normalized_title in seen_titles:
                # Mark previous occurrence for removal.
                seen_titles[normalized_title] = i
            else:
                seen_titles[normalized_title] = i

        # Keep only last occurrence of each title.
        unique_hits = []
        last_indices = set(seen_titles.values())
        for i, hit in enumerate(hits):
            if i in last_indices:
                unique_hits.append(hit)

        unique_hits = ChapterDetector._filter_numeric_heading_noise(unique_hits)
        return unique_hits

    @staticmethod
    def _filter_numeric_heading_noise(hits: list[_HeadingHit]) -> list[_HeadingHit]:
        """
        Discard numeric_heading hits whose numbers look like footnotes
        rather than real chapter numbers.

        Footnotes restart numbering per chapter, so their leading numbers
        repeatedly drop below the running maximum when read in document
        order.  Real chapter numbers are monotonically increasing.
        """
        numeric_hits = [h for h in hits if h.pattern_label == "numeric_heading"]
        if len(numeric_hits) < 3:
            return hits

        num_re = re.compile(r"^\s*(\d+)")
        numbers: list[int] = []
        for h in numeric_hits:
            m = num_re.match(h.heading_text)
            if m:
                numbers.append(int(m.group(1)))

        if not numbers:
            return hits

        # Count how many times the number drops below the running max
        # (a "restart").  Footnotes restart per chapter; real chapters don't.
        running_max = 0
        restarts = 0
        for n in numbers:
            if n < running_max:
                restarts += 1
            running_max = max(running_max, n)

        restart_rate = restarts / len(numbers)
        if restart_rate > 0.25:
            logger.info(
                "Discarding %d numeric_heading hits (restart_rate=%.2f, likely footnotes).",
                len(numeric_hits),
                restart_rate,
            )
            return [h for h in hits if h.pattern_label != "numeric_heading"]

        return hits

    # "Глава" + single short token (1-10 non-space chars) + end of line.
    # Rejects TOC entries like "Глава I Сержант гвардии 7".
    _RE_ORPHAN_GLAVA = re.compile(
        r"^\s*[Гг][Лл][Аа][Вв][Аа]\s+\S{1,10}\s*$"
    )

    @staticmethod
    def _recover_orphan_glava_headings(
        paragraphs: list[Paragraph],
        hits: list[_HeadingHit],
    ) -> list[_HeadingHit]:
        """
        Recover chapter headings where 'Глава' is followed by an
        unrecognisable token (e.g. OCR-damaged numeral like '[М' for IV).

        Activated only when the book already has ≥ 3 confirmed 'Глава'-style
        hits, proving it consistently uses this convention.  The orphan line
        must contain exactly one short token after 'Глава' to avoid false
        positives from sentences or TOC entries.
        """
        glava_hits = [
            h for h in hits
            if h.heading_text.strip().lower().startswith("глава")
        ]
        if len(glava_hits) < 3:
            return hits

        hit_indices = {h.paragraph_index for h in hits}

        recovered: list[_HeadingHit] = []
        for idx, para in enumerate(paragraphs):
            if idx in hit_indices:
                continue
            text = para.raw_text.strip()
            if not text:
                continue
            first_line = text.split("\n", maxsplit=1)[0].strip()
            if not ChapterDetector._RE_ORPHAN_GLAVA.match(first_line):
                continue
            if match_chapter_heading(first_line) is not None:
                continue
            recovered.append(
                _HeadingHit(
                    paragraph_index=idx,
                    heading_text=first_line,
                    pattern_label="chapter_recovered",
                )
            )

        if recovered:
            logger.info(
                "Recovered %d orphaned 'Глава' heading(s) with damaged numerals.",
                len(recovered),
            )
            all_hits = hits + recovered
            all_hits.sort(key=lambda h: h.paragraph_index)
            return all_hits

        return hits

    @staticmethod
    def _find_toc_based_headings(paragraphs: list[Paragraph], toc_titles: list[str]) -> list[_HeadingHit]:
        """
        Find headings in paragraphs based on TOC titles.

        Matches paragraph lines against TOC titles (fuzzy matching).
        Checks ALL lines in a paragraph, not just the first one.
        """
        hits: list[_HeadingHit] = []

        for idx, para in enumerate(paragraphs):
            text = para.raw_text.strip()
            if not text:
                continue

            # Split into lines and check each line.
            lines = text.split("\n")

            for line in lines:
                stripped_line = line.strip()
                if not stripped_line or len(stripped_line) < 5:
                    continue

                # Normalize line.
                normalized_line = stripped_line.rstrip(".,:;!? ")

                # Try to match against TOC titles.
                for toc_title in toc_titles:
                    normalized_toc = toc_title.rstrip(".,:;!? ")

                    # Check if TOC title appears in line (as substring).
                    if len(normalized_toc) > 5 and normalized_toc in normalized_line:
                        # Make sure it's not part of the TOC list itself (like "0. Title ... 6").
                        # Skip lines that look like TOC entries (have "..." or page numbers).
                        if '...' in stripped_line or '…' in stripped_line:
                            continue

                        hits.append(_HeadingHit(paragraph_index=idx, heading_text=toc_title, pattern_label="toc_match"))
                        break

                # If we found a match for this paragraph, don't check other lines.
                if hits and hits[-1].paragraph_index == idx:
                    break

        # Remove duplicates (same paragraph matched multiple times).
        seen = set()
        unique_hits = []
        for hit in hits:
            if hit.paragraph_index not in seen:
                seen.add(hit.paragraph_index)
                unique_hits.append(hit)

        return unique_hits

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

            # Get the paragraph containing the heading.
            heading_para = paragraphs[start]
            lines = heading_para.raw_text.strip().split('\n')

            # Find which line contains the heading.
            heading_line_idx = -1
            full_title = hit.heading_text
            for line_idx, line in enumerate(lines):
                normalized_line = line.strip().rstrip('.,:;!? ')
                normalized_title = hit.heading_text.strip().rstrip('.,:;!? ')
                
                if normalized_title in normalized_line or normalized_line.startswith(normalized_title):
                    heading_line_idx = line_idx
                    full_title = line.strip()
                    break

            # Split paragraph at heading line if found.
            chapter_paras: list[Paragraph] = []

            if heading_line_idx >= 0:
                # Create new paragraph starting from heading line.
                lines_from_heading = lines[heading_line_idx:]
                if lines_from_heading:
                    split_para = Paragraph(
                        raw_text='\n'.join(lines_from_heading),
                        index_in_chapter=0,  # Will be reindexed later.
                    )
                    chapter_paras.append(split_para)

                # Add remaining paragraphs.
                chapter_paras.extend(paragraphs[start + 1 : end])

                # If there were lines BEFORE heading, add them to previous chapter.
                if heading_line_idx > 0 and chapters:
                    lines_before_heading = lines[:heading_line_idx]
                    if lines_before_heading:
                        prev_para = Paragraph(
                            raw_text='\n'.join(lines_before_heading),
                            index_in_chapter=len(chapters[-1].paragraphs),
                        )
                        chapters[-1].paragraphs.append(prev_para)
            else:
                # Heading not found in lines, use standard logic.
                if len(lines) == 1:
                    # Single-line paragraph, skip it.
                    chapter_paras = paragraphs[start + 1 : end]
                else:
                    # Multi-line paragraph, include it.
                    chapter_paras = paragraphs[start:end]

            # Skip empty chapters (e.g., from table of contents).
            if not chapter_paras:
                continue

            self._reindex_paragraphs(chapter_paras)

            chapters.append(
                Chapter(
                    title=full_title,
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

        # Consider chapter meaningful if it has at least 10 chars of actual content.
        return total_chars >= 10

    @staticmethod
    def _reindex_paragraphs(paragraphs: list[Paragraph]) -> None:
        """Re-assign sequential index_in_chapter values."""
        for idx, para in enumerate(paragraphs):
            para.index_in_chapter = idx
