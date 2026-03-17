from pathlib import Path

from book_normalizer.memory.correction_store import CorrectionStore
from book_normalizer.models.book import Book, Chapter, Paragraph
from book_normalizer.models.memory import CorrectionMemoryEntry
from book_normalizer.models.review import IssueSeverity, IssueType, ReviewIssue
from book_normalizer.review.reviewer import Reviewer
from book_normalizer.review.session import ReviewDecision, ReviewSession


def _make_book(text: str) -> Book:
    para = Paragraph(raw_text=text, normalized_text=text, index_in_chapter=0)
    ch = Chapter(title="Test", index=0, paragraphs=[para])
    return Book(chapters=[ch])


def test_numeric_tokens_are_not_auto_corrected(tmp_path: Path) -> None:
    store = CorrectionStore(tmp_path / "corrections.json")
    # Risky entry: naive "0" -> "о" should not be auto-applied.
    store.add(
        CorrectionMemoryEntry(
            original="0",
            replacement="о",
            confirmed=True,
            issue_type="ocr_artifact",
            token="0",
            normalized_token="0",
            auto_apply_safe=False,
        )
    )

    text = "Год 2020. Всего 30 примеров. Глава 3. 1.2. Раздел."
    book = _make_book(text)
    reviewer = Reviewer(correction_store=store, skip_punctuation=True, skip_spellcheck=False)
    session = reviewer.scan(book)

    # No issues should be auto-resolved by this unsafe memory.
    assert session.resolved_count == 0


def test_word_level_ocr_corrections_still_possible(tmp_path: Path) -> None:
    store = CorrectionStore(tmp_path / "corrections.json")
    store.add(
        CorrectionMemoryEntry(
            original="м0сква",
            replacement="москва",
            confirmed=True,
            issue_type="ocr_artifact",
            token="м0сква",
            normalized_token="м0сква",
            auto_apply_safe=True,
        )
    )

    text = "Мы приехали в м0сква."
    book = _make_book(text)

    # Manually construct an issue that matches the stored entry.
    para = book.chapters[0].paragraphs[0]
    issue = ReviewIssue(
        issue_type=IssueType.OCR_ARTIFACT,
        severity=IssueSeverity.HIGH,
        original_fragment="м0сква",
        suggested_fragment="москва",
        chapter_id=book.chapters[0].id,
        paragraph_id=para.id,
    )

    reviewer = Reviewer(correction_store=store, skip_punctuation=True, skip_spellcheck=True)
    pending, resolved, decisions = reviewer._apply_memory([issue])  # type: ignore[attr-defined]

    assert len(resolved) == 1
    assert isinstance(decisions[0], ReviewDecision)
    assert decisions[0].final_fragment == "москва"


def test_word_level_digit_substitution_not_global(tmp_path: Path) -> None:
    store = CorrectionStore(tmp_path / "corrections.json")
    store.add(
        CorrectionMemoryEntry(
            original="ска3ал",
            replacement="сказал",
            confirmed=True,
            issue_type="ocr_artifact",
            token="ска3ал",
            normalized_token="ска3ал",
            auto_apply_safe=True,
        )
    )

    text = "Он ска3ал правду. В 2020 году было 3 варианта."
    book = _make_book(text)
    para = book.chapters[0].paragraphs[0]

    issue_word = ReviewIssue(
        issue_type=IssueType.OCR_ARTIFACT,
        severity=IssueSeverity.HIGH,
        original_fragment="ска3ал",
        suggested_fragment="сказал",
        chapter_id=book.chapters[0].id,
        paragraph_id=para.id,
    )

    reviewer = Reviewer(correction_store=store, skip_punctuation=True, skip_spellcheck=True)
    _, resolved, decisions = reviewer._apply_memory([issue_word])  # type: ignore[attr-defined]

    assert len(resolved) == 1
    assert decisions[0].final_fragment == "сказал"

