"""Loader for PDF (.pdf) book files using PyMuPDF."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from book_normalizer.config import OcrMode
from book_normalizer.languages import (
    readable_word_ratio,
    target_script_char_count,
    target_script_ratio,
    text_unreadable,
)
from book_normalizer.loaders.base import BaseLoader
from book_normalizer.loaders.pdf_ocr_engine import (
    ocr_image_via_tesseract_cli as _ocr_image_via_tesseract_cli,
)
from book_normalizer.loaders.pdf_ocr_engine import (
    tesseract_available as _tesseract_available,
)
from book_normalizer.loaders.pdf_ocr_engine import (
    tesseract_cli_available as _tesseract_cli_available,
)
from book_normalizer.models.book import Book, Chapter, Metadata, Paragraph
from book_normalizer.normalization.cleanup import remove_repeated_headers

logger = logging.getLogger(__name__)

MIN_READABLE_TARGET_RATIO = 0.3
MIN_OCR_TARGET_CHARS = 80
MIN_OCR_READABLE_WORD_RATIO = 0.35
MAX_OCR_SYMBOL_NOISE_RATIO = 0.06
SPREAD_PAGE_RATIO = 1.2
MIN_STRUCTURED_TEXT_CHARS = 40
LARGE_IMAGE_PAGE_RATIO = 0.65


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

        if find_spec("fitz") is None:
            raise ImportError(
                "PyMuPDF is required for PDF loading. Install it: pip install PyMuPDF"
            )

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
        try:
            structured = _extract_pdf_structured(path, run_ocr=False)
            structured_text = structured.to_text()
            if structured_text.strip():
                logger.info("PDF structure detected as %s.", structured.document_type)
                return structured_text
        except ImportError as exc:
            logger.debug("Structured PDF extraction dependencies unavailable: %s", exc)
        except Exception as exc:
            logger.debug("Structured PDF extraction failed, falling back to PyMuPDF: %s", exc)

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
        raw_blocks = _repair_isolated_layout_word_blocks(text.split("\n\n"))
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
    document_type: str = "unknown"


@dataclass
class PdfOcrCompareResult:
    """Result of running native and optional OCR extraction."""

    native: PdfTextVariant
    ocr: PdfTextVariant | None
    native_structure: PdfStructuredExtraction | None = None
    ocr_structure: PdfStructuredExtraction | None = None


def _repair_isolated_layout_word_blocks(blocks: list[str]) -> list[str]:
    """Remove or reflow words that PDF extraction split out of one visual line."""

    result: list[str] = []
    index = 0
    while index < len(blocks):
        block = blocks[index]
        stripped = block.strip()
        if not _is_isolated_layout_word_block(stripped):
            result.append(block)
            index += 1
            continue

        words: list[str] = []
        run_start = index
        while index < len(blocks) and _is_isolated_layout_word_block(blocks[index].strip()):
            words.append(blocks[index].strip())
            index += 1

        if result and _try_reflow_isolated_words_into_previous(result, words):
            continue

        next_block = blocks[index].strip() if index < len(blocks) else ""
        if result and next_block and _try_reflow_isolated_words_between_blocks(result, words, blocks, index):
            continue

        previous = result[-1].strip() if result else ""
        if _should_drop_isolated_layout_word_run(words, previous=previous, next_block=next_block):
            continue

        result.extend(blocks[run_start:index])
    return result


def _is_isolated_layout_word_block(text: str) -> bool:
    if not text or "\n" in text:
        return False
    return bool(re.fullmatch(r"\(?[А-ЯЁа-яё]{1,14}", text.strip()))


def _try_reflow_isolated_words_into_previous(previous_blocks: list[str], words: list[str]) -> bool:
    previous = previous_blocks[-1]
    joined = " ".join(words)
    final_parenthetical_matches = list(
        re.finditer(
            r"\((?P<head>[А-ЯЁа-яё]{1,20})\s+"
            r"(?P<tail>[А-ЯЁа-яё]{1,20})(?P<close>\)[.!?…]?)",
            previous,
        )
    )
    final_parenthetical = final_parenthetical_matches[-1] if final_parenthetical_matches else None
    if final_parenthetical and all(not word.startswith("(") for word in words):
        replacement = (
            f"({final_parenthetical.group('head')} {joined} "
            f"{final_parenthetical.group('tail')}{final_parenthetical.group('close')}"
        )
        previous_blocks[-1] = (
            previous[: final_parenthetical.start()]
            + replacement
            + previous[final_parenthetical.end():]
        )
        return True

    if any(word.startswith("(") for word in words):
        phrase = " ".join(word.strip() for word in words)
        gap = re.search(
            r"\b(?P<anchor>[А-ЯЁа-яё]{2,20})\s+(?P<trailer>[А-ЯЁа-яё]{2,20}\)\))",
            previous,
        )
        if gap:
            replacement = f"{gap.group('anchor')} {phrase} {gap.group('trailer')}"
            previous_blocks[-1] = previous[: gap.start()] + replacement + previous[gap.end():]
            return True
    return False


def _try_reflow_isolated_words_between_blocks(
    previous_blocks: list[str],
    words: list[str],
    blocks: list[str],
    next_index: int,
) -> bool:
    previous = previous_blocks[-1]
    next_block = blocks[next_index]
    if any(word.startswith("(") for word in words):
        return False

    previous_match = re.search(r"\((?P<head>[А-ЯЁа-яё]{1,20})\s*$", previous)
    next_match = re.match(
        r"\s*(?P<tail>[А-ЯЁа-яё]{1,20})(?P<close>\)[.!?…]?)(?P<rest>.*)$",
        next_block,
        re.DOTALL,
    )
    if not previous_match or not next_match:
        return False

    joined = " ".join(words)
    rest = next_match.group("rest").lstrip()
    previous_blocks[-1] = (
        previous[: previous_match.start()]
        + f"({previous_match.group('head')} {joined} "
        + f"{next_match.group('tail')}{next_match.group('close')}"
        + (f" {rest}" if rest else "")
    )
    blocks[next_index] = ""
    return True


def _should_drop_isolated_layout_word_run(
    words: list[str],
    *,
    previous: str,
    next_block: str,
) -> bool:
    if len(words) < 2:
        return False
    if not previous or not next_block:
        return False
    if len(words) >= 3:
        return True
    return bool(re.search(r"[.!?…]\s*$", previous) and next_block[:1].isupper())


@dataclass
class PdfPageExtraction:
    """Structured extraction result for one PDF page."""

    page_number: int
    pdf_type: str = "unknown"
    page_text: list[str] = field(default_factory=list)
    line_format: list[list[Any]] = field(default_factory=list)
    text_from_images: list[str] = field(default_factory=list)
    text_from_tables: list[str] = field(default_factory=list)
    page_content: list[str] = field(default_factory=list)


@dataclass
class PdfStructuredExtraction:
    """Structured PDF extraction with per-page components."""

    pages: dict[int, PdfPageExtraction]
    document_type: str

    def to_text(self) -> str:
        """Return readable text assembled from page content."""
        page_texts: list[str] = []
        for page_number in sorted(self.pages):
            content = [part.strip() for part in self.pages[page_number].page_content if part.strip()]
            if content:
                page_texts.append("\n\n".join(content))
        return "\n\n".join(page_texts)


def _unique_preserving_order(values: list[Any]) -> list[Any]:
    """Return unique values while preserving their first-seen order."""
    seen: set[str] = set()
    result: list[Any] = []
    for value in values:
        marker = repr(value)
        if marker in seen:
            continue
        seen.add(marker)
        result.append(value)
    return result


def _extract_text_container(element: Any) -> tuple[str, list[Any]]:
    """Extract text and font metadata from a pdfminer text container."""
    from pdfminer.layout import LTChar

    formats: list[Any] = []

    def walk(node: Any) -> None:
        if isinstance(node, LTChar):
            formats.append(node.fontname)
            formats.append(round(float(node.size), 1))
            return
        if hasattr(node, "__iter__"):
            for child in node:
                walk(child)

    walk(element)
    return element.get_text(), _unique_preserving_order(formats)


def _clean_table_cell(value: Any) -> str:
    """Normalize a pdfplumber table cell for LLM-friendly text output."""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\n", " ")).strip()


def _table_converter(table: list[list[Any]]) -> str:
    """Convert a pdfplumber table into a compact pipe-separated string."""
    rows: list[str] = []
    for row in table:
        cells = [_clean_table_cell(cell) for cell in row]
        if any(cells):
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def _pdfplumber_bbox_to_pdfminer(
    bbox: tuple[float, float, float, float],
    page_height: float,
) -> tuple[float, float, float, float]:
    """Convert a pdfplumber bbox (top-left origin) to pdfminer coordinates."""
    x0, top, x1, bottom = bbox
    return (x0, page_height - bottom, x1, page_height - top)


def _bbox_area(bbox: tuple[float, float, float, float]) -> float:
    """Return area for a PDF bbox."""
    x0, y0, x1, y1 = bbox
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def _bbox_center_inside(
    inner: tuple[float, float, float, float],
    outer: tuple[float, float, float, float],
) -> bool:
    """Return true when the inner bbox center is inside outer."""
    x0, y0, x1, y1 = inner
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    ox0, oy0, ox1, oy1 = outer
    return ox0 <= cx <= ox1 and oy0 <= cy <= oy1


def _bbox_intersects(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> bool:
    """Return true when two PDF bboxes intersect."""
    ax0, ay0, ax1, ay1 = first
    bx0, by0, bx1, by1 = second
    return ax0 < bx1 and ax1 > bx0 and ay0 < by1 and ay1 > by0


def _extract_page_tables(plumber_page: Any | None) -> list[tuple[tuple[float, float, float, float], str]]:
    """Extract tables from a pdfplumber page as (pdfminer_bbox, table_text)."""
    if plumber_page is None:
        return []

    tables: list[tuple[tuple[float, float, float, float], str]] = []
    try:
        for table in plumber_page.find_tables():
            table_text = _table_converter(table.extract())
            if not table_text:
                continue
            bbox = _pdfplumber_bbox_to_pdfminer(table.bbox, float(plumber_page.height))
            tables.append((bbox, table_text))
    except Exception as exc:
        logger.debug("pdfplumber table detection failed on page %s: %s", getattr(plumber_page, "page_number", "?"), exc)

    return tables


def _classify_pdf_page(
    *,
    text_chars: int,
    table_count: int,
    image_area_ratio: float,
    image_text_count: int = 0,
) -> str:
    """Classify a page before choosing the extraction strategy."""
    has_text_layer = text_chars >= MIN_STRUCTURED_TEXT_CHARS or table_count > 0
    has_full_page_image = image_area_ratio >= LARGE_IMAGE_PAGE_RATIO

    if has_text_layer and has_full_page_image:
        return "scanned_with_ocr"
    if not has_text_layer and image_text_count > 0:
        return "scanned"
    if has_full_page_image and not has_text_layer:
        return "scanned"
    if has_text_layer and image_text_count > 0:
        return "hybrid"
    if has_text_layer:
        return "programmatic"
    return "unknown"


def _classify_pdf_document(pages: dict[int, PdfPageExtraction]) -> str:
    """Classify the full PDF from per-page classifications."""
    counts: dict[str, int] = {}
    for page in pages.values():
        counts[page.pdf_type] = counts.get(page.pdf_type, 0) + 1

    if not counts:
        return "unknown"
    if counts.get("scanned", 0) == len(pages):
        return "scanned"
    if counts.get("scanned_with_ocr", 0) == len(pages):
        return "scanned_with_ocr"
    if counts.get("programmatic", 0) == len(pages):
        return "programmatic"
    return "mixed"


def _should_keep_image_ocr_text(text: str, language_code: str = "ru") -> bool:
    """Keep short OCR snippets from embedded images without accepting pure debris."""
    stripped = text.strip()
    if not stripped:
        return False
    target_chars = target_script_char_count(stripped, language_code)
    alnum = sum(ch.isalnum() for ch in stripped)
    return (target_chars >= 3 or alnum >= 6) and _ocr_symbol_noise_ratio(stripped) <= 0.18


def _load_tesseract_runtime() -> tuple[str, Any | None]:
    """Resolve pytesseract or the local Tesseract CLI in the current OS."""
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return "pytesseract", pytesseract
    except Exception:
        if _tesseract_cli_available():
            return "cli", None
        raise RuntimeError("Tesseract is not installed in the current OS environment.")


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


def _image_dark_bbox(img: Any, threshold: int = 205) -> tuple[int, int, int, int] | None:
    """Return the bounding box of dark content in a page image."""
    from PIL import ImageOps

    gray = img.convert("L") if img.mode != "L" else img
    gray = ImageOps.autocontrast(gray, cutoff=0.5)
    mask = gray.point(lambda px: 255 if px < threshold else 0, "L")
    return mask.getbbox()


def _crop_image_to_content(img: Any, margin: int | None = None) -> Any:
    """Crop scan margins while leaving a small safety border around text."""
    bbox = _image_dark_bbox(img)
    if bbox is None:
        return img

    width, height = img.size
    pad = margin if margin is not None else max(16, int(min(width, height) * 0.015))
    left, top, right, bottom = bbox
    return img.crop((
        max(0, left - pad),
        max(0, top - pad),
        min(width, right + pad),
        min(height, bottom + pad),
    ))


def _image_ink_ratio(img: Any, threshold: int = 180) -> float:
    """Estimate how much real dark content is present in an image."""
    from PIL import ImageOps

    probe = img.convert("L") if img.mode != "L" else img.copy()
    probe.thumbnail((300, 300))
    probe = ImageOps.autocontrast(probe, cutoff=0.5)
    mask = probe.point(lambda px: 255 if px < threshold else 0, "L")
    hist = mask.histogram()
    dark = hist[255]
    total = probe.size[0] * probe.size[1]
    return dark / total if total else 0.0


def _prepare_ocr_page_images(img: Any) -> list[Any]:
    """Return page-like OCR regions, splitting scanned book spreads when needed."""
    width, height = img.size
    if height and width / height >= SPREAD_PAGE_RATIO:
        mid = width // 2
        parts = [
            img.crop((0, 0, mid, height)),
            img.crop((mid, 0, width, height)),
        ]
        segments = [
            _crop_image_to_content(part)
            for part in parts
            if _image_ink_ratio(part) >= 0.002
        ]
        if segments:
            return segments

    cropped = _crop_image_to_content(img)
    return [cropped] if _image_ink_ratio(cropped) >= 0.001 else []


def _encode_png(img: Any) -> bytes:
    """Encode a PIL image to PNG bytes for Tesseract CLI."""
    import io

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _ocr_pil_image_with_tesseract(
    img: Any,
    *,
    lang: str,
    psm: int,
    preprocess: bool,
    runtime: str,
    pytesseract_module: Any | None = None,
) -> str:
    """Run Tesseract against a PIL image through pytesseract or local CLI."""
    if preprocess:
        img = _preprocess_image_for_ocr(img)

    if runtime == "cli":
        return _ocr_image_via_tesseract_cli(_encode_png(img), lang, psm=psm)
    if runtime != "pytesseract":
        raise RuntimeError(f"Unsupported Tesseract runtime: {runtime}")

    if pytesseract_module is None:
        import pytesseract as pytesseract_module

    return pytesseract_module.image_to_string(
        img,
        lang=lang,
        config=f"--psm {psm}",
    )


def _render_pdf_page_to_image(fitz_doc: Any, page_index: int, dpi: int) -> Any:
    """Render a full PDF page to a grayscale PIL image."""
    import fitz
    from PIL import Image

    zoom = dpi / 72
    pix = fitz_doc[page_index].get_pixmap(
        matrix=fitz.Matrix(zoom, zoom),
        colorspace=fitz.csGRAY,
    )
    return Image.frombytes("L", [pix.width, pix.height], pix.samples)


def _render_pdf_region_to_image(
    fitz_doc: Any,
    page_index: int,
    bbox: tuple[float, float, float, float],
    dpi: int,
) -> Any | None:
    """Render a pdfminer bbox from one PDF page to a grayscale PIL image."""
    import fitz
    from PIL import Image

    page = fitz_doc[page_index]
    x0, y0, x1, y1 = bbox
    clip = fitz.Rect(x0, page.rect.height - y1, x1, page.rect.height - y0) & page.rect
    if clip.is_empty or clip.width < 1 or clip.height < 1:
        return None

    zoom = dpi / 72
    pix = page.get_pixmap(
        matrix=fitz.Matrix(zoom, zoom),
        colorspace=fitz.csGRAY,
        clip=clip,
    )
    return Image.frombytes("L", [pix.width, pix.height], pix.samples)


def _ocr_rendered_image(
    img: Any,
    *,
    lang: str,
    language_code: str,
    psm: int,
    preprocess: bool,
    runtime: str,
    pytesseract_module: Any | None,
) -> str:
    """Run OCR against a rendered PIL image and post-process the result."""
    raw_text = _ocr_pil_image_with_tesseract(
        img,
        lang=lang,
        psm=psm,
        preprocess=preprocess,
        runtime=runtime,
        pytesseract_module=pytesseract_module,
    )
    return _postprocess_ocr_text(raw_text, language_code=language_code)


def _extract_pdf_structured(
    path: Path,
    *,
    run_ocr: bool,
    lang: str = "rus",
    language_code: str = "ru",
    dpi: int = 400,
    psm: int = 6,
    preprocess: bool = True,
) -> PdfStructuredExtraction:
    """Extract PDF content by component: text blocks, tables, and image OCR."""
    import pdfplumber
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LTFigure, LTRect, LTTextContainer

    ocr_runtime = "pytesseract"
    pytesseract_module: Any | None = None
    fitz_doc: Any | None = None

    if run_ocr:
        import fitz

        ocr_runtime, pytesseract_module = _load_tesseract_runtime()
        fitz_doc = fitz.open(str(path))

    pages: dict[int, PdfPageExtraction] = {}
    try:
        with pdfplumber.open(str(path)) as plumber_pdf:
            for page_index, layout_page in enumerate(extract_pages(str(path))):
                plumber_page = (
                    plumber_pdf.pages[page_index]
                    if page_index < len(plumber_pdf.pages)
                    else None
                )
                table_items = _extract_page_tables(plumber_page)
                table_bboxes = [bbox for bbox, _ in table_items]
                added_tables: set[int] = set()

                page = PdfPageExtraction(page_number=page_index + 1)
                page_area = max(1.0, float(layout_page.width * layout_page.height))
                figure_bboxes: list[tuple[float, float, float, float]] = []
                image_area = 0.0

                elements = sorted(
                    list(layout_page),
                    key=lambda item: (-float(getattr(item, "y1", 0.0)), float(getattr(item, "x0", 0.0))),
                )
                for element in elements:
                    if isinstance(element, LTTextContainer):
                        if any(_bbox_center_inside(element.bbox, bbox) for bbox in table_bboxes):
                            continue
                        text, line_formats = _extract_text_container(element)
                        text = text.strip()
                        if text:
                            page.page_text.append(text)
                            page.line_format.append(line_formats)
                            page.page_content.append(text)
                        continue

                    if isinstance(element, LTFigure):
                        bbox = tuple(float(value) for value in element.bbox)
                        figure_bboxes.append(bbox)
                        image_area += _bbox_area(bbox)
                        continue

                    if isinstance(element, LTRect):
                        for table_index, (bbox, table_text) in enumerate(table_items):
                            if table_index in added_tables:
                                continue
                            if _bbox_intersects(element.bbox, bbox):
                                page.text_from_tables.append(table_text)
                                page.page_content.append(table_text)
                                added_tables.add(table_index)

                for table_index, (_, table_text) in enumerate(table_items):
                    if table_index in added_tables:
                        continue
                    page.text_from_tables.append(table_text)
                    page.page_content.append(table_text)

                text_chars = sum(len(text) for text in page.page_text) + sum(
                    len(text) for text in page.text_from_tables
                )
                image_area_ratio = min(1.0, image_area / page_area)
                page.pdf_type = _classify_pdf_page(
                    text_chars=text_chars,
                    table_count=len(page.text_from_tables),
                    image_area_ratio=image_area_ratio,
                )

                if run_ocr and fitz_doc is not None:
                    needs_full_page_ocr = (
                        page.pdf_type == "scanned"
                        or (text_chars < MIN_STRUCTURED_TEXT_CHARS and not figure_bboxes)
                    )
                    if needs_full_page_ocr:
                        full_image = _render_pdf_page_to_image(fitz_doc, page_index, dpi)
                        for segment in _prepare_ocr_page_images(full_image):
                            ocr_text = _ocr_rendered_image(
                                segment,
                                lang=lang,
                                language_code=language_code,
                                psm=psm,
                                preprocess=preprocess,
                                runtime=ocr_runtime,
                                pytesseract_module=pytesseract_module,
                            )
                            if _should_keep_ocr_text(ocr_text, language_code):
                                page.text_from_images.append(ocr_text)
                                page.page_content.append(ocr_text)
                    else:
                        for bbox in figure_bboxes:
                            is_full_page_overlay = (
                                _bbox_area(bbox) / page_area >= LARGE_IMAGE_PAGE_RATIO
                                and text_chars >= MIN_STRUCTURED_TEXT_CHARS
                            )
                            if is_full_page_overlay:
                                continue
                            image = _render_pdf_region_to_image(fitz_doc, page_index, bbox, dpi)
                            if image is None:
                                continue
                            image = _crop_image_to_content(image)
                            if _image_ink_ratio(image) < 0.001:
                                continue
                            ocr_text = _ocr_rendered_image(
                                image,
                                lang=lang,
                                language_code=language_code,
                                psm=psm,
                                preprocess=preprocess,
                                runtime=ocr_runtime,
                                pytesseract_module=pytesseract_module,
                            )
                            if _should_keep_image_ocr_text(ocr_text, language_code):
                                page.text_from_images.append(ocr_text)
                                page.page_content.append(ocr_text)

                    page.pdf_type = _classify_pdf_page(
                        text_chars=text_chars,
                        table_count=len(page.text_from_tables),
                        image_area_ratio=image_area_ratio,
                        image_text_count=len(page.text_from_images),
                    )

                pages[page.page_number] = page
    finally:
        if fitz_doc is not None:
            fitz_doc.close()

    return PdfStructuredExtraction(
        pages=pages,
        document_type=_classify_pdf_document(pages),
    )


_CYRILLIC_RE = re.compile(r"[\u0400-\u04ff]")
_OCR_HYPHEN_LINEBREAK_RE = re.compile(
    r"([\u0400-\u04ff])[-\u00ad\u2010-\u2015]\s*\n\s*([\u0400-\u04ff])"
)
_OCR_CROSS_SEGMENT_HYPHEN_RE = re.compile(
    r"([\u0400-\u04ff])[-\u00ad\u2010-\u2015]\s*\n{2,}\s*([\u0430-\u044fё])"
)
_OCR_CROSS_SEGMENT_PARTICIPLE_RE = re.compile(
    r"([\u0430-\u044fё]+вш)\s*\n{2,}\s*(ееся|аяся|ийся|иеся)\b"
)
_OCR_LEADING_ARTIFACT_RE = re.compile(r"^[`'\"_.,:;|\\/\s]+(?=[\u0400-\u04ff])")
_OCR_TRAILING_PAGE_MARK_RE = re.compile(r"\s+[|\\/_—–-]?\s*\d{1,3}\s*$")
_OCR_GLAVA_HEADING_RE = re.compile(
    r"^\s*[Гг][Лл][Аа][Вв][Аа]\s+\S{1,20}(?:\s+[Оо0])?\s*$"
)
_INLINE_GLAVA_HEADING_RE = re.compile(
    r"(?<![\u0400-\u04ff])(?P<heading>ГЛАВА\s+(?:[А-ЯЁ]{3,}|[IVXLCDMl|]{1,8}|\d+))"
)
_CHAPTER_AFTER_LEADING_NOISE_RE = re.compile(
    r"^[\s,.;:!?\"'`«»()[\]{}|\\/_^#*~—–-]+"
)
_CHAPTER_TITLE_LEADING_OCR_RE = re.compile(r"^(?:[Оо0]\s+){1,2}(?=[А-ЯЁ])")
_INLINE_PIPE_NOISE_RE = re.compile(
    r"\s+[\u0400-\u04ffA-Za-z]{1,3}\s*\|\s+(?=[\u0400-\u04ffA-Z])"
)
_INLINE_NOISE_BEFORE_DASH_RE = re.compile(
    r"\s+(?:[оОoO]\s+)?[\u0410-\u042fЁA-Z]{1,3}"
    r"(?:\s+[\u0410-\u042fЁA-Z]{1,3}){0,2}\s*[|_\\/#^]+(?=\s*[—-])"
)
_INLINE_HYPHEN_PIPE_RE = re.compile(r"([\u0400-\u04ff])-\s*\|\s*([\u0400-\u04ff])")
_INLINE_PAGE_MARK_RE = re.compile(r"(?<=[.!?…])\s+[|\\/_—–-]?\s*\d{1,3}\s+(?=[А-ЯЁ])")
_DIGIT_HYPHENATED_ZA_RE = re.compile(r"\b32-\s+(?=[\u0400-\u04ff])")
_SPURIOUS_PERIOD_INSIDE_WORD_RE = re.compile(r"(?<=[\u0430-\u044fё])\.\s*(?=[\u0430-\u044fё])")
_TRAILING_SYMBOL_NOISE_RE = re.compile(r"\s+[\^#*_~|\\/:\s\d]+$")
_OCR_BACKTICK_NOISE_RE = re.compile(r"[`'\u2018\u2019\u201A]")
_OCR_BACKTICK_WORD_BOUNDARY_RE = re.compile(
    r"(?<=[\u0400-\u04ff])"
    r"[`'\u2018\u2019\u201A]"
    r"(?=[\u0400-\u04ff])"
)
_OCR_COLLAPSED_I_TUT_RE = re.compile(r"\b([Ии])тут\b")
_OCR_SYMBOL_CLUSTER_RE = re.compile(r"\s+[\^#*_~|\\/`=<>$%]{2,}\s+")
_OCR_SYMBOL_WORD_NOISE_RE = re.compile(
    r"\s+[\^#*_~|\\/`=<>$%]+"
    r"(?:\s+[А-Яа-яЁёA-Za-z\d]{1,3}){0,4}"
    r"\s*[:;,.!?]*\s+(?=[А-ЯЁ])"
)
_OCR_LEFTOVER_FORBIDDEN_SYMBOL_RE = re.compile(
    r"\s*[|^&®©°№‹›{}<>]\s*[!;:,.»«\"'`-]*\s*"
)
_OCR_PAGE_WORD_MARK_RE = re.compile(r"(?:^|\s+)[Сс]траница\s+\d{1,4}\s*:\s*")
_OCR_PAGE_ABBR_MARK_RE = re.compile(r"\s+[Сс]\.\s*\d{1,4}\s*:\s*")
_TRAILING_SINGLE_LETTER_PUNCT_RE = re.compile(r"\s+[\u0400-\u04ff]\s*[:;,.!?]+$")
_OCR_SHORT_TOKEN_RUN_RE = re.compile(
    r"\s+[;:,.!?-]?\s*"
    r"(?:\d+\s+){1,3}"
    r"(?:[\u0400-\u04ffA-Z]{1,3}\s+){2,}"
    r"(?=[А-ЯЁ])"
)
_OCR_SHORT_WORD_RUN_BEFORE_UPPER_RE = re.compile(
    r"(?<=[.!?])\s+(?:[\u0400-\u04ff]{1,3}\s+){2,}(?=[А-ЯЁ])"
)
_OCR_SHORT_WORD_RUN_BEFORE_PLUS_RE = re.compile(
    r"\s+(?:[\u0400-\u04ff]{1,4}\s+){3,}.{0,80}?\+\s+(?=[А-ЯЁ])"
)
_SHORT_SENTENCE_FRAGMENT_RE = re.compile(r"(?<=[.!?])\s+([^.!?]{1,45}[.!?])")
_OCR_DASH_DOT_SHORT_RE = re.compile(r"\s*[«»“”]?\s+—\.\.\s+[\u0400-\u04ff]\s*\.")
_OCR_DASH_DOT_WORDS_RE = re.compile(
    r"\s*[«»“”]?\s+—\.\.[^А-ЯЁ]*"
    r"(?:[\u0400-\u04ff]{1,8}\s+){0,2}"
    r"(?=[А-ЯЁ])"
)
_OCR_DASH_SPACED_DOT_WORDS_RE = re.compile(
    r"\s*[«»“”„]?\s+—\s*\.\s*\.[^А-ЯЁ]*"
    r"(?:[\u0400-\u04ff]{1,8}\s+){0,2}"
    r"(?=[А-ЯЁ])"
)


def _cyrillic_char_count(text: str) -> int:
    """Count Cyrillic letters in text."""
    return len(_CYRILLIC_RE.findall(text))


def _is_ocr_noise_line(line: str) -> bool:
    """Return true for OCR lines made mostly of punctuation or scan artifacts."""
    stripped = line.strip()
    if not stripped:
        return False
    cyr = _cyrillic_char_count(stripped)
    alnum = sum(ch.isalnum() for ch in stripped)
    if cyr == 0 and alnum <= 2:
        return True
    if cyr < 2 and len(stripped) <= 12:
        return True
    punctuation = sum(not ch.isalnum() and not ch.isspace() for ch in stripped)
    return cyr == 0 and punctuation / max(1, len(stripped)) > 0.35


def _is_chapter_heading_line(line: str) -> bool:
    """Return true for short OCR lines that look like a chapter boundary."""
    return bool(_OCR_GLAVA_HEADING_RE.match(line.strip()))


def _strip_trailing_page_marker(line: str) -> str:
    """Remove page numbers glued to the end of an OCR line."""
    if _cyrillic_char_count(line) < 8:
        return line
    return _OCR_TRAILING_PAGE_MARK_RE.sub("", line).strip()


def _strip_text_after_inline_heading(text: str) -> str:
    """Remove OCR crumbs commonly glued between a chapter heading and title."""
    text = _CHAPTER_AFTER_LEADING_NOISE_RE.sub("", text.strip())
    text = _CHAPTER_TITLE_LEADING_OCR_RE.sub("", text).strip()
    return text


def _split_inline_chapter_headings(paragraph: str) -> list[str]:
    """Split paragraphs where OCR glued a chapter heading into surrounding text."""
    if _is_chapter_heading_line(paragraph):
        return [paragraph]

    parts: list[str] = []
    pos = 0
    for match in _INLINE_GLAVA_HEADING_RE.finditer(paragraph):
        before = paragraph[pos:match.start()].strip()
        if before:
            parts.append(before)
        parts.append(match.group("heading").strip())
        pos = match.end()

    tail = paragraph[pos:].strip()
    if tail:
        if parts and parts[-1].startswith("ГЛАВА"):
            tail = _strip_text_after_inline_heading(tail)
        if tail:
            parts.append(tail)

    return parts or [paragraph]


def _trim_trailing_ocr_garbage(paragraph: str) -> str:
    """Drop short noisy tails accidentally glued after the last sentence."""
    for idx in range(len(paragraph) - 1, -1, -1):
        if paragraph[idx] not in ".!?…":
            continue

        tail = paragraph[idx + 1:].strip()
        if not tail or len(tail) > 80:
            return paragraph

        tail_words = _cyrillic_words(tail)
        all_short_tail_words = (
            len(tail_words) >= 2
            and all(len(word) <= 3 for word in tail_words)
            and not tail.lstrip().startswith("—")
        )
        has_noise_symbol = bool(re.search(r"[\^#*_~|\\/`=<>]", tail))
        low_word_quality = _readable_cyrillic_word_ratio(tail) < 0.35
        very_short = _cyrillic_char_count(tail) <= 8
        if all_short_tail_words and (low_word_quality or very_short):
            return paragraph[:idx + 1].strip()
        if has_noise_symbol and (low_word_quality or very_short):
            return paragraph[:idx + 1].strip()

        return paragraph

    return paragraph


def _trim_leading_ocr_garbage(paragraph: str) -> str:
    """Drop noisy leading token runs before the first readable sentence."""
    plus = paragraph.find("+ ")
    if plus < 0 or plus > 90 or plus + 2 >= len(paragraph):
        return paragraph
    if not re.match(r"[А-ЯЁ]", paragraph[plus + 2]):
        return paragraph

    prefix = paragraph[:plus + 1]
    words = _cyrillic_words(prefix)
    if not words:
        return paragraph[plus + 2:].strip()

    short_words = sum(1 for word in words if len(word) <= 3)
    if short_words / len(words) >= 0.65 and _readable_cyrillic_word_ratio(prefix) < 0.35:
        return paragraph[plus + 2:].strip()

    return paragraph


def _normalize_common_ocr_glitches(paragraph: str) -> str:
    """Fix high-confidence OCR glitches seen in Russian scanned book pages."""
    paragraph = _INLINE_PAGE_MARK_RE.sub(" ", paragraph)
    paragraph = _OCR_SYMBOL_WORD_NOISE_RE.sub(" ", paragraph)
    paragraph = _OCR_SYMBOL_CLUSTER_RE.sub(" ", paragraph)
    paragraph = _OCR_SHORT_TOKEN_RUN_RE.sub(" ", paragraph)
    paragraph = _OCR_SHORT_WORD_RUN_BEFORE_UPPER_RE.sub(" ", paragraph)
    paragraph = _OCR_SHORT_WORD_RUN_BEFORE_PLUS_RE.sub(" ", paragraph)
    paragraph = _DIGIT_HYPHENATED_ZA_RE.sub("за", paragraph)
    paragraph = _OCR_COLLAPSED_I_TUT_RE.sub(r"\1 тут", paragraph)
    paragraph = re.sub(r"\b([Ии])в\s+помине\b", r"\1 в помине", paragraph)
    paragraph = _OCR_BACKTICK_WORD_BOUNDARY_RE.sub(" ", paragraph)
    paragraph = _OCR_BACKTICK_NOISE_RE.sub("", paragraph)
    paragraph = _OCR_SYMBOL_WORD_NOISE_RE.sub(" ", paragraph)
    paragraph = _OCR_SYMBOL_CLUSTER_RE.sub(" ", paragraph)
    paragraph = _OCR_PAGE_WORD_MARK_RE.sub(" ", paragraph)
    paragraph = _OCR_PAGE_ABBR_MARK_RE.sub(" ", paragraph)
    paragraph = _OCR_LEFTOVER_FORBIDDEN_SYMBOL_RE.sub(" ", paragraph)
    paragraph = _TRAILING_SINGLE_LETTER_PUNCT_RE.sub("", paragraph)
    paragraph = _OCR_DASH_DOT_SHORT_RE.sub(" ", paragraph)
    paragraph = _OCR_DASH_DOT_WORDS_RE.sub(" ", paragraph)
    paragraph = _OCR_DASH_SPACED_DOT_WORDS_RE.sub(" ", paragraph)
    paragraph = _remove_short_noisy_fragments(paragraph)
    paragraph = _OCR_SHORT_WORD_RUN_BEFORE_UPPER_RE.sub(" ", paragraph)
    paragraph = _OCR_SHORT_WORD_RUN_BEFORE_PLUS_RE.sub(" ", paragraph)
    paragraph = _trim_leading_ocr_garbage(paragraph)
    paragraph = _trim_trailing_ocr_garbage(paragraph)
    paragraph = _normalize_ocr_punctuation(paragraph)
    paragraph = re.sub(r"\s{2,}", " ", paragraph)
    return paragraph.strip()


def _normalize_ocr_punctuation(text: str) -> str:
    """Normalize punctuation combinations that are almost always OCR accidents."""
    text = re.sub(r"([,;])\1+", r"\1", text)
    text = re.sub(r"\?+\.", "?", text)
    text = re.sub(r"\.\s*:", ".", text)
    text = re.sub(r"\.\s*-\s+(?=[А-ЯЁ])", ". — ", text)
    text = re.sub(r";\s+(?=[А-ЯЁ])", ". ", text)
    return text


def _remove_short_noisy_fragments(text: str) -> str:
    """Remove short OCR pseudo-sentences while preserving real short replies."""
    return _SHORT_SENTENCE_FRAGMENT_RE.sub(
        lambda match: " " if _is_short_noisy_fragment(match.group(1)) else match.group(0),
        text,
    )


def _is_short_noisy_fragment(fragment: str) -> bool:
    """Return true for compact fragments made of OCR debris, not prose."""
    stripped = fragment.strip()
    if len(stripped) > 45:
        return False

    words = _cyrillic_words(stripped)
    cyr = sum(len(word) for word in words)
    has_digit = any(ch.isdigit() for ch in stripped)
    has_noise_symbol = (
        any(ch in "<>[]{}*_~|\\/^#%$=°" for ch in stripped)
        or "««" in stripped
        or "»»" in stripped
        or ".." in stripped
    )

    if cyr == 0 and (has_digit or has_noise_symbol):
        return True

    if cyr <= 4 and len(words) >= 2:
        return True

    if has_digit and _readable_cyrillic_word_ratio(stripped) < 0.5:
        return True

    return has_noise_symbol and _readable_cyrillic_word_ratio(stripped) < 0.5


def _is_ocr_noise_paragraph(paragraph: str) -> bool:
    """Return true for short paragraphs that are mostly OCR debris."""
    if _is_chapter_heading_line(paragraph):
        return False

    cyr = _cyrillic_char_count(paragraph)
    if cyr == 0:
        return True

    if cyr < 8:
        return True

    word_ratio = _readable_cyrillic_word_ratio(paragraph)
    symbol_ratio = _ocr_symbol_noise_ratio(paragraph)
    if len(paragraph) < 90 and word_ratio < 0.25:
        return True
    return len(paragraph) < 140 and symbol_ratio > 0.08 and word_ratio < 0.45


def _repair_ocr_cross_segment_breaks(text: str) -> str:
    """Repair words split across OCR page/segment boundaries."""
    text = _OCR_CROSS_SEGMENT_HYPHEN_RE.sub(r"\1\2", text)
    return _OCR_CROSS_SEGMENT_PARTICIPLE_RE.sub(r"\1\2", text)


def _postprocess_ocr_text(text: str, language_code: str = "ru") -> str:
    """Clean OCR text from a single page image before downstream normalization."""
    language_code = (language_code or "ru").strip().lower()
    russian_rules = language_code in {"ru", "rus", "russian"}
    text = text.replace("\r", "\n").replace("\f", "\n")
    text = _OCR_HYPHEN_LINEBREAK_RE.sub(r"\1\2", text)

    lines: list[str] = []
    previous_blank = False
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        line = _OCR_LEADING_ARTIFACT_RE.sub("", line).strip()
        line = _strip_trailing_page_marker(line)
        if not line:
            if not previous_blank:
                lines.append("")
            previous_blank = True
            continue
        previous_blank = False
        is_noise_line = (
            _is_ocr_noise_line(line)
            if russian_rules
            else _is_multilingual_ocr_noise_line(line, language_code)
        )
        if is_noise_line:
            continue
        lines.append(line)

    paragraphs: list[str] = []
    current: list[str] = []
    for line in lines:
        if not line:
            if current:
                paragraphs.append(" ".join(current).strip())
                current = []
            continue
        if _is_chapter_heading_line(line):
            if current:
                paragraphs.append(" ".join(current).strip())
                current = []
            paragraphs.append(line.strip())
            continue
        current.append(line)
    if current:
        paragraphs.append(" ".join(current).strip())

    cleaned_paragraphs: list[str] = []
    for paragraph in paragraphs:
        paragraph = _INLINE_HYPHEN_PIPE_RE.sub(r"\1\2", paragraph)
        paragraph = _SPURIOUS_PERIOD_INSIDE_WORD_RE.sub(" ", paragraph)
        paragraph = _INLINE_PIPE_NOISE_RE.sub(" ", paragraph)
        paragraph = _INLINE_NOISE_BEFORE_DASH_RE.sub("", paragraph)
        if paragraph and re.search(r"[\^#*_~|\\/]", paragraph[-20:]):
            paragraph = _TRAILING_SYMBOL_NOISE_RE.sub("", paragraph)
        if russian_rules:
            paragraph = _trim_trailing_ocr_garbage(paragraph)
            paragraph = _normalize_common_ocr_glitches(paragraph)
        paragraph = re.sub(r"\s{2,}", " ", paragraph).strip()
        if paragraph:
            parts = _split_inline_chapter_headings(paragraph) if russian_rules else [paragraph]
            for part in parts:
                is_noise = (
                    _is_ocr_noise_paragraph(part)
                    if russian_rules
                    else _is_multilingual_ocr_noise_paragraph(part, language_code)
                )
                if not is_noise:
                    cleaned_paragraphs.append(part)

    return "\n\n".join(cleaned_paragraphs)


def _is_multilingual_ocr_noise_line(line: str, language_code: str) -> bool:
    """Return true for non-Russian OCR lines that are only scan debris."""
    stripped = line.strip()
    if not stripped:
        return False
    target_chars = target_script_char_count(stripped, language_code)
    alnum = sum(ch.isalnum() for ch in stripped)
    if target_chars == 0 and alnum <= 2:
        return True
    punctuation = sum(not ch.isalnum() and not ch.isspace() for ch in stripped)
    return target_chars == 0 and punctuation / max(1, len(stripped)) > 0.45


def _is_multilingual_ocr_noise_paragraph(paragraph: str, language_code: str) -> bool:
    """Return true for non-Russian OCR paragraphs that lack target-language text."""
    stripped = paragraph.strip()
    if not stripped:
        return True
    target_chars = target_script_char_count(stripped, language_code)
    if target_chars == 0:
        alnum = sum(ch.isalnum() for ch in stripped)
        return alnum <= 2 or _ocr_symbol_noise_ratio(stripped) > 0.35
    if target_chars < 4 and len(stripped) < 20:
        return True
    return target_script_ratio(stripped, language_code) < 0.25 and _ocr_symbol_noise_ratio(stripped) > 0.2


def _looks_like_toc(text: str) -> bool:
    """Return true when an OCR block is likely a table of contents page."""
    sample = text[:2500].lower()
    if "содержание" not in sample:
        return False
    glava_count = sample.count("глава")
    dotted_leaders = sample.count("....") + sample.count("…")
    return glava_count >= 3 or dotted_leaders >= 3


def _ocr_text_is_usable(text: str, language_code: str = "ru") -> bool:
    """Return true when OCR text contains enough readable target-language content."""
    return (
        target_script_char_count(text, language_code) >= MIN_OCR_TARGET_CHARS
        and _page_text_quality(text, language_code) >= 0.3
        and readable_word_ratio(text, language_code) >= MIN_OCR_READABLE_WORD_RATIO
        and _ocr_symbol_noise_ratio(text) <= MAX_OCR_SYMBOL_NOISE_RATIO
    )


def _should_keep_ocr_text(text: str, language_code: str = "ru") -> bool:
    """Decide whether an OCR page/segment is useful book text."""
    if not _ocr_text_is_usable(text, language_code):
        return False
    return not _looks_like_toc(text)


def _page_text_quality(text: str, language_code: str = "ru") -> float:
    """Estimate OCR quality of a page — ratio of Cyrillic alpha chars.

    Returns a float 0.0..1.0 where 1.0 means all alpha chars are Cyrillic.
    """
    return target_script_ratio(text, language_code)


def _cyrillic_words(text: str) -> list[str]:
    """Extract Cyrillic word runs without relying on locale-specific regex classes."""
    words: list[str] = []
    current: list[str] = []
    for ch in text:
        if "\u0400" <= ch <= "\u04ff":
            current.append(ch)
            continue
        if current:
            words.append("".join(current))
            current = []
    if current:
        words.append("".join(current))
    return words


def _readable_cyrillic_word_ratio(text: str) -> float:
    """Estimate whether OCR output is made of real words instead of short debris."""
    words = _cyrillic_words(text)
    if not words:
        return 0.0
    readable = sum(1 for word in words if len(word) >= 4)
    return readable / len(words)


def _ocr_symbol_noise_ratio(text: str) -> float:
    """Estimate how much non-text scan debris survived OCR post-processing."""
    if not text:
        return 0.0
    allowed = set(".,:;!?—–-«»\"()[]…，。？！：；、“”‘’《》〈〉")
    noisy = sum(
        1
        for ch in text
        if not ch.isalnum() and not ch.isspace() and ch not in allowed
    )
    return noisy / len(text)


def _ocr_pdf_with_tesseract(
    path: Path,
    lang: str = "rus",
    language_code: str = "ru",
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

    ocr_runtime = "pytesseract"
    try:
        import pytesseract
        from PIL import Image
        pytesseract.get_tesseract_version()
    except Exception:
        if _tesseract_cli_available():
            from PIL import Image

            pytesseract = None
            ocr_runtime = "cli"
            logger.info("Using Tesseract via local CLI.")
        else:
            raise RuntimeError("Tesseract is not installed in the current OS environment.")

    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)

    pages: list[str] = []
    with fitz.open(str(path)) as doc:
        total = len(doc)
        for page_num in range(total):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csGRAY)
            img = Image.frombytes("L", [pix.width, pix.height], pix.samples)
            segments = _prepare_ocr_page_images(img)

            for segment_num, segment in enumerate(segments, start=1):
                page_text = _ocr_pil_image_with_tesseract(
                    segment,
                    lang=lang,
                    psm=psm,
                    preprocess=preprocess,
                    runtime=ocr_runtime,
                    pytesseract_module=pytesseract if ocr_runtime == "pytesseract" else None,
                )
                page_text = _postprocess_ocr_text(page_text, language_code=language_code)

                if not _should_keep_ocr_text(page_text, language_code):
                    logger.debug(
                        "Page %d segment %d skipped: chars=%d, cyr=%d, quality=%.0f%%.",
                        page_num + 1,
                        segment_num,
                        len(page_text),
                        target_script_char_count(page_text, language_code),
                        _page_text_quality(page_text, language_code) * 100,
                    )
                    continue
                pages.append(page_text)

            if (page_num + 1) % 20 == 0 or page_num == total - 1:
                logger.info("OCR progress: %d/%d pages", page_num + 1, total)

    return _repair_ocr_cross_segment_breaks("\n\n".join(pages))


def extract_pdf_with_ocr_mode(
    path: Path,
    mode: OcrMode,
    dpi: int = 400,
    psm: int = 6,
    preprocess: bool = True,
    lang: str = "rus",
    language_code: str = "ru",
) -> PdfOcrCompareResult:
    """Extract PDF text according to the requested OCR mode.

    Uses a PDFMiner/pdfplumber structural pass first.  When OCR is requested,
    Tesseract is applied to image-like regions or image-only pages.
    """
    loader = PdfLoader()
    resolved = path.resolve()
    native_structure: PdfStructuredExtraction | None = None
    try:
        native_structure = _extract_pdf_structured(resolved, run_ocr=False)
        native_text = native_structure.to_text()
        logger.info("PDF structure detected as %s.", native_structure.document_type)
    except ImportError as exc:
        logger.debug("Structured PDF extraction dependencies unavailable: %s", exc)
        native_text = loader._extract_text(resolved)
    except Exception as exc:
        logger.debug("Structured PDF extraction failed, falling back to PyMuPDF: %s", exc)
        native_text = loader._extract_text(resolved)

    native_text = remove_repeated_headers(native_text, min_occurrences=3)
    native_variant = PdfTextVariant(
        kind="native",
        text=native_text,
        document_type=native_structure.document_type if native_structure else "unknown",
    )

    if mode == OcrMode.OFF:
        return PdfOcrCompareResult(
            native=native_variant,
            ocr=None,
            native_structure=native_structure,
        )

    if not _tesseract_available():
        logger.warning(
            "Tesseract OCR is not installed in this OS environment. "
            "Run install.bat --interactive --install-system-tools --download-tessdata on Windows "
            "or ./install.sh --interactive --install-system-tools --download-tessdata on Linux/macOS. "
            "Falling back to native text extraction."
        )
        return PdfOcrCompareResult(
            native=native_variant,
            ocr=None,
            native_structure=native_structure,
        )

    ocr_structure: PdfStructuredExtraction | None = None
    try:
        logger.info(
            "Running structured PDF extraction with OCR on '%s' (dpi=%d, psm=%d, preprocess=%s)...",
            resolved.name, dpi, psm, preprocess,
        )
        try:
            ocr_structure = _extract_pdf_structured(
                resolved,
                run_ocr=True,
                lang=lang,
                language_code=language_code,
                dpi=dpi,
                psm=psm,
                preprocess=preprocess,
            )
            ocr_text = _repair_ocr_cross_segment_breaks(ocr_structure.to_text())
        except ImportError as exc:
            logger.debug("Structured OCR dependencies unavailable, using full-page OCR: %s", exc)
            ocr_text = _ocr_pdf_with_tesseract(
                resolved,
                lang=lang,
                language_code=language_code,
                dpi=dpi,
                psm=psm,
                preprocess=preprocess,
            )

        if _target_text_unreadable(native_text, language_code) and _target_text_unreadable(ocr_text, language_code):
            fallback_text = _ocr_pdf_with_tesseract(
                resolved,
                lang=lang,
                language_code=language_code,
                dpi=dpi,
                psm=psm,
                preprocess=preprocess,
            )
            if len(fallback_text.strip()) > len(ocr_text.strip()):
                logger.info("Full-page OCR fallback produced more text than structured OCR.")
                ocr_text = fallback_text
                ocr_structure = None

        ocr_text = remove_repeated_headers(ocr_text, min_occurrences=3)
        ocr_variant = PdfTextVariant(
            kind="ocr",
            text=ocr_text,
            document_type=ocr_structure.document_type if ocr_structure else "ocr_full_page",
        )
        logger.info("OCR complete: %d characters extracted.", len(ocr_text))
    except Exception as exc:
        logger.warning("OCR extraction failed for '%s': %s", resolved, exc)
        ocr_variant = None

    return PdfOcrCompareResult(
        native=native_variant,
        ocr=ocr_variant,
        native_structure=native_structure,
        ocr_structure=ocr_structure,
    )


def _cyrillic_ratio(text: str) -> float:
    """Return the fraction of alphabetic characters that are Cyrillic."""
    sample = text[:10000]
    alpha = [c for c in sample if c.isalpha()]
    if not alpha:
        return 0.0
    cyr = sum(1 for c in alpha if "\u0400" <= c <= "\u04ff")
    return cyr / len(alpha)


def _target_text_unreadable(text: str, language_code: str = "ru") -> bool:
    """Return true when text is empty or does not match the selected language."""
    return text_unreadable(text, language_code, MIN_READABLE_TARGET_RATIO)


def _ocr_is_substantially_more_complete(
    native_text: str,
    ocr_text: str,
    language_code: str = "ru",
) -> bool:
    """Return true when a small native text layer is only a partial PDF overlay."""
    native_len = len(native_text.strip())
    ocr_len = len(ocr_text.strip())
    if ocr_len < 1000 or native_len <= 0:
        return False

    native_target_chars = target_script_char_count(native_text, language_code)
    ocr_target_chars = target_script_char_count(ocr_text, language_code)
    length_jump = ocr_len >= native_len * 3 or ocr_len >= native_len + 2500
    target_script_jump = ocr_target_chars >= max(
        native_target_chars * 3,
        native_target_chars + 500,
    )
    return length_jump and target_script_jump


def select_pdf_text_for_mode(
    compare: PdfOcrCompareResult,
    mode: OcrMode,
    language_code: str = "ru",
) -> tuple[PdfTextVariant, dict[str, Any]]:
    """
    Select which text variant to use for downstream processing.

    Returns (chosen_variant, stats_dict).
    """
    native = compare.native
    ocr = compare.ocr

    native_cyr = _cyrillic_ratio(native.text)
    ocr_cyr = _cyrillic_ratio(ocr.text) if ocr else 0.0
    ocr_much_longer = (
        _ocr_is_substantially_more_complete(native.text, ocr.text, language_code)
        if ocr
        else False
    )

    stats: dict[str, Any] = {
        "mode": mode.value,
        "native_len": len(native.text),
        "ocr_len": len(ocr.text) if ocr else 0,
        "native_empty": len(native.text.strip()) == 0,
        "ocr_empty": (len(ocr.text.strip()) == 0) if ocr else True,
        "native_cyrillic_ratio": round(native_cyr, 3),
        "ocr_cyrillic_ratio": round(ocr_cyr, 3),
        "native_cyrillic_chars": _cyrillic_char_count(native.text),
        "ocr_cyrillic_chars": _cyrillic_char_count(ocr.text) if ocr else 0,
        "native_document_type": native.document_type,
        "ocr_document_type": ocr.document_type if ocr else None,
        "language": language_code,
        "native_target_ratio": round(target_script_ratio(native.text, language_code), 3),
        "ocr_target_ratio": round(target_script_ratio(ocr.text, language_code), 3) if ocr else 0.0,
        "native_target_chars": target_script_char_count(native.text, language_code),
        "ocr_target_chars": target_script_char_count(ocr.text, language_code) if ocr else 0,
        "native_unreadable": _target_text_unreadable(native.text, language_code),
        "ocr_unreadable": _target_text_unreadable(ocr.text, language_code) if ocr else True,
        "ocr_much_longer": ocr_much_longer,
        "selected": "native",
        "reason": "",
    }

    if mode == OcrMode.OFF:
        stats["reason"] = "ocr_mode=off"
        return native, stats

    if ocr is None:
        if stats["native_unreadable"]:
            stats["reason"] = "ocr_unavailable_native_unreadable"
        else:
            stats["reason"] = "ocr_unavailable_falling_back_to_native"
        return native, stats

    if mode == OcrMode.FORCE:
        stats["selected"] = "ocr"
        stats["reason"] = "ocr_mode=force"
        return ocr, stats

    # AUTO / COMPARE: prefer OCR when native text is empty, garbage, or clearly partial.
    native_is_bad = bool(stats["native_unreadable"])
    ocr_usable = not stats["ocr_unreadable"]

    if native_is_bad and ocr_usable:
        stats["selected"] = "ocr"
        reason_detail = "native_empty" if stats["native_empty"] else f"native_cyr={native_cyr:.2f}"
        stats["reason"] = f"{'auto' if mode == OcrMode.AUTO else 'compare'}_mode_{reason_detail}_use_ocr"
        return ocr, stats

    if ocr_usable and ocr_much_longer:
        stats["selected"] = "ocr"
        stats["reason"] = f"{'auto' if mode == OcrMode.AUTO else 'compare'}_mode_ocr_much_longer_use_ocr"
        return ocr, stats

    if native_is_bad and not ocr_usable:
        stats["reason"] = f"{'auto' if mode == OcrMode.AUTO else 'compare'}_mode_no_readable_ocr"
        return native, stats

    stats["reason"] = f"{'auto' if mode == OcrMode.AUTO else 'compare'}_mode_native_preferred"
    return native, stats


def write_pdf_compare_report(
    output_dir: Path,
    compare: PdfOcrCompareResult,
    stats: dict[str, Any],
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
        "native_cyrillic_ratio": stats.get("native_cyrillic_ratio"),
        "ocr_cyrillic_ratio": stats.get("ocr_cyrillic_ratio"),
        "native_cyrillic_chars": stats.get("native_cyrillic_chars"),
        "ocr_cyrillic_chars": stats.get("ocr_cyrillic_chars"),
        "native_document_type": stats.get("native_document_type"),
        "ocr_document_type": stats.get("ocr_document_type"),
        "language": stats.get("language"),
        "native_target_ratio": stats.get("native_target_ratio"),
        "ocr_target_ratio": stats.get("ocr_target_ratio"),
        "native_target_chars": stats.get("native_target_chars"),
        "ocr_target_chars": stats.get("ocr_target_chars"),
        "native_unreadable": stats.get("native_unreadable"),
        "ocr_unreadable": stats.get("ocr_unreadable"),
        "ocr_much_longer": stats.get("ocr_much_longer"),
    }
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
