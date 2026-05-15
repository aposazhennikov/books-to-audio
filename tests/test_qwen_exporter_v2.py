"""Tests for the enhanced Qwen exporter with stress strategies."""

from __future__ import annotations

from pathlib import Path

from book_normalizer.exporters.qwen_exporter import QwenExporter, StressExportStrategy
from book_normalizer.models.book import Book, Chapter, Metadata, Paragraph, Segment
from book_normalizer.stress.dictionary import COMBINING_ACUTE


def _make_book_with_stress() -> Book:
    """Create a book with stress-annotated segments."""
    seg1 = Segment(text="молоко", stress_form="молоко" + COMBINING_ACUTE)
    seg2 = Segment(text=" ", stress_form="")
    seg3 = Segment(text="и", stress_form="и")
    seg4 = Segment(text=" ", stress_form="")
    seg5 = Segment(text="вода", stress_form="вода" + COMBINING_ACUTE)

    para = Paragraph(
        raw_text="молоко и вода",
        normalized_text="молоко и вода",
        index_in_chapter=0,
        segments=[seg1, seg2, seg3, seg4, seg5],
    )
    ch = Chapter(title="Test", index=0, paragraphs=[para])
    return Book(metadata=Metadata(), chapters=[ch])


class TestQwenExporterStrategies:
    def test_strip_strategy(self, tmp_path: Path) -> None:
        book = _make_book_with_stress()
        exporter = QwenExporter(stress_strategy=StressExportStrategy.STRIP)
        exporter.export(book, tmp_path)

        content = (tmp_path / "qwen_full.txt").read_text(encoding="utf-8")
        assert COMBINING_ACUTE not in content
        assert "молоко" in content
        assert "вода" in content

    def test_keep_acute_strategy(self, tmp_path: Path) -> None:
        book = _make_book_with_stress()
        exporter = QwenExporter(stress_strategy=StressExportStrategy.KEEP_ACUTE)
        exporter.export(book, tmp_path)

        content = (tmp_path / "qwen_full.txt").read_text(encoding="utf-8")
        assert COMBINING_ACUTE in content

    def test_plain_strategy(self, tmp_path: Path) -> None:
        book = _make_book_with_stress()
        exporter = QwenExporter(stress_strategy=StressExportStrategy.PLAIN)
        exporter.export(book, tmp_path)

        content = (tmp_path / "qwen_full.txt").read_text(encoding="utf-8")
        assert COMBINING_ACUTE not in content
        assert content.strip() == "молоко и вода"

    def test_default_is_strip(self, tmp_path: Path) -> None:
        book = _make_book_with_stress()
        exporter = QwenExporter()
        exporter.export(book, tmp_path)

        content = (tmp_path / "qwen_full.txt").read_text(encoding="utf-8")
        assert COMBINING_ACUTE not in content

    def test_no_segments_fallback(self, tmp_path: Path) -> None:
        para = Paragraph(
            raw_text="простой текст",
            normalized_text="простой текст",
            index_in_chapter=0,
        )
        ch = Chapter(title="Test", index=0, paragraphs=[para])
        book = Book(metadata=Metadata(), chapters=[ch])

        exporter = QwenExporter(stress_strategy=StressExportStrategy.KEEP_ACUTE)
        exporter.export(book, tmp_path)

        content = (tmp_path / "qwen_full.txt").read_text(encoding="utf-8")
        assert content.strip() == "простой текст"

    def test_chapter_files_created(self, tmp_path: Path) -> None:
        book = _make_book_with_stress()
        exporter = QwenExporter()
        files = exporter.export(book, tmp_path)

        assert files
        assert (tmp_path / "qwen_full.txt").exists()
        assert (tmp_path / "qwen_chapter_001.txt").exists()
        assert (tmp_path / "qwen_chunks").is_dir()
