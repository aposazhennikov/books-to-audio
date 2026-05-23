from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from book_normalizer.loaders.pdf_loader import PdfOcrCompareResult, PdfTextVariant


def _load_benchmark_module() -> ModuleType:
    script = Path(__file__).resolve().parent.parent / "scripts" / "quality_benchmark.py"
    spec = importlib.util.spec_from_file_location("quality_benchmark", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_offline_quality_benchmark_covers_supported_languages(tmp_path: Path) -> None:
    module = _load_benchmark_module()

    report = module.run_benchmark(books_dir=tmp_path / "missing", run_ollama=False)

    languages = {case["language"] for case in report["cases"]}
    assert languages == {"ru", "en", "zh", "kk", "uz"}
    assert report["run_ollama"] is False
    assert all(case["text_preserved"] for case in report["cases"])
    assert all(case["chunks"] >= 1 for case in report["cases"])


def test_quality_benchmark_reads_local_txt_books(tmp_path: Path) -> None:
    module = _load_benchmark_module()
    books_dir = tmp_path / "books"
    books_dir.mkdir()
    (books_dir / "sample.txt").write_text("Alpha beta.\n\nGamma delta.", encoding="utf-8")

    report = module.run_benchmark(books_dir=books_dir, run_ollama=False)

    sources = {case["source"] for case in report["cases"]}
    assert str(books_dir / "sample.txt") in sources


def test_quality_benchmark_uses_ocr_aware_pdf_loader(tmp_path: Path, monkeypatch) -> None:
    module = _load_benchmark_module()
    books_dir = tmp_path / "books"
    books_dir.mkdir()
    pdf_path = books_dir / "scan.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    native_compare = PdfOcrCompareResult(
        native=PdfTextVariant(kind="native", text="Co,11;ep'l\\:aHne", document_type="text"),
        ocr=None,
    )
    ocr_compare = PdfOcrCompareResult(
        native=native_compare.native,
        ocr=PdfTextVariant(kind="ocr", text="ГЛАВА ПЕРВАЯ\n\nСергей сидел за столом.", document_type="ocr"),
    )
    calls = []

    def fake_extract(path, mode, **kwargs):  # noqa: ANN001
        assert path == pdf_path
        assert kwargs["language_code"] == "ru"
        calls.append(mode)
        return native_compare if mode == module.OcrMode.OFF else ocr_compare

    def fake_select(compare_arg, mode, language_code="ru"):  # noqa: ANN001
        assert mode == module.OcrMode.AUTO
        assert language_code == "ru"
        if compare_arg is native_compare:
            return native_compare.native, {"selected": "native", "native_unreadable": True}
        return ocr_compare.ocr, {
            "selected": "ocr",
            "reason": "auto_mode_native_cyr=0.00_use_ocr",
            "native_unreadable": True,
        }

    monkeypatch.setattr(module, "extract_pdf_with_ocr_mode", fake_extract)
    monkeypatch.setattr(module, "select_pdf_text_for_mode", fake_select)

    report = module.run_benchmark(books_dir=books_dir, run_ollama=False, limit_books=1)

    pdf_case = next(case for case in report["cases"] if case["source"] == str(pdf_path))
    assert pdf_case["source_format"] == "pdf"
    assert calls == [module.OcrMode.OFF, module.OcrMode.AUTO]
    assert pdf_case["metadata_extra"]["pdf_text_variant"] == "ocr"
    assert pdf_case["metadata_extra"]["pdf_text_stats"]["selected"] == "ocr"


def test_quality_benchmark_skips_pdf_ocr_when_native_text_is_readable(tmp_path: Path, monkeypatch) -> None:
    module = _load_benchmark_module()
    books_dir = tmp_path / "books"
    books_dir.mkdir()
    pdf_path = books_dir / "native.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    native_compare = PdfOcrCompareResult(
        native=PdfTextVariant(kind="native", text="ГЛАВА ПЕРВАЯ\n\nСергей сидел за столом.", document_type="text"),
        ocr=None,
    )
    calls = []

    def fake_extract(path, mode, **kwargs):  # noqa: ANN001
        assert path == pdf_path
        calls.append(mode)
        return native_compare

    def fake_select(compare_arg, mode, language_code="ru"):  # noqa: ANN001
        assert compare_arg is native_compare
        assert mode == module.OcrMode.AUTO
        return native_compare.native, {"selected": "native", "native_unreadable": False}

    monkeypatch.setattr(module, "extract_pdf_with_ocr_mode", fake_extract)
    monkeypatch.setattr(module, "select_pdf_text_for_mode", fake_select)

    report = module.run_benchmark(books_dir=books_dir, run_ollama=False, limit_books=1)

    pdf_case = next(case for case in report["cases"] if case["source"] == str(pdf_path))
    assert calls == [module.OcrMode.OFF]
    assert pdf_case["metadata_extra"]["pdf_text_variant"] == "native"
    assert pdf_case["metadata_extra"]["pdf_text_stats"]["reason"] == "benchmark_native_precheck_preferred"


def test_quality_benchmark_excerpts_real_books(tmp_path: Path) -> None:
    module = _load_benchmark_module()
    text = " ".join(f"word{i}" for i in range(200))
    book = module.Book.from_raw_text(text, source_path=tmp_path / "long.txt")

    excerpt = module._excerpt_book(book, max_chars=120)

    assert len(excerpt.raw_text) <= 120
    assert excerpt.metadata.extra["benchmark_excerpt"] is True
    assert excerpt.metadata.extra["benchmark_original_chars"] == len(text)


def test_quality_benchmark_excerpt_does_not_keep_tiny_partial_tail() -> None:
    module = _load_benchmark_module()
    book = module.Book(
        metadata=module.Metadata(language="ru"),
        chapters=[
            module.Chapter(
                index=0,
                paragraphs=[
                    module.Paragraph(raw_text="A" * 340, index_in_chapter=0),
                    module.Paragraph(raw_text="Эта книга не должна быть обрублена.", index_in_chapter=1),
                ],
            )
        ],
    )

    excerpt = module._excerpt_book(book, max_chars=350)

    assert "Эта кни" not in excerpt.raw_text
    assert len(excerpt.raw_text) <= 350
