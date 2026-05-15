"""Background worker for text normalization pipeline."""

from __future__ import annotations

import time
from hashlib import sha1
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from book_normalizer.config import OcrMode
from book_normalizer.gui.i18n import t


def _format_eta(seconds: float) -> str:
    """Format seconds to human-readable string."""
    if seconds < 60:
        return f"{int(seconds)}s"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}m {s:02d}s"


def _effective_pdf_extraction_mode(
    requested_mode: OcrMode,
    *,
    tesseract_available: bool,
) -> OcrMode:
    """Return the PDF extraction mode the GUI can safely run."""
    if tesseract_available or requested_mode == OcrMode.OFF:
        return requested_mode

    if requested_mode == OcrMode.FORCE:
        raise RuntimeError(t("norm.err_tesseract_missing_force"))

    return OcrMode.OFF


def _ensure_pdf_selection_is_usable(
    requested_mode: OcrMode,
    stats: dict[str, object],
    *,
    tesseract_available: bool,
) -> None:
    """Raise a GUI-friendly error instead of passing broken PDF text downstream."""
    if requested_mode == OcrMode.OFF:
        return

    ocr_unreadable = bool(stats.get("ocr_unreadable", stats.get("ocr_empty", True)))

    if requested_mode == OcrMode.FORCE and ocr_unreadable:
        raise RuntimeError(t("norm.err_ocr_failed_force"))

    if stats.get("native_unreadable") and ocr_unreadable:
        if tesseract_available:
            raise RuntimeError(t("norm.err_ocr_failed_unreadable"))
        raise RuntimeError(t("norm.err_tesseract_missing_scanned"))


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
        llm_normalize: bool = False,
        llm_endpoint: str = "http://localhost:11434/v1",
        llm_model: str = "qwen3:8b",
        llm_api_key: str = "",
        skip_stress: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self._input_path = input_path
        self._ocr_mode = ocr_mode
        self._ocr_dpi = ocr_dpi
        self._ocr_psm = ocr_psm
        self._llm_normalize = llm_normalize
        self._llm_endpoint = llm_endpoint
        self._llm_model = llm_model
        self._llm_api_key = llm_api_key
        self._skip_stress = skip_stress

    def _ocr_with_progress(self, path: Path, ocr_mode, dpi: int, psm: int):
        """Run OCR with per-page progress reporting."""
        import fitz

        from book_normalizer.loaders.pdf_loader import (
            _ocr_pil_image_with_tesseract,
            _postprocess_ocr_text,
            _prepare_ocr_page_images,
            _repair_ocr_cross_segment_breaks,
            _should_keep_ocr_text,
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
                from PIL import Image
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
                img = Image.frombytes("L", [pix.width, pix.height], pix.samples)

                for segment_num, segment in enumerate(
                    _prepare_ocr_page_images(img),
                    start=1,
                ):
                    page_text = _ocr_pil_image_with_tesseract(
                        segment,
                        lang="rus",
                        psm=psm,
                        preprocess=True,
                        use_wsl=use_wsl,
                        pytesseract_module=None if use_wsl else pytesseract,
                    )
                    page_text = _postprocess_ocr_text(page_text)
                    if _should_keep_ocr_text(page_text):
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

        ocr_text = _repair_ocr_cross_segment_breaks("\n\n".join(pages_text))
        return remove_repeated_headers(ocr_text, min_occurrences=3)

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

    def _llm_cache_dir(self) -> Path:
        """Return a stable cache directory for GUI LLM normalization."""
        try:
            source = str(self._input_path.resolve()).casefold()
        except OSError:
            source = str(self._input_path).casefold()
        digest = sha1(source.encode("utf-8")).hexdigest()[:16]
        return Path("data") / "user_memory" / "llm_norm_cache" / digest

    def _llm_normalize_with_progress(self, book):
        """Run optional LLM normalization over already rule-normalized text."""
        from book_normalizer.normalization.llm_normalizer import LlmNormalizer

        total_paragraphs = sum(len(ch.paragraphs) for ch in book.chapters)
        if total_paragraphs == 0:
            return book

        start_time = time.time()
        report_interval = max(1, total_paragraphs // 50)

        normalizer = LlmNormalizer(
            endpoint=self._llm_endpoint,
            model=self._llm_model,
            cache_dir=self._llm_cache_dir(),
            api_key=self._llm_api_key,
        )

        def report(done: int, total: int, accepted: int, rejected: int) -> None:
            if done % report_interval != 0 and done != total:
                return
            elapsed = time.time() - start_time
            avg = elapsed / done if done else 0
            remaining = avg * (total - done)
            eta = _format_eta(remaining)
            self.progress.emit(
                t(
                    "norm.llm_progress",
                    done=done,
                    total=total,
                    accepted=accepted,
                    rejected=rejected,
                    eta=eta,
                )
            )
            self.progress_pct.emit(done, total, eta)

        accepted, rejected = normalizer.normalize_book(book, progress_callback=report)
        self.progress.emit(
            t(
                "norm.llm_done",
                accepted=accepted,
                rejected=rejected,
            )
        )
        return book

    def run(self) -> None:
        try:
            from book_normalizer.chaptering.detector import ChapterDetector
            from book_normalizer.loaders.factory import LoaderFactory
            from book_normalizer.loaders.pdf_loader import (
                PdfLoader,
                PdfOcrCompareResult,
                PdfTextVariant,
                _tesseract_available,
                extract_pdf_with_ocr_mode,
                select_pdf_text_for_mode,
            )
            from book_normalizer.models.book import Book, Chapter, Metadata
            from book_normalizer.normalization.cleanup import remove_repeated_headers

            t0 = time.time()
            self.progress.emit(t("norm.loading"))
            is_pdf = self._input_path.suffix.lower() == ".pdf"

            if is_pdf:
                ocr = OcrMode(self._ocr_mode)
                tesseract_available = _tesseract_available()
                effective_ocr = _effective_pdf_extraction_mode(
                    ocr,
                    tesseract_available=tesseract_available,
                )

                if effective_ocr == OcrMode.OFF:
                    if ocr != OcrMode.OFF:
                        self.progress.emit(t("norm.ocr_unavailable_native"))

                    compare = extract_pdf_with_ocr_mode(
                        self._input_path, effective_ocr,
                        dpi=self._ocr_dpi, psm=self._ocr_psm,
                    )
                    chosen, stats = select_pdf_text_for_mode(compare, ocr)

                    _ensure_pdf_selection_is_usable(
                        ocr,
                        stats,
                        tesseract_available=tesseract_available,
                    )
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
                    chosen, stats = select_pdf_text_for_mode(compare, ocr)
                    _ensure_pdf_selection_is_usable(
                        ocr,
                        stats,
                        tesseract_available=tesseract_available,
                    )

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

            if self._llm_normalize:
                self.progress.emit(
                    t("norm.llm_start", model=self._llm_model)
                )
                book = self._llm_normalize_with_progress(book)

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
