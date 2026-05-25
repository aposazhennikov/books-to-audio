from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

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


def test_quality_benchmark_filters_synthetic_languages(tmp_path: Path) -> None:
    module = _load_benchmark_module()

    report = module.run_benchmark(
        books_dir=tmp_path / "missing",
        run_ollama=False,
        languages=["zh", "zh", "en"],
    )

    assert report["languages"] == ["zh", "en"]
    assert [case["language"] for case in report["cases"]] == ["zh", "en"]


def test_quality_benchmark_can_skip_synthetic_cases(tmp_path: Path) -> None:
    module = _load_benchmark_module()

    report = module.run_benchmark(
        books_dir=tmp_path / "missing",
        run_ollama=False,
        include_synthetic=False,
    )

    assert report["include_synthetic"] is False
    assert report["cases"] == []


def test_quality_benchmark_reads_local_txt_books(tmp_path: Path) -> None:
    module = _load_benchmark_module()
    books_dir = tmp_path / "books"
    books_dir.mkdir()
    (books_dir / "sample.txt").write_text("Alpha beta.\n\nGamma delta.", encoding="utf-8")

    report = module.run_benchmark(books_dir=books_dir, run_ollama=False)

    sources = {case["source"] for case in report["cases"]}
    assert str(books_dir / "sample.txt") in sources


def test_quality_benchmark_loads_real_offline_book_formats(tmp_path: Path) -> None:
    """Exercise real loader paths for the formats a user can drop into books/."""
    module = _load_benchmark_module()
    books_dir = tmp_path / "books"
    books_dir.mkdir()
    _write_txt_book(books_dir / "sample.txt")
    _write_fb2_book(books_dir / "sample.fb2")
    _write_docx_book(books_dir / "sample.docx")
    _write_epub_book(books_dir / "sample.epub")
    _write_native_pdf_book(books_dir / "sample.pdf")

    report = module.run_benchmark(
        books_dir=books_dir,
        run_ollama=False,
        include_synthetic=False,
        languages=["ru", "en"],
        book_language="en",
        limit_books=10,
    )

    by_format = {
        case["source_format"]: case
        for case in report["cases"]
        if case.get("status") != "error"
    }
    assert {"txt", "fb2", "docx", "epub", "pdf"}.issubset(by_format)
    for source_format in ("txt", "fb2", "docx", "epub", "pdf"):
        case = by_format[source_format]
        assert case["status"] == "offline_checked"
        assert case["paragraphs"] >= 1
        assert case["chars_before"] > 20
        assert case["text_preserved"] is True
        assert case["chunks"] >= 1
    assert by_format["pdf"]["metadata_extra"]["pdf_text_variant"] == "native"


def test_quality_benchmark_filters_local_books_by_glob(tmp_path: Path) -> None:
    module = _load_benchmark_module()
    books_dir = tmp_path / "books"
    books_dir.mkdir()
    keep = books_dir / "keep.txt"
    drop = books_dir / "drop.txt"
    keep.write_text("Keep this local benchmark book.", encoding="utf-8")
    drop.write_text("Drop this local benchmark book.", encoding="utf-8")

    report = module.run_benchmark(
        books_dir=books_dir,
        run_ollama=False,
        include_synthetic=False,
        book_globs=["keep*"],
    )

    assert report["book_globs"] == ["keep*"]
    assert [case["source"] for case in report["cases"]] == [str(keep)]


def test_quality_benchmark_maps_local_book_languages_by_glob(tmp_path: Path) -> None:
    module = _load_benchmark_module()
    books_dir = tmp_path / "books"
    (books_dir / "english").mkdir(parents=True)
    (books_dir / "china").mkdir()
    english = books_dir / "english" / "dialogue.txt"
    chinese = books_dir / "china" / "dialogue.txt"
    english.write_text('Alice opened the door.\n\n"Come in," she said.', encoding="utf-8")
    chinese.write_text("李雷打开了门。\n\n“请进，”韩梅梅说。", encoding="utf-8")

    report = module.run_benchmark(
        books_dir=books_dir,
        run_ollama=False,
        include_synthetic=False,
        languages=["en", "zh"],
        book_language="ru",
        book_language_map={
            "english/*.txt": "en",
            "china/*.txt": "zh",
        },
        limit_books=10,
    )

    by_source = {case["source"]: case for case in report["cases"]}
    assert report["book_language"] == "ru"
    assert report["book_language_map"] == {
        "english/*.txt": "en",
        "china/*.txt": "zh",
    }
    assert by_source[str(english)]["language"] == "en"
    assert by_source[str(chinese)]["language"] == "zh"
    assert all(case["status"] == "offline_checked" for case in by_source.values())


