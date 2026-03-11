"""Chapter detection and splitting module."""

from book_normalizer.chaptering.detector import ChapterDetector
from book_normalizer.chaptering.patterns import CHAPTER_PATTERNS

__all__ = ["ChapterDetector", "CHAPTER_PATTERNS"]
