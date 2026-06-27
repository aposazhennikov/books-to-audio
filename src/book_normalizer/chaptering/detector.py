"""Hybrid chapter detector for splitting a Book into chapters."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from book_normalizer.chaptering.patterns import match_chapter_heading, match_work_heading
from book_normalizer.chaptering.toc_parser import extract_main_titles, find_toc_section, parse_toc_entries
from book_normalizer.chunking.annotations import classify_chapter_paragraphs
from book_normalizer.models.book import Book, Chapter, Paragraph

logger = logging.getLogger(__name__)


@dataclass
class _HeadingHit:
    """Internal representation of a detected chapter heading."""

    paragraph_index: int
    heading_text: str
    pattern_label: str


@dataclass
class _WorkRange:
    """Internal representation of a top-level work inside one source file."""

    index: int
    title: str
    start: int
    end: int


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

        full_text = "\n\n".join(p.raw_text for p in all_paragraphs)
        toc_work_titles = self._extract_toc_work_titles(full_text)
        toc_para_indices: set[int] = set()
        toc_range = find_toc_section(full_text)
        if toc_range:
            start, end = toc_range
            toc_para_indices = self._paragraphs_in_range(
                all_paragraphs, full_text, start, end,
            )

        work_hits = self._find_work_headings(all_paragraphs, skip_indices=toc_para_indices)

        # First try: scan for chapter headings in text.
        hits = self._find_headings(all_paragraphs, skip_indices=toc_para_indices)

        # Recover orphaned "Глава" lines with OCR-damaged numerals.
        hits = self._recover_orphan_glava_headings(all_paragraphs, hits)
        work_hits = self._augment_work_headings_from_chapter_resets(
            all_paragraphs,
            work_hits,
            hits,
            toc_work_titles=toc_work_titles,
        )

        # Second try: if no headings or very few (<= 2), try parsing TOC.
        if len(hits) <= 2 and not work_hits:
            if toc_range:
                start, end = toc_range
                toc_text = full_text[start:end]
                toc_entries = parse_toc_entries(toc_text)

                if toc_entries:
                    main_titles = extract_main_titles(toc_entries, max_level=0)

                    if len(main_titles) < 5:
                        level1_titles = extract_main_titles(toc_entries, max_level=1)
                        # Only use sub-chapters if there aren't too many
                        # (many level-1 entries suggest sub-sections, not chapters).
                        if len(level1_titles) <= 20:
                            main_titles = level1_titles

                    logger.info("Found %d chapters in TOC (level 0-1).", len(main_titles))

                    toc_hits = self._find_toc_based_headings(
                        all_paragraphs, main_titles, skip_indices=toc_para_indices,
                    )

                    if len(toc_hits) > len(hits):
                        logger.info(
                            "Using TOC-based chapters (%d) instead of pattern-based (%d).",
                            len(toc_hits),
                            len(hits),
                        )
                        hits = toc_hits

        if not hits:
            if len(work_hits) >= 2:
                chapters = self._split_at_work_boundaries(all_paragraphs, work_hits, [])
                new_book = book.model_copy(deep=True)
                new_book.chapters = chapters
                self._write_structure_metadata(new_book, chapters, work_hits)
                new_book.add_audit("chaptering", "work_split", f"works={len(work_hits)}, chapters={len(chapters)}")
                return new_book
            logger.info("No chapter headings detected; book will have a single chapter.")
            self._write_structure_metadata(book, book.chapters, work_hits)
            book.add_audit("chaptering", "no_headings", "Single chapter retained.")
            return book

        if len(work_hits) >= 2:
            chapters = self._split_at_work_boundaries(all_paragraphs, work_hits, hits)
        else:
            chapters = self._split_at_headings(all_paragraphs, hits)
        self._normalize_chapter_titles(chapters)
        logger.info("Detected %d chapters.", len(chapters))

        new_book = book.model_copy(deep=True)
        new_book.chapters = chapters
        self._write_structure_metadata(new_book, chapters, work_hits)
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
    def _find_headings(
        paragraphs: list[Paragraph],
        skip_indices: set[int] | None = None,
    ) -> list[_HeadingHit]:
        """Scan paragraphs for lines that match chapter heading patterns."""
        hits: list[_HeadingHit] = []
        _skip = skip_indices or set()
        for idx, para in enumerate(paragraphs):
            if idx in _skip:
                continue
            text = para.raw_text.strip()
            if not text:
                continue
            first_line = text.split("\n", maxsplit=1)[0]
            result = match_chapter_heading(first_line)
            if result:
                heading_text, label = result
                hits.append(_HeadingHit(paragraph_index=idx, heading_text=heading_text, pattern_label=label))

        return ChapterDetector._filter_numeric_heading_noise(hits)

    @staticmethod
    def _find_work_headings(
        paragraphs: list[Paragraph],
        skip_indices: set[int] | None = None,
    ) -> list[_HeadingHit]:
        """Scan paragraphs for top-level book/work/volume boundaries."""
        hits: list[_HeadingHit] = []
        _skip = skip_indices or set()
        for idx, para in enumerate(paragraphs):
            if idx in _skip:
                continue
            text = para.raw_text.strip()
            if not text:
                continue
            first_line = text.split("\n", maxsplit=1)[0]
            result = match_work_heading(first_line)
            if result:
                heading_text, label = result
                hits.append(_HeadingHit(paragraph_index=idx, heading_text=heading_text, pattern_label=label))
        return hits

    _RE_FIRST_GLAVA = re.compile(
        r"^\s*[Гг][Лл][Аа][Вв][Аа]\s+(?:1|I|i|[Пп]ервая)\b"
    )
    _RE_NUMBERED_WORK_TITLE = re.compile(
        r"^\s*\d{1,2}\.\s+[А-Яа-яЁё][А-Яа-яЁё\s-]{4,80}$"
    )

    @staticmethod
    def _augment_work_headings_from_chapter_resets(
        paragraphs: list[Paragraph],
        work_hits: list[_HeadingHit],
        chapter_hits: list[_HeadingHit],
        *,
        toc_work_titles: dict[int, str] | None = None,
    ) -> list[_HeadingHit]:
        """
        Infer work boundaries in omnibus PDFs where each book restarts at
        "Глава первая" and the work title sits on a nearby numbered title page.
        """
        if len(work_hits) >= 2:
            return work_hits

        first_chapter_hits = [
            hit for hit in chapter_hits
            if ChapterDetector._RE_FIRST_GLAVA.match(hit.heading_text)
        ]
        if len(first_chapter_hits) < 2:
            return work_hits

        existing_indices = {hit.paragraph_index for hit in work_hits}
        inferred: list[_HeadingHit] = []
        toc_titles = toc_work_titles or {}
        for sequence, hit in enumerate(first_chapter_hits, start=1):
            title_index, title = ChapterDetector._find_nearby_numbered_work_title(
                paragraphs,
                hit.paragraph_index,
            )
            start_index = title_index if title_index is not None else hit.paragraph_index
            if start_index in existing_indices:
                continue
            inferred.append(
                _HeadingHit(
                    paragraph_index=start_index,
                    heading_text=title or toc_titles.get(sequence, f"Book {sequence}"),
                    pattern_label="work_inferred_chapter_reset",
                )
            )

        if not inferred:
            return work_hits
        combined = work_hits + inferred
        combined.sort(key=lambda item: item.paragraph_index)
        return combined

    @staticmethod
    def _find_nearby_numbered_work_title(
        paragraphs: list[Paragraph],
        chapter_index: int,
    ) -> tuple[int | None, str | None]:
        for idx in range(chapter_index - 1, max(-1, chapter_index - 8), -1):
            text = re.sub(r"\s+", " ", paragraphs[idx].raw_text).strip()
            if ChapterDetector._RE_NUMBERED_WORK_TITLE.match(text):
                return idx, text
        return None, None

    @staticmethod
    def _extract_toc_work_titles(full_text: str) -> dict[int, str]:
        """Extract omnibus work titles from simple TOC blocks."""
        titles: dict[int, str] = {}
        lines = [line.strip() for line in full_text.splitlines() if line.strip()]
        book_re = re.compile(r"^Книга\s+(?P<number>\d{1,2})$", re.IGNORECASE)
        for idx, line in enumerate(lines[:-2]):
            match = book_re.match(line)
            if not match:
                continue
            title = lines[idx + 1]
            page = lines[idx + 2]
            if not re.fullmatch(r"\d{1,4}", page):
                continue
            if not re.fullmatch(r"[А-Яа-яЁё][А-Яа-яЁё\s-]{2,80}", title):
                continue
            number = int(match.group("number"))
            normalized_title = re.sub(r"\s+", " ", title).strip()
            titles[number] = f"{number}. {normalized_title}"
        return titles

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
    def _paragraphs_in_range(
        paragraphs: list[Paragraph],
        full_text: str,
        range_start: int,
        range_end: int,
    ) -> set[int]:
        """Return indices of paragraphs whose text overlaps a character range in full_text."""
        result: set[int] = set()
        pos = 0
        for idx, para in enumerate(paragraphs):
            para_start = full_text.find(para.raw_text, pos)
            if para_start == -1:
                continue
            para_end = para_start + len(para.raw_text)
            if para_start < range_end and para_end > range_start:
                result.add(idx)
            pos = para_end
        return result

    @staticmethod
    def _find_toc_based_headings(
        paragraphs: list[Paragraph],
        toc_titles: list[str],
        skip_indices: set[int] | None = None,
    ) -> list[_HeadingHit]:
        """
        Find headings in paragraphs based on TOC titles.

        Matches paragraph lines against TOC titles (fuzzy matching).
        Checks ALL lines in a paragraph, not just the first one.
        """
        hits: list[_HeadingHit] = []
        _skip = skip_indices or set()

        for idx, para in enumerate(paragraphs):
            if idx in _skip:
                continue
            text = para.raw_text.strip()
            if not text:
                continue

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

    def _split_at_work_boundaries(
        self,
        paragraphs: list[Paragraph],
        work_hits: list[_HeadingHit],
        chapter_hits: list[_HeadingHit],
    ) -> list[Chapter]:
        """Split one source file into top-level works, then chapters inside each work."""
        work_ranges = self._build_work_ranges(len(paragraphs), work_hits)
        chapters: list[Chapter] = []

        if work_ranges[0].start > 0:
            preamble_paras = paragraphs[: work_ranges[0].start]
            preamble_hits = [
                h for h in chapter_hits
                if h.paragraph_index < work_ranges[0].start
            ]
            chapters.extend(
                self._split_range_as_work(
                    preamble_paras,
                    preamble_hits,
                    work_index=-1,
                    work_title="Preamble",
                    title_prefix="",
                )
            )

        for work_range in work_ranges:
            local_paragraphs = paragraphs[work_range.start:work_range.end]
            local_hits = [
                _HeadingHit(
                    paragraph_index=h.paragraph_index - work_range.start,
                    heading_text=h.heading_text,
                    pattern_label=h.pattern_label,
                  )
                  for h in chapter_hits
                  if work_range.start <= h.paragraph_index < work_range.end
              ]
            chapters.extend(
                self._split_range_as_work(
                    local_paragraphs,
                    local_hits,
                    work_index=work_range.index,
                    work_title=work_range.title,
                    title_prefix=work_range.title,
                )
            )

        for idx, chapter in enumerate(chapters):
            chapter.index = idx
        return chapters

    @staticmethod
    def _build_work_ranges(total_paragraphs: int, work_hits: list[_HeadingHit]) -> list[_WorkRange]:
        ranges: list[_WorkRange] = []
        for idx, hit in enumerate(work_hits):
            end = work_hits[idx + 1].paragraph_index if idx + 1 < len(work_hits) else total_paragraphs
            if end <= hit.paragraph_index:
                continue
            ranges.append(
                _WorkRange(
                    index=len(ranges),
                    title=hit.heading_text,
                    start=hit.paragraph_index,
                    end=end,
                )
            )
        return ranges

    def _split_range_as_work(
        self,
        paragraphs: list[Paragraph],
        hits: list[_HeadingHit],
        *,
        work_index: int,
        work_title: str,
        title_prefix: str,
    ) -> list[Chapter]:
        if not paragraphs:
            return []

        if hits:
            chapters = self._split_at_headings(paragraphs, hits)
            chapters = self._drop_work_title_only_preamble(chapters, work_title)
        else:
            chapter = Chapter(
                title=work_title or "Full Text",
                index=0,
                paragraphs=paragraphs,
            )
            chapters = [chapter] if self._has_meaningful_content(chapter) else []

        for section_index, chapter in enumerate(chapters):
            chapter.work_index = work_index
            chapter.work_title = work_title
            chapter.section_index = section_index
            if title_prefix and chapter.title and chapter.title != title_prefix:
                chapter.title = f"{title_prefix} - {chapter.title}"
        return chapters

    @staticmethod
    def _drop_work_title_only_preamble(chapters: list[Chapter], work_title: str) -> list[Chapter]:
        """Drop a synthetic preamble that contains only the work boundary title."""
        if not chapters or chapters[0].title != "Preamble":
            return chapters
        first = chapters[0]
        text = re.sub(r"\s+", " ", first.raw_text).strip(" .,:;!?")
        title = re.sub(r"\s+", " ", work_title).strip(" .,:;!?")
        if text.casefold() == title.casefold():
            return chapters[1:]
        return chapters

    def _split_at_headings(
        self,
        paragraphs: list[Paragraph],
        hits: list[_HeadingHit],
    ) -> list[Chapter]:
        """Split paragraph list into chapters at heading boundaries."""
        chapters: list[Chapter] = []
        starts = [
            self._leading_epigraph_start(paragraphs, hit.paragraph_index)
            for hit in hits
        ]

        if starts[0] > 0:
            preamble_paras = paragraphs[: starts[0]]
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
            start = starts[i]
            heading_start = hit.paragraph_index
            end = starts[i + 1] if i + 1 < len(hits) else len(paragraphs)

            # Get the paragraph containing the heading.
            heading_para = paragraphs[heading_start]
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
            chapter_paras: list[Paragraph] = list(paragraphs[start:heading_start])

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
                chapter_paras.extend(paragraphs[heading_start + 1 : end])

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
                    chapter_paras.extend(paragraphs[heading_start + 1 : end])
                else:
                    # Multi-line paragraph, include it.
                    chapter_paras.extend(paragraphs[heading_start:end])

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
    def _leading_epigraph_start(paragraphs: list[Paragraph], heading_index: int) -> int:
        """Include a short epigraph immediately before a chapter heading."""
        if heading_index <= 0:
            return heading_index
        previous = paragraphs[heading_index - 1].raw_text
        heading = paragraphs[heading_index].raw_text
        kinds = classify_chapter_paragraphs([previous, heading])
        if kinds and kinds[0] == "epigraph":
            return heading_index - 1
        return heading_index

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

    _RE_GLAVA_TITLE = re.compile(
        r"^(\s*[Гг][Лл][Аа][Вв][Аа]\s+)\S+\s*$"
    )

    @staticmethod
    def _normalize_chapter_titles(chapters: list[Chapter]) -> None:
        """
        Replace OCR-damaged chapter numerals with sequential numbers.

        For titles matching 'Глава <garbled>', substitute with
        'Глава <N>' where N is the sequential index among Глава-titled
        chapters.  This makes chapter titles TTS-friendly.
        """
        glava_re = re.compile(r"^\s*[Гг][Лл][Аа][Вв][Аа]\s+", re.IGNORECASE)
        glava_indices = [
            i for i, ch in enumerate(chapters)
            if glava_re.match(ch.title)
        ]
        if len(glava_indices) < 2:
            return

        by_work: dict[int, list[int]] = {}
        for ch_idx in glava_indices:
            by_work.setdefault(chapters[ch_idx].work_index, []).append(ch_idx)

        for indices in by_work.values():
            if len(indices) < 2:
                continue
            for seq, ch_idx in enumerate(indices, start=1):
                ch = chapters[ch_idx]
                m = glava_re.match(ch.title)
                if m:
                    prefix = m.group(0).rstrip() + " "
                    ch.title = f"{prefix.strip()} {seq}"

    @staticmethod
    def _write_structure_metadata(
        book: Book,
        chapters: list[Chapter],
        work_hits: list[_HeadingHit],
    ) -> None:
        """Persist a lightweight structure summary for GUI/export review."""
        work_titles: list[str] = []
        seen: set[tuple[int, str]] = set()
        for chapter in chapters:
            title = chapter.work_title or ""
            if chapter.work_index < 0 or title == "Preamble":
                continue
            key = (chapter.work_index, title)
            if title and key not in seen:
                seen.add(key)
                work_titles.append(title)

        duplicate_titles: dict[str, int] = {}
        for chapter in chapters:
            key = re.sub(r"\s+", " ", chapter.title.casefold()).strip()
            duplicate_titles[key] = duplicate_titles.get(key, 0) + 1

        repeated_chapter_titles = sorted(
            title for title, count in duplicate_titles.items()
            if title and count > 1
        )

        book.metadata.extra["structure"] = {
            "work_count": max(len(work_titles), 1 if chapters else 0),
            "work_titles": work_titles,
            "detected_work_boundaries": len(work_hits),
            "chapter_count": len(chapters),
            "repeated_chapter_titles": repeated_chapter_titles,
            "needs_review": bool(repeated_chapter_titles) or len(work_hits) >= 2,
        }
