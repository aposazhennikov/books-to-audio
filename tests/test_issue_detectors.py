"""Tests for issue detection modules."""

from __future__ import annotations

from book_normalizer.models.book import Book, Chapter, Paragraph
from book_normalizer.models.review import IssueType
from book_normalizer.review.issues import OcrSpellingDetector, PunctuationIssueDetector


def _make_book(text: str) -> Book:
    """Create a minimal book with a single paragraph containing the given text."""
    para = Paragraph(raw_text=text, normalized_text=text, index_in_chapter=0)
    ch = Chapter(title="Test", index=0, paragraphs=[para])
    return Book(chapters=[ch])


class TestPunctuationIssueDetector:
    def test_missing_space_after_comma(self) -> None:
        book = _make_book("слово,слово")
        detector = PunctuationIssueDetector()
        issues = detector.detect(book)
        assert len(issues) >= 1
        assert any(i.issue_type == IssueType.PUNCTUATION for i in issues)

    def test_repeated_comma(self) -> None:
        book = _make_book("слово,,слово")
        detector = PunctuationIssueDetector()
        issues = detector.detect(book)
        assert any(
            "comma" in (i.suggested_fragment or i.original_fragment)
            or i.original_fragment == ",,"
            for i in issues
        )

    def test_space_before_comma(self) -> None:
        book = _make_book("слово , слово")
        detector = PunctuationIssueDetector()
        issues = detector.detect(book)
        assert len(issues) >= 1

    def test_clean_text_no_issues(self) -> None:
        book = _make_book("Чистый текст, без проблем.")
        detector = PunctuationIssueDetector()
        issues = detector.detect(book)
        assert len(issues) == 0

    def test_two_dots(self) -> None:
        book = _make_book("Текст.. ещё текст.")
        detector = PunctuationIssueDetector()
        issues = detector.detect(book)
        assert any(i.original_fragment == ".." for i in issues)

    def test_context_is_populated(self) -> None:
        book = _make_book("Длинный текст слово,слово ещё текст.")
        detector = PunctuationIssueDetector()
        issues = detector.detect(book)
        assert len(issues) >= 1
        issue = issues[0]
        assert issue.context_before or issue.context_after
        assert issue.chapter_id
        assert issue.paragraph_id


class TestOcrSpellingDetector:
    def test_mixed_script(self) -> None:
        book = _make_book("Пpимер")
        detector = OcrSpellingDetector()
        issues = detector.detect(book)
        assert any(i.issue_type == IssueType.OCR_ARTIFACT for i in issues)

    def test_digit_in_cyrillic_word(self) -> None:
        book = _make_book("сл0во")
        detector = OcrSpellingDetector()
        issues = detector.detect(book)
        assert any(i.issue_type == IssueType.OCR_ARTIFACT for i in issues)

    def test_digit_in_cyrillic_word_suggestion_word_level(self) -> None:
        book = _make_book("Он ска3ал правду.")
        detector = OcrSpellingDetector()
        issues = detector.detect(book)
        assert any(i.original_fragment == "ска3ал" and i.suggested_fragment == "сказал" for i in issues)

    def test_digit_in_cyrillic_word_suggestion_m0skva(self) -> None:
        book = _make_book("Мы поехали в м0сква.")
        detector = OcrSpellingDetector()
        issues = detector.detect(book)
        assert any(i.original_fragment == "м0сква" and i.suggested_fragment == "москва" for i in issues)

    def test_multiple_digits_single_issue_m0l0k0(self) -> None:
        book = _make_book("Это м0л0к0 очень вкусное.")
        detector = OcrSpellingDetector()
        issues = detector.detect(book)
        matches = [i for i in issues if i.original_fragment == "м0л0к0"]
        assert len(matches) == 1
        assert matches[0].suggested_fragment == "молоко"

    def test_digit_at_start_and_end_detected(self) -> None:
        book = _make_book("0тдельный случай и молок0.")
        detector = OcrSpellingDetector()
        issues = detector.detect(book)
        originals = {i.original_fragment for i in issues if i.issue_type == IssueType.OCR_ARTIFACT}
        assert "0тдельный" in originals
        assert "молок0" in originals

    def test_repeated_same_ocr_token_two_issues(self) -> None:
        book = _make_book("Он ска3ал и ещё раз ска3ал.")
        detector = OcrSpellingDetector()
        issues = detector.detect(book)
        matches = [i for i in issues if i.original_fragment == "ска3ал"]
        assert len(matches) == 2

    def test_clean_text_no_issues(self) -> None:
        book = _make_book("Чистый русский текст без артефактов.")
        detector = OcrSpellingDetector()
        issues = detector.detect(book)
        assert len(issues) == 0

    def test_suspicious_consonant_run(self) -> None:
        book = _make_book("абвгджзк текст")
        detector = OcrSpellingDetector()
        issues = detector.detect(book)
        assert any(i.issue_type == IssueType.SPELLING for i in issues)

    def test_transliterate_suggestion(self) -> None:
        detector = OcrSpellingDetector()
        result = detector._transliterate_to_cyrillic("a")
        assert result == "\u0430"
