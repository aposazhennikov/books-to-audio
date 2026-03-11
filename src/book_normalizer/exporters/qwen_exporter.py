"""Qwen3-TTS-compatible plain text exporter."""

from __future__ import annotations

import enum
import logging
import re
from pathlib import Path

from book_normalizer.models.book import Book, Paragraph

logger = logging.getLogger(__name__)

COMBINING_ACUTE = "\u0301"


class StressExportStrategy(str, enum.Enum):
    """Strategy for handling stress marks in exported text."""

    STRIP = "strip"
    KEEP_ACUTE = "keep_acute"
    PLAIN = "plain"


class QwenExporter:
    """
    Export a Book as clean UTF-8 plain text optimized for Qwen3-TTS.

    Supports configurable stress export strategies:
    - STRIP: remove all stress marks (default, safest for TTS).
    - KEEP_ACUTE: preserve combining acute accent marks.
    - PLAIN: output from normalized_text only, ignoring segments.

    This is the final step before feeding text to the TTS engine.
    """

    def __init__(
        self,
        stress_strategy: StressExportStrategy = StressExportStrategy.STRIP,
    ) -> None:
        self._strategy = stress_strategy

    def export(self, book: Book, output_dir: Path) -> list[Path]:
        """
        Write Qwen-ready text files and return created paths.

        Produces:
        - qwen_full.txt - full book.
        - qwen_chapter_NNN.txt - per-chapter files.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        created: list[Path] = []

        full_parts: list[str] = []
        for chapter in book.chapters:
            text = self._build_chapter_text(chapter)
            clean = self._sanitize_for_tts(text)
            full_parts.append(clean)

            chapter_num = chapter.index + 1
            ch_path = output_dir / f"qwen_chapter_{chapter_num:03d}.txt"
            ch_path.write_text(clean, encoding="utf-8")
            created.append(ch_path)

        full_path = output_dir / "qwen_full.txt"
        full_path.write_text("\n\n".join(full_parts), encoding="utf-8")
        created.insert(0, full_path)

        logger.info("Exported %d Qwen-TTS files to %s", len(created), output_dir)
        book.add_audit("export", "qwen_export", f"files={len(created)}, strategy={self._strategy.value}")
        return created

    def _build_chapter_text(self, chapter: object) -> str:
        """Build chapter text using the configured strategy."""
        from book_normalizer.models.book import Chapter

        if not isinstance(chapter, Chapter):
            return ""

        if self._strategy == StressExportStrategy.PLAIN:
            return chapter.normalized_text or chapter.raw_text

        parts: list[str] = []
        for para in chapter.paragraphs:
            para_text = self._build_paragraph_text(para)
            if para_text:
                parts.append(para_text)
        return "\n\n".join(parts)

    def _build_paragraph_text(self, para: Paragraph) -> str:
        """Build paragraph text, optionally using segments with stress."""
        if not para.segments:
            return para.normalized_text or para.raw_text

        if self._strategy == StressExportStrategy.KEEP_ACUTE:
            return self._reassemble_with_stress(para)

        return para.normalized_text or para.raw_text

    @staticmethod
    def _reassemble_with_stress(para: Paragraph) -> str:
        """Reassemble text from segments, using stress_form where available."""
        parts: list[str] = []
        for seg in para.segments:
            if seg.stress_form:
                parts.append(seg.stress_form)
            else:
                parts.append(seg.text)
        return "".join(parts)

    def _sanitize_for_tts(self, text: str) -> str:
        """Remove annotations and control characters, keeping clean Russian text."""
        result = text

        if self._strategy == StressExportStrategy.STRIP:
            result = result.replace(COMBINING_ACUTE, "")

        result = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", result)
        result = re.sub(r"\n{3,}", "\n\n", result)
        result = result.strip()
        return result
