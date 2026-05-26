"""Background worker for text normalization pipeline."""

from __future__ import annotations

import platform
import time
from hashlib import sha1
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from book_normalizer.config import OcrMode
from book_normalizer.gui.i18n import t
from book_normalizer.languages import (
    is_russian_language,
    normalize_book_language,
    tesseract_language,
)
from book_normalizer.llm.model_router import PRIMARY_QWEN3_MODEL, model_plan_for_language
from book_normalizer.runtime_paths import configured_ollama_endpoint


def _apply_selected_book_language(book: object, language: str) -> object:
    """Persist the user-selected language on a loaded Book instance."""
    selected = normalize_book_language(language)
    metadata = getattr(book, "metadata", None)
    if metadata is not None:
        metadata.language = selected
    if hasattr(book, "add_audit"):
        book.add_audit("language", "selected", f"language={selected}")
    return book


def _format_eta(seconds: float) -> str:
    """Format seconds to human-readable string."""
    if seconds < 60:
        return f"{int(seconds)}s"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}m {s:02d}s"


def _native_ocr_install_hint() -> str:
    """Return the native installer command that enables OCR tools."""
    script = "install.bat" if platform.system() == "Windows" else "./install.sh"
    return f"{script} --interactive --install-system-tools --download-tessdata"


def _effective_pdf_extraction_mode(
    requested_mode: OcrMode,
    *,
    tesseract_available: bool,
) -> OcrMode:
    """Return the PDF extraction mode the GUI can safely run."""
    if tesseract_available or requested_mode == OcrMode.OFF:
        return requested_mode

    if requested_mode == OcrMode.FORCE:
        raise RuntimeError(
            t(
                "norm.err_tesseract_missing_force",
                hint=_native_ocr_install_hint(),
            )
        )

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
        raise RuntimeError(
            t(
                "norm.err_tesseract_missing_scanned",
                hint=_native_ocr_install_hint(),
            )
        )


