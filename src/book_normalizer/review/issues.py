"""Issue detection modules that scan text and produce ReviewIssue objects."""

from __future__ import annotations

import re
from typing import Protocol

from book_normalizer.models.book import Book, Chapter, Paragraph
from book_normalizer.models.review import IssueSeverity, IssueType, ReviewIssue
from book_normalizer.normalization.yoficator import collect_yo_suggestions


class IssueDetector(Protocol):
    """Protocol for issue detection plugins."""

    def detect(self, book: Book) -> list[ReviewIssue]:
        """Scan the book and return a list of detected issues."""
        ...


def _extract_context(text: str, start: int, end: int, window: int = 40) -> tuple[str, str]:
    """Extract context strings around a match position."""
    ctx_before = text[max(0, start - window):start]
    ctx_after = text[end:end + window]
    return ctx_before, ctx_after


class PunctuationIssueDetector:
    """
    Detect suspicious punctuation patterns in Russian text.

    Catches things like:
    - Missing space after punctuation.
    - Double punctuation marks.
    - Space before punctuation.
    - Mismatched quotes.
    """

    _PATTERNS: list[tuple[re.Pattern[str], str, str, float]] = [
        (
            re.compile(r"[а-яёА-ЯЁ][,.:;][а-яёА-ЯЁ]"),
            "Missing space after punctuation mark.",
            "medium",
            0.85,
        ),
        (
            re.compile(r"[,]{2,}"),
            "Repeated comma.",
            "high",
            0.95,
        ),
        (
            re.compile(r"[.]{2}(?![.])"),
            "Exactly two dots (likely broken ellipsis).",
            "medium",
            0.80,
        ),
        (
            re.compile(r"\s[,.:;!?]"),
            "Space before punctuation mark.",
            "low",
            0.75,
        ),
        (
            re.compile(r"[!?]{3,}"),
            "Excessive exclamation/question marks.",
            "low",
            0.70,
        ),
    ]

    def detect(self, book: Book) -> list[ReviewIssue]:
        """Scan normalized text for punctuation anomalies."""
        issues: list[ReviewIssue] = []

        for chapter in book.chapters:
            for para in chapter.paragraphs:
                text = para.normalized_text or para.raw_text
                if not text:
                    continue

                for pattern, description, severity_str, confidence in self._PATTERNS:
                    for match in pattern.finditer(text):
                        fragment = match.group()
                        ctx_before, ctx_after = _extract_context(text, match.start(), match.end())
                        suggested = self._suggest_fix(fragment, description)

                        issues.append(
                            ReviewIssue(
                                issue_type=IssueType.PUNCTUATION,
                                severity=IssueSeverity(severity_str),
                                original_fragment=fragment,
                                suggested_fragment=suggested,
                                context_before=ctx_before,
                                context_after=ctx_after,
                                chapter_id=chapter.id,
                                paragraph_id=para.id,
                                confidence=confidence,
                            )
                        )

        return issues

    @staticmethod
    def _suggest_fix(fragment: str, description: str) -> str:
        """Generate a naive fix suggestion based on the issue type."""
        if "Missing space after" in description:
            for punct in ",.;:":
                if punct in fragment:
                    return fragment.replace(punct, punct + " ")
        if "Space before punctuation" in description:
            return fragment.strip()
        if "Repeated comma" in description:
            return ","
        if "two dots" in description:
            return "\u2026"
        return fragment


