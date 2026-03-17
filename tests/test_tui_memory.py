from __future__ import annotations

import io
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console

from book_normalizer.memory.correction_store import CorrectionStore
from book_normalizer.memory.punctuation_store import PunctuationStore
from book_normalizer.models.book import Book, Chapter, Paragraph
from book_normalizer.models.review import IssueSeverity, IssueType, ReviewAction, ReviewDecision, ReviewIssue
from book_normalizer.review.session import ReviewSession
from book_normalizer.review.tui import InteractiveReviewer


def _make_issue(
    issue_type: IssueType,
    original: str,
    suggested: str,
) -> ReviewIssue:
    para = Paragraph(raw_text=f"context {original} context", normalized_text="", index_in_chapter=0)
    ch = Chapter(title="Test", index=0, paragraphs=[para])
    book = Book(chapters=[ch])
    return ReviewIssue(
        issue_type=issue_type,
        severity=IssueSeverity.MEDIUM,
        original_fragment=original,
        suggested_fragment=suggested,
        context_before="before " + original,
        context_after=original + " after",
        chapter_id=ch.id,
        paragraph_id=para.id,
        confidence=0.9,
    )


def _make_console() -> Console:
    """Create a silent console for tests."""
    return Console(file=io.StringIO(), stderr=False, force_terminal=False, color_system=None)


class TestTuiMemoryPersistence:
    def test_risky_single_char_stored_as_review_only(self, tmp_path: Path) -> None:
        correction_store = CorrectionStore(tmp_path / "corr.json")
        punct_store = PunctuationStore(tmp_path / "punct.json")
        console = _make_console()
        reviewer = InteractiveReviewer(
            correction_store=correction_store,
            punctuation_store=punct_store,
            console=console,
        )

        issue = _make_issue(IssueType.OCR_ARTIFACT, original="0", suggested="о")
        session = ReviewSession(
            pending_issues=[issue],
        )

        decision = ReviewDecision(
            issue_id=issue.id,
            action=ReviewAction.ACCEPT,
            original_fragment=issue.original_fragment,
            final_fragment=issue.suggested_fragment,
            timestamp=datetime.now(timezone.utc),
        )

        reviewer._persist_to_memory(issue, decision)  # type: ignore[attr-defined]

        entries = correction_store.all_entries()
        assert len(entries) == 1
        entry = entries[0]
        assert entry.issue_type == IssueType.OCR_ARTIFACT.value
        assert entry.token == "0"
        assert entry.normalized_token == "0"
        assert entry.auto_apply_safe is False

    def test_ocr_word_with_digit_marked_auto_safe(self, tmp_path: Path) -> None:
        correction_store = CorrectionStore(tmp_path / "corr.json")
        punct_store = PunctuationStore(tmp_path / "punct.json")
        console = _make_console()
        reviewer = InteractiveReviewer(
            correction_store=correction_store,
            punctuation_store=punct_store,
            console=console,
        )

        issue = _make_issue(IssueType.OCR_ARTIFACT, original="м0сква", suggested="москва")
        session = ReviewSession(
            pending_issues=[issue],
        )

        decision = ReviewDecision(
            issue_id=issue.id,
            action=ReviewAction.ACCEPT,
            original_fragment=issue.original_fragment,
            final_fragment=issue.suggested_fragment,
            timestamp=datetime.now(timezone.utc),
        )

        reviewer._persist_to_memory(issue, decision)  # type: ignore[attr-defined]

        entries = correction_store.all_entries()
        assert len(entries) == 1
        entry = entries[0]
        assert entry.issue_type == IssueType.OCR_ARTIFACT.value
        assert entry.token == "м0сква"
        assert entry.normalized_token == "м0сква"
        assert entry.auto_apply_safe is True

    def test_digit_at_edges_not_auto_safe(self, tmp_path: Path) -> None:
        correction_store = CorrectionStore(tmp_path / "corr.json")
        punct_store = PunctuationStore(tmp_path / "punct.json")
        console = _make_console()
        reviewer = InteractiveReviewer(
            correction_store=correction_store,
            punctuation_store=punct_store,
            console=console,
        )

        for original, suggested in (("0тдельный", "отдельный"), ("молок0", "молоко")):
            issue = _make_issue(IssueType.OCR_ARTIFACT, original=original, suggested=suggested)
            decision = ReviewDecision(
                issue_id=issue.id,
                action=ReviewAction.ACCEPT,
                original_fragment=issue.original_fragment,
                final_fragment=issue.suggested_fragment,
                timestamp=datetime.now(timezone.utc),
            )
            reviewer._persist_to_memory(issue, decision)  # type: ignore[attr-defined]

        entries = {e.token: e for e in correction_store.all_entries()}
        assert entries["0тдельный"].auto_apply_safe is False
        assert entries["молок0"].auto_apply_safe is False

    def test_code_like_tokens_never_auto_safe(self, tmp_path: Path) -> None:
        correction_store = CorrectionStore(tmp_path / "corr.json")
        punct_store = PunctuationStore(tmp_path / "punct.json")
        console = _make_console()
        reviewer = InteractiveReviewer(
            correction_store=correction_store,
            punctuation_store=punct_store,
            console=console,
        )

        # Even if such tokens are ever passed through the TUI as OCR issues,
        # they must not be marked as auto-apply-safe.
        for original in ("М4А1", "RTX3060"):
            issue = _make_issue(IssueType.OCR_ARTIFACT, original=original, suggested=original)
            decision = ReviewDecision(
                issue_id=issue.id,
                action=ReviewAction.ACCEPT,
                original_fragment=issue.original_fragment,
                final_fragment=issue.suggested_fragment,
                timestamp=datetime.now(timezone.utc),
            )
            reviewer._persist_to_memory(issue, decision)  # type: ignore[attr-defined]

        entries = {e.token: e for e in correction_store.all_entries()}
        assert entries["М4А1"].auto_apply_safe is False
        assert entries["RTX3060"].auto_apply_safe is False

