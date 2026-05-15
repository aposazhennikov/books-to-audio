"""Tests for the FB2 loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from book_normalizer.loaders.fb2_loader import Fb2Loader

MINIMAL_FB2 = """\
<?xml version="1.0" encoding="utf-8"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">
  <description>
    <title-info>
      <book-title>Test Book</book-title>
      <author>
        <first-name>Ivan</first-name>
        <last-name>Petrov</last-name>
      </author>
      <lang>ru</lang>
      <date value="2025">2025</date>
    </title-info>
  </description>
  <body>
    <section>
      <title><p>Chapter One</p></title>
      <p>First paragraph of chapter one.</p>
      <p>Second paragraph of chapter one.</p>
    </section>
    <section>
      <title><p>Chapter Two</p></title>
      <p>First paragraph of chapter two.</p>
    </section>
  </body>
</FictionBook>
"""

MINIMAL_FB2_NO_SECTIONS = """\
<?xml version="1.0" encoding="utf-8"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">
  <description>
    <title-info>
      <book-title>Flat Book</book-title>
      <author>
        <first-name>Author</first-name>
        <last-name>Name</last-name>
      </author>
      <lang>ru</lang>
    </title-info>
  </description>
  <body>
    <p>Standalone paragraph one.</p>
    <p>Standalone paragraph two.</p>
  </body>
</FictionBook>
"""

FB2_WITH_GENERATED_FRONT_MATTER = """\
<?xml version="1.0" encoding="utf-8"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">
  <description>
    <title-info>
      <book-title>Generated Front Matter</book-title>
      <author><first-name>Boris</first-name><last-name>Monosov</last-name></author>
      <lang>ru</lang>
    </title-info>
  </description>
  <body>
    <section>
      <p><strong>Annotation</strong></p>
      <p>Служебная аннотация из карточки книги.</p>
      <p>ГЛАВА ПЕРВАЯ</p>
      <p>ГЛАВА ВТОРАЯ</p>
      <p>ГЛАВА ТРЕТЬЯ</p>
      <p>Автор</p>
      <p>Название книги</p>
      <p><strong>ГЛАВА ПЕРВАЯ</strong></p>
      <p><strong>В которой описывается первая глава</strong></p>
      <p>Первый настоящий абзац.</p>
      <p><strong>ГЛАВА ВТОРАЯ</strong></p>
      <p><strong>В которой описывается вторая глава</strong></p>
      <p>Второй настоящий абзац.</p>
      <p><strong>ГЛАВА ТРЕТЬЯ</strong></p>
      <p><strong>В которой описывается третья глава</strong></p>
      <p>Третий настоящий абзац.</p>
    </section>
  </body>
</FictionBook>
"""


class TestFb2Loader:
    def test_supported_extensions(self) -> None:
        loader = Fb2Loader()
        assert ".fb2" in loader.supported_extensions

    def test_can_load(self, tmp_path: Path) -> None:
        loader = Fb2Loader()
        assert loader.can_load(tmp_path / "book.fb2")
        assert not loader.can_load(tmp_path / "book.epub")

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        loader = Fb2Loader()
        with pytest.raises(FileNotFoundError):
            loader.load(tmp_path / "missing.fb2")

    def test_load_with_sections(self, tmp_path: Path) -> None:
        fb2_file = tmp_path / "test.fb2"
        fb2_file.write_text(MINIMAL_FB2, encoding="utf-8")

        loader = Fb2Loader()
        book = loader.load(fb2_file)

        assert book.metadata.title == "Test Book"
        assert book.metadata.author == "Ivan Petrov"
        assert book.metadata.source_format == "fb2"
        assert book.metadata.year == "2025"
        assert len(book.chapters) == 2
        assert book.chapters[0].title == "Chapter One"
        assert len(book.chapters[0].paragraphs) == 2
        assert book.chapters[1].title == "Chapter Two"
        assert len(book.chapters[1].paragraphs) == 1

    def test_load_no_sections_fallback(self, tmp_path: Path) -> None:
        fb2_file = tmp_path / "flat.fb2"
        fb2_file.write_text(MINIMAL_FB2_NO_SECTIONS, encoding="utf-8")

        loader = Fb2Loader()
        book = loader.load(fb2_file)

        assert book.metadata.title == "Flat Book"
        assert len(book.chapters) == 1
        assert len(book.chapters[0].paragraphs) == 2

    def test_load_trims_generated_front_matter_before_repeated_headings(
        self,
        tmp_path: Path,
    ) -> None:
        fb2_file = tmp_path / "front_matter.fb2"
        fb2_file.write_text(FB2_WITH_GENERATED_FRONT_MATTER, encoding="utf-8")

        loader = Fb2Loader()
        book = loader.load(fb2_file)

        texts = [p.raw_text for p in book.chapters[0].paragraphs]
        assert texts[:2] == ["ГЛАВА ПЕРВАЯ", "Первый настоящий абзац."]
        assert "Annotation" not in texts
        assert "Служебная аннотация из карточки книги." not in texts
        assert "Название книги" not in texts
        assert "В которой описывается первая глава" not in texts

    def test_paragraph_text_content(self, tmp_path: Path) -> None:
        fb2_file = tmp_path / "test.fb2"
        fb2_file.write_text(MINIMAL_FB2, encoding="utf-8")

        loader = Fb2Loader()
        book = loader.load(fb2_file)

        assert book.chapters[0].paragraphs[0].raw_text == "First paragraph of chapter one."

    def test_audit_trail(self, tmp_path: Path) -> None:
        fb2_file = tmp_path / "test.fb2"
        fb2_file.write_text(MINIMAL_FB2, encoding="utf-8")

        loader = Fb2Loader()
        book = loader.load(fb2_file)
        assert any(r["stage"] == "loading" for r in book.audit_trail)
        assert any("fb2_loader" in r["action"] for r in book.audit_trail)
