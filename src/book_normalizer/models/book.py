"""Core data models for book structure representation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


def _generate_id() -> str:
    """Generate a unique identifier."""
    return uuid.uuid4().hex[:12]


def _now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class Metadata(BaseModel):
    """Book metadata extracted from the source file."""

    title: str = "Untitled"
    author: str = "Unknown"
    language: str = "ru"
    publisher: str = ""
    year: str = ""
    source_path: str = ""
    source_format: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)


class Segment(BaseModel):
    """
    A sub-paragraph unit for fine-grained annotation.

    Segments allow attaching stress marks, review flags,
    or other annotations to parts of a paragraph without
    modifying the paragraph text directly.
    """

    id: str = Field(default_factory=_generate_id)
    text: str = ""
    stress_form: str = ""
    annotations: dict[str, Any] = Field(default_factory=dict)


class Paragraph(BaseModel):
    """A single paragraph inside a chapter."""

    id: str = Field(default_factory=_generate_id)
    raw_text: str = ""
    normalized_text: str = ""
    index_in_chapter: int = 0
    segments: list[Segment] = Field(default_factory=list)


class Chapter(BaseModel):
    """A chapter or a named section of the book."""

    id: str = Field(default_factory=_generate_id)
    title: str = ""
    index: int = 0
    paragraphs: list[Paragraph] = Field(default_factory=list)
    source_span_start: int | None = None
    source_span_end: int | None = None

    @property
    def raw_text(self) -> str:
        """Concatenate raw text of all paragraphs."""
        return "\n\n".join(p.raw_text for p in self.paragraphs if p.raw_text)

    @property
    def normalized_text(self) -> str:
        """Concatenate normalized text of all paragraphs."""
        return "\n\n".join(
            (p.normalized_text or p.raw_text) for p in self.paragraphs if (p.normalized_text or p.raw_text)
        )


class Book(BaseModel):
    """Top-level representation of a processed book."""

    id: str = Field(default_factory=_generate_id)
    metadata: Metadata = Field(default_factory=Metadata)
    chapters: list[Chapter] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)
    audit_trail: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def raw_text(self) -> str:
        """Full raw text assembled from all chapters."""
        return "\n\n".join(ch.raw_text for ch in self.chapters if ch.raw_text)

    @property
    def normalized_text(self) -> str:
        """Full normalized text assembled from all chapters."""
        return "\n\n".join(ch.normalized_text for ch in self.chapters if ch.normalized_text)

    def add_audit(self, stage: str, action: str, details: str = "") -> None:
        """Append an audit record to the trail."""
        self.audit_trail.append(
            {
                "stage": stage,
                "action": action,
                "details": details,
                "timestamp": _now().isoformat(),
            }
        )

    @classmethod
    def from_raw_text(cls, text: str, source_path: Path | str = "", source_format: str = "txt") -> Book:
        """
        Create a Book from raw text with a single synthetic chapter.

        The text is stored as-is. Chapter splitting should be done
        later by the chaptering module.
        """
        paragraph = Paragraph(raw_text=text, normalized_text="", index_in_chapter=0)
        chapter = Chapter(title="Full Text", index=0, paragraphs=[paragraph])
        metadata = Metadata(
            source_path=str(source_path),
            source_format=source_format,
        )
        book = cls(metadata=metadata, chapters=[chapter])
        book.add_audit("creation", "from_raw_text", f"source={source_path}")
        return book
