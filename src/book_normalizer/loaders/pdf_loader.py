"""Loader for PDF (.pdf) book files using PyMuPDF."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from book_normalizer.config import OcrMode
from book_normalizer.loaders.base import BaseLoader
from book_normalizer.models.book import Book, Chapter, Metadata, Paragraph
from book_normalizer.normalization.cleanup import remove_repeated_headers

logger = logging.getLogger(__name__)

MIN_READABLE_CYRILLIC_RATIO = 0.3
MIN_OCR_CYRILLIC_CHARS = 80
MIN_OCR_READABLE_WORD_RATIO = 0.35
MAX_OCR_SYMBOL_NOISE_RATIO = 0.06
SPREAD_PAGE_RATIO = 1.2


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
    """Encode a PIL image to PNG bytes for WSL Tesseract."""
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
    use_wsl: bool,
    pytesseract_module: Any | None = None,
) -> str:
    """Run Tesseract against a PIL image, either natively or via WSL."""
    if preprocess:
        img = _preprocess_image_for_ocr(img)

    if use_wsl:
        return _ocr_image_via_wsl(_encode_png(img), lang, psm=psm)

    if pytesseract_module is None:
        import pytesseract as pytesseract_module

    return pytesseract_module.image_to_string(
        img,
        lang=lang,
        config=f"--psm {psm}",
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


def _postprocess_ocr_text(text: str) -> str:
    """Clean OCR text from a single page image before downstream normalization."""
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
        if _is_ocr_noise_line(line):
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
        paragraph = _trim_trailing_ocr_garbage(paragraph)
        paragraph = _normalize_common_ocr_glitches(paragraph)
        paragraph = re.sub(r"\s{2,}", " ", paragraph).strip()
        if paragraph:
            for part in _split_inline_chapter_headings(paragraph):
                if not _is_ocr_noise_paragraph(part):
                    cleaned_paragraphs.append(part)

    return "\n\n".join(cleaned_paragraphs)


def _looks_like_toc(text: str) -> bool:
    """Return true when an OCR block is likely a table of contents page."""
    sample = text[:2500].lower()
    if "содержание" not in sample:
        return False
    glava_count = sample.count("глава")
    dotted_leaders = sample.count("....") + sample.count("…")
    return glava_count >= 3 or dotted_leaders >= 3


def _ocr_text_is_usable(text: str) -> bool:
    """Return true when OCR text contains enough readable Russian content."""
    return (
        _cyrillic_char_count(text) >= MIN_OCR_CYRILLIC_CHARS
        and _page_text_quality(text) >= 0.3
        and _readable_cyrillic_word_ratio(text) >= MIN_OCR_READABLE_WORD_RATIO
        and _ocr_symbol_noise_ratio(text) <= MAX_OCR_SYMBOL_NOISE_RATIO
    )


def _should_keep_ocr_text(text: str) -> bool:
    """Decide whether an OCR page/segment is useful book text."""
    if not _ocr_text_is_usable(text):
        return False
    return not _looks_like_toc(text)


def _page_text_quality(text: str) -> float:
    """Estimate OCR quality of a page — ratio of Cyrillic alpha chars.

    Returns a float 0.0..1.0 where 1.0 means all alpha chars are Cyrillic.
    """
    alpha = [c for c in text if c.isalpha()]
    if not alpha:
        return 0.0
    cyrillic = sum(1 for c in alpha if "\u0400" <= c <= "\u04ff")
    return cyrillic / len(alpha)


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
    allowed = set(".,:;!?—–-«»\"()[]…")
    noisy = sum(
        1
        for ch in text
        if not ch.isalnum() and not ch.isspace() and ch not in allowed
    )
    return noisy / len(text)


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
            from PIL import Image
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
            img = Image.frombytes("L", [pix.width, pix.height], pix.samples)
            segments = _prepare_ocr_page_images(img)

            for segment_num, segment in enumerate(segments, start=1):
                page_text = _ocr_pil_image_with_tesseract(
                    segment,
                    lang=lang,
                    psm=psm,
                    preprocess=preprocess,
                    use_wsl=use_wsl,
                    pytesseract_module=None if use_wsl else pytesseract,
                )
                page_text = _postprocess_ocr_text(page_text)

                if not _should_keep_ocr_text(page_text):
                    logger.debug(
                        "Page %d segment %d skipped: chars=%d, cyr=%d, quality=%.0f%%.",
                        page_num + 1,
                        segment_num,
                        len(page_text),
                        _cyrillic_char_count(page_text),
                        _page_text_quality(page_text) * 100,
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


def _russian_text_unreadable(text: str) -> bool:
    """Return true when text is empty or does not look like readable Russian."""
    return len(text.strip()) == 0 or _cyrillic_ratio(text) < MIN_READABLE_CYRILLIC_RATIO


def _ocr_is_substantially_more_complete(native_text: str, ocr_text: str) -> bool:
    """Return true when a small native text layer is only a partial PDF overlay."""
    native_len = len(native_text.strip())
    ocr_len = len(ocr_text.strip())
    if ocr_len < 1000 or native_len <= 0:
        return False

    native_cyr = _cyrillic_char_count(native_text)
    ocr_cyr = _cyrillic_char_count(ocr_text)
    length_jump = ocr_len >= native_len * 3 or ocr_len >= native_len + 2500
    cyrillic_jump = ocr_cyr >= max(native_cyr * 3, native_cyr + 500)
    return length_jump and cyrillic_jump


def select_pdf_text_for_mode(
    compare: PdfOcrCompareResult,
    mode: OcrMode,
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
        _ocr_is_substantially_more_complete(native.text, ocr.text)
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
        "native_unreadable": _russian_text_unreadable(native.text),
        "ocr_unreadable": _russian_text_unreadable(ocr.text) if ocr else True,
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
        "native_unreadable": stats.get("native_unreadable"),
        "ocr_unreadable": stats.get("ocr_unreadable"),
        "ocr_much_longer": stats.get("ocr_much_longer"),
    }
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
