"""Application configuration with sensible defaults."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class OcrMode(str, Enum):
    """OCR execution mode for PDF handling."""

    OFF = "off"
    AUTO = "auto"
    FORCE = "force"
    COMPARE = "compare"


class AppConfig(BaseModel):
    """Top-level configuration for the book normalizer."""

    data_dir: Path = Field(default=Path("data"))
    user_memory_dir: Path = Field(default=Path("data/user_memory"))
    verbose: bool = False
    interactive: bool = False
    resume: bool = False
    skip_stress: bool = False
    skip_punctuation_review: bool = False
    skip_spellcheck: bool = False
    export_json: bool = True
    chapters_only: bool = False
    ocr_mode: OcrMode = OcrMode.OFF

    @property
    def stress_dict_path(self) -> Path:
        return self.user_memory_dir / "stress_dictionary.json"

    @property
    def correction_memory_path(self) -> Path:
        return self.user_memory_dir / "correction_memory.json"

    @property
    def punctuation_memory_path(self) -> Path:
        return self.user_memory_dir / "punctuation_memory.json"

    @property
    def review_sessions_dir(self) -> Path:
        return self.user_memory_dir / "review_sessions"
