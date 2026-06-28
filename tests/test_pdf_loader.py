"""Tests for the PDF loader."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from book_normalizer.chaptering.detector import ChapterDetector
from book_normalizer.config import OcrMode
from book_normalizer.loaders.pdf_loader import (
    PdfLoader,
    PdfOcrCompareResult,
    PdfPageExtraction,
    PdfStructuredExtraction,
    PdfTextVariant,
    _classify_pdf_page,
    _extract_pdf_structured,
    _looks_like_toc,
    _postprocess_ocr_text,
    _prepare_ocr_page_images,
    _repair_ocr_cross_segment_breaks,
    _should_keep_ocr_text,
    _should_use_fast_native_pdf_extraction,
    _table_converter,
    extract_pdf_with_ocr_mode,
    select_pdf_text_for_mode,
)


def _scan_like_png_bytes(width: int = 500, height: int = 700) -> bytes:
    """Create a simple scan-like image with dark text bars."""
    pil_image = pytest.importorskip("PIL.Image")
    image_draw = pytest.importorskip("PIL.ImageDraw")

    image = pil_image.new("L", (width, height), 255)
    draw = image_draw.Draw(image)
    x_margin = max(10, width // 10)
    y_margin = max(10, height // 10)
    line_height = max(4, height // 90)
    line_gap = max(12, height // 22)
    for y in range(y_margin, height - y_margin, line_gap):
        draw.rectangle((x_margin, y, width - x_margin, y + line_height), fill=0)

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _write_image_only_pdf(path: Path) -> None:
    """Write a PDF page that is only a full-page image."""
    fitz = pytest.importorskip("fitz")

    doc = fitz.open()
    page = doc.new_page(width=500, height=700)
    page.insert_image(page.rect, stream=_scan_like_png_bytes())
    doc.save(path)
    doc.close()


def _good_ocr_text() -> str:
    """Return enough readable Russian text to pass OCR quality gates."""
    return (
        "Русский распознанный текст страницы содержит несколько длинных слов "
        "и выглядит как обычный абзац художественной книги. "
    ).strip()


class TestPdfLoader:
    def test_supported_extensions(self) -> None:
        loader = PdfLoader()
        assert ".pdf" in loader.supported_extensions

    def test_can_load(self, tmp_path: Path) -> None:
        loader = PdfLoader()
        assert loader.can_load(tmp_path / "book.pdf")
        assert not loader.can_load(tmp_path / "book.txt")

    def test_large_pdf_uses_fast_native_extraction(self, tmp_path: Path) -> None:
        fitz = pytest.importorskip("fitz")
        pdf_file = tmp_path / "large.pdf"
        doc = fitz.open()
        for _ in range(31):
            page = doc.new_page()
            page.insert_text((72, 72), "Book page")
        doc.save(str(pdf_file))
        doc.close()

        assert _should_use_fast_native_pdf_extraction(pdf_file) is True

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        loader = PdfLoader()
        with pytest.raises(FileNotFoundError):
            loader.load(tmp_path / "missing.pdf")

    @patch("book_normalizer.loaders.pdf_loader.PdfLoader._extract_text")
    def test_load_with_mocked_extraction(self, mock_extract: MagicMock, tmp_path: Path) -> None:
        mock_extract.return_value = "Первый абзац.\n\nВторой абзац."

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy")

        loader = PdfLoader()
        book = loader.load(pdf_file)

        assert book.metadata.source_format == "pdf"
        assert len(book.chapters[0].paragraphs) == 2
        assert book.chapters[0].paragraphs[0].raw_text == "Первый абзац."

    @patch("book_normalizer.loaders.pdf_loader.PdfLoader._extract_text")
    def test_load_repairs_utf8_mojibake_before_paragraph_split(
        self,
        mock_extract: MagicMock,
        tmp_path: Path,
    ) -> None:
        readable = "Б. М. Моносов\n\nГлава первая\n\nСергей сидел за столом."
        mock_extract.return_value = readable.encode("utf-8").decode("latin1")
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy")

        book = PdfLoader().load(pdf_file)
        paragraphs = [p.raw_text for p in book.chapters[0].paragraphs]

        assert paragraphs == [
            "Б. М. Моносов",
            "Глава первая",
            "Сергей сидел за столом.",
        ]

    @patch("book_normalizer.loaders.pdf_loader.PdfLoader._extract_text")
    def test_load_repairs_mojibake_so_chapter_detector_finds_works(
        self,
        mock_extract: MagicMock,
        tmp_path: Path,
    ) -> None:
        readable = (
            "Книга первая\n\n"
            "Глава первая\n\n"
            "Текст первой книги.\n\n"
            "Эпилог\n\n"
            "Финал первой книги.\n\n"
            "Книга вторая\n\n"
            "Глава первая\n\n"
            "Текст второй книги."
        )
        mock_extract.return_value = readable.encode("utf-8").decode("latin1")
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy")

        book = PdfLoader().load(pdf_file)
        detected = ChapterDetector().detect_and_split(book)

        assert detected.metadata.extra["structure"]["work_count"] == 2
        assert len(detected.chapters) == 3
        assert [chapter.work_title for chapter in detected.chapters] == [
            "Книга первая",
            "Книга первая",
            "Книга вторая",
        ]
        assert detected.chapters[1].title == "Книга первая - Эпилог"

    @patch("book_normalizer.loaders.pdf_loader.PdfLoader._extract_text")
    def test_load_splits_heading_lines_embedded_in_native_pdf_blocks(
        self,
        mock_extract: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_extract.return_value = (
            "Аннотация\n"
            "Короткое описание книги.\n"
            "Книга первая\n"
            "Глава первая,\n"
            "Текст первой главы.\n"
            "Глава вторая,\n"
            "Текст второй главы.\n"
            "Эпилог\n"
            "Финал первой книги.\n"
            "Книга вторая\n"
            "Глава первая,\n"
            "Текст второй книги."
        )
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy")

        book = PdfLoader().load(pdf_file)
        detected = ChapterDetector().detect_and_split(book)

        assert len(book.chapters[0].paragraphs) == 7
        assert detected.metadata.extra["structure"]["work_count"] == 2
        assert len(detected.chapters) == 5
        assert detected.chapters[0].title == "Preamble"
        assert detected.chapters[1].title == "Книга первая - Глава первая,"
        assert detected.chapters[3].title == "Книга первая - Эпилог"

    @patch("book_normalizer.loaders.pdf_loader.PdfLoader._extract_text")
    def test_load_repairs_drop_cap_after_embedded_chapter_heading(
        self,
        mock_extract: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_extract.return_value = (
            "Глава первая,\n"
            "повествующая в общем-то ни о чем\n"
            "глубокое исследование этого предмета\n"
            "ергей сидел за столом и пил чай."
        )
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy")

        book = PdfLoader().load(pdf_file)

        assert "Сергей сидел за столом" in book.raw_text
        assert "\nергей сидел за столом" not in book.raw_text

    @patch("book_normalizer.loaders.pdf_loader.PdfLoader._extract_text")
    def test_audit_trail(self, mock_extract: MagicMock, tmp_path: Path) -> None:
        mock_extract.return_value = "Текст."
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy")

        loader = PdfLoader()
        book = loader.load(pdf_file)
        assert any(r["stage"] == "loading" for r in book.audit_trail)

    @patch("book_normalizer.loaders.pdf_loader.PdfLoader._extract_text")
    def test_reflows_isolated_justified_words_into_parenthetical_gap(
        self,
        mock_extract: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_extract.return_value = (
            "Гор спросил (мир\n\n"
            "ему\n\n"
            "особенно\n\n"
            "по\n\n"
            "пятницам). Новый абзац."
        )
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy")

        book = PdfLoader().load(pdf_file)
        paragraphs = [p.raw_text for p in book.chapters[0].paragraphs]

        assert paragraphs == [
            "Гор спросил (мир ему особенно по пятницам). Новый абзац.",
        ]

    @patch("book_normalizer.loaders.pdf_loader.PdfLoader._extract_text")
    def test_reflows_isolated_justified_words_inside_final_parenthetical(
        self,
        mock_extract: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_extract.return_value = (
            "Гор спросил (мир\nпятницам). Я ответил.\n\n"
            "ему\n\n"
            "особенно\n\n"
            "по\n\n"
            "Новый абзац."
        )
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy")

        book = PdfLoader().load(pdf_file)
        paragraphs = [p.raw_text for p in book.chapters[0].paragraphs]

        assert paragraphs == [
            "Гор спросил (мир ему особенно по пятницам). Я ответил.",
            "Новый абзац.",
        ]

    @patch("book_normalizer.loaders.pdf_loader.PdfLoader._extract_text")
    def test_reflows_parenthetical_page_break_words(
        self,
        mock_extract: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_extract.return_value = (
            "Талисманы эти ничем взгляд)).\n\n"
            "не\n\n"
            "были\n\n"
            "заряжены\n\n"
            "(на\n\n"
            "мой\n\n"
            "Пока я извинялся."
        )
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy")

        book = PdfLoader().load(pdf_file)
        paragraphs = [p.raw_text for p in book.chapters[0].paragraphs]

        assert paragraphs == [
            "Талисманы эти ничем не были заряжены (на мой взгляд)).",
            "Пока я извинялся.",
        ]


class TestOcrModeSelection:
    def test_extract_pdf_with_ocr_mode_off_returns_only_native(self, tmp_path: Path) -> None:
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy")

        with patch.object(PdfLoader, "_extract_text", return_value="native text"):
            result = extract_pdf_with_ocr_mode(pdf_file, OcrMode.OFF)

        assert result.native.text == "native text"
        assert result.ocr is None

    def test_select_pdf_text_for_mode_off_uses_native(self) -> None:
        compare = PdfOcrCompareResult(
            native=PdfTextVariant(kind="native", text="native"),
            ocr=PdfTextVariant(kind="ocr", text="ocr"),
        )
        chosen, stats = select_pdf_text_for_mode(compare, OcrMode.OFF)
        assert chosen.kind == "native"
        assert stats["selected"] == "native"

    def test_select_pdf_text_for_mode_force_uses_ocr(self) -> None:
        compare = PdfOcrCompareResult(
            native=PdfTextVariant(kind="native", text="native"),
            ocr=PdfTextVariant(kind="ocr", text="ocr"),
        )
        chosen, stats = select_pdf_text_for_mode(compare, OcrMode.FORCE)
        assert chosen.kind == "ocr"
        assert stats["selected"] == "ocr"

    def test_select_pdf_text_for_mode_image_uses_ocr_even_when_native_is_readable(self) -> None:
        compare = PdfOcrCompareResult(
            native=PdfTextVariant(
                kind="native",
                text="Родной читаемый текст PDF слоя с русскими словами.",
            ),
            ocr=PdfTextVariant(
                kind="ocr",
                text="Распознанный текст с отрендеренной страницы книги.",
            ),
        )

        chosen, stats = select_pdf_text_for_mode(compare, OcrMode.IMAGE)

        assert chosen.kind == "ocr"
        assert stats["selected"] == "ocr"
        assert stats["reason"] == "image_mode_full_page_ocr"

    def test_select_pdf_text_for_mode_auto_falls_back_when_native_empty(self) -> None:
        compare = PdfOcrCompareResult(
            native=PdfTextVariant(kind="native", text="   "),
            ocr=PdfTextVariant(kind="ocr", text="Распознанный русский текст"),
        )
        chosen, stats = select_pdf_text_for_mode(compare, OcrMode.AUTO)
        assert chosen.kind == "ocr"
        assert stats["selected"] == "ocr"
        assert stats["ocr_unreadable"] is False

    def test_select_pdf_text_for_mode_auto_does_not_use_unreadable_ocr(self) -> None:
        compare = PdfOcrCompareResult(
            native=PdfTextVariant(kind="native", text="Co,11;ep'l\\:aHne rJIABA"),
            ocr=PdfTextVariant(kind="ocr", text="lorem ipsum OCR garbage"),
        )

        chosen, stats = select_pdf_text_for_mode(compare, OcrMode.AUTO)

        assert chosen.kind == "native"
        assert stats["native_unreadable"] is True
        assert stats["ocr_unreadable"] is True
        assert stats["reason"] == "auto_mode_no_readable_ocr"

    def test_select_pdf_text_for_mode_auto_prefers_native_when_not_empty(self) -> None:
        compare = PdfOcrCompareResult(
            native=PdfTextVariant(kind="native", text="Родной текст на русском языке"),
            ocr=PdfTextVariant(kind="ocr", text="Текст после распознавания"),
        )
        chosen, stats = select_pdf_text_for_mode(compare, OcrMode.AUTO)
        assert chosen.kind == "native"
        assert stats["selected"] == "native"
        assert stats["native_unreadable"] is False

    def test_select_pdf_text_for_mode_compare_uses_ocr_when_native_is_short_overlay(self) -> None:
        native = "Верёвка есть вервие простое Из учебного наставления для палачей"
        ocr_text = (
            "ГЛАВА ПЕРВАЯ Повествующая, в общем-то, ни о чем, но зато содержащая "
            "глубокое исследование этого предмета. Сергей сидел за столом и пил "
            "чай с малиновым вареньем. Состояние было весьма тоскливым. "
        ) * 20
        compare = PdfOcrCompareResult(
            native=PdfTextVariant(kind="native", text=native),
            ocr=PdfTextVariant(kind="ocr", text=ocr_text),
        )

        chosen, stats = select_pdf_text_for_mode(compare, OcrMode.COMPARE)

        assert chosen.kind == "ocr"
        assert stats["selected"] == "ocr"
        assert stats["native_unreadable"] is False
        assert stats["ocr_much_longer"] is True
        assert stats["reason"] == "compare_mode_ocr_much_longer_use_ocr"

    def test_select_pdf_text_for_mode_marks_broken_native_when_ocr_unavailable(self) -> None:
        compare = PdfOcrCompareResult(
            native=PdfTextVariant(kind="native", text="Co,11;ep'l\\:aHne rJIABA llEPBMI"),
            ocr=None,
        )

        chosen, stats = select_pdf_text_for_mode(compare, OcrMode.AUTO)

        assert chosen.kind == "native"
        assert stats["native_unreadable"] is True
        assert stats["reason"] == "ocr_unavailable_native_unreadable"

    def test_extract_pdf_with_ocr_mode_uses_full_page_fallback_after_empty_structured_ocr(
        self,
        tmp_path: Path,
    ) -> None:
        pdf_file = tmp_path / "hard_scan.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy")
        empty_structure = PdfStructuredExtraction(
            pages={1: PdfPageExtraction(page_number=1, pdf_type="scanned")},
            document_type="scanned",
        )

        with (
            patch("book_normalizer.loaders.pdf_loader._tesseract_available", return_value=True),
            patch("book_normalizer.loaders.pdf_loader._extract_pdf_structured", return_value=empty_structure),
            patch("book_normalizer.loaders.pdf_loader._ocr_pdf_with_tesseract", return_value=_good_ocr_text()),
        ):
            compare = extract_pdf_with_ocr_mode(pdf_file, OcrMode.AUTO)

        assert compare.native.text == ""
        assert compare.ocr is not None
        assert compare.ocr.text == _good_ocr_text()
        assert compare.ocr.document_type == "ocr_full_page"

    def test_extract_pdf_with_ocr_mode_uses_full_page_ocr_for_unreadable_native_layer(
        self,
        tmp_path: Path,
    ) -> None:
        pdf_file = tmp_path / "bad_text_layer_scan.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy")
        native_structure = PdfStructuredExtraction(
            pages={
                1: PdfPageExtraction(
                    page_number=1,
                    pdf_type="programmatic",
                    page_content=["Co,11;ep'l\\:aHne rJIABA llEPBMI CepreM"],
                ),
            },
            document_type="programmatic",
        )

        with (
            patch("book_normalizer.loaders.pdf_loader._tesseract_available", return_value=True),
            patch("book_normalizer.loaders.pdf_loader._extract_pdf_structured") as structured,
            patch("book_normalizer.loaders.pdf_loader._ocr_pdf_with_tesseract", return_value=_good_ocr_text()),
        ):
            structured.return_value = native_structure
            compare = extract_pdf_with_ocr_mode(pdf_file, OcrMode.COMPARE)

        assert structured.call_count == 1
        assert compare.native.text.startswith("Co,11")
        assert compare.ocr is not None
        assert compare.ocr.text == _good_ocr_text()
        assert compare.ocr.document_type == "ocr_full_page"

    def test_extract_pdf_with_ocr_mode_image_uses_full_page_ocr_with_readable_native_layer(
        self,
        tmp_path: Path,
    ) -> None:
        pdf_file = tmp_path / "readable_text_layer.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy")
        native_structure = PdfStructuredExtraction(
            pages={
                1: PdfPageExtraction(
                    page_number=1,
                    pdf_type="programmatic",
                    page_content=["Родной текстовый слой достаточно читаем."],
                ),
            },
            document_type="programmatic",
        )

        with (
            patch("book_normalizer.loaders.pdf_loader._tesseract_available", return_value=True),
            patch("book_normalizer.loaders.pdf_loader._extract_pdf_structured") as structured,
            patch(
                "book_normalizer.loaders.pdf_loader._ocr_pdf_with_tesseract",
                return_value=_good_ocr_text(),
            ) as full_page_ocr,
        ):
            structured.return_value = native_structure
            compare = extract_pdf_with_ocr_mode(pdf_file, OcrMode.IMAGE)

        assert compare.native.text.startswith("Родной")
        assert compare.ocr is not None
        assert compare.ocr.text == _good_ocr_text()
        assert compare.ocr.document_type == "ocr_full_page"
        full_page_ocr.assert_called_once()
        assert [call.kwargs["run_ocr"] for call in structured.call_args_list] == [False]

    def test_extract_pdf_with_ocr_mode_does_not_repeat_full_page_ocr_for_unreadable_results(
        self,
        tmp_path: Path,
    ) -> None:
        pdf_file = tmp_path / "unreadable_scan.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy")
        native_structure = PdfStructuredExtraction(
            pages={
                1: PdfPageExtraction(
                    page_number=1,
                    pdf_type="programmatic",
                    page_content=["Co,11;ep'l\\:aHne rJIABA llEPBMI CepreM"],
                ),
            },
            document_type="programmatic",
        )

        with (
            patch("book_normalizer.loaders.pdf_loader._tesseract_available", return_value=True),
            patch("book_normalizer.loaders.pdf_loader._extract_pdf_structured", return_value=native_structure),
            patch(
                "book_normalizer.loaders.pdf_loader._ocr_pdf_with_tesseract",
                return_value="lorem ipsum OCR garbage",
            ) as full_page_ocr,
        ):
            compare = extract_pdf_with_ocr_mode(pdf_file, OcrMode.AUTO)

        full_page_ocr.assert_called_once()
        assert compare.native.text.startswith("Co,11")
        assert compare.ocr is not None
        assert compare.ocr.text == "lorem ipsum OCR garbage"
        assert compare.ocr.document_type == "ocr_full_page"

    def test_missing_tesseract_warning_points_to_native_install_scripts(
        self,
        tmp_path: Path,
    ) -> None:
        pdf_file = tmp_path / "native.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy")
        native_structure = PdfStructuredExtraction(
            pages={
                1: PdfPageExtraction(
                    page_number=1,
                    pdf_type="programmatic",
                    page_content=["Readable native PDF text."],
                )
            },
            document_type="programmatic",
        )

        with (
            patch("book_normalizer.loaders.pdf_loader._extract_pdf_structured", return_value=native_structure),
            patch("book_normalizer.loaders.pdf_loader._tesseract_available", return_value=False),
            patch("book_normalizer.loaders.pdf_loader.logger.warning") as warning,
        ):
            compare = extract_pdf_with_ocr_mode(pdf_file, OcrMode.FORCE)

        assert compare.ocr is None
        warning.assert_called_once()
        warning_text = str(warning.call_args.args[0])
        assert "install.bat --interactive --install-system-tools --download-tessdata" in warning_text
        assert "./install.sh --interactive --install-system-tools --download-tessdata" in warning_text
        assert "wsl" not in warning_text.lower()


class TestStructuredPdfExtractionHelpers:
    def test_table_converter_keeps_multiline_cells_in_one_row(self) -> None:
        table = [
            ["Имя", "Описание"],
            ["Герой", "первая строка\nвторая строка"],
            [None, ""],
        ]

        converted = _table_converter(table)

        assert converted == "Имя | Описание\nГерой | первая строка вторая строка"

    def test_classify_pdf_page_distinguishes_pdf_types(self) -> None:
        assert (
            _classify_pdf_page(text_chars=200, table_count=0, image_area_ratio=0.1)
            == "programmatic"
        )
        assert (
            _classify_pdf_page(text_chars=0, table_count=0, image_area_ratio=0.9)
            == "scanned"
        )
        assert (
            _classify_pdf_page(text_chars=200, table_count=0, image_area_ratio=0.9)
            == "scanned_with_ocr"
        )
        assert (
            _classify_pdf_page(text_chars=0, table_count=0, image_area_ratio=0.0, image_text_count=1)
            == "scanned"
        )

    def test_structured_extraction_assembles_page_content_in_page_order(self) -> None:
        structured = PdfStructuredExtraction(
            pages={
                2: PdfPageExtraction(page_number=2, page_content=["Вторая страница"]),
                1: PdfPageExtraction(page_number=1, page_content=["Текст", "Таблица"]),
            },
            document_type="mixed",
        )

        assert structured.to_text() == "Текст\n\nТаблица\n\nВторая страница"

    def test_extract_pdf_structured_reads_programmatic_pdf(self, tmp_path: Path) -> None:
        fitz = pytest.importorskip("fitz")
        pytest.importorskip("pdfminer")
        pytest.importorskip("pdfplumber")

        pdf_file = tmp_path / "generated.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text(
            (72, 72),
            "Chapter one: this generated PDF has a searchable text layer for structural extraction.",
        )
        doc.save(pdf_file)
        doc.close()

        structured = _extract_pdf_structured(pdf_file, run_ocr=False)

        assert structured.document_type == "programmatic"
        assert "Chapter one" in structured.to_text()
        assert structured.pages[1].page_text
        assert structured.pages[1].line_format

    def test_extract_pdf_structured_extracts_pdfplumber_table(self, tmp_path: Path) -> None:
        fitz = pytest.importorskip("fitz")
        pytest.importorskip("pdfminer")
        pytest.importorskip("pdfplumber")

        pdf_file = tmp_path / "table.pdf"
        doc = fitz.open()
        page = doc.new_page(width=500, height=700)
        left, top, width, height = 72, 100, 300, 90
        for x in (left, left + 150, left + width):
            page.draw_line((x, top), (x, top + height), color=(0, 0, 0), width=1)
        for y in (top, top + 45, top + height):
            page.draw_line((left, y), (left + width, y), color=(0, 0, 0), width=1)
        page.insert_text((left + 10, top + 27), "Name", fontsize=10)
        page.insert_text((left + 160, top + 27), "Value", fontsize=10)
        page.insert_text((left + 10, top + 72), "Alpha", fontsize=10)
        page.insert_text((left + 160, top + 72), "42", fontsize=10)
        doc.save(pdf_file)
        doc.close()

        structured = _extract_pdf_structured(pdf_file, run_ocr=False)

        assert structured.document_type == "programmatic"
        assert structured.pages[1].text_from_tables == ["Name | Value\nAlpha | 42"]
        assert structured.pages[1].page_content == ["Name | Value\nAlpha | 42"]

    def test_extract_pdf_structured_classifies_image_only_scan_without_ocr(self, tmp_path: Path) -> None:
        pytest.importorskip("pdfminer")
        pytest.importorskip("pdfplumber")

        pdf_file = tmp_path / "scan.pdf"
        _write_image_only_pdf(pdf_file)

        structured = _extract_pdf_structured(pdf_file, run_ocr=False)

        assert structured.document_type == "scanned"
        assert structured.pages[1].pdf_type == "scanned"
        assert structured.pages[1].page_content == []

    def test_extract_pdf_structured_ocr_reads_good_image_only_scan(self, tmp_path: Path) -> None:
        pytest.importorskip("pdfminer")
        pytest.importorskip("pdfplumber")

        pdf_file = tmp_path / "scan_good_ocr.pdf"
        _write_image_only_pdf(pdf_file)

        with (
            patch("book_normalizer.loaders.pdf_loader._load_tesseract_runtime", return_value=("pytesseract", object())),
            patch("book_normalizer.loaders.pdf_loader._ocr_rendered_image", return_value=_good_ocr_text()),
        ):
            structured = _extract_pdf_structured(pdf_file, run_ocr=True)

        assert structured.document_type == "scanned"
        assert structured.pages[1].text_from_images == [_good_ocr_text()]
        assert structured.to_text() == _good_ocr_text()

    def test_extract_pdf_structured_rejects_poor_quality_scan_ocr(self, tmp_path: Path) -> None:
        pytest.importorskip("pdfminer")
        pytest.importorskip("pdfplumber")

        pdf_file = tmp_path / "scan_bad_ocr.pdf"
        _write_image_only_pdf(pdf_file)

        with (
            patch("book_normalizer.loaders.pdf_loader._load_tesseract_runtime", return_value=("pytesseract", object())),
            patch("book_normalizer.loaders.pdf_loader._ocr_rendered_image", return_value="||| 123 !!!"),
        ):
            structured = _extract_pdf_structured(pdf_file, run_ocr=True)

        assert structured.document_type == "scanned"
        assert structured.pages[1].text_from_images == []
        assert structured.to_text() == ""

    def test_extract_pdf_structured_detects_scanned_pdf_with_existing_ocr_layer(self, tmp_path: Path) -> None:
        fitz = pytest.importorskip("fitz")
        pytest.importorskip("pdfminer")
        pytest.importorskip("pdfplumber")

        pdf_file = tmp_path / "scan_with_ocr_layer.pdf"
        doc = fitz.open()
        page = doc.new_page(width=500, height=700)
        page.insert_image(page.rect, stream=_scan_like_png_bytes())
        page.insert_text(
            (60, 100),
            "This scan already has a searchable OCR text layer with enough characters to classify it.",
            fontsize=10,
        )
        doc.save(pdf_file)
        doc.close()

        structured = _extract_pdf_structured(pdf_file, run_ocr=False)

        assert structured.document_type == "scanned_with_ocr"
        assert structured.pages[1].pdf_type == "scanned_with_ocr"
        assert "searchable OCR text layer" in structured.to_text()

    def test_extract_pdf_structured_adds_ocr_from_small_hybrid_image(self, tmp_path: Path) -> None:
        fitz = pytest.importorskip("fitz")
        pytest.importorskip("pdfminer")
        pytest.importorskip("pdfplumber")

        pdf_file = tmp_path / "hybrid.pdf"
        doc = fitz.open()
        page = doc.new_page(width=500, height=700)
        page.insert_text(
            (72, 72),
            "Readable generated text layer long enough to keep native extraction as the primary component.",
            fontsize=11,
        )
        page.insert_image(fitz.Rect(72, 150, 232, 230), stream=_scan_like_png_bytes(width=160, height=80))
        doc.save(pdf_file)
        doc.close()

        logo_text = "Логотип издательства"
        with (
            patch("book_normalizer.loaders.pdf_loader._load_tesseract_runtime", return_value=("pytesseract", object())),
            patch("book_normalizer.loaders.pdf_loader._ocr_rendered_image", return_value=logo_text),
        ):
            structured = _extract_pdf_structured(pdf_file, run_ocr=True)

        assert structured.document_type == "mixed"
        assert structured.pages[1].pdf_type == "hybrid"
        assert structured.pages[1].text_from_images == [logo_text]
        assert "Readable generated text layer" in structured.to_text()
        assert logo_text in structured.to_text()


class TestOcrImagePreparation:
    def test_prepare_ocr_page_images_splits_landscape_spread(self) -> None:
        pil_image = pytest.importorskip("PIL.Image")

        img = pil_image.new("L", (1000, 600), 255)
        for x0 in (120, 620):
            for y in range(120, 480, 18):
                for x in range(x0, x0 + 260):
                    img.putpixel((x, y), 0)

        segments = _prepare_ocr_page_images(img)

        assert len(segments) == 2
        assert all(segment.size[0] < img.size[0] for segment in segments)

    def test_postprocess_ocr_text_drops_noise_and_joins_hyphenation(self) -> None:
        raw = "' \\\\ . p .\nСОДЕРЖА-\nЩАЯ ГЛУБОКОЕ\nисследование предмета ^^: #2"

        cleaned = _postprocess_ocr_text(raw)

        assert "p ." not in cleaned
        assert "СОДЕРЖАЩАЯ ГЛУБОКОЕ исследование предмета" in cleaned
        assert "#2" not in cleaned

    @pytest.mark.parametrize(
        ("language", "raw", "expected"),
        [
            (
                "en",
                "Chapter One.\nIt was a clear autumn morning.\nMargaret said good morning.",
                "Chapter One. It was a clear autumn morning. Margaret said good morning.",
            ),
            (
                "zh",
                "第一章。\n这是一个晴朗的秋日早晨。\n旁白平静地描写房间。",
                "第一章。 这是一个晴朗的秋日早晨。 旁白平静地描写房间。",
            ),
            (
                "kk",
                "Бірінші тарау.\nБұл ашық күзгі таң еді.\nБаяндаушы тыныш қаланы суреттеді.",
                "Бірінші тарау. Бұл ашық күзгі таң еді. Баяндаушы тыныш қаланы суреттеді.",
            ),
            (
                "uz",
                "Birinchi bob.\nBu yorug kuz tongi edi.\nHikoyachi sokin shaharni tasvirladi.",
                "Birinchi bob. Bu yorug kuz tongi edi. Hikoyachi sokin shaharni tasvirladi.",
            ),
        ],
    )
    def test_postprocess_ocr_text_preserves_supported_non_russian_languages(
        self,
        language: str,
        raw: str,
        expected: str,
    ) -> None:
        cleaned = _postprocess_ocr_text(raw, language_code=language)

        assert cleaned == expected

    def test_postprocess_ocr_text_removes_inline_pipe_noise_before_dialogue(self) -> None:
        raw = (
            "Он нахватался зайчиков. Го | Фаланга пошла.\n"
            "Песок: о РЕ Г | — Гера, ты помнишь?\n"
            "воины под.при- | крытием щитов"
        )

        cleaned = _postprocess_ocr_text(raw)

        assert "Го |" not in cleaned
        assert "РЕ Г |" not in cleaned
        assert "Он нахватался зайчиков. Фаланга пошла." in cleaned
        assert "Песок: — Гера, ты помнишь?" in cleaned
        assert "под прикрытием" in cleaned

    def test_postprocess_ocr_text_removes_glued_page_numbers(self) -> None:
        raw = (
            "снежный ком. | 5\n"
            "Сергей представил себе картину битвы."
        )

        cleaned = _postprocess_ocr_text(raw)

        assert "| 5" not in cleaned
        assert "ком. Сергей" in cleaned
        assert "ком. 5 Сергей" not in cleaned

    def test_postprocess_ocr_text_drops_short_debris_paragraphs(self) -> None:
        raw = (
            "Сергей открыл дверь. ^ й В по\n\n"
            "и. = т р. НН: | с.\n\n"
            "Затем он вернулся на кухню."
        )

        cleaned = _postprocess_ocr_text(raw)

        assert "^ й В по" not in cleaned
        assert "НН:" not in cleaned
        assert "Сергей открыл дверь." in cleaned
        assert "Затем он вернулся на кухню." in cleaned

    def test_postprocess_ocr_text_removes_inline_symbol_clusters(self) -> None:
        raw = (
            "Это же Геркулес, - закричали воины. ^ г: Сергей поднялся.\n"
            "Он за него возьмусь. ^ :` | Гроза началась."
        )

        cleaned = _postprocess_ocr_text(raw)

        assert "^" not in cleaned
        assert "|" not in cleaned
        assert "воины. Сергей поднялся" in cleaned
        assert "возьмусь. Гроза началась" in cleaned

    def test_postprocess_ocr_text_uses_backtick_as_word_boundary(self) -> None:
        raw = "Сергей`поднял руку. Герасим меж ТЕМ‘трансформировал облик."

        cleaned = _postprocess_ocr_text(raw)

        assert "Сергей поднял" in cleaned
        assert "ТЕМ трансформировал" in cleaned

    def test_postprocess_ocr_text_removes_short_token_runs(self) -> None:
        raw = "Уходите, там смерть, туда нельзя, — крикнул он; 2 3 КО и СР НЕ Воспоминание окончилось."

        cleaned = _postprocess_ocr_text(raw)

        assert "2 3" not in cleaned
        assert "СР НЕ" not in cleaned
        assert "он. Воспоминание" in cleaned

    def test_postprocess_ocr_text_removes_leftover_forbidden_symbols(self) -> None:
        raw = (
            "Льготы? — переспросил старший монах. |!\n\n"
            "Сатисфакции? ®› и. Нет мадам.\n\n"
            "Ответил Сергей с. 7:\n\n"
            "Подземных {сооружений и церквей №.\n\n"
            "Конец первой части & ^ © ° < > и:\n\n"
            "страница 7:"
        )

        cleaned = _postprocess_ocr_text(raw)

        assert "|" not in cleaned
        assert "^" not in cleaned
        assert "&" not in cleaned
        assert "®" not in cleaned
        assert "№" not in cleaned
        assert "{" not in cleaned
        assert "©" not in cleaned
        assert "страница 7" not in cleaned
        assert "с. 7" not in cleaned
        assert "Льготы? — переспросил старший монах." in cleaned
        assert "Ответил Сергей" in cleaned
        assert "Конец первой части" in cleaned
        assert "части и:" not in cleaned

    def test_postprocess_ocr_text_removes_short_noisy_fragments(self) -> None:
        raw = (
            "Герасим меж ТЕМ‘трансформировал облик. ««- 1. тЫ РИ. - Это же Геркулес.\n"
            "Рыжую шевелюру.“ —.. и . — Феб здесь.: Сергей`поднял руку.\n"
            "Габриель, деточка, разберись с этими жуликами. Бет а\n"
            "Ангел появился с мечом. . . И у. ЕО С ЕЁ\n"
            "дей ии р один р: к « Н к,. + Вы больше не требуете сатисфакции?\n"
            "Нет мадам, совершенно точно нет. „ — . .# г о . Из разговора.\n"
            "Уходите, там смерть, туда нельзя, — крикнул он; Воспоминание окончилось.\n"
            "Он спросил. — Да. Она ответила."
        )

        cleaned = _postprocess_ocr_text(raw)

        assert "тЫ РИ" not in cleaned
        assert "—.." not in cleaned
        assert "Бет а" not in cleaned
        assert "ЕО С ЕЁ" not in cleaned
        assert "дей ии" not in cleaned
        assert "# г о" not in cleaned
        assert "жуликами. Ангел появился" in cleaned
        assert "Вы больше не требуете сатисфакции?" in cleaned
        assert "нет. Из разговора" in cleaned
        assert "здесь. Сергей поднял" in cleaned
        assert "крикнул он. Воспоминание" in cleaned
        assert "Он спросил. — Да. Она ответила." in cleaned

    def test_postprocess_ocr_text_removes_leading_scan_debris(self) -> None:
        raw = ". . - у . Краткость - родная сестра таланта.\n\n2: Я закопал клад здесь."

        cleaned = _postprocess_ocr_text(raw)

        assert ". . - у ." not in cleaned
        assert cleaned.startswith("Краткость - родная сестра таланта.")
        assert "\n\nЯ закопал клад здесь." in cleaned

    def test_postprocess_ocr_text_keeps_dialogue_dash_after_leading_cleanup(self) -> None:
        raw = "— Белые гиббоны обитали в Лимурии.\n— Вранье."

        cleaned = _postprocess_ocr_text(raw)

        assert cleaned.startswith("— Белые гиббоны")
        assert "— Вранье." in cleaned

    def test_postprocess_ocr_text_trims_noisy_chapter_heading(self) -> None:
        raw = "ГЛАВА ТРЕТЬЯ ..\n\nГЛАВА СЕДЬМАЯ о и"

        cleaned = _postprocess_ocr_text(raw)

        assert cleaned.split("\n\n") == ["ГЛАВА ТРЕТЬЯ", "ГЛАВА СЕДЬМАЯ"]

    def test_postprocess_ocr_text_removes_epigraph_source_prefix_noise(self) -> None:
        raw = (
            "Я закопал клад здесь. Не помню, _.. „ПЬЯН был. "
            "В общем, где-то же я его закопал? о. 7 Из показаний капитана Флинта"
        )

        cleaned = _postprocess_ocr_text(raw)

        assert "_.." not in cleaned
        assert "о. 7 Из" not in cleaned
        assert "ПЬЯН был" in cleaned
        assert "закопал? Из показаний капитана Флинта" in cleaned

    def test_postprocess_ocr_text_fixes_common_digit_hyphen_glitch(self) -> None:
        raw = "Ночь влекла вперед к новым 32-\nботам."

        cleaned = _postprocess_ocr_text(raw)

        assert "новым заботам" in cleaned
        assert "32" not in cleaned

    def test_repair_ocr_cross_segment_breaks_joins_split_words(self) -> None:
        raw = "Электричество, скопивш\n\nееся в атмосфере.\n\nОн держал при-\n\nкрытие."

        cleaned = _repair_ocr_cross_segment_breaks(raw)

        assert "скопившееся в атмосфере" in cleaned
        assert "прикрытие" in cleaned
        assert "скопивш\n\nееся" not in cleaned
        assert "при-\n\nкрытие" not in cleaned

    def test_repair_ocr_cross_segment_breaks_removes_joined_epigraph_noise(self) -> None:
        raw = "Он закопал клад? о. 7 Из показаний капитана Флинта"

        cleaned = _repair_ocr_cross_segment_breaks(raw)

        assert cleaned == "Он закопал клад? Из показаний капитана Флинта"

    def test_postprocess_ocr_text_keeps_chapter_heading_separate(self) -> None:
        raw = (
            "_ Веревка есть вервие простое\n"
            "Из учебного наставления для палачей\n"
            "ГЛАВА ПЕРВАЯ О\n"
            "ПОВЕСТВУЮЩАЯ, В ОБЩЕМ-ТО, НИ О ЧЕМ\n"
            "Сергей сидел за столом."
        )

        cleaned = _postprocess_ocr_text(raw)

        assert cleaned.split("\n\n") == [
            "Веревка есть вервие простое Из учебного наставления для палачей",
            "ГЛАВА ПЕРВАЯ",
            "ПОВЕСТВУЮЩАЯ, В ОБЩЕМ-ТО, НИ О ЧЕМ Сергей сидел за столом.",
        ]

    @pytest.mark.parametrize(
        ("raw_body", "expected"),
        [
            ("ПОВЕСТВУЮЩАЯ, В ОБЩЕМ-ТО, НИ О ЧЕМ ергей сидел за столом.", "Сергей сидел"),
            ("В КОТОРОЙ ПОЯВЛЯЕТСЯ НАМЕК НА СЮЖЕТ ыганка просочилась в квартиру.", "Цыганка просочилась"),
            ("СОБЫТИЯ В КОТОРОЙ РАЗВИВАЮТСЯ ВО СНЕ так, господа, у нас мало времени.", "Итак, господа"),
        ],
    )
    def test_postprocess_ocr_text_repairs_lost_decorative_drop_caps(
        self,
        raw_body: str,
        expected: str,
    ) -> None:
        raw = f"ГЛАВА ПЕРВАЯ\n{raw_body}"

        cleaned = _postprocess_ocr_text(raw)

        assert expected in cleaned

    def test_repair_isolated_layout_blocks_keeps_split_chapter_heading(self) -> None:
        from book_normalizer.loaders.pdf_loader import _repair_isolated_layout_word_blocks

        blocks = [
            "Веревка есть вервие простое.",
            "Глава",
            "первая",
            "повествующая в общем-то ни о чем",
        ]

        repaired = _repair_isolated_layout_word_blocks(blocks)

        assert "Глава" in repaired
        assert "первая" in repaired

    def test_postprocess_ocr_text_splits_inline_chapter_heading(self) -> None:
        raw = (
            "Из библии для чиновников ГЛАВА ТРЕТЬЯ -. "
            "СОБЫТИЯ В КОТОРОЙ РАЗВИВАЮТСЯ ВО СНЕ"
        )

        cleaned = _postprocess_ocr_text(raw)

        assert cleaned.split("\n\n") == [
            "Из библии для чиновников",
            "ГЛАВА ТРЕТЬЯ",
            "СОБЫТИЯ В КОТОРОЙ РАЗВИВАЮТСЯ ВО СНЕ",
        ]

    def test_should_keep_ocr_text_rejects_title_page_debris(self) -> None:
        debris = (
            "Б. М. Моносов Часть первая ‚ИТ о о ИТ ‚аа ся к о УЗО у о ВОт ли "
            "Кр а О р о Я к а с ы т два че У ть Ре ФЕ с Л Я ВЫ три процента "
            "Санкт-Петербург две тысячи шесть"
        )
        body = (
            "Сергей сидел за столом и пил чай с малиновым вареньем. "
            "Состояние было весьма тоскливым. Болели старые раны, знаменуя "
            "собой приближение грозы. С улицы парило через открытое окно."
        )

        assert _should_keep_ocr_text(debris) is False
        assert _should_keep_ocr_text(body) is True

    def test_should_keep_ocr_text_rejects_toc_blocks(self) -> None:
        toc = (
            "Содержание\n"
            "ГЛАВА ПЕРВАЯ ................................ 3\n"
            "ГЛАВА ВТОРАЯ ................................ 7\n"
            "ГЛАВА ТРЕТЬЯ ................................ 10\n"
        )

        assert _looks_like_toc(toc) is True
        assert _should_keep_ocr_text(toc) is False

    def test_should_keep_ocr_text_uses_selected_non_russian_language(self) -> None:
        english = " ".join(
            [
                "This scanned page contains readable English prose with enough",
                "ordinary words for the OCR quality gate to accept it safely.",
            ]
            * 4
        )

        assert _should_keep_ocr_text(english, "en") is True
        assert _should_keep_ocr_text(english, "ru") is False

    def test_should_keep_ocr_text_accepts_chinese_punctuation(self) -> None:
        text = (
            "第一章。这是一个晴朗的秋日早晨。玛格丽特说：早上好，师傅。"
            "旁白平静地描写房间和窗外安静的城市。"
        ) * 2

        assert _should_keep_ocr_text(text, language_code="zh") is True

    def test_select_pdf_text_for_mode_uses_selected_language_quality(self) -> None:
        native = PdfTextVariant(kind="native", text="")
        ocr = PdfTextVariant(
            kind="ocr",
            text="This is readable English text from OCR.",
        )
        compare = PdfOcrCompareResult(native=native, ocr=ocr)

        chosen, stats = select_pdf_text_for_mode(
            compare,
            OcrMode.AUTO,
            language_code="en",
        )

        assert chosen is ocr
        assert stats["language"] == "en"
        assert stats["ocr_unreadable"] is False
