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


def _build_omnibus(work_sizes: list[int]) -> Book:
    chapters: list[Chapter] = []
    for work_index, chapter_count in enumerate(work_sizes):
        for section_index in range(chapter_count):
            chapters.append(
                Chapter(
                    title=f"Work {work_index} - Chapter {section_index}",
                    index=len(chapters),
                    work_index=work_index,
                    work_title=f"Work {work_index}",
                    section_index=section_index,
                    paragraphs=[
                        Paragraph(raw_text=f"Para {work_index}-{section_index}-{i}", index_in_chapter=i)
                        for i in range(4)
                    ],
                )
            )
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


def test_chapter_sanity_allows_multiwork_collections(tmp_path: Path) -> None:
    book = _build_omnibus([20, 18, 17])

    from book_normalizer.cli import _write_chapter_sanity_report

    out_dir = tmp_path / "out"
    _write_chapter_sanity_report(book, out_dir)

    content = (out_dir / "chapter_sanity_report.txt").read_text(encoding="utf-8")
    assert "total_chapters=55" in content
    assert "work_count=3" in content
    assert "suspicious=no" in content
    assert "too_many_chapters" not in content