def test_quality_benchmark_loads_language_map_from_json(tmp_path: Path) -> None:
    module = _load_benchmark_module()
    mapping_path = tmp_path / "languages.json"
    mapping_path.write_text(
        json.dumps({"english/*.txt": "en", "kazakh/*.txt": "kk"}, ensure_ascii=False),
        encoding="utf-8",
    )

    assert module._load_book_language_map(str(mapping_path)) == {
        "english/*.txt": "en",
        "kazakh/*.txt": "kk",
    }


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


def test_quality_benchmark_formats_human_review_summary() -> None:
    module = _load_benchmark_module()
    report = {
        "created_at": "2026-05-25T00:00:00+00:00",
        "run_ollama": True,
        "primary_model": "qwen",
        "cases": [
            {
                "source": "synthetic",
                "language": "ru",
                "status": "ok",
                "chars_before": 42,
                "segments": 2,
                "chunks": 2,
                "text_preserved": True,
                "segments_preserve_text": True,
                "chunk_text_preserved": True,
            },
            {
                "source": "books/example.pdf",
                "language": "ru",
                "status": "review_required",
                "chars_before": 300,
                "segments": 4,
                "chunks": 1,
                "text_preserved": True,
                "segments_preserve_text": False,
                "chunk_text_preserved": True,
                "llm_rejected": 1,
                "error": "segment/chunk mismatch",
            },
        ],
    }

    markdown = module.format_markdown_report(report)

    assert "# Books to Audio Quality Benchmark" in markdown
    assert "| 1 | ok | ru | synthetic | 42 | 2 | 2 | yes |  |" in markdown
    assert (
        "| 2 | review_required | ru | books/example.pdf | 300 | 4 | 1 | no | "
        "LLM rejected 1; segment/chunk mismatch |"
    ) in markdown


def test_quality_benchmark_records_llm_review_reports(tmp_path: Path, monkeypatch) -> None:
    module = _load_benchmark_module()
    review_dir = tmp_path / "llm_reviews"
    seen: dict[str, Path | str] = {}

    class FakeNormalizer:
        def __init__(self, *, language, review_report_path, **kwargs):  # noqa: ANN001
            seen["normalizer_language"] = language
            seen["normalizer_path"] = review_report_path

        def normalize_book(self, book):  # noqa: ANN001
            path = seen["normalizer_path"]
            assert isinstance(path, Path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"requires_human_review": false}', encoding="utf-8")
            for chapter in book.chapters:
                for paragraph in chapter.paragraphs:
                    paragraph.normalized_text = paragraph.raw_text
            return 1, 0

    class FakeSegmenter:
        def __init__(self, *, language, review_report_path, **kwargs):  # noqa: ANN001
            seen["segmenter_language"] = language
            seen["segmenter_path"] = review_report_path

        def segment_book(self, book):  # noqa: ANN001
            path = seen["segmenter_path"]
            assert isinstance(path, Path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"requires_human_review": false}', encoding="utf-8")
            text = book.normalized_text or book.raw_text
            return [
                {
                    "segment_index": 0,
                    "chapter_index": 0,
                    "language": book.metadata.language,
                    "is_dialogue": True,
                    "role": "unknown",
                    "voice_id": "narrator_calm",
                    "intonation": "calm",
                    "text": text,
                    "pause_after_ms": 0,
                    "boundary_after": "chapter",
                }
            ]

    monkeypatch.setattr(module, "LlmNormalizer", FakeNormalizer)
    monkeypatch.setattr(module, "LlmVoiceSegmenter", FakeSegmenter)

    report = module.run_benchmark(
        books_dir=tmp_path / "missing",
        run_ollama=True,
        languages=["en"],
        review_dir=review_dir,
    )

    case = report["cases"][0]
    normalizer_path = seen["normalizer_path"]
    segmenter_path = seen["segmenter_path"]
    assert seen["normalizer_language"] == "en"
    assert seen["segmenter_language"] == "en"
    assert isinstance(normalizer_path, Path)
    assert isinstance(segmenter_path, Path)
    assert normalizer_path.parent == review_dir
    assert segmenter_path.parent == review_dir
    assert normalizer_path != segmenter_path
    assert normalizer_path.exists()
    assert segmenter_path.exists()
    assert case["status"] == "ok"
    assert case["llm_normalization_review_report"] == str(normalizer_path)
    assert case["llm_segmentation_review_report"] == str(segmenter_path)
    assert "normalization review:" in module.format_markdown_report(report)
    assert "segmentation review:" in module.format_markdown_report(report)


