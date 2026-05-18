"""Stress/accent annotation, dictionary, and interactive resolution."""

from book_normalizer.stress.annotator import AnnotationResult, StressAnnotator
from book_normalizer.stress.dictionary import StressDictionary
from book_normalizer.stress.rendering import (
    StressRenderMode,
    render_annotated_chapters_for_tts,
    render_book_for_tts,
    render_stressed_text,
)
from book_normalizer.stress.resolver import StressResolver

__all__ = [
    "StressDictionary",
    "StressAnnotator",
    "StressResolver",
    "AnnotationResult",
    "StressRenderMode",
    "render_annotated_chapters_for_tts",
    "render_book_for_tts",
    "render_stressed_text",
]
