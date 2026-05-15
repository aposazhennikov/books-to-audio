"""Stress annotator that tokenizes text and produces annotated Segments."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from book_normalizer.models.book import Book, Paragraph, Segment
from book_normalizer.stress.dictionary import (
    COMBINING_ACUTE,
    StressDictionary,
    count_vowels,
    is_russian_word,
    strip_stress,
)

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"([а-яёА-ЯЁ]+|[^а-яёА-ЯЁ]+)", re.UNICODE)
_STRESSED_WORD_RE = re.compile(r"(?:[а-яёА-ЯЁ]\u0301?)+", re.UNICODE)


@dataclass
class AnnotationResult:
    """Result of annotating a book with stress information."""

    total_words: int = 0
    known_words: int = 0
    single_vowel_words: int = 0
    unknown_words: int = 0
    predicted_words: int = 0
    unknown_word_set: set[str] = field(default_factory=set)


class StressAnnotator:
    """
    Annotate a Book's paragraphs with stress information.

    For each paragraph, tokenizes the normalized text into Segments.
    Each Segment representing a Russian word gets its stress_form
    populated from the dictionary. Words not found remain with
    an empty stress_form for later interactive resolution.
    """

    def __init__(self, dictionary: StressDictionary) -> None:
        self._dict = dictionary

    def annotate_book(self, book: Book) -> AnnotationResult:
        """
        Annotate all paragraphs in the book with stress segments.

        Populates paragraph.segments for each paragraph.
        Returns statistics about known/unknown words.
        """
        result = AnnotationResult()

        for chapter in book.chapters:
            for para in chapter.paragraphs:
                self._annotate_paragraph(para, result)

        logger.info(
            "Stress annotation: %d total words, %d known, %d single-vowel, %d unknown.",
            result.total_words,
            result.known_words,
            result.single_vowel_words,
            result.unknown_words,
        )

        book.add_audit(
            "stress",
            "annotate",
            f"total={result.total_words}, known={result.known_words}, "
            f"single_vowel={result.single_vowel_words}, unknown={result.unknown_words}",
        )

        return result

    def _annotate_paragraph(self, para: Paragraph, result: AnnotationResult) -> None:
        """Tokenize and annotate a single paragraph."""
        text = para.normalized_text or para.raw_text
        if not text:
            return

        tokens = _TOKEN_RE.findall(text)
        predicted_words = self._predicted_words_for_text(text)
        predicted_index = 0
        segments: list[Segment] = []

        for token in tokens:
            if is_russian_word(token):
                result.total_words += 1
                predicted = ""
                if predicted_index < len(predicted_words):
                    candidate = predicted_words[predicted_index]
                    if _same_word_ignoring_stress_and_yo(token, candidate):
                        predicted = candidate
                    predicted_index += 1
                stressed = self._resolve_token(token, result, predicted)
                segments.append(
                    Segment(
                        text=token,
                        stress_form=stressed,
                    )
                )
            else:
                segments.append(Segment(text=token, stress_form=""))

        para.segments = segments

    def _resolve_token(
        self,
        token: str,
        result: AnnotationResult,
        predicted: str = "",
    ) -> str:
        """Try to resolve stress for a single Russian word token."""
        if count_vowels(token) <= 1:
            result.single_vowel_words += 1
            return token

        stressed = self._dict.lookup_user(token)
        if stressed:
            result.known_words += 1
            return stressed

        if predicted and COMBINING_ACUTE in predicted:
            result.known_words += 1
            result.predicted_words += 1
            return predicted

        stressed = self._dict.lookup_builtin(token)
        if stressed is not None:
            result.known_words += 1
            return stressed

        stressed = self._dict.predict_word(token)
        if stressed is not None:
            result.known_words += 1
            result.predicted_words += 1
            return stressed

        result.unknown_words += 1
        result.unknown_word_set.add(token.lower())
        return ""

    def _predicted_words_for_text(self, text: str) -> list[str]:
        """Return model-predicted word forms for the whole paragraph."""
        stressed_text = self._dict.predict_text(text)
        if not stressed_text:
            return []
        return [m.group(0) for m in _STRESSED_WORD_RE.finditer(stressed_text)]

    @staticmethod
    def reassemble_text(para: Paragraph, use_stress: bool = True) -> str:
        """
        Reassemble paragraph text from segments.

        If use_stress is True, uses stress_form where available.
        Otherwise uses the original token text.
        """
        if not para.segments:
            return para.normalized_text or para.raw_text

        parts: list[str] = []
        for seg in para.segments:
            if use_stress and seg.stress_form:
                parts.append(seg.stress_form)
            else:
                parts.append(seg.text)
        return "".join(parts)


def _same_word_ignoring_stress_and_yo(left: str, right: str) -> bool:
    """Compare words while ignoring stress marks and е/ё differences."""
    def _norm(value: str) -> str:
        return strip_stress(value).replace("ё", "е").replace("Ё", "Е").lower()

    return _norm(left) == _norm(right)
