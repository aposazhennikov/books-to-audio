from pathlib import Path

from book_normalizer.models.book import Book
from book_normalizer.verification.report import (
    VerificationConfig,
    _collect_candidate_headings,
    compute_book_stats,
    generate_reports,
)


def make_simple_book(raw: str) -> Book:
    return Book.from_raw_text(raw, source_path="test.txt", source_format="txt")


def test_compute_book_stats_basic(tmp_path: Path) -> None:
    text = "Глава 1\n\nЭто первый абзац.\n\nЭто второй абзац…"
    book = make_simple_book(text)

    stats = compute_book_stats(book, normalized=False)

    assert stats.character_count == len(text)
    assert stats.paragraph_count == 3
    assert stats.chapter_count == 1
    assert stats.word_count >= 5
    assert stats.ellipsis_char_count == 1


def test_heading_detection_finds_simple_headings() -> None:
    text = "Глава 1. Начало\n\nПросто текст."
    book = make_simple_book(text)

    headings = _collect_candidate_headings(book, normalized=False)

    assert any("Глава 1" in h or "Глава 1. Начало" in h for h in headings)


def test_generate_reports_creates_artifacts(tmp_path: Path) -> None:
    before = make_simple_book("Глава 1\n\nТекст до.\n\nЕще текст.")
    after = make_simple_book("Глава 1\n\nТекст после.\n\nЕще текст…")

    config = VerificationConfig(sample_size=2)
    result = generate_reports(before=before, after=after, output_dir=tmp_path, config=config)

    for key, path_str in result.artifacts.items():
        path = Path(path_str)
        assert path.exists(), f"Artifact {key} was not created"

