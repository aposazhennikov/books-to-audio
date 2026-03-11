"""Tests for the loader factory."""

from __future__ import annotations

from pathlib import Path

import pytest

from book_normalizer.loaders.factory import LoaderFactory


class TestLoaderFactory:
    def test_default_factory_has_all_loaders(self) -> None:
        factory = LoaderFactory.default()
        assert len(factory._loaders) == 5

    def test_supported_extensions(self) -> None:
        factory = LoaderFactory.default()
        supported = set()
        for loader in factory._loaders:
            supported.update(loader.supported_extensions)
        assert {".txt", ".pdf", ".epub", ".fb2", ".docx"} == supported

    def test_get_loader_for_txt(self, tmp_path: Path) -> None:
        factory = LoaderFactory.default()
        loader = factory.get_loader(tmp_path / "book.txt")
        assert type(loader).__name__ == "TxtLoader"

    def test_get_loader_for_pdf(self, tmp_path: Path) -> None:
        factory = LoaderFactory.default()
        loader = factory.get_loader(tmp_path / "book.pdf")
        assert type(loader).__name__ == "PdfLoader"

    def test_get_loader_for_epub(self, tmp_path: Path) -> None:
        factory = LoaderFactory.default()
        loader = factory.get_loader(tmp_path / "book.epub")
        assert type(loader).__name__ == "EpubLoader"

    def test_get_loader_for_fb2(self, tmp_path: Path) -> None:
        factory = LoaderFactory.default()
        loader = factory.get_loader(tmp_path / "book.fb2")
        assert type(loader).__name__ == "Fb2Loader"

    def test_get_loader_for_docx(self, tmp_path: Path) -> None:
        factory = LoaderFactory.default()
        loader = factory.get_loader(tmp_path / "book.docx")
        assert type(loader).__name__ == "DocxLoader"

    def test_unsupported_format_raises(self, tmp_path: Path) -> None:
        factory = LoaderFactory.default()
        with pytest.raises(ValueError, match="No loader found"):
            factory.get_loader(tmp_path / "book.xyz")

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        factory = LoaderFactory.default()
        with pytest.raises(FileNotFoundError):
            factory.load(tmp_path / "nonexistent.txt")

    def test_register_custom_loader(self) -> None:
        from book_normalizer.loaders.base import BaseLoader
        from book_normalizer.models.book import Book

        class CustomLoader(BaseLoader):
            @property
            def supported_extensions(self) -> set[str]:
                return {".custom"}

            def load(self, path: Path) -> Book:
                return Book()

        factory = LoaderFactory()
        factory.register(CustomLoader())
        loader = factory.get_loader(Path("test.custom"))
        assert type(loader).__name__ == "CustomLoader"
