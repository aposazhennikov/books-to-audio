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


def _wsl_tesseract_available() -> bool:
    """Check if Tesseract is available inside WSL (Windows Subsystem for Linux)."""
    import platform
    import subprocess

    if platform.system() != "Windows":
        return False
    try:
        result = subprocess.run(
            ["wsl", "tesseract", "--version"],
            capture_output=True, timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def _tesseract_available() -> bool:
    """Check if Tesseract OCR is installed and accessible (native or WSL)."""
    try:
        import pytesseract  # noqa: F401
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        pass
    return _wsl_tesseract_available()


def _win_to_wsl_path(win_path: str) -> str:
    """Convert a Windows path like C:\\Users\\... to /mnt/c/Users/..."""
    p = win_path.replace("\\", "/")
    if len(p) >= 2 and p[1] == ":":
        drive = p[0].lower()
        p = f"/mnt/{drive}{p[2:]}"
    return p


def _ocr_image_via_wsl(img_bytes: bytes, lang: str, psm: int = 6) -> str:
    """Run Tesseract OCR on image bytes via WSL bridge."""
    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(img_bytes)
        tmp_path = tmp.name

    try:
        wsl_path = _win_to_wsl_path(tmp_path)
        result = subprocess.run(
            [
                "wsl", "tesseract", wsl_path, "stdout",
                "-l", lang, "--psm", str(psm),
            ],
            capture_output=True, timeout=120,
        )
        return result.stdout.decode("utf-8", errors="replace")
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _preprocess_image_for_ocr(img: Any) -> Any:
    """Apply image preprocessing to improve OCR accuracy.

    Pipeline:
    1. Convert to grayscale.
    2. Gentle noise reduction (small median filter).
    3. Contrast enhancement via histogram equalization.
    4. Adaptive binarization using Otsu's method.
    5. Light sharpening to recover edge detail.
    """
    from PIL import ImageFilter, ImageOps

    if img.mode != "L":
        img = img.convert("L")

    # Gentle noise reduction — size=3 removes salt-and-pepper without destroying detail.
    img = img.filter(ImageFilter.MedianFilter(size=3))

    # Contrast enhancement — autocontrast stretches histogram to full range.
    img = ImageOps.autocontrast(img, cutoff=0.5)

    # Otsu's adaptive threshold — compute optimal threshold from histogram.
    histogram = img.histogram()
    total_pixels = sum(histogram)
    current_sum = 0
    current_weight = 0
    max_variance = 0.0
    threshold = 128

    total_mean = sum(i * histogram[i] for i in range(256))

    for i in range(256):
        current_weight += histogram[i]
        if current_weight == 0:
            continue
        bg_weight = total_pixels - current_weight
        if bg_weight == 0:
            break

        current_sum += i * histogram[i]
        bg_mean = (total_mean - current_sum) / bg_weight
        fg_mean = current_sum / current_weight

        variance = current_weight * bg_weight * (fg_mean - bg_mean) ** 2
        if variance > max_variance:
            max_variance = variance
            threshold = i

    img = img.point(lambda x, thr=threshold: 255 if x > thr else 0, "1")
    img = img.convert("L")

    # Sharpen to recover edge detail lost during binarization.
    img = img.filter(ImageFilter.SHARPEN)

    return img


def _page_text_quality(text: str) -> float:
    """Estimate OCR quality of a page — ratio of Cyrillic alpha chars.

    Returns a float 0.0..1.0 where 1.0 means all alpha chars are Cyrillic.
    """
    alpha = [c for c in text if c.isalpha()]
    if not alpha:
        return 0.0
    cyrillic = sum(1 for c in alpha if "\u0400" <= c <= "\u04ff")
    return cyrillic / len(alpha)


def _ocr_pdf_with_tesseract(
    path: Path,
    lang: str = "rus",
    dpi: int = 400,
    psm: int = 6,
    preprocess: bool = True,
) -> str:
    """OCR a PDF file page-by-page using PyMuPDF + Tesseract.

    Renders each page to an image at the given DPI, optionally applies
    image preprocessing (binarization + noise removal), then runs
    Tesseract for text recognition.
    """
    import fitz

    use_wsl = False
    try:
        import pytesseract
        from PIL import Image
        pytesseract.get_tesseract_version()
    except Exception:
        if _wsl_tesseract_available():
            use_wsl = True
            logger.info("Using Tesseract via WSL bridge.")
        else:
            raise RuntimeError("Tesseract is not installed (neither native nor WSL).")

    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)

    pages: list[str] = []
    with fitz.open(str(path)) as doc:
        total = len(doc)
        for page_num in range(total):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csGRAY)

            if use_wsl:
                if preprocess:
                    from PIL import Image as PILImage
                    img = PILImage.frombytes("L", [pix.width, pix.height], pix.samples)
                    img = _preprocess_image_for_ocr(img)
                    import io
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    page_text = _ocr_image_via_wsl(buf.getvalue(), lang, psm=psm)
                else:
                    page_text = _ocr_image_via_wsl(pix.tobytes("png"), lang, psm=psm)
            else:
                img = Image.frombytes("L", [pix.width, pix.height], pix.samples)
                if preprocess:
                    img = _preprocess_image_for_ocr(img)
                tess_config = f"--psm {psm}"
                page_text = pytesseract.image_to_string(img, lang=lang, config=tess_config)

            if page_text and page_text.strip():
                quality = _page_text_quality(page_text)
                if quality < 0.15:
                    logger.debug(
                        "Page %d skipped: low quality (%.0f%% Cyrillic).",
                        page_num + 1, quality * 100,
                    )
                    continue
                pages.append(page_text)

            if (page_num + 1) % 20 == 0 or page_num == total - 1:
                logger.info("OCR progress: %d/%d pages", page_num + 1, total)

    return "\n\n".join(pages)


