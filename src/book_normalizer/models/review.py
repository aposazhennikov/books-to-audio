"""Models for review issues, decisions, stress, and audit records."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _generate_id() -> str:
    """Generate a unique identifier."""
    return uuid.uuid4().hex[:12]


def _now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class IssueSeverity(str, enum.Enum):
    """Severity levels for detected review issues."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueType(str, enum.Enum):
    """Categories of text issues that may require review."""

    PUNCTUATION = "punctuation"
    SPELLING = "spelling"
    OCR_ARTIFACT = "ocr_artifact"
    FORMATTING = "formatting"
    ENCODING = "encoding"
    STRESS = "stress"
    OTHER = "other"


class ReviewAction(str, enum.Enum):
    """Possible user actions when reviewing an issue."""

    ACCEPT = "accept"
    KEEP_ORIGINAL = "keep_original"
    CUSTOM = "custom"
    SKIP = "skip"


class ReviewIssue(BaseModel):
    """A detected issue that may require human review."""

    id: str = Field(default_factory=_generate_id)
    issue_type: IssueType = IssueType.OTHER
    severity: IssueSeverity = IssueSeverity.MEDIUM
    original_fragment: str = ""
    suggested_fragment: str = ""
    context_before: str = ""
    context_after: str = ""
    chapter_id: str = ""
    paragraph_id: str = ""
    confidence: float = 0.5
    resolved: bool = False


class ReviewDecision(BaseModel):
    """A recorded decision for a specific review issue."""

    issue_id: str = ""
    action: ReviewAction = ReviewAction.SKIP
    original_fragment: str = ""
    final_fragment: str = ""
    user_note: str = ""
    timestamp: datetime = Field(default_factory=_now)


class StressDecision(BaseModel):
    """A recorded user decision for stress/accent placement on a word."""

    word: str = ""
    normalized_word: str = ""
    stressed_form: str = ""
    source: str = "user"
    confirmed_by_user: bool = False
    timestamp: datetime = Field(default_factory=_now)


class AuditRecord(BaseModel):
    """An immutable record of a processing action for traceability."""

    stage: str = ""
    action: str = ""
    details: str = ""
    timestamp: datetime = Field(default_factory=_now)
