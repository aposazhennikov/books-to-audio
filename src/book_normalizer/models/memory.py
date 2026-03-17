"""Models for persistent user memory entries."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class StressMemoryEntry(BaseModel):
    """A single stress dictionary entry persisted across sessions."""

    word: str
    normalized_word: str = ""
    stressed_form: str = ""
    confirmed: bool = False
    context_hint: str = ""
    updated_at: datetime = Field(default_factory=_now)


class CorrectionMemoryEntry(BaseModel):
    """A single spelling/OCR correction persisted across sessions."""

    original: str
    replacement: str
    context_hint: str = ""
    confirmed: bool = False
    issue_type: str = ""
    token: str = ""
    normalized_token: str = ""
    auto_apply_safe: bool = False
    updated_at: datetime = Field(default_factory=_now)


class PunctuationMemoryEntry(BaseModel):
    """A single punctuation correction persisted across sessions."""

    original: str
    replacement: str
    context_hint: str = ""
    confirmed: bool = False
    updated_at: datetime = Field(default_factory=_now)
