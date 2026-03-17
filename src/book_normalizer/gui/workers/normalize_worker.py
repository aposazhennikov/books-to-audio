"""Background worker for text normalization pipeline."""

from __future__ import annotations

import time
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from book_normalizer.gui.i18n import t


def _format_eta(seconds: float) -> str:
    """Format seconds to human-readable string."""
    if seconds < 60:
        return f"{int(seconds)}s"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}m {s:02d}s"


class NormalizeWorker(QThread):
    """Run book loading + normalization + chapter detection in a background thread."""

    progress = pyqtSignal(str)
    progress_pct = pyqtSignal(int, int, str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(
        self,
        input_path: Path,
        ocr_mode: str = "auto",
        ocr_dpi: int = 400,
        ocr_psm: int = 6,
        skip_stress: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self._input_path = input_path
        self._ocr_mode = ocr_mode
        self._ocr_dpi = ocr_dpi
        self._ocr_psm = ocr_psm
        self._skip_stress = skip_stress

    def _ocr_with_progress(self, path: Path, ocr_mode, dpi: int, psm: int):
        """Run OCR with per-page progress reporting."""
        import fitz

        from book_normalizer.loaders.pdf_loader import (
            _ocr_image_via_wsl,
            _page_text_quality,
            _preprocess_image_for_ocr,
            _wsl_tesseract_available,
            remove_repeated_headers,
        )

        resolved = path.resolve()
        use_wsl = False
        try:
            import pytesseract
            from PIL import Image
            pytesseract.get_tesseract_version()
        except Exception:
            if _wsl_tesseract_available():
                use_wsl = True
            else:
                raise RuntimeError("Tesseract is not installed.")

        zoom = dpi / 72
        matrix = fitz.Matrix(zoom, zoom)
        pages_text: list[str] = []

        with fitz.open(str(resolved)) as doc:
            total_pages = len(doc)
            start_time = time.time()

            for page_num in range(total_pages):
                page = doc[page_num]
                pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csGRAY)

                if use_wsl:
                    import io

                    from PIL import Image as PILImage
                    img = PILImage.frombytes("L", [pix.width, pix.height], pix.samples)
                    img = _preprocess_image_for_ocr(img)
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    page_text = _ocr_image_via_wsl(buf.getvalue(), "rus", psm=psm)
                else:
                    img = Image.frombytes("L", [pix.width, pix.height], pix.samples)
                    img = _preprocess_image_for_ocr(img)
                    tess_config = f"--psm {psm}"
                    page_text = pytesseract.image_to_string(
                        img, lang="rus", config=tess_config,
                    )

                if page_text and page_text.strip():
                    quality = _page_text_quality(page_text)
                    if quality >= 0.15:
                        pages_text.append(page_text)

                elapsed = time.time() - start_time
                done = page_num + 1
                if done > 1:
                    avg_per_page = elapsed / done
                    remaining = avg_per_page * (total_pages - done)
                    eta = _format_eta(remaining)
                else:
                    eta = "..."

                self.progress.emit(f"OCR: {done}/{total_pages} — ETA: {eta}")
                self.progress_pct.emit(done, total_pages, eta)

        return remove_repeated_headers("\n\n".join(pages_text), min_occurrences=3)

    def _normalize_with_progress(self, book):
        """Run normalization pipeline with per-paragraph progress."""
        from book_normalizer.normalization.pipeline import NormalizationPipeline

        pipeline = NormalizationPipeline()

        total_paragraphs = sum(len(ch.paragraphs) for ch in book.chapters)
        if total_paragraphs == 0:
            return pipeline, book

        done = 0
        start_time = time.time()
        report_interval = max(1, total_paragraphs // 50)

        for chapter in book.chapters:
            for para in chapter.paragraphs:
                para.normalized_text, _ = pipeline.normalize_text_with_tracking(
                    para.raw_text,
                )
                done += 1

                if done % report_interval == 0 or done == total_paragraphs:
                    elapsed = time.time() - start_time
                    if done > 0:
                        avg = elapsed / done
                        remaining = avg * (total_paragraphs - done)
                        eta = _format_eta(remaining)
                    else:
                        eta = "..."

                    self.progress.emit(
                        t(
                            "norm.norm_paragraphs",
                            done=done,
                            total=total_paragraphs,
                            eta=eta,
                        )
                    )
                    self.progress_pct.emit(done, total_paragraphs, eta)

        return pipeline, book

    def run(self) -> None:
        try:
            from book_normalizer.chaptering.detector import ChapterDetector
            from book_normalizer.config import OcrMode
            from book_normalizer.loaders.factory import LoaderFactory
            from book_normalizer.loaders.pdf_loader import (
                PdfLoader,
                PdfOcrCompareResult,
                PdfTextVariant,
                select_pdf_text_for_mode,
            )
            from book_normalizer.models.book import Book, Chapter, Metadata
            from book_normalizer.normalization.cleanup import remove_repeated_headers

            t0 = time.time()
            self.progress.emit(t("norm.loading"))
            is_pdf = self._input_path.suffix.lower() == ".pdf"

            if is_pdf:
                ocr = OcrMode(self._ocr_mode)

                if ocr == OcrMode.OFF:
                    from book_normalizer.loaders.pdf_loader import (
                        extract_pdf_with_ocr_mode,
                    )
                    compare = extract_pdf_with_ocr_mode(
                        self._input_path, ocr,
                        dpi=self._ocr_dpi, psm=self._ocr_psm,
                    )
                    chosen, _ = select_pdf_text_for_mode(compare, ocr)
                else:
                    self.progress.emit(
                        f"OCR (DPI={self._ocr_dpi}, PSM={self._ocr_psm})..."
                    )
                    loader = PdfLoader()
                    native_text = remove_repeated_headers(
                        loader._extract_text(self._input_path.resolve()),
                        min_occurrences=3,
                    )
                    native_variant = PdfTextVariant(kind="native", text=native_text)

                    ocr_text = self._ocr_with_progress(
                        self._input_path, ocr, self._ocr_dpi, self._ocr_psm,
                    )
                    ocr_variant = PdfTextVariant(kind="ocr", text=ocr_text)

                    compare = PdfOcrCompareResult(
                        native=native_variant, ocr=ocr_variant,
                    )
                    chosen, _ = select_pdf_text_for_mode(compare, ocr)

                paragraphs = PdfLoader._split_paragraphs(chosen.text)
                chapter = Chapter(title="Full Text", index=0, paragraphs=paragraphs)
                metadata = Metadata(
                    source_path=str(self._input_path), source_format="pdf",
                )
                book = Book(metadata=metadata, chapters=[chapter])
            else:
                factory = LoaderFactory.default()
                book = factory.load(self._input_path)

            pipeline, book = self._normalize_with_progress(book)

            self.progress.emit(t("norm.detecting_chapters"))
            detector = ChapterDetector()
            book = detector.detect_and_split(book)

            # Re-normalize after chapter split.
            pipeline, book = self._normalize_with_progress(book)

            if not self._skip_stress:
                self.progress.emit(t("norm.annotating_stress"))
                from book_normalizer.config import AppConfig
                from book_normalizer.memory.stress_store import StressStore
                from book_normalizer.stress.annotator import StressAnnotator
                from book_normalizer.stress.dictionary import StressDictionary

                config = AppConfig()
                stress_store = StressStore(config.stress_dict_path)
                stress_dict = StressDictionary(store=stress_store)
                annotator = StressAnnotator(stress_dict)
                annotator.annotate_book(book)

            total_time = _format_eta(time.time() - t0)
            self.progress.emit(
                t("norm.done", n=len(book.chapters), time=total_time)
            )
            self.progress_pct.emit(1, 1, "")
            self.finished.emit(book)

        except Exception as exc:
            self.error.emit(str(exc))
