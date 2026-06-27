"""Failure records for LLM segmentation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class LlmSegmentationError(RuntimeError):
    """Raised when smart segmentation cannot preserve source text."""


@dataclass
class SegmentationFailure:
    chapter_index: int
    window_index: int
    model: str
    reason: str
    source_preview: str
    output_preview: str = ""

    def to_record(self) -> dict[str, Any]:
        return {
            "chapter_index": self.chapter_index,
            "window_index": self.window_index,
            "model": self.model,
            "reason": self.reason,
            "source_preview": self.source_preview,
            "output_preview": self.output_preview,
        }

