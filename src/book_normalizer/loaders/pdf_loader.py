"""Loader for PDF (.pdf) book files using PyMuPDF."""

from __future__ import annotations

import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict, Tuple

from book_normalizer.loaders.base import BaseLoader
from book_normalizer.models.book import Book, Chapter, Metadata, Paragraph
from book_normalizer.normalization.cleanup import remove_repeated_headers
from book_normalizer.config import OcrMode

logger = logging.getLogger(__name__)


class PdfLoader(BaseLoader):
    """
    PDF loader built on top of PyMuPDF (fitz).

    Extracts text page by page, concatenates, and builds
    a Book with a single synthetic chapter.
    """

    @property
    def supported_extensions(self) -> set[str]:
        return {".pdf"}

    def load(self, path: Path) -> Book:
        """Load a PDF file and return a Book."""
        resolved = path.resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"File not found: {resolved}")

        try:
            import fitz  # PyMuPDF.
        except ImportError as exc:
            raise ImportError(
                "PyMuPDF is required for PDF loading. Install it: pip install PyMuPDF"
            ) from exc

        text = self._extract_text(resolved)
        logger.info("Extracted %d characters from '%s'", len(text), resolved.name)

        # Remove repeated headers/footers before splitting into paragraphs.
        text = remove_repeated_headers(text, min_occurrences=3)

        paragraphs = self._split_paragraphs(text)

        chapter = Chapter(
            title="Full Text",
            index=0,
            paragraphs=paragraphs,
            source_span_start=0,
            source_span_end=len(text),
        )

        metadata = Metadata(
            source_path=str(resolved),
            source_format="pdf",
        )

        book = Book(metadata=metadata, chapters=[chapter])
        book.add_audit("loading", "pdf_loader", f"chars={len(text)}, paragraphs={len(paragraphs)}")
        return book

    @staticmethod
    def _extract_text(path: Path) -> str:
        """Extract full text from all pages of a PDF."""
        import fitz  # PyMuPDF.

        pages: list[str] = []
        with fitz.open(str(path)) as doc:
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text("text")
                if page_text:
                    pages.append(page_text)

        return "\n\n".join(pages)

    @staticmethod
    def _split_paragraphs(text: str) -> list[Paragraph]:
        """Split extracted text into paragraphs by double-newline boundaries."""
        raw_blocks = text.split("\n\n")
        paragraphs: list[Paragraph] = []
        for idx, block in enumerate(raw_blocks):
            stripped = block.strip()
            if not stripped:
                continue
            paragraphs.append(
                Paragraph(
                    raw_text=stripped,
                    normalized_text="",
                    index_in_chapter=idx,
                )
            )
        return paragraphs


@dataclass
class PdfTextVariant:
    """Single text variant extracted from a PDF."""

    kind: str  # "native" or "ocr"
    text: str


@dataclass
class PdfOcrCompareResult:
    """Result of running native and optional OCR extraction."""

    native: PdfTextVariant
    ocr: PdfTextVariant | None


def extract_pdf_with_ocr_mode(path: Path, mode: OcrMode) -> PdfOcrCompareResult:
    """
    Extract PDF text according to the requested OCR mode.

    NOTE: OCR path currently reuses native extraction as a placeholder.
    The structure is in place so real OCR integration can be plugged in later.
    """
    loader = PdfLoader()
    resolved = path.resolve()
    native_text = remove_repeated_headers(loader._extract_text(resolved), min_occurrences=3)
    native_variant = PdfTextVariant(kind="native", text=native_text)

    if mode == OcrMode.OFF:
        return PdfOcrCompareResult(native=native_variant, ocr=None)

    # Placeholder OCR implementation: currently reuses native text.
    # In future, this should call an external OCR engine (ocrmypdf/tesseract)
    # and read back OCR-annotated text.
    try:
        # Placeholder OCR implementation: reuse native text for now.
        ocr_text = native_text
        ocr_variant = PdfTextVariant(kind="ocr", text=ocr_text)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("OCR extraction failed for '%s': %s", resolved, exc)
        ocr_variant = None

    return PdfOcrCompareResult(native=native_variant, ocr=ocr_variant)


def select_pdf_text_for_mode(
    compare: PdfOcrCompareResult,
    mode: OcrMode,
) -> Tuple[PdfTextVariant, Dict[str, Any]]:
    """
    Select which text variant to use for downstream processing.

    Returns (chosen_variant, stats_dict).
    """
    native = compare.native
    ocr = compare.ocr

    stats: Dict[str, Any] = {
        "mode": mode.value,
        "native_len": len(native.text),
        "ocr_len": len(ocr.text) if ocr else 0,
        "native_empty": len(native.text.strip()) == 0,
        "ocr_empty": (len(ocr.text.strip()) == 0) if ocr else True,
        "selected": "native",
        "reason": "",
    }

    if mode == OcrMode.OFF:
        stats["reason"] = "ocr_mode=off"
        return native, stats

    if ocr is None:
        stats["reason"] = "ocr_unavailable_falling_back_to_native"
        return native, stats

    if mode == OcrMode.FORCE:
        stats["selected"] = "ocr"
        stats["reason"] = "ocr_mode=force"
        return ocr, stats

    if mode == OcrMode.AUTO:
        # Simple heuristic: if native text is essentially empty, fall back to OCR.
        if stats["native_empty"] and not stats["ocr_empty"]:
            stats["selected"] = "ocr"
            stats["reason"] = "native_empty_use_ocr"
            return ocr, stats
        stats["reason"] = "native_preferred_in_auto_mode"
        return native, stats

    # COMPARE: choose like AUTO for pipeline, but stats will be written to a report.
    if stats["native_empty"] and not stats["ocr_empty"]:
        stats["selected"] = "ocr"
        stats["reason"] = "compare_mode_native_empty_use_ocr"
        return ocr, stats

    stats["reason"] = "compare_mode_native_preferred"
    return native, stats


def write_pdf_compare_report(
    output_dir: Path,
    compare: PdfOcrCompareResult,
    stats: Dict[str, Any],
) -> None:
    """
    Write simple compare artifacts for OCR COMPARE mode.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    native_preview = (compare.native.text or "")[:2000]
    ocr_preview = (compare.ocr.text or "")[:2000] if compare.ocr else ""

    (output_dir / "native_extract_preview.txt").write_text(native_preview, encoding="utf-8")
    (output_dir / "ocr_extract_preview.txt").write_text(ocr_preview, encoding="utf-8")

    report_path = output_dir / "pdf_compare_report.json"
    import json

    payload = {
        "mode": stats.get("mode"),
        "selected": stats.get("selected"),
        "reason": stats.get("reason"),
        "native_len": stats.get("native_len"),
        "ocr_len": stats.get("ocr_len"),
        "native_empty": stats.get("native_empty"),
        "ocr_empty": stats.get("ocr_empty"),
    }
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
