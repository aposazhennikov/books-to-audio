from __future__ import annotations

from pathlib import Path

from book_normalizer.models.book import Book, Chapter, Paragraph


def _build_book(chapter_sizes: list[int]) -> Book:
    chapters: list[Chapter] = []
    for idx, size in enumerate(chapter_sizes):
        paras = [
            Paragraph(raw_text=f"Para {idx}-{i}", normalized_text="", index_in_chapter=i)
            for i in range(size)
        ]
        chapters.append(Chapter(title=f"Chapter {idx}", index=idx, paragraphs=paras))
    return Book(chapters=chapters)


def test_chapter_sanity_report_written(tmp_path: Path) -> None:
    # Suspicious: many tiny chapters and very uneven distribution.
    book = _build_book([1, 1, 10, 1, 1, 1, 1, 1])

    from book_normalizer.cli import _write_chapter_sanity_report

    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    _write_chapter_sanity_report(book, out_dir)

    report_path = out_dir / "chapter_sanity_report.txt"
    assert report_path.exists()

    content = report_path.read_text(encoding="utf-8")
    assert "total_chapters=8" in content
    assert "suspicious=" in content
