"""Resumable review session management."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from book_normalizer.models.review import ReviewDecision, ReviewIssue

logger = logging.getLogger(__name__)


def _now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class ReviewSession(BaseModel):
    """
    A resumable review session that tracks progress across issues.

    The session keeps separate lists for pending and resolved issues,
    along with all recorded decisions. It can be serialized to JSON
    and resumed later.
    """

    session_id: str = ""
    book_id: str = ""
    source_path: str = ""
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    pending_issues: list[ReviewIssue] = Field(default_factory=list)
    resolved_issues: list[ReviewIssue] = Field(default_factory=list)
    decisions: list[ReviewDecision] = Field(default_factory=list)
    current_index: int = 0
    completed: bool = False

    @property
    def total_issues(self) -> int:
        """Total number of issues (pending + resolved)."""
        return len(self.pending_issues) + len(self.resolved_issues)

    @property
    def resolved_count(self) -> int:
        """Number of resolved issues."""
        return len(self.resolved_issues)

    @property
    def pending_count(self) -> int:
        """Number of unresolved issues."""
        return len(self.pending_issues)

    @property
    def progress_pct(self) -> float:
        """Progress as a percentage (0-100)."""
        total = self.total_issues
        if total == 0:
            return 100.0
        return (self.resolved_count / total) * 100.0

    def get_current_issue(self) -> ReviewIssue | None:
        """Return the current pending issue, or None if all are resolved."""
        if self.current_index < len(self.pending_issues):
            return self.pending_issues[self.current_index]
        return None

    def record_decision(self, decision: ReviewDecision) -> None:
        """Record a decision and move the current issue to resolved."""
        self.decisions.append(decision)

        if self.current_index < len(self.pending_issues):
            issue = self.pending_issues.pop(self.current_index)
            issue.resolved = True
            self.resolved_issues.append(issue)

        if self.current_index >= len(self.pending_issues) and self.pending_issues:
            self.current_index = len(self.pending_issues) - 1

        if not self.pending_issues:
            self.completed = True

        self.updated_at = _now()

    def skip_current(self) -> None:
        """Skip the current issue without recording a decision."""
        if self.current_index < len(self.pending_issues) - 1:
            self.current_index += 1
        elif self.pending_issues:
            self.current_index = 0
        self.updated_at = _now()


class SessionManager:
    """
    Manages saving and loading review sessions to/from disk.

    Sessions are stored as individual JSON files in a configured directory.
    """

    def __init__(self, sessions_dir: Path) -> None:
        self._dir = Path(sessions_dir)

    def save(self, session: ReviewSession) -> Path:
        """Save a session to disk and return the file path."""
        self._dir.mkdir(parents=True, exist_ok=True)

        filename = f"session_{session.book_id or 'unknown'}_{session.session_id[:8]}.json"
        path = self._dir / filename

        data = session.model_dump(mode="json")
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        logger.info("Saved review session to %s", path)
        return path

    def load(self, path: Path) -> ReviewSession:
        """Load a session from a JSON file."""
        resolved = Path(path).resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"Session file not found: {resolved}")

        text = resolved.read_text(encoding="utf-8")
        data = json.loads(text)
        session = ReviewSession.model_validate(data)
        logger.info(
            "Loaded session: %d pending, %d resolved",
            session.pending_count,
            session.resolved_count,
        )
        return session

    def find_latest_for_book(self, book_id: str) -> Path | None:
        """Find the most recent session file for a given book ID."""
        if not self._dir.is_dir():
            return None

        candidates: list[tuple[float, Path]] = []
        for f in self._dir.glob(f"session_{book_id}_*.json"):
            candidates.append((f.stat().st_mtime, f))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    def list_sessions(self) -> list[Path]:
        """List all session files in the sessions directory."""
        if not self._dir.is_dir():
            return []
        return sorted(self._dir.glob("session_*.json"))
