"""Table of Contents (TOC) parser for extracting chapter structure."""

from __future__ import annotations

import re
from typing import NamedTuple


class TocEntry(NamedTuple):
    """A single entry from table of contents."""

    title: str  # Chapter title extracted from TOC.
    page_num: str | None  # Page number if present.
    level: int  # Nesting level (0 = main chapter, 1 = subchapter).


def find_toc_section(text: str) -> tuple[int, int] | None:
    """
    Find the start and end positions of TOC section in text.

    Looks for markers like "ОГЛАВЛЕНИЕ", "Содержание", "CONTENTS" etc.
    Returns (start_pos, end_pos) or None if not found.
    """
    # Common TOC markers in Russian and English.
    toc_markers = [
        r"ОГЛАВЛЕНИЕ",
        r"Оглавление",
        r"СОДЕРЖАНИЕ",
        r"Содержание",
        r"CONTENTS",
        r"Contents",
        r"TABLE OF CONTENTS",
    ]

    pattern = re.compile(r"^\s*(" + "|".join(toc_markers) + r")\s*$", re.MULTILINE | re.IGNORECASE)
    match = pattern.search(text)

    if not match:
        return None

    start_pos = match.start()

    # Find end of TOC: look for first long paragraph (not a TOC entry).
    # TOC entries are typically: "1.2. Title ... 123" or similar (< 150 chars).
    # After TOC, we'll find full paragraphs (> 200 chars).
    search_text = text[start_pos:]
    lines = search_text.split("\n")

    toc_entry_pattern = re.compile(r"^\s*\d+(?:\.\d+)*\.\s+.+$")

    in_toc = True
    current_pos = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        current_pos += len(line) + 1  # +1 for newline.

        # Skip empty lines.
        if not stripped:
            continue

        # If line looks like TOC entry, continue.
        if toc_entry_pattern.match(stripped) and len(stripped) < 150:
            continue

        # If we hit a long paragraph (> 200 chars), TOC likely ended.
        if len(stripped) > 200 and in_toc:
            # TOC ends before this paragraph.
            return (start_pos, start_pos + current_pos - len(line) - 1)

        # If we find section number pattern like "1.0." or "0." at line start, it's content start.
        if re.match(r"^\s*\d+(?:\.\d+)*\.\s+[А-Яа-яЁё]", stripped):
            # This is actual chapter content, not TOC.
            # Back up to find where TOC entries ended.
            # Look back for last TOC-like line.
            for j in range(i - 1, max(0, i - 20), -1):
                prev_line = lines[j].strip()
                if prev_line and (toc_entry_pattern.match(prev_line) or len(prev_line) < 150):
                    # Found last TOC line.
                    back_pos = sum(len(lines[k]) + 1 for k in range(j + 1))
                    return (start_pos, start_pos + back_pos)

            break

    # Fallback: assume TOC is first ~1500 chars after marker.
    return (start_pos, min(start_pos + 1500, len(text)))


def parse_toc_entries(toc_text: str) -> list[TocEntry]:
    """
    Parse TOC text and extract chapter entries.

    Looks for patterns like:
    - "1. Предисловие ... 5"
    - "2.1. Медицина как совокупность методик ... 14"
    - "Глава первая ... 10"
    """
    entries: list[TocEntry] = []

    # Pattern for numbered entries: "1.2.3. Title ... 123" or "1. Title".
    numbered_pattern = re.compile(
        r"^\s*(\d+(?:\.\d+)*)\.\s+([^.…]+?)(?:\s*[.…]+\s*(\d+))?\s*$", re.MULTILINE
    )

    # Pattern for word entries: "Глава первая ... 10".
    word_pattern = re.compile(
        r"^\s*((?:[Гг][Лл][Аа][Вв][Аа]|[Чч][Аа][Сс][Тт][Ьь])\s+[А-Яа-яЁё]+)"
        r"(?:\s*[.…]+\s*(\d+))?\s*$",
        re.MULTILINE,
    )

    for match in numbered_pattern.finditer(toc_text):
        number = match.group(1)
        title = match.group(2).strip()
        page_num = match.group(3)

        # Determine nesting level by counting dots.
        level = number.count(".")

        entries.append(TocEntry(title=title, page_num=page_num, level=level))

    for match in word_pattern.finditer(toc_text):
        title = match.group(1).strip()
        page_num = match.group(2)

        entries.append(TocEntry(title=title, page_num=page_num, level=0))

    return entries


def extract_main_titles(entries: list[TocEntry], max_level: int = 0) -> list[str]:
    """
    Extract main chapter titles from TOC entries.

    Only returns entries at level <= max_level (0 = top-level only).
    For better chapter detection, we extract entries like "1.", "2.", "3." (not "1.1.", "2.3.").
    """
    main_titles: list[str] = []

    for entry in entries:
        if entry.level <= max_level:
            # Skip very generic or short titles that might cause false positives.
            if entry.title and len(entry.title) > 3:
                main_titles.append(entry.title)

    return main_titles