def extract_pdf_with_ocr_mode(
    path: Path,
    mode: OcrMode,
    dpi: int = 400,
    psm: int = 6,
    preprocess: bool = True,
) -> PdfOcrCompareResult:
    """Extract PDF text according to the requested OCR mode.

    Uses PyMuPDF for native text extraction.  When OCR is requested,
    renders each page to an image at the given DPI and runs Tesseract.
    """
    loader = PdfLoader()
    resolved = path.resolve()
    native_text = remove_repeated_headers(loader._extract_text(resolved), min_occurrences=3)
    native_variant = PdfTextVariant(kind="native", text=native_text)

    if mode == OcrMode.OFF:
        return PdfOcrCompareResult(native=native_variant, ocr=None)

    if not _tesseract_available():
        logger.warning(
            "Tesseract OCR is not installed. Install it: "
            "apt install tesseract-ocr tesseract-ocr-rus  (Linux) or "
            "choco install tesseract  (Windows) + pip install pytesseract Pillow. "
            "Falling back to native text extraction."
        )
        return PdfOcrCompareResult(native=native_variant, ocr=None)

    try:
        logger.info(
            "Running Tesseract OCR on '%s' (dpi=%d, psm=%d, preprocess=%s)...",
            resolved.name, dpi, psm, preprocess,
        )
        ocr_text = _ocr_pdf_with_tesseract(
            resolved, dpi=dpi, psm=psm, preprocess=preprocess,
        )
        ocr_text = remove_repeated_headers(ocr_text, min_occurrences=3)
        ocr_variant = PdfTextVariant(kind="ocr", text=ocr_text)
        logger.info("OCR complete: %d characters extracted.", len(ocr_text))
    except Exception as exc:
        logger.warning("OCR extraction failed for '%s': %s", resolved, exc)
        ocr_variant = None

    return PdfOcrCompareResult(native=native_variant, ocr=ocr_variant)


def _cyrillic_ratio(text: str) -> float:
    """Return the fraction of alphabetic characters that are Cyrillic."""
    sample = text[:10000]
    alpha = [c for c in sample if c.isalpha()]
    if not alpha:
        return 0.0
    cyr = sum(1 for c in alpha if "\u0400" <= c <= "\u04ff")
    return cyr / len(alpha)


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

    native_cyr = _cyrillic_ratio(native.text)

    stats: Dict[str, Any] = {
        "mode": mode.value,
        "native_len": len(native.text),
        "ocr_len": len(ocr.text) if ocr else 0,
        "native_empty": len(native.text.strip()) == 0,
        "ocr_empty": (len(ocr.text.strip()) == 0) if ocr else True,
        "native_cyrillic_ratio": round(native_cyr, 3),
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

    # AUTO / COMPARE: prefer OCR when native text is empty or garbage.
    native_is_bad = stats["native_empty"] or native_cyr < 0.3
    ocr_usable = not stats["ocr_empty"]

    if native_is_bad and ocr_usable:
        stats["selected"] = "ocr"
        reason_detail = "native_empty" if stats["native_empty"] else f"native_cyr={native_cyr:.2f}"
        stats["reason"] = f"{'auto' if mode == OcrMode.AUTO else 'compare'}_mode_{reason_detail}_use_ocr"
        return ocr, stats

    stats["reason"] = f"{'auto' if mode == OcrMode.AUTO else 'compare'}_mode_native_preferred"
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
