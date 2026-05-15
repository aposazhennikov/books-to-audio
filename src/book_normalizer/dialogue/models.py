"""Data models for dialogue detection and speaker attribution."""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def _generate_id() -> str:
    """Generate a short unique identifier."""
    return uuid.uuid4().hex[:12]


class SpeakerRole(str, Enum):
    """Voice role assigned to a text segment for TTS synthesis."""

    NARRATOR = "narrator"
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class DialogueLine(BaseModel):
    """A single line extracted from a paragraph, tagged with a speaker role."""

    id: str = Field(default_factory=_generate_id)
    text: str = ""
    role: SpeakerRole = SpeakerRole.NARRATOR
    paragraph_id: str = ""
    line_index: int = 0
    is_dialogue: bool = False
    attribution_tag: str = ""


class AnnotatedParagraph(BaseModel):
    """A paragraph broken into dialogue lines with speaker roles."""

    paragraph_id: str = ""
    chapter_index: int = 0
    lines: list[DialogueLine] = Field(default_factory=list)

    @property
    def has_dialogue(self) -> bool:
        """Return True if any line in this paragraph is dialogue."""
        return any(line.is_dialogue for line in self.lines)


class AnnotatedChapter(BaseModel):
    """A chapter with all paragraphs annotated for dialogue and speakers."""

    chapter_index: int = 0
    chapter_title: str = ""
    paragraphs: list[AnnotatedParagraph] = Field(default_factory=list)

    @property
    def dialogue_count(self) -> int:
        """Count total dialogue lines across all paragraphs."""
        return sum(
            1 for p in self.paragraphs for line in p.lines if line.is_dialogue
        )

    @property
    def narrator_count(self) -> int:
        """Count total narrator lines across all paragraphs."""
        return sum(
            1 for p in self.paragraphs for line in p.lines if not line.is_dialogue
        )


class VoiceAnnotatedChunk(BaseModel):
    """A text chunk with an assigned speaker role, ready for TTS."""

    index: int = 0
    text: str = ""
    chapter_index: int = 0
    role: SpeakerRole = SpeakerRole.NARRATOR
    voice_id: str = ""
    intonation: str = "neutral"
    pause_after_ms: int = 0
    boundary_after: str = ""


class VoiceSegment(BaseModel):
    """A single dialogue/narrator segment before chunking.

    Represents the finest granularity of voice assignment.
    Users assign voice_id and intonation per segment,
    then segments are grouped into chunks for TTS.
    """

    segment_index: int = 0
    chapter_index: int = 0
    is_dialogue: bool = False
    role: SpeakerRole = SpeakerRole.NARRATOR
    voice_id: str = ""
    intonation: str = "neutral"
    text: str = ""


class SpeakerAnnotationResult(BaseModel):
    """Summary of speaker annotation applied to a book."""

    total_lines: int = 0
    narrator_lines: int = 0
    male_lines: int = 0
    female_lines: int = 0
    unknown_lines: int = 0
    chapters_processed: int = 0
    strategy: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)
