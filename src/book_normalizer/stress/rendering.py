"""Render canonical stress annotations for TTS input."""

from __future__ import annotations

import copy
from enum import Enum

from book_normalizer.models.book import Book, Paragraph
from book_normalizer.stress.dictionary import COMBINING_ACUTE, VOWELS, strip_stress


class StressRenderMode(str, Enum):
    """Supported TTS render modes for stress hints."""

    PLAIN = "plain"
    KEEP_ACUTE = "keep_acute"
    DOUBLE_VOWEL = "double_vowel"


def render_stressed_text(text: str, mode: str | StressRenderMode) -> str:
    """Render U+0301 stress marks in a TTS-friendly notation."""
    render_mode = _coerce_mode(mode)
    if render_mode == StressRenderMode.KEEP_ACUTE:
        return text
    if render_mode == StressRenderMode.PLAIN:
        return strip_stress(text)
    return double_stressed_vowels(text)


def double_stressed_vowels(text: str) -> str:
    """Convert combining acute stress marks into doubled vowels."""
    if not text:
        return text

    result: list[str] = []
    for ch in text:
        if ch == COMBINING_ACUTE:
            if result and result[-1] in VOWELS:
                result.append(result[-1])
            continue
        result.append(ch)
    return "".join(result)


def render_paragraph_for_tts(
    paragraph: Paragraph,
    mode: str | StressRenderMode = StressRenderMode.DOUBLE_VOWEL,
) -> str:
    """Return paragraph text rendered for TTS from stress segments if present."""
    if paragraph.segments:
        stressed = "".join(
            _stress_form_preserving_text(seg.text, seg.stress_form)
            if seg.stress_form
            else seg.text
            for seg in paragraph.segments
        )
    else:
        stressed = paragraph.normalized_text or paragraph.raw_text
    return render_stressed_text(stressed, mode)


def render_book_for_tts(
    book: Book,
    mode: str | StressRenderMode = StressRenderMode.DOUBLE_VOWEL,
) -> Book:
    """Return a deep copy whose paragraph text is rendered for TTS only."""
    if hasattr(book, "model_copy"):
        rendered = book.model_copy(deep=True)
    else:  # pragma: no cover - pydantic v1 fallback
        rendered = copy.deepcopy(book)

    for chapter in rendered.chapters:
        for paragraph in chapter.paragraphs:
            paragraph.normalized_text = render_paragraph_for_tts(paragraph, mode)
    return rendered


def render_annotated_chapters_for_tts(
    annotated_chapters: object,
    book: Book,
    mode: str | StressRenderMode = StressRenderMode.DOUBLE_VOWEL,
) -> None:
    """Mutate detected dialogue lines so only exported TTS text gets hints."""
    render_mode = _coerce_mode(mode)
    if render_mode == StressRenderMode.PLAIN:
        return

    paragraph_maps = {
        paragraph.id: _ParagraphRenderMap(
            source=paragraph.normalized_text or paragraph.raw_text,
            rendered=render_paragraph_for_tts(paragraph, render_mode),
        )
        for chapter in book.chapters
        for paragraph in chapter.paragraphs
    }

    for chapter in annotated_chapters:
        for paragraph in chapter.paragraphs:
            render_map = paragraph_maps.get(paragraph.paragraph_id)
            if render_map is None:
                continue
            for line in paragraph.lines:
                line.text = render_map.render_fragment(line.text)


def _coerce_mode(mode: str | StressRenderMode) -> StressRenderMode:
    if isinstance(mode, StressRenderMode):
        return mode
    try:
        return StressRenderMode(str(mode))
    except ValueError:
        return StressRenderMode.DOUBLE_VOWEL


def _stress_form_preserving_text(text: str, stress_form: str) -> str:
    """Apply stress position from stress_form to text without changing casing."""
    if not stress_form:
        return text

    stress_index = stress_form.find(COMBINING_ACUTE)
    if stress_index < 1:
        return text

    base_before_stress = len(strip_stress(stress_form[:stress_index]))
    stress_base = strip_stress(stress_form)
    if len(stress_base) != len(text):
        return stress_form

    insert_after = base_before_stress - 1
    if insert_after < 0 or insert_after >= len(text):
        return stress_form
    return text[: insert_after + 1] + COMBINING_ACUTE + text[insert_after + 1:]


class _ParagraphRenderMap:
    """Map detected clean-text fragments back to their rendered TTS form."""

    def __init__(self, *, source: str, rendered: str) -> None:
        self._source = source
        self._rendered = rendered
        self._cursor = 0
        self._boundaries = _build_boundary_map(source, rendered)

    def render_fragment(self, fragment: str) -> str:
        if not fragment or self._boundaries is None:
            return render_stressed_text(fragment, StressRenderMode.PLAIN)

        start = self._source.find(fragment, self._cursor)
        if start < 0:
            start = self._source.find(fragment)
        if start < 0:
            return render_stressed_text(fragment, StressRenderMode.PLAIN)

        end = start + len(fragment)
        self._cursor = end
        return self._rendered[self._boundaries[start]: self._boundaries[end]]


def _build_boundary_map(source: str, rendered: str) -> list[int] | None:
    """Return source boundary indexes mapped into the rendered string."""
    boundaries = [0] * (len(source) + 1)
    j = 0
    for i, ch in enumerate(source):
        while j < len(rendered) and rendered[j] != ch:
            j += 1
        if j >= len(rendered):
            return None
        boundaries[i] = j
        j += 1
    boundaries[len(source)] = len(rendered)
    return boundaries
