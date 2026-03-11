"""Tests for core data models."""

from __future__ import annotations

from book_normalizer.models.book import Book, Chapter, Metadata, Paragraph, Segment
from book_normalizer.models.review import (
    AuditRecord,
    IssueSeverity,
    IssueType,
    ReviewAction,
    ReviewDecision,
    ReviewIssue,
    StressDecision,
)


class TestMetadata:
    def test_defaults(self) -> None:
        m = Metadata()
        assert m.title == "Untitled"
        assert m.author == "Unknown"
        assert m.language == "ru"

    def test_custom_values(self) -> None:
        m = Metadata(title="Война и мир", author="Толстой Л.Н.", year="1869")
        assert m.title == "Война и мир"
        assert m.year == "1869"


class TestParagraph:
    def test_auto_id(self) -> None:
        p = Paragraph(raw_text="Текст абзаца.")
        assert p.id
        assert len(p.id) == 12

    def test_stores_text(self) -> None:
        p = Paragraph(raw_text="Оригинал.", normalized_text="Нормализовано.")
        assert p.raw_text == "Оригинал."
        assert p.normalized_text == "Нормализовано."


class TestChapter:
    def test_raw_text_property(self) -> None:
        ch = Chapter(
            title="Test",
            paragraphs=[
                Paragraph(raw_text="Абзац 1."),
                Paragraph(raw_text="Абзац 2."),
            ],
        )
        assert "Абзац 1." in ch.raw_text
        assert "Абзац 2." in ch.raw_text

    def test_normalized_text_fallback(self) -> None:
        ch = Chapter(
            paragraphs=[
                Paragraph(raw_text="Raw.", normalized_text=""),
            ],
        )
        assert ch.normalized_text == "Raw."


class TestBook:
    def test_from_raw_text(self) -> None:
        book = Book.from_raw_text("Текст книги.", source_path="/tmp/test.txt")
        assert len(book.chapters) == 1
        assert book.chapters[0].paragraphs[0].raw_text == "Текст книги."
        assert book.metadata.source_format == "txt"

    def test_audit_trail(self) -> None:
        book = Book()
        book.add_audit("test_stage", "test_action", "details")
        assert len(book.audit_trail) == 1
        assert book.audit_trail[0]["stage"] == "test_stage"

    def test_raw_text_concatenation(self, sample_book: Book) -> None:
        full = sample_book.raw_text
        assert "Первый абзац." in full
        assert "Третий абзац." in full


class TestSegment:
    def test_defaults(self) -> None:
        s = Segment(text="слово")
        assert s.text == "слово"
        assert s.stress_form == ""


class TestReviewIssue:
    def test_creation(self) -> None:
        issue = ReviewIssue(
            issue_type=IssueType.PUNCTUATION,
            severity=IssueSeverity.LOW,
            original_fragment="тест,тест",
            suggested_fragment="тест, тест",
            confidence=0.9,
        )
        assert issue.issue_type == IssueType.PUNCTUATION
        assert issue.confidence == 0.9
        assert not issue.resolved


class TestReviewDecision:
    def test_creation(self) -> None:
        d = ReviewDecision(
            issue_id="abc123",
            action=ReviewAction.ACCEPT,
            original_fragment="old",
            final_fragment="new",
        )
        assert d.action == ReviewAction.ACCEPT


class TestStressDecision:
    def test_creation(self) -> None:
        sd = StressDecision(word="замок", stressed_form="за́мок", confirmed_by_user=True)
        assert sd.confirmed_by_user


class TestAuditRecord:
    def test_creation(self) -> None:
        r = AuditRecord(stage="loading", action="txt_load")
        assert r.stage == "loading"
        assert r.timestamp is not None