def test_quality_benchmark_requires_dialogue_segments_for_dialogue_sources(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_benchmark_module()

    class FakeNormalizer:
        def __init__(self, **_kwargs):  # noqa: ANN003
            pass

        def normalize_book(self, book):  # noqa: ANN001
            for chapter in book.chapters:
                for paragraph in chapter.paragraphs:
                    paragraph.normalized_text = paragraph.raw_text
            return 1, 0

    class BadSegmenter:
        def __init__(self, **_kwargs):  # noqa: ANN003
            pass

        def segment_book(self, book):  # noqa: ANN001
            return [
                {
                    "segment_index": 0,
                    "chapter_index": 0,
                    "language": book.metadata.language,
                    "is_dialogue": False,
                    "role": "narrator",
                    "voice_id": "narrator_calm",
                    "intonation": "calm",
                    "text": book.normalized_text or book.raw_text,
                    "pause_after_ms": 0,
                    "boundary_after": "chapter",
                }
            ]

    monkeypatch.setattr(module, "LlmNormalizer", FakeNormalizer)
    monkeypatch.setattr(module, "LlmVoiceSegmenter", BadSegmenter)

    report = module.run_benchmark(
        books_dir=tmp_path / "missing",
        run_ollama=True,
        languages=["en"],
    )

    case = report["cases"][0]
    assert case["expected_dialogue"] is True
    assert case["dialogue_segments"] == 0
    assert case["status"] == "review_required"
    assert "no dialogue segments" in case["error"]


def test_quality_benchmark_pdf_ocr_error_points_to_native_installer(tmp_path: Path) -> None:
    module = _load_benchmark_module()
    pdf_path = tmp_path / "scan.pdf"

    case = module._error_case(
        pdf_path,
        RuntimeError("PDF text unreadable and OCR unavailable/unusable: ocr_unavailable_native_unreadable"),
    )
    markdown = module.format_markdown_report({"cases": [case]})

    assert case["install_hint"] == module.OCR_INSTALL_HINT
    assert "install.bat --interactive --install-system-tools" in markdown
    assert "./install.sh --interactive --install-system-tools" in markdown
    assert "wsl" not in markdown.lower()


def _write_txt_book(path: Path) -> None:
    path.write_text(
        "TXT Chapter\n\nAlpha opened the door.\n\n\"Who is there?\" he asked.",
        encoding="utf-8",
    )


def _write_fb2_book(path: Path) -> None:
    path.write_text(
        """\
<?xml version="1.0" encoding="utf-8"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">
  <description>
    <title-info>
      <book-title>FB2 Sample</book-title>
      <author><first-name>Ivan</first-name><last-name>Petrov</last-name></author>
      <lang>ru</lang>
    </title-info>
  </description>
  <body>
    <section>
      <title><p>Глава первая</p></title>
      <p>Сергей открыл дверь.</p>
      <p>— Кто там? — спросил он.</p>
    </section>
  </body>
</FictionBook>
""",
        encoding="utf-8",
    )


def _write_docx_book(path: Path) -> None:
    docx = pytest.importorskip("docx")
    doc = docx.Document()
    doc.core_properties.title = "DOCX Sample"
    doc.add_heading("Chapter One", level=1)
    doc.add_paragraph("Maya checked the old map.")
    doc.add_paragraph("\"The road bends here,\" she said.")
    doc.save(str(path))


def _write_epub_book(path: Path) -> None:
    epub = pytest.importorskip("ebooklib.epub")
    book = epub.EpubBook()
    book.set_identifier("sample-epub")
    book.set_title("EPUB Sample")
    book.set_language("en")
    chapter = epub.EpubHtml(title="Chapter One", file_name="chapter.xhtml", lang="en")
    chapter.content = (
        "<html><body><h1>Chapter One</h1>"
        "<p>Li Wei lit the lantern.</p>"
        "<p>\"We leave at dawn,\" he said.</p>"
        "</body></html>"
    )
    book.add_item(chapter)
    book.spine = ["nav", chapter]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    epub.write_epub(str(path), book)


def _write_native_pdf_book(path: Path) -> None:
    fitz = pytest.importorskip("fitz")
    doc = fitz.open()
    page = doc.new_page(width=420, height=595)
    page.insert_text((48, 72), "Chapter One", fontsize=16)
    page.insert_text((48, 110), "The native PDF text layer is readable.", fontsize=12)
    page.insert_text((48, 132), '"No OCR should be needed," Nora said.', fontsize=12)
    doc.save(path)
    doc.close()
