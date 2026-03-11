"""Configurable normalization pipeline that applies transformations in order."""

from __future__ import annotations

import logging
from typing import Callable

from book_normalizer.models.book import Book
from book_normalizer.normalization.cleanup import remove_page_numbers, remove_repeated_headers
from book_normalizer.normalization.encoding import fix_common_mojibake, normalize_encoding_artifacts
from book_normalizer.normalization.paragraphs import collapse_empty_lines, strip_paragraph_indents
from book_normalizer.normalization.punctuation import normalize_dashes, normalize_ellipsis, normalize_quotes
from book_normalizer.normalization.whitespace import (
    normalize_spacing_around_punctuation,
    normalize_whitespace,
    repair_broken_lines,
    repair_hyphenated_words,
)

logger = logging.getLogger(__name__)

TextTransform = Callable[[str], str]

DEFAULT_STAGES: list[tuple[str, TextTransform]] = [
    ("normalize_encoding_artifacts", normalize_encoding_artifacts),
    ("fix_common_mojibake", fix_common_mojibake),
    ("normalize_whitespace", normalize_whitespace),
    ("repair_hyphenated_words", repair_hyphenated_words),
    ("repair_broken_lines", repair_broken_lines),
    ("remove_page_numbers", remove_page_numbers),
    ("remove_repeated_headers", remove_repeated_headers),
    ("collapse_empty_lines", collapse_empty_lines),
    ("strip_paragraph_indents", strip_paragraph_indents),
    ("normalize_quotes", normalize_quotes),
    ("normalize_dashes", normalize_dashes),
    ("normalize_ellipsis", normalize_ellipsis),
    ("normalize_spacing_around_punctuation", normalize_spacing_around_punctuation),
]


class NormalizationPipeline:
    """
    Sequential pipeline of text transformations.

    Each stage is a named callable that takes str and returns str.
    The pipeline applies stages in order to every paragraph's raw_text,
    storing the result in normalized_text. Per-stage change tracking
    is available via the audit trail.
    """

    def __init__(self, stages: list[tuple[str, TextTransform]] | None = None) -> None:
        self._stages = stages if stages is not None else list(DEFAULT_STAGES)

    def add_stage(self, name: str, transform: TextTransform) -> None:
        """Append a custom stage to the pipeline."""
        self._stages.append((name, transform))

    def insert_stage_before(self, before: str, name: str, transform: TextTransform) -> None:
        """Insert a stage before an existing stage by name."""
        for i, (existing_name, _) in enumerate(self._stages):
            if existing_name == before:
                self._stages.insert(i, (name, transform))
                return
        self._stages.append((name, transform))

    def remove_stage(self, name: str) -> bool:
        """Remove a stage by name. Returns True if found and removed."""
        for i, (existing_name, _) in enumerate(self._stages):
            if existing_name == name:
                self._stages.pop(i)
                return True
        return False

    @property
    def stage_names(self) -> list[str]:
        """Return ordered list of stage names."""
        return [name for name, _ in self._stages]

    def normalize_text(self, text: str) -> str:
        """Apply all stages to a text string and return the result."""
        result = text
        for _name, fn in self._stages:
            result = fn(result)
        return result

    def normalize_text_with_tracking(self, text: str) -> tuple[str, list[str]]:
        """
        Apply all stages and return (result, list_of_stages_that_changed_text).

        Useful for audit trail: only stages that actually modified the
        text are reported.
        """
        result = text
        changed_stages: list[str] = []
        for name, fn in self._stages:
            new_result = fn(result)
            if new_result != result:
                changed_stages.append(name)
            result = new_result
        return result, changed_stages

    def normalize_book(self, book: Book, detailed_audit: bool = True) -> Book:
        """
        Apply normalization to every paragraph in the book.

        Fills normalized_text on each Paragraph. Returns the same
        book instance (mutation in place) for convenience.

        When detailed_audit is True, records which stages actually
        changed text for each paragraph (aggregated per-stage count).
        """
        total_paragraphs = 0
        stage_hit_counts: dict[str, int] = {}

        for chapter in book.chapters:
            for para in chapter.paragraphs:
                if detailed_audit:
                    para.normalized_text, changed = self.normalize_text_with_tracking(para.raw_text)
                    for stage_name in changed:
                        stage_hit_counts[stage_name] = stage_hit_counts.get(stage_name, 0) + 1
                else:
                    para.normalized_text = self.normalize_text(para.raw_text)
                total_paragraphs += 1

        logger.info(
            "Normalized %d paragraphs across %d chapters.",
            total_paragraphs,
            len(book.chapters),
        )

        if detailed_audit and stage_hit_counts:
            active_stages = ", ".join(
                f"{name}={count}" for name, count in sorted(stage_hit_counts.items())
            )
            book.add_audit(
                "normalization",
                "pipeline_complete",
                f"stages={len(self._stages)}, paragraphs={total_paragraphs}, "
                f"active_stages=[{active_stages}]",
            )
        else:
            book.add_audit(
                "normalization",
                "pipeline_complete",
                f"stages={len(self._stages)}, paragraphs={total_paragraphs}",
            )

        return book
