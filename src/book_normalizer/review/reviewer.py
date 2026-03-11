"""Reviewer orchestrator that scans a book and produces a review session."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from book_normalizer.memory.correction_store import CorrectionStore
from book_normalizer.memory.punctuation_store import PunctuationStore
from book_normalizer.models.book import Book
from book_normalizer.models.memory import CorrectionMemoryEntry, PunctuationMemoryEntry
from book_normalizer.models.review import (
    IssueType,
    ReviewAction,
    ReviewDecision,
    ReviewIssue,
)
from book_normalizer.review.issues import OcrSpellingDetector, PunctuationIssueDetector
from book_normalizer.review.session import ReviewSession

logger = logging.getLogger(__name__)


class Reviewer:
    """
    Orchestrates issue detection, memory-based auto-resolution,
    and session construction.

    The workflow:
    1. Run all enabled detectors on the book.
    2. For each detected issue, check persistent memory.
    3. Auto-resolve issues that match a previous confirmed decision.
    4. Remaining unresolved issues go into the review session.
    """

    def __init__(
        self,
        correction_store: CorrectionStore | None = None,
        punctuation_store: PunctuationStore | None = None,
        skip_punctuation: bool = False,
        skip_spellcheck: bool = False,
    ) -> None:
        self._correction_store = correction_store
        self._punctuation_store = punctuation_store
        self._skip_punctuation = skip_punctuation
        self._skip_spellcheck = skip_spellcheck

    def scan(self, book: Book) -> ReviewSession:
        """
        Scan the book for issues and return a review session.

        Auto-resolved issues are moved to resolved_issues with
        their decisions pre-filled from memory.
        """
        all_issues: list[ReviewIssue] = []

        if not self._skip_punctuation:
            detector = PunctuationIssueDetector()
            issues = detector.detect(book)
            logger.info("Punctuation detector found %d issue(s).", len(issues))
            all_issues.extend(issues)

        if not self._skip_spellcheck:
            detector = OcrSpellingDetector()
            issues = detector.detect(book)
            logger.info("OCR/spelling detector found %d issue(s).", len(issues))
            all_issues.extend(issues)

        pending, resolved, auto_decisions = self._apply_memory(all_issues)

        session = ReviewSession(
            session_id=uuid.uuid4().hex[:12],
            book_id=book.id,
            source_path=book.metadata.source_path,
            pending_issues=pending,
            resolved_issues=resolved,
            decisions=auto_decisions,
        )

        logger.info(
            "Review session created: %d total, %d auto-resolved, %d pending.",
            len(all_issues),
            len(resolved),
            len(pending),
        )

        book.add_audit(
            "review",
            "scan_complete",
            f"total={len(all_issues)}, auto_resolved={len(resolved)}, pending={len(pending)}",
        )

        return session

    def _apply_memory(
        self, issues: list[ReviewIssue],
    ) -> tuple[list[ReviewIssue], list[ReviewIssue], list[ReviewDecision]]:
        """
        Check each issue against persistent memory.

        Returns (pending_issues, auto_resolved_issues, auto_decisions).
        """
        pending: list[ReviewIssue] = []
        resolved: list[ReviewIssue] = []
        decisions: list[ReviewDecision] = []

        for issue in issues:
            decision = self._try_auto_resolve(issue)
            if decision is not None:
                issue.resolved = True
                resolved.append(issue)
                decisions.append(decision)
            else:
                pending.append(issue)

        return pending, resolved, decisions

    def _try_auto_resolve(self, issue: ReviewIssue) -> ReviewDecision | None:
        """Try to auto-resolve an issue from memory stores."""
        if issue.issue_type == IssueType.PUNCTUATION and self._punctuation_store:
            entry = self._punctuation_store.lookup(issue.original_fragment)
            if entry and entry.confirmed:
                return ReviewDecision(
                    issue_id=issue.id,
                    action=ReviewAction.ACCEPT,
                    original_fragment=issue.original_fragment,
                    final_fragment=entry.replacement,
                    user_note="auto-resolved from punctuation memory",
                )

        if issue.issue_type in (IssueType.OCR_ARTIFACT, IssueType.SPELLING) and self._correction_store:
            entry = self._correction_store.lookup(issue.original_fragment)
            if entry and entry.confirmed:
                return ReviewDecision(
                    issue_id=issue.id,
                    action=ReviewAction.ACCEPT,
                    original_fragment=issue.original_fragment,
                    final_fragment=entry.replacement,
                    user_note="auto-resolved from correction memory",
                )

        return None

    def apply_decisions_to_book(self, book: Book, session: ReviewSession) -> Book:
        """
        Apply all accept/custom decisions back to the book text.

        Modifies normalized_text of paragraphs in-place.
        """
        decision_map: dict[str, ReviewDecision] = {}
        for d in session.decisions:
            if d.action in (ReviewAction.ACCEPT, ReviewAction.CUSTOM):
                decision_map[d.issue_id] = d

        all_resolved = session.resolved_issues
        applied_count = 0

        for issue in all_resolved:
            decision = decision_map.get(issue.id)
            if decision is None:
                continue

            for chapter in book.chapters:
                if chapter.id != issue.chapter_id:
                    continue
                for para in chapter.paragraphs:
                    if para.id != issue.paragraph_id:
                        continue
                    old = para.normalized_text or para.raw_text
                    new = old.replace(decision.original_fragment, decision.final_fragment, 1)
                    if new != old:
                        para.normalized_text = new
                        applied_count += 1

        logger.info("Applied %d correction(s) to book text.", applied_count)
        book.add_audit("review", "apply_decisions", f"applied={applied_count}")
        return book
