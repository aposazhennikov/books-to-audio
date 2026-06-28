"""Text preservation validator for LLM-based normalization.

After an LLM corrects a text passage (grammar, punctuation, yofication),
this module verifies that the LLM did NOT significantly alter the content.
This is the primary defence against hallucination.

Three checks are performed:
1. Character-level similarity (difflib SequenceMatcher) — catches rewrites.
2. Word count ratio — catches additions / deletions of sentences.
3. Sentence count ratio — catches paragraph merges / splits.

Usage::

    validator = TextPreservationValidator()
    result = validator.validate(original_text, llm_output_text)
    if result.is_valid:
        use_corrected_text(result.corrected)
    else:
        keep_original(original_text)
        log_issues(result.issues)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from book_normalizer.normalization.whitespace import repair_pdf_split_russian_words

logger = logging.getLogger(__name__)


# ── Validation result ─────────────────────────────────────────────────────────


@dataclass
class ValidationResult:
    """Outcome of a text preservation check."""

    is_valid: bool
    similarity: float          # 0–1, char-level SequenceMatcher ratio
    word_ratio: float          # corrected_words / original_words
    sentence_ratio: float      # corrected_sentences / original_sentences
    original: str
    corrected: str
    issues: list[str] = field(default_factory=list)

    @property
    def accepted_text(self) -> str:
        """Return corrected text if valid, else the original."""
        return self.corrected if self.is_valid else self.original


# ── Validator ─────────────────────────────────────────────────────────────────


class TextPreservationValidator:
    """Validate that LLM output is a conservative correction of the input.

    All thresholds are configurable.  The defaults are tuned for typical
    LLM grammar/punctuation/yofication corrections of Russian prose.

    Args:
        min_similarity:     Minimum SequenceMatcher ratio (default 0.82).
        min_word_ratio:     Minimum corrected/original word count ratio (0.88).
        max_word_ratio:     Maximum corrected/original word count ratio (1.12).
        min_sentence_ratio: Minimum sentence count ratio (0.80).
        max_sentence_ratio: Maximum sentence count ratio (1.20).
    """

    def __init__(
        self,
        min_similarity: float = 0.82,
        min_word_ratio: float = 0.88,
        max_word_ratio: float = 1.12,
        min_sentence_ratio: float = 0.80,
        max_sentence_ratio: float = 1.20,
    ) -> None:
        self._min_sim = min_similarity
        self._min_wr = min_word_ratio
        self._max_wr = max_word_ratio
        self._min_sr = min_sentence_ratio
        self._max_sr = max_sentence_ratio

    def validate(self, original: str, corrected: str) -> ValidationResult:
        """Run all checks and return a ValidationResult.

        Args:
            original:  The text before LLM correction.
            corrected: The text returned by the LLM.

        Returns:
            A ValidationResult whose ``is_valid`` flag indicates whether the
            corrected text is safe to use.  ``accepted_text`` returns the
            corrected text on success, the original on failure.
        """
        issues: list[str] = []

        # Guard: if LLM returned empty string, always reject.
        if not corrected or not corrected.strip():
            return ValidationResult(
                is_valid=False,
                similarity=0.0,
                word_ratio=0.0,
                sentence_ratio=0.0,
                original=original,
                corrected=corrected,
                issues=["LLM returned empty text"],
            )

        similarity = _char_similarity(original, corrected)
        word_ratio = _word_ratio(original, corrected)
        sentence_ratio = _sentence_ratio(original, corrected)

        if similarity < self._min_sim:
            issues.append(
                f"Similarity too low: {similarity:.3f} < {self._min_sim:.3f}"
            )
        if word_ratio < self._min_wr:
            issues.append(
                f"Too many words removed: ratio {word_ratio:.3f} < {self._min_wr:.3f}"
            )
        if word_ratio > self._max_wr:
            issues.append(
                f"Too many words added: ratio {word_ratio:.3f} > {self._max_wr:.3f}"
            )
        if sentence_ratio < self._min_sr:
            issues.append(
                f"Too many sentences removed: ratio {sentence_ratio:.3f} < {self._min_sr:.3f}"
            )
        if sentence_ratio > self._max_sr:
            issues.append(
                f"Too many sentences added: ratio {sentence_ratio:.3f} > {self._max_sr:.3f}"
            )
        issues.extend(_punctuation_structure_issues(original, corrected))

        # When there are issues, also report word-level statistics and a few
        # concrete mismatches to aid debugging.
        if issues:
            orig_words = _words(original)
            corr_words = _words(corrected)
            issues.append(
                f"Word counts: original={len(orig_words)}, corrected={len(corr_words)}"
            )

            # Find a few example positions where words differ.
            mismatches: list[str] = []
            max_examples = 5
            for idx, (ow, cw) in enumerate(zip(orig_words, corr_words)):
                if ow == cw:
                    continue
                # Allow translation of standalone Latin words into Cyrillic.
                if _LATIN_RE.match(ow) and _CYRILLIC_RE.match(cw):
                    continue
                mismatches.append(f"{idx}: '{ow}' -> '{cw}'")
                if len(mismatches) >= max_examples:
                    break

            # Handle extra trailing words on either side.
            if len(orig_words) > len(corr_words):
                extra = orig_words[len(corr_words) : len(corr_words) + max_examples]
                if extra:
                    extra_str = ", ".join(f"'{w}'" for w in extra)
                    mismatches.append(
                        f"extra original words starting at {len(corr_words)}: {extra_str}"
                    )
            elif len(corr_words) > len(orig_words):
                extra = corr_words[len(orig_words) : len(orig_words) + max_examples]
                if extra:
                    extra_str = ", ".join(f"'{w}'" for w in extra)
                    mismatches.append(
                        f"extra corrected words starting at {len(orig_words)}: {extra_str}"
                    )

            if mismatches:
                msg = "Word mismatches: " + "; ".join(mismatches)
                issues.append(msg)
                logger.debug(
                    "Text preservation mismatches for paragraph: %s",
                    msg,
                )

        return ValidationResult(
            is_valid=not issues,
            similarity=similarity,
            word_ratio=word_ratio,
            sentence_ratio=sentence_ratio,
            original=original,
            corrected=corrected,
            issues=issues,
        )

    def validate_batch(
        self,
        originals: list[str],
        corrected_list: list[str],
    ) -> list[ValidationResult]:
        """Validate multiple (original, corrected) pairs."""
        return [
            self.validate(orig, corr)
            for orig, corr in zip(originals, corrected_list)
        ]


# ── Helper functions ──────────────────────────────────────────────────────────


_WORD_RE = re.compile(r"\w+", re.UNICODE)
_SENTENCE_END_RE = re.compile(r"[.!?…]+\s+|\n")
_OBVIOUS_PUNCTUATION_ARTIFACT_RE = re.compile(r",,{1,}|[;:]{2,}|[!?]{4,}|\.{4,}")
_DIALOGUE_DASH_RE = re.compile(r"(^|[\n\r\s])[—–-]\s*(?=\S)")
_QUOTE_CHARS = "\"'«»“”„"


def _char_similarity(a: str, b: str) -> float:
    """Return SequenceMatcher similarity ratio ignoring punctuation.

    Punctuation-only changes (commas, dots, dashes, quotes) should not
    drastically reduce the similarity score, so we strip them out before
    computing the ratio. Word and sentence ratios still guard against
    additions / deletions of content.
    """
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0

    # Remove common punctuation that we allow the LLM to adjust freely.
    punctuation = r"""[.,;:!?\"'«»“”„–—\-()\[\]{}]"""
    a_stripped = re.sub(punctuation, "", a).lower()
    b_stripped = re.sub(punctuation, "", b).lower()

    if not a_stripped and not b_stripped:
        # Texts differ only by punctuation.
        return 1.0
    if not a_stripped or not b_stripped:
        return 0.0

    return SequenceMatcher(None, a_stripped, b_stripped).ratio()


def _word_count(text: str) -> int:
    """Count words using Unicode word boundary pattern."""
    return len(_WORD_RE.findall(repair_pdf_split_russian_words(text)))


def _words(text: str) -> list[str]:
    """Tokenise text into words (case-insensitive) using the same pattern as _word_count."""
    return [w.lower() for w in _WORD_RE.findall(repair_pdf_split_russian_words(text))]


_LATIN_RE = re.compile(r"^[A-Za-z]+$")
_CYRILLIC_RE = re.compile(r"^[А-Яа-яЁё]+$")


def _word_ratio(original: str, corrected: str) -> float:
    """Return corrected_word_count / original_word_count."""
    orig_count = _word_count(original)
    if orig_count == 0:
        return 1.0
    return _word_count(corrected) / orig_count


def _sentence_count(text: str) -> int:
    """Estimate sentence count by splitting on sentence-ending punctuation."""
    parts = [p.strip() for p in _SENTENCE_END_RE.split(text) if p.strip()]
    return max(1, len(parts))


def _sentence_ratio(original: str, corrected: str) -> float:
    """Return corrected_sentence_count / original_sentence_count."""
    orig = _sentence_count(original)
    if orig == 0:
        return 1.0
    return _sentence_count(corrected) / orig


def _punctuation_structure_issues(original: str, corrected: str) -> list[str]:
    """Return issues for punctuation changes that break audiobook structure.

    The validator allows small punctuation edits, but direct-speech boundaries
    are structural data for casting and TTS. A result with repeated commas or
    changed dialogue/quote marker counts is unsafe even when words are preserved.
    """
    issues: list[str] = []

    artifact = _OBVIOUS_PUNCTUATION_ARTIFACT_RE.search(corrected)
    if artifact:
        issues.append(f"Suspicious punctuation artifact introduced: {artifact.group()!r}")

    original_dialogue_dashes = len(_DIALOGUE_DASH_RE.findall(original))
    corrected_dialogue_dashes = len(_DIALOGUE_DASH_RE.findall(corrected))
    if original_dialogue_dashes and original_dialogue_dashes != corrected_dialogue_dashes:
        issues.append(
            "Dialogue dash count changed: "
            f"original={original_dialogue_dashes}, corrected={corrected_dialogue_dashes}"
        )

    original_quotes = _count_quote_markers(original)
    corrected_quotes = _count_quote_markers(corrected)
    if original_quotes and original_quotes != corrected_quotes:
        issues.append(
            f"Quote marker count changed: original={original_quotes}, corrected={corrected_quotes}"
        )

    return issues


def _count_quote_markers(text: str) -> int:
    return sum(1 for char in text if char in _QUOTE_CHARS)
