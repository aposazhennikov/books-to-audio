"""Tests for exporters."""

from __future__ import annotations

import json
from pathlib import Path

from book_normalizer.exporters.json_exporter import JsonExporter
from book_normalizer.exporters.qwen_exporter import QwenExporter
from book_normalizer.exporters.txt_exporter import TxtExporter
from book_normalizer.models.book import Book


class TestTxtExporter:
    def test_creates_full_and_chapter_files(self, sample_book: Book, tmp_path: Path) -> None:
        exporter = TxtExporter()
        files = exporter.export(sample_book, tmp_path)

        assert len(files) == 3
        assert (tmp_path / "000_full_book.txt").exists()
        assert (tmp_path / "001_chapter_01.txt").exists()
        assert (tmp_path / "002_chapter_02.txt").exists()

    def test_full_book_contains_all_text(self, sample_book: Book, tmp_path: Path) -> None:
        exporter = TxtExporter()
        exporter.export(sample_book, tmp_path)

        content = (tmp_path / "000_full_book.txt").read_text(encoding="utf-8")
        assert "Первый абзац." in content
        assert "Третий абзац." in content

    def test_chapter_file_content(self, sample_book: Book, tmp_path: Path) -> None:
        exporter = TxtExporter()
        exporter.export(sample_book, tmp_path)

        ch1 = (tmp_path / "001_chapter_01.txt").read_text(encoding="utf-8")
        assert "Первый абзац." in ch1

    def test_creates_output_dir(self, sample_book: Book, tmp_path: Path) -> None:
        out = tmp_path / "nested" / "output"
        exporter = TxtExporter()
        exporter.export(sample_book, out)
        assert out.is_dir()


class TestJsonExporter:
    def test_creates_json_file(self, sample_book: Book, tmp_path: Path) -> None:
        exporter = JsonExporter()
        path = exporter.export(sample_book, tmp_path)

        assert path.exists()
        assert path.name == "book_structure.json"

    def test_json_structure(self, sample_book: Book, tmp_path: Path) -> None:
        exporter = JsonExporter()
        exporter.export(sample_book, tmp_path)

        data = json.loads((tmp_path / "book_structure.json").read_text(encoding="utf-8"))
        assert data["total_chapters"] == 2
        assert data["metadata"]["title"] == "Тестовая книга"
        assert len(data["chapters"]) == 2


class TestQwenExporter:
    def test_creates_files(self, sample_book: Book, tmp_path: Path) -> None:
        exporter = QwenExporter()
        files = exporter.export(sample_book, tmp_path)

        assert files
        assert (tmp_path / "qwen_full.txt").exists()
        assert (tmp_path / "qwen_chapter_001.txt").exists()
        assert (tmp_path / "qwen_chapter_002.txt").exists()
        assert (tmp_path / "qwen_chunks").is_dir()

    def test_strips_stress_marks(self, tmp_path: Path) -> None:
        from book_normalizer.exporters.qwen_exporter import StressExportStrategy
        from book_normalizer.models.book import Chapter, Metadata, Paragraph

        para = Paragraph(raw_text="", normalized_text="замо\u0301к", index_in_chapter=0)
        ch = Chapter(title="Test", index=0, paragraphs=[para])
        book = Book(metadata=Metadata(), chapters=[ch])

        exporter = QwenExporter(stress_strategy=StressExportStrategy.STRIP)
        exporter.export(book, tmp_path)

        content = (tmp_path / "qwen_full.txt").read_text(encoding="utf-8")
        assert "\u0301" not in content
        assert "замок" in content

    def test_clean_output(self, sample_book: Book, tmp_path: Path) -> None:
        exporter = QwenExporter()
        exporter.export(sample_book, tmp_path)

        content = (tmp_path / "qwen_full.txt").read_text(encoding="utf-8")
        assert "\x00" not in content
        assert "\n\n\n" not in content
