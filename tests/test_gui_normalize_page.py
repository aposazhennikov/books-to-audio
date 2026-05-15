from __future__ import annotations

from book_normalizer.gui.pages.normalize_page import _book_preview_lines
from book_normalizer.models.book import Book, Chapter, Paragraph


def test_book_preview_default_is_not_truncated() -> None:
    book = Book(chapters=[
        Chapter(
            title="Long Chapter",
            index=0,
            paragraphs=[
                Paragraph(raw_text=f"Paragraph {idx}", normalized_text=f"Paragraph {idx}")
                for idx in range(35)
            ],
        ),
    ])

    raw_lines, norm_lines = _book_preview_lines(book)

    assert "Paragraph 34" in raw_lines
    assert norm_lines == raw_lines


def test_book_preview_continues_after_short_preamble() -> None:
    book = Book(chapters=[
        Chapter(
            title="Preamble",
            index=0,
            paragraphs=[
                Paragraph(raw_text="Верёвка есть вервие простое.", normalized_text="Верёвка есть вервие простое."),
            ],
        ),
        Chapter(
            title="ГЛАВА 1",
            index=1,
            paragraphs=[
                Paragraph(raw_text="Сергей сидел за столом.", normalized_text="Сергей сидел за столом."),
                Paragraph(raw_text="Гроза началась.", normalized_text="Гроза началась."),
            ],
        ),
    ])

    raw_lines, norm_lines = _book_preview_lines(book, limit=3)

    assert "Preamble" in raw_lines[0]
    assert "Верёвка есть вервие простое." in raw_lines
    assert "=== ГЛАВА 1 ===" in raw_lines
    assert "Сергей сидел за столом." in raw_lines
    assert norm_lines == raw_lines
