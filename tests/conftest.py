"""Shared fixtures for the book normalizer test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from book_normalizer.models.book import Book, Chapter, Metadata, Paragraph


@pytest.fixture()
def tmp_txt_file(tmp_path: Path) -> Path:
    """Create a temporary .txt file with sample Russian text."""
    content = (
        "Глава 1\n\n"
        "Это первый абзац первой главы. Он содержит несколько предложений.\n"
        "Вот второе предложение.\n\n"
        "Это второй абзац первой главы.\n\n"
        "Глава 2\n\n"
        "Это первый абзац второй главы.\n\n"
        "Это второй абзац второй главы.\n"
    )
    file_path = tmp_path / "test_book.txt"
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.fixture()
def sample_book() -> Book:
    """Create a sample Book with two chapters for testing."""
    ch1 = Chapter(
        title="Глава 1",
        index=0,
        paragraphs=[
            Paragraph(raw_text="Первый абзац.", normalized_text="Первый абзац.", index_in_chapter=0),
            Paragraph(raw_text="Второй абзац.", normalized_text="Второй абзац.", index_in_chapter=1),
        ],
    )
    ch2 = Chapter(
        title="Глава 2",
        index=1,
        paragraphs=[
            Paragraph(raw_text="Третий абзац.", normalized_text="Третий абзац.", index_in_chapter=0),
        ],
    )
    return Book(
        metadata=Metadata(title="Тестовая книга", author="Тест Тестович", source_format="txt"),
        chapters=[ch1, ch2],
    )
