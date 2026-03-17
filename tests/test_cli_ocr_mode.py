from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from book_normalizer.cli import main
from book_normalizer.config import OcrMode


def test_process_accepts_ocr_mode_option(tmp_path: Path) -> None:
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 dummy")

    # Patch extract_pdf_with_ocr_mode to avoid real PDF parsing.
    with patch(
        "book_normalizer.loaders.pdf_loader.extract_pdf_with_ocr_mode"
    ) as mock_extract, patch(
        "book_normalizer.loaders.pdf_loader.select_pdf_text_for_mode"
    ) as mock_select:
        from book_normalizer.loaders.pdf_loader import PdfOcrCompareResult, PdfTextVariant

        compare = PdfOcrCompareResult(
            native=PdfTextVariant(kind="native", text="native"),
            ocr=PdfTextVariant(kind="ocr", text="ocr"),
        )
        mock_extract.return_value = compare
        mock_select.return_value = (compare.native, {"selected": "native", "mode": OcrMode.OFF.value})

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["process", str(pdf_file), "--ocr-mode", "force", "--out", str(tmp_path / "out")],
        )

        assert result.exit_code == 0
        # Ensure our patched helpers were called, meaning OCR mode plumbing is active.
        mock_extract.assert_called_once()
        mock_select.assert_called_once()

