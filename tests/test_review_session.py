"""Tests for review session management."""

from __future__ import annotations

from pathlib import Path

from book_normalizer.models.review import (
    IssueSeverity,
    IssueType,
    ReviewAction,
    ReviewDecision,
    ReviewIssue,
)
from book_normalizer.review.session import ReviewSession, SessionManager


def _make_issue(original: str = "test", suggested: str = "fixed") -> ReviewIssue:
    """Create a minimal review issue for testing."""
    return ReviewIssue(
        issue_type=IssueType.PUNCTUATION,
        severity=IssueSeverity.MEDIUM,
        original_fragment=original,
        suggested_fragment=suggested,
        chapter_id="ch1",
        paragraph_id="p1",
        confidence=0.9,
    )


class TestReviewSession:
    def test_initial_state(self) -> None:
        session = ReviewSession()
        assert session.total_issues == 0
        assert session.progress_pct == 100.0
        assert session.completed is False

    def test_pending_and_resolved_counts(self) -> None:
        session = ReviewSession(pending_issues=[_make_issue(), _make_issue()])
        assert session.pending_count == 2
        assert session.resolved_count == 0
        assert session.total_issues == 2

    def test_get_current_issue(self) -> None:
        issue1 = _make_issue("a")
        issue2 = _make_issue("b")
        session = ReviewSession(pending_issues=[issue1, issue2])
        assert session.get_current_issue() == issue1

    def test_record_decision(self) -> None:
        issue = _make_issue()
        session = ReviewSession(pending_issues=[issue])

        decision = ReviewDecision(
            issue_id=issue.id,
            action=ReviewAction.ACCEPT,
            original_fragment="test",
            final_fragment="fixed",
        )
        session.record_decision(decision)

        assert session.pending_count == 0
        assert session.resolved_count == 1
        assert session.completed is True
        assert len(session.decisions) == 1

    def test_skip_current(self) -> None:
        issues = [_make_issue("a"), _make_issue("b"), _make_issue("c")]
        session = ReviewSession(pending_issues=issues)

        session.skip_current()
        assert session.current_index == 1

        session.skip_current()
        assert session.current_index == 2

    def test_progress_pct(self) -> None:
        issues = [_make_issue("a"), _make_issue("b")]
        session = ReviewSession(pending_issues=issues)
        assert session.progress_pct == 0.0

        decision = ReviewDecision(
            issue_id=issues[0].id,
            action=ReviewAction.ACCEPT,
            original_fragment="a",
            final_fragment="fixed",
        )
        session.record_decision(decision)
        assert session.progress_pct == 50.0

    def test_get_current_returns_none_when_empty(self) -> None:
        session = ReviewSession()
        assert session.get_current_issue() is None


class TestSessionManager:
    def test_save_and_load(self, tmp_path: Path) -> None:
        mgr = SessionManager(tmp_path / "sessions")
        issue = _make_issue()
        session = ReviewSession(
            session_id="abc123",
            book_id="book001",
            pending_issues=[issue],
        )

        path = mgr.save(session)
        assert path.exists()

        loaded = mgr.load(path)
        assert loaded.session_id == "abc123"
        assert loaded.book_id == "book001"
        assert loaded.pending_count == 1

    def test_find_latest_for_book(self, tmp_path: Path) -> None:
        import time

        mgr = SessionManager(tmp_path / "sessions")

        s1 = ReviewSession(session_id="aaa", book_id="mybook")
        mgr.save(s1)
        time.sleep(0.05)

        s2 = ReviewSession(session_id="bbb", book_id="mybook")
        path2 = mgr.save(s2)

        found = mgr.find_latest_for_book("mybook")
        assert found is not None
        assert found == path2

    def test_find_latest_no_match(self, tmp_path: Path) -> None:
        mgr = SessionManager(tmp_path / "sessions")
        (tmp_path / "sessions").mkdir(parents=True, exist_ok=True)
        assert mgr.find_latest_for_book("nonexistent") is None

    def test_list_sessions(self, tmp_path: Path) -> None:
        mgr = SessionManager(tmp_path / "sessions")
        mgr.save(ReviewSession(session_id="aaa", book_id="b1"))
        mgr.save(ReviewSession(session_id="bbb", book_id="b2"))
        sessions = mgr.list_sessions()
        assert len(sessions) == 2

    def test_load_nonexistent_raises(self, tmp_path: Path) -> None:
        import pytest

        mgr = SessionManager(tmp_path)
        with pytest.raises(FileNotFoundError):
            mgr.load(tmp_path / "missing.json")
