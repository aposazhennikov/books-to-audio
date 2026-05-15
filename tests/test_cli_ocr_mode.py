from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from book_normalizer.cli import main
from book_normalizer.config import OcrMode


def test_process_accepts_ocr_mode_option(tmp_path: Path) -> None:
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 dummy")

    # Patch where the CLI actually references the helpers (module-level import).
    with patch(
        "book_normalizer.cli.extract_pdf_with_ocr_mode"
    ) as mock_extract, patch(
        "book_normalizer.cli.select_pdf_text_for_mode"
    ) as mock_select:
        from book_normalizer.loaders.pdf_loader import PdfOcrCompareResult, PdfTextVariant

        compare = PdfOcrCompareResult(
            native=PdfTextVariant(kind="native", text="native"),
            ocr=PdfTextVariant(kind="ocr", text="ocr"),
        )
        mock_extract.return_value = compare
        mock_select.return_value = (
            compare.ocr,
            {"selected": "ocr", "mode": OcrMode.FORCE.value, "ocr_len": 3},
        )

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["process", str(pdf_file), "--ocr-mode", "force", "--out", str(tmp_path / "out")],
        )

        assert result.exit_code == 0
        # Ensure our patched helpers were called, meaning OCR mode plumbing is active.
        mock_extract.assert_called_once()
        mock_select.assert_called_once()


def test_process_pdf_off_mode_cli_does_not_crash(tmp_path: Path) -> None:
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 dummy")

    # Avoid importing real PyMuPDF.
    with patch(
        "book_normalizer.loaders.pdf_loader.PdfLoader._extract_text",
        return_value="Some PDF text",
    ):
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["process", str(pdf_file), "--ocr-mode", "off", "--out", str(tmp_path / "out")],
        )

    assert result.exit_code == 0


def test_process_compare_report_reuses_selected_ocr_result(tmp_path: Path) -> None:
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 dummy")

    with patch(
        "book_normalizer.cli.extract_pdf_with_ocr_mode"
    ) as mock_extract, patch(
        "book_normalizer.cli.select_pdf_text_for_mode"
    ) as mock_select, patch(
        "book_normalizer.cli.write_pdf_compare_report"
    ) as mock_report:
        from book_normalizer.loaders.pdf_loader import PdfOcrCompareResult, PdfTextVariant

        compare = PdfOcrCompareResult(
            native=PdfTextVariant(kind="native", text="native"),
            ocr=PdfTextVariant(kind="ocr", text="ocr"),
        )
        mock_extract.return_value = compare
        mock_select.return_value = (
            compare.ocr,
            {"selected": "ocr", "mode": OcrMode.COMPARE.value},
        )

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "process",
                str(pdf_file),
                "--ocr-mode",
                "compare",
                "--ocr-dpi",
                "333",
                "--ocr-psm",
                "4",
                "--out",
                str(tmp_path / "out"),
            ],
        )

        assert result.exit_code == 0
        mock_extract.assert_called_once_with(
            pdf_file, OcrMode.COMPARE, dpi=333, psm=4,
        )
        mock_select.assert_called_once_with(compare, OcrMode.COMPARE)
        mock_report.assert_called_once()


def test_process_pdf_auto_rejects_unreadable_native_without_ocr(tmp_path: Path) -> None:
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 dummy")

    with patch(
        "book_normalizer.cli.extract_pdf_with_ocr_mode"
    ) as mock_extract, patch(
        "book_normalizer.cli.select_pdf_text_for_mode"
    ) as mock_select:
        from book_normalizer.loaders.pdf_loader import PdfOcrCompareResult, PdfTextVariant

        compare = PdfOcrCompareResult(
            native=PdfTextVariant(kind="native", text="Co,11;ep'l\\:aHne rJIABA"),
            ocr=None,
        )
        mock_extract.return_value = compare
        mock_select.return_value = (
            compare.native,
            {
                "selected": "native",
                "mode": OcrMode.AUTO.value,
                "native_unreadable": True,
                "native_cyrillic_ratio": 0.0,
                "ocr_len": 0,
            },
        )

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["process", str(pdf_file), "--ocr-mode", "auto", "--out", str(tmp_path / "out")],
        )

    assert result.exit_code == 1
    assert "OCR is required" in result.output


def test_process_can_run_optional_llm_normalization(tmp_path: Path) -> None:
    txt_file = tmp_path / "book.txt"
    txt_file.write_text("Alpha beta.", encoding="utf-8")

    with patch("book_normalizer.cli._run_llm_normalization", return_value=(1, 0)) as mock_llm:
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "process",
                str(txt_file),
                "--out",
                str(tmp_path / "out"),
                "--skip-stress",
                "--skip-punctuation-review",
                "--skip-spellcheck",
                "--llm-normalize",
                "--llm-endpoint",
                "http://localhost:11434/v1",
                "--llm-model",
                "qwen3:8b",
            ],
        )

    assert result.exit_code == 0
    mock_llm.assert_called_once()
    assert "LLM normalization complete: 1 accepted, 0 rejected." in result.output