class OcrSpellingDetector:
    """
    Detect probable OCR artifacts and common misspellings in Russian text.

    Uses pattern-based heuristics to find:
    - Latin characters mixed with Cyrillic.
    - Common OCR substitution pairs (e.g. 0 for O, l for I).
    - Suspicious character sequences unlikely in Russian.
    """

    _MIXED_SCRIPT = re.compile(r"[а-яёА-ЯЁ][a-zA-Z]|[a-zA-Z][а-яёА-ЯЁ]")

    _OCR_SUBSTITUTIONS: dict[str, tuple[str, str]] = {
        "0": ("\u043e", "\u041e"),  # о / О
        "3": ("\u0437", "\u0417"),  # з / З
        "6": ("\u0431", "\u0411"),  # б / Б
    }

    _SUSPICIOUS_SEQUENCES = re.compile(
        r"[бвгджзклмнпрстфхцчшщ]{5,}"
        r"|[аеёиоуыэюя]{5,}",
        re.IGNORECASE,
    )

    def detect(self, book: Book) -> list[ReviewIssue]:
        """Scan normalized text for OCR artifacts and spelling issues."""
        issues: list[ReviewIssue] = []

        for chapter in book.chapters:
            for para in chapter.paragraphs:
                text = para.normalized_text or para.raw_text
                if not text:
                    continue

                issues.extend(self._detect_mixed_script(text, chapter, para))
                issues.extend(self._detect_ocr_substitutions(text, chapter, para))
                issues.extend(self._detect_suspicious_sequences(text, chapter, para))

        return issues

    def _detect_mixed_script(
        self, text: str, chapter: Chapter, para: Paragraph,
    ) -> list[ReviewIssue]:
        """Find mixed Cyrillic/Latin character sequences."""
        results: list[ReviewIssue] = []
        for match in self._MIXED_SCRIPT.finditer(text):
            ctx_before, ctx_after = _extract_context(text, match.start(), match.end())

            results.append(
                ReviewIssue(
                    issue_type=IssueType.OCR_ARTIFACT,
                    severity=IssueSeverity.HIGH,
                    original_fragment=match.group(),
                    suggested_fragment=self._transliterate_to_cyrillic(match.group()),
                    context_before=ctx_before,
                    context_after=ctx_after,
                    chapter_id=chapter.id,
                    paragraph_id=para.id,
                    confidence=0.85,
                )
            )
        return results

    def _detect_ocr_substitutions(
        self, text: str, chapter: Chapter, para: Paragraph,
    ) -> list[ReviewIssue]:
        """Find digit-for-letter OCR substitutions inside words (token-based)."""
        results: list[ReviewIssue] = []
        # Tokenize into Cyrillic+digit chunks and everything else.
        token_re = re.compile(r"[А-Яа-яЁё0-9\-]+|[^А-Яа-яЁё0-9\-]+")

        for match in token_re.finditer(text):
            token = match.group(0)
            start, end = match.start(), match.end()

            if not self._is_suspicious_ocr_token_for_issue(token):
                continue

            fixed = self._correct_ocr_token(token)
            if fixed == token:
                continue

            ctx_before, ctx_after = _extract_context(text, start, end)
            results.append(
                ReviewIssue(
                    issue_type=IssueType.OCR_ARTIFACT,
                    severity=IssueSeverity.HIGH,
                    original_fragment=token,
                    suggested_fragment=fixed,
                    context_before=ctx_before,
                    context_after=ctx_after,
                    chapter_id=chapter.id,
                    paragraph_id=para.id,
                    confidence=0.80,
                )
            )

        return results

    def _is_suspicious_ocr_token_for_issue(self, token: str) -> bool:
        """Detect tokens that likely contain digit-for-letter OCR substitutions."""
        has_digit = any(ch.isdigit() for ch in token)
        has_cyr = any("\u0400" <= ch <= "\u04FF" for ch in token)
        if not (has_digit and has_cyr):
            return False

        core = token.replace("-", "").replace("'", "")
        if not core:
            return False
        for ch in core:
            if not (ch.isdigit() or ("\u0400" <= ch <= "\u04FF")):
                return False
        return len(core) >= 2

    def _correct_ocr_token(self, token: str) -> str:
        """Return a canonical corrected form for an OCR-corrupted token."""
        chars: list[str] = list(token)
        changed = False
        for i, ch in enumerate(chars):
            if ch not in self._OCR_SUBSTITUTIONS:
                continue
            # Only treat as OCR substitution if neighbor is Cyrillic.
            left_cyr = i > 0 and ("\u0400" <= chars[i - 1] <= "\u04FF")
            right_cyr = i + 1 < len(chars) and ("\u0400" <= chars[i + 1] <= "\u04FF")
            if not (left_cyr or right_cyr):
                continue
            lower, upper = self._OCR_SUBSTITUTIONS[ch]
            if ch.isdigit():
                # Preserve case based on neighbors if possible.
                use_upper = (
                    (i > 0 and chars[i - 1].isupper())
                    or (i + 1 < len(chars) and chars[i + 1].isupper())
                )
                chars[i] = upper if use_upper else lower
                changed = True
        return "".join(chars) if changed else token

    def _detect_suspicious_sequences(
        self, text: str, chapter: Chapter, para: Paragraph,
    ) -> list[ReviewIssue]:
        """Find suspiciously long consonant-only or vowel-only runs."""
        results: list[ReviewIssue] = []
        for match in self._SUSPICIOUS_SEQUENCES.finditer(text):
            ctx_before, ctx_after = _extract_context(text, match.start(), match.end())
            results.append(
                ReviewIssue(
                    issue_type=IssueType.SPELLING,
                    severity=IssueSeverity.MEDIUM,
                    original_fragment=match.group(),
                    suggested_fragment="",
                    context_before=ctx_before,
                    context_after=ctx_after,
                    chapter_id=chapter.id,
                    paragraph_id=para.id,
                    confidence=0.60,
                )
            )
        return results

    @staticmethod
    def _transliterate_to_cyrillic(text: str) -> str:
        """Best-effort transliteration of Latin lookalikes to Cyrillic."""
        transliteration_map = {
            "a": "\u0430", "A": "\u0410",
            "e": "\u0435", "E": "\u0415",
            "o": "\u043e", "O": "\u041e",
            "p": "\u0440", "P": "\u0420",
            "c": "\u0441", "C": "\u0421",
            "x": "\u0445", "X": "\u0425",
            "H": "\u041d",
            "K": "\u041a",
            "M": "\u041c",
            "T": "\u0422",
            "B": "\u0412",
            "y": "\u0443",
        }
        return "".join(transliteration_map.get(ch, ch) for ch in text)


class YoAmbiguityDetector:
    """Detect peyo not_safe ё suggestions for user review."""

    def detect(self, book: Book) -> list[ReviewIssue]:
        """Scan normalized text for ambiguous ё candidates."""
        issues: list[ReviewIssue] = []

        for chapter in book.chapters:
            for para in chapter.paragraphs:
                text = para.normalized_text or para.raw_text
                if not text:
                    continue

                for suggestion in collect_yo_suggestions(text):
                    start = suggestion.index
                    end = start + len(suggestion.before)
                    if text[start:end] != suggestion.before:
                        found_at = text.find(suggestion.before, max(0, start - 10))
                        if found_at < 0:
                            continue
                        start = found_at
                        end = start + len(suggestion.before)

                    ctx_before, ctx_after = _extract_context(text, start, end)
                    issues.append(
                        ReviewIssue(
                            issue_type=IssueType.YOFICATION,
                            severity=IssueSeverity.LOW,
                            original_fragment=suggestion.before,
                            suggested_fragment=suggestion.after,
                            context_before=ctx_before,
                            context_after=ctx_after,
                            chapter_id=chapter.id,
                            paragraph_id=para.id,
                            confidence=0.55,
                        )
                    )

        return issues
