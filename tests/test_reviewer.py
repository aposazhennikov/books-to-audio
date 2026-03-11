"""Tests for the reviewer orchestrator."""

from __future__ import annotations

from pathlib import Path

from book_normalizer.memory.correction_store import CorrectionStore
from book_normalizer.memory.punctuation_store import PunctuationStore
from book_normalizer.models.book import Book, Chapter, Paragraph
from book_normalizer.models.memory import CorrectionMemoryEntry, PunctuationMemoryEntry
from book_normalizer.models.review import IssueType, ReviewAction, ReviewDecision
from book_normalizer.review.reviewer import Reviewer
from book_normalizer.review.session import ReviewSession


def _make_book_with_issues() -> Book:
    """Create a book with text containing known detectable issues."""
    para = Paragraph(
        raw_text="Слово,слово и сл0во.",
        normalized_text="Слово,слово и сл0во.",
        index_in_chapter=0,
    )
    ch = Chapter(title="Test", index=0, paragraphs=[para])
    return Book(chapters=[ch])


def _make_clean_book() -> Book:
    """Create a book with clean text."""
    para = Paragraph(
        raw_text="Чистый текст, без проблем.",
        normalized_text="Чистый текст, без проблем.",
        index_in_chapter=0,
    )
    ch = Chapter(title="Test", index=0, paragraphs=[para])
    return Book(chapters=[ch])


class TestReviewer:
    def test_scan_finds_issues(self) -> None:
        book = _make_book_with_issues()
        reviewer = Reviewer(skip_punctuation=False, skip_spellcheck=False)
        session = reviewer.scan(book)
        assert session.pending_count > 0

    def test_scan_clean_book(self) -> None:
        book = _make_clean_book()
        reviewer = Reviewer(skip_punctuation=False, skip_spellcheck=False)
        session = reviewer.scan(book)
        assert session.pending_count == 0

    def test_skip_flags(self) -> None:
        book = _make_book_with_issues()
        reviewer = Reviewer(skip_punctuation=True, skip_spellcheck=True)
        session = reviewer.scan(book)
        assert session.pending_count == 0

    def test_auto_resolve_from_memory(self, tmp_path: Path) -> None:
        punct_store = PunctuationStore(tmp_path / "punct.json")
        punct_store.add(
            PunctuationMemoryEntry(original="о,с", replacement="о, с", confirmed=True)
        )

        book = _make_book_with_issues()
        reviewer = Reviewer(
            punctuation_store=punct_store,
            skip_punctuation=False,
            skip_spellcheck=True,
        )
        session = reviewer.scan(book)

        auto_resolved = [i for i in session.resolved_issues if i.resolved]
        assert len(auto_resolved) >= 1

    def test_apply_decisions_to_book(self) -> None:
        para = Paragraph(
            id="p1",
            raw_text="Слово,слово.",
            normalized_text="Слово,слово.",
            index_in_chapter=0,
        )
        ch = Chapter(id="ch1", title="Test", index=0, paragraphs=[para])
        book = Book(chapters=[ch])

        session = ReviewSession(
            resolved_issues=[],
            decisions=[
                ReviewDecision(
                    issue_id="i1",
                    action=ReviewAction.ACCEPT,
                    original_fragment="о,с",
                    final_fragment="о, с",
                )
            ],
        )

        from book_normalizer.models.review import ReviewIssue, IssueSeverity

        resolved_issue = ReviewIssue(
            id="i1",
            issue_type=IssueType.PUNCTUATION,
            severity=IssueSeverity.MEDIUM,
            original_fragment="о,с",
            chapter_id="ch1",
            paragraph_id="p1",
            resolved=True,
        )
        session.resolved_issues.append(resolved_issue)

        reviewer = Reviewer()
        reviewer.apply_decisions_to_book(book, session)
        assert "о, с" in para.normalized_text

    def test_audit_trail_after_scan(self) -> None:
        book = _make_book_with_issues()
        reviewer = Reviewer(skip_punctuation=False, skip_spellcheck=False)
        reviewer.scan(book)
        assert any(r["stage"] == "review" for r in book.audit_trail)