class NormalizeWorker(QThread):
    """Run book loading + normalization + chapter detection in a background thread."""

    progress = pyqtSignal(str)
    progress_pct = pyqtSignal(int, int, str)
    preview_ready = pyqtSignal(object)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(
        self,
        input_path: Path,
        ocr_mode: str = "auto",
        ocr_dpi: int = 400,
        ocr_psm: int = 6,
        llm_normalize: bool = False,
        llm_endpoint: str = "",
        llm_model: str = PRIMARY_QWEN3_MODEL,
        llm_api_key: str = "",
        skip_stress: bool = False,
        book_language: str = "ru",
        parent=None,
    ):
        super().__init__(parent)
        self._input_path = input_path
        self._ocr_mode = ocr_mode
        self._ocr_dpi = ocr_dpi
        self._ocr_psm = ocr_psm
        self._llm_normalize = llm_normalize
        self._llm_endpoint = llm_endpoint or configured_ollama_endpoint()
        self._llm_model = llm_model
        self._llm_api_key = llm_api_key
        self._skip_stress = skip_stress
        self._book_language = normalize_book_language(book_language)

    def _ocr_with_progress(self, path: Path, ocr_mode, dpi: int, psm: int):
        """Run OCR with per-page progress reporting."""
        import fitz

        from book_normalizer.loaders.pdf_loader import (
            _load_tesseract_runtime,
            _ocr_pil_image_with_tesseract,
            _postprocess_ocr_text,
            _prepare_ocr_page_images,
            _repair_ocr_cross_segment_breaks,
            _should_keep_ocr_text,
            remove_repeated_headers,
        )

        resolved = path.resolve()
        ocr_lang = tesseract_language(self._book_language)
        try:
            from PIL import Image
        except Exception as exc:
            raise RuntimeError("Pillow is not installed. Install the OCR dependencies first.") from exc
        ocr_runtime, pytesseract_module = _load_tesseract_runtime()

        zoom = dpi / 72
        matrix = fitz.Matrix(zoom, zoom)
        pages_text: list[str] = []

        with fitz.open(str(resolved)) as doc:
            total_pages = len(doc)
            start_time = time.time()
            self.progress.emit(
                t(
                    "norm.ocr_pages_start",
                    total=total_pages,
                    dpi=dpi,
                    psm=psm,
                )
            )
            self.progress_pct.emit(0, total_pages, "")

            for page_num in range(total_pages):
                page_index = page_num + 1
                self.progress.emit(
                    t(
                        "norm.ocr_page_rendering",
                        page=page_index,
                        total=total_pages,
                        dpi=dpi,
                    )
                )
                page = doc[page_num]
                pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csGRAY)
                img = Image.frombytes("L", [pix.width, pix.height], pix.samples)

                segments = list(_prepare_ocr_page_images(img))
                for segment_num, segment in enumerate(segments, start=1):
                    self.progress.emit(
                        t(
                            "norm.ocr_page_recognizing",
                            page=page_index,
                            total=total_pages,
                            segment=segment_num,
                            segments=len(segments),
                        )
                    )
                    page_text = _ocr_pil_image_with_tesseract(
                        segment,
                        lang=ocr_lang,
                        psm=psm,
                        preprocess=True,
                        runtime=ocr_runtime,
                        pytesseract_module=pytesseract_module,
                    )
                    page_text = _postprocess_ocr_text(
                        page_text,
                        language_code=self._book_language,
                    )
                    if _should_keep_ocr_text(page_text, self._book_language):
                        pages_text.append(page_text)

                elapsed = time.time() - start_time
                done = page_num + 1
                if done > 1:
                    avg_per_page = elapsed / done
                    remaining = avg_per_page * (total_pages - done)
                    eta = _format_eta(remaining)
                else:
                    eta = "..."

                self.progress.emit(
                    t("norm.ocr_page_done", done=done, total=total_pages, eta=eta)
                )
                self.progress_pct.emit(done, total_pages, eta)

        ocr_text = _repair_ocr_cross_segment_breaks("\n\n".join(pages_text))
        return remove_repeated_headers(ocr_text, min_occurrences=3)

    def _normalize_with_progress(self, book):
        """Run normalization pipeline with per-paragraph progress."""
        from book_normalizer.normalization.pipeline import NormalizationPipeline

        pipeline = NormalizationPipeline.for_language(self._book_language)

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
        digest = self._source_digest()
        return Path("data") / "user_memory" / "llm_norm_cache" / digest

    def _llm_review_report_path(self) -> Path:
        """Return the review report path for rejected LLM normalization windows."""
        return Path("data") / "user_memory" / "llm_norm_reviews" / f"{self._source_digest()}.json"

    def _source_digest(self) -> str:
        """Return a stable digest for the selected source file path."""
        try:
            source = str(self._input_path.resolve()).casefold()
        except OSError:
            source = str(self._input_path).casefold()
        return sha1(source.encode("utf-8")).hexdigest()[:16]

    def _llm_normalize_with_progress(self, book):
        """Run optional LLM normalization over already rule-normalized text."""
        from book_normalizer.normalization.llm_normalizer import LlmNormalizer

        total_paragraphs = sum(len(ch.paragraphs) for ch in book.chapters)
        if total_paragraphs == 0:
            return book

        self.progress_pct.emit(0, total_paragraphs, "")
        start_time = time.time()
        report_interval = max(1, total_paragraphs // 50)

        review_report_path = self._llm_review_report_path()
        normalizer = LlmNormalizer(
            endpoint=self._llm_endpoint,
            model=self._llm_model,
            cache_dir=self._llm_cache_dir(),
            api_key=self._llm_api_key,
            language=self._book_language,
            review_report_path=review_report_path,
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
        metadata = getattr(book, "metadata", None)
        if metadata is not None:
            plan = model_plan_for_language(
                self._book_language,
                preferred_model=self._llm_model,
            )
            metadata.extra["llm_processing_enabled"] = True
            metadata.extra["llm_language"] = self._book_language
            metadata.extra["llm_model_candidates"] = list(plan.candidates)
            if rejected:
                metadata.extra["llm_normalization_review_report"] = str(review_report_path)
        self.progress.emit(
            t(
                "norm.llm_done",
                accepted=accepted,
                rejected=rejected,
            )
        )
        if rejected:
            self.progress.emit(
                t(
                    "norm.llm_review_required",
                    rejected=rejected,
                    path=review_report_path,
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
                self.progress.emit(t("norm.pdf_checking"))
                tesseract_available = _tesseract_available()
                effective_ocr = _effective_pdf_extraction_mode(
                    ocr,
                    tesseract_available=tesseract_available,
                )

                if effective_ocr == OcrMode.OFF:
                    if ocr != OcrMode.OFF:
                        self.progress.emit(
                            t(
                                "norm.ocr_unavailable_native",
                                hint=_native_ocr_install_hint(),
                            )
                        )

                    self.progress.emit(t("norm.pdf_native_extracting"))
                    compare = extract_pdf_with_ocr_mode(
                        self._input_path, effective_ocr,
                        dpi=self._ocr_dpi, psm=self._ocr_psm,
                        lang=tesseract_language(self._book_language),
                        language_code=self._book_language,
                    )
                    chosen, stats = select_pdf_text_for_mode(
                        compare,
                        ocr,
                        language_code=self._book_language,
                    )

                    _ensure_pdf_selection_is_usable(
                        ocr,
                        stats,
                        tesseract_available=tesseract_available,
                    )
                else:
                    self.progress.emit(
                        t(
                            "norm.ocr_prepare",
                            dpi=self._ocr_dpi,
                            psm=self._ocr_psm,
                        )
                    )
                    loader = PdfLoader()
                    self.progress.emit(t("norm.pdf_native_extracting"))
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
                    chosen, stats = select_pdf_text_for_mode(
                        compare,
                        ocr,
                        language_code=self._book_language,
                    )
                    _ensure_pdf_selection_is_usable(
                        ocr,
                        stats,
                        tesseract_available=tesseract_available,
                    )

                paragraphs = PdfLoader._split_paragraphs(chosen.text)
                chapter = Chapter(title="Full Text", index=0, paragraphs=paragraphs)
                metadata = Metadata(
                    source_path=str(self._input_path),
                    source_format="pdf",
                    language=self._book_language,
                )
                book = Book(metadata=metadata, chapters=[chapter])
            else:
                factory = LoaderFactory.default()
                book = factory.load(self._input_path)
                _apply_selected_book_language(book, self._book_language)

            pipeline, book = self._normalize_with_progress(book)

            self.progress.emit(t("norm.detecting_chapters"))
            detector = ChapterDetector()
            book = detector.detect_and_split(book)

            # Re-normalize after chapter split.
            pipeline, book = self._normalize_with_progress(book)
            self.preview_ready.emit(book)

            if self._llm_normalize:
                self.progress.emit(
                    t("norm.llm_start", model=self._llm_model)
                )
                book = self._llm_normalize_with_progress(book)

            if not self._skip_stress and is_russian_language(self._book_language):
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
