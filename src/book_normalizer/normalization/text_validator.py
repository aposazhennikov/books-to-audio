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
        issues.extend(_word_substitution_issues(original, corrected))
        issues.extend(_capitalization_issues(original, corrected))

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
_WORD_SPAN_RE = re.compile(r"\w+", re.UNICODE)
_SENTENCE_END_RE = re.compile(r"[.!?…]+(?:\s+|$)")
_PDF_PARENTHESIS_SPLIT_RE = re.compile(r"([А-ЯЁа-яё])\([ \t\r\n]+([А-ЯЁа-яё])")
_OBVIOUS_PUNCTUATION_ARTIFACT_RE = re.compile(r",,{1,}|[;:]{2,}|[!?]{4,}|\.{4,}")
_DIALOGUE_DASH_RE = re.compile(r"(^|[\n\r\s])[—–-]\s*(?=\S)")
_IN_WORD_HYPHEN_WRAP_RE = re.compile(r"[А-ЯЁа-яё]-\s+[А-ЯЁа-яё]")
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

    a = _canonical_text_for_validation(a)
    b = _canonical_text_for_validation(b)

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
    return len(_WORD_RE.findall(_canonical_text_for_validation(text)))


def _words(text: str) -> list[str]:
    """Tokenise text into words (case-insensitive) using the same pattern as _word_count."""
    return [w.lower() for w in _WORD_RE.findall(_canonical_text_for_validation(text))]


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
    text = _canonical_text_for_validation(text)
    parts = [p.strip() for p in _SENTENCE_END_RE.split(text) if p.strip()]
    return max(1, len(parts))


def _canonical_text_for_validation(text: str) -> str:
    """Normalize layout-only OCR artifacts before preservation metrics."""

    text = _PDF_PARENTHESIS_SPLIT_RE.sub(r"\1\2", text or "")
    text = repair_pdf_split_russian_words(text)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


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

    hyphen_wrap = _IN_WORD_HYPHEN_WRAP_RE.search(corrected)
    if hyphen_wrap:
        issues.append(f"In-word hyphenated line wrap introduced: {hyphen_wrap.group()!r}")

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


def _word_substitution_issues(original: str, corrected: str) -> list[str]:
    """Reject non-mechanical word substitutions after OCR canonicalization."""

    orig_words = _words(original)
    corr_words = _words(corrected)
    if len(orig_words) != len(corr_words):
        return []
    changed: list[str] = []
    for index, (original_word, corrected_word) in enumerate(zip(orig_words, corr_words)):
        if _words_equivalent_for_minimal_correction(original_word, corrected_word):
            continue
        changed.append(f"{index}: '{original_word}' -> '{corrected_word}'")
        if len(changed) >= 5:
            break
    if not changed:
        return []
    return ["Unexpected word substitution after OCR normalization: " + "; ".join(changed)]


def _capitalization_issues(original: str, corrected: str) -> list[str]:
    """Reject unsafe case-only edits inside a sentence.

    Heading starts such as ``1. вход`` -> ``1. Вход`` are safe, but changing
    ``тром`` -> ``Тром`` in the middle of prose is usually a model guess and
    can alter pronunciation, role detection, or character/name handling.
    """

    original_text = _canonical_text_for_validation(original)
    corrected_text = _canonical_text_for_validation(corrected)
    original_tokens = list(_WORD_SPAN_RE.finditer(original_text))
    corrected_tokens = list(_WORD_SPAN_RE.finditer(corrected_text))
    if len(original_tokens) != len(corrected_tokens):
        return []

    changed: list[str] = []
    for index, (original_match, corrected_match) in enumerate(zip(original_tokens, corrected_tokens)):
        original_word = original_match.group()
        corrected_word = corrected_match.group()
        if original_word == corrected_word:
            continue
        if original_word.casefold().replace("ё", "е") != corrected_word.casefold().replace("ё", "е"):
            continue
        if not _is_lower_to_uppercase_guess(original_word, corrected_word):
            continue
        if _is_phrase_start(corrected_text, corrected_match.start()):
            continue
        changed.append(f"{index}: '{original_word}' -> '{corrected_word}'")
        if len(changed) >= 5:
            break
    if not changed:
        return []
    return ["Unsafe mid-sentence capitalization: " + "; ".join(changed)]


def _is_lower_to_uppercase_guess(original_word: str, corrected_word: str) -> bool:
    return (
        original_word[:1].islower()
        and corrected_word[:1].isupper()
        and original_word[1:].casefold() == corrected_word[1:].casefold()
    )


def _is_phrase_start(text: str, word_start: int) -> bool:
    prefix = text[:word_start].rstrip()
    if not prefix:
        return True
    prefix = prefix.rstrip(_QUOTE_CHARS + "»”’)]} ")
    if not prefix:
        return True
    return prefix[-1] in ".!?…:—–-("


def _words_equivalent_for_minimal_correction(original: str, corrected: str) -> bool:
    if original == corrected:
        return True
    original_plain = original.replace("ё", "е")
    corrected_plain = corrected.replace("ё", "е")
    if original_plain == corrected_plain:
        return True
    return _is_mechanical_cyrillic_ocr_substitution(original_plain, corrected_plain)


def _is_mechanical_cyrillic_ocr_substitution(original: str, corrected: str) -> bool:
    if min(len(original), len(corrected)) < 5:
        return False
    if abs(len(original) - len(corrected)) > 1:
        return False
    if not (_CYRILLIC_RE.fullmatch(original) and _CYRILLIC_RE.fullmatch(corrected)):
        return False

    original_cf = original.casefold()
    corrected_cf = corrected.casefold()
    if len(original_cf) == len(corrected_cf):
        differing_pairs = [
            frozenset((left, right))
            for left, right in zip(original_cf, corrected_cf)
            if left != right
        ]
        return len(differing_pairs) == 1 and differing_pairs[0] in _MECHANICAL_CYRILLIC_OCR_PAIRS

    shorter, longer = sorted((original_cf, corrected_cf), key=len)
    if longer == shorter + "ь":
        return True
    return bool(shorter) and longer == shorter + shorter[-1] and shorter[-1] in _CYRILLIC_VOWELS


_MECHANICAL_CYRILLIC_OCR_PAIRS = {frozenset(("ш", "щ"))}
_CYRILLIC_VOWELS = set("аеёиоуыэюя")
