"""Background worker for text normalization pipeline."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal


class NormalizeWorker(QThread):
    """Run book loading + normalization + chapter detection in a background thread."""

    progress = pyqtSignal(str)
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

    def run(self) -> None:
        try:
            from book_normalizer.chaptering.detector import ChapterDetector
            from book_normalizer.config import OcrMode
            from book_normalizer.loaders.factory import LoaderFactory
            from book_normalizer.loaders.pdf_loader import (
                PdfLoader,
                extract_pdf_with_ocr_mode,
                select_pdf_text_for_mode,
            )
            from book_normalizer.models.book import Book, Chapter, Metadata, Paragraph
            from book_normalizer.normalization.pipeline import NormalizationPipeline

            self.progress.emit("Loading book...")
            is_pdf = self._input_path.suffix.lower() == ".pdf"

            if is_pdf:
                ocr = OcrMode(self._ocr_mode)
                self.progress.emit(f"Running OCR (DPI={self._ocr_dpi}, PSM={self._ocr_psm})...")
                compare = extract_pdf_with_ocr_mode(
                    self._input_path, ocr,
                    dpi=self._ocr_dpi, psm=self._ocr_psm,
                )
                chosen, _ = select_pdf_text_for_mode(compare, ocr)
                paragraphs = PdfLoader._split_paragraphs(chosen.text)
                chapter = Chapter(title="Full Text", index=0, paragraphs=paragraphs)
                metadata = Metadata(source_path=str(self._input_path), source_format="pdf")
                book = Book(metadata=metadata, chapters=[chapter])
            else:
                factory = LoaderFactory.default()
                book = factory.load(self._input_path)

            self.progress.emit("Normalizing text...")
            pipeline = NormalizationPipeline()
            book = pipeline.normalize_book(book)

            self.progress.emit("Detecting chapters...")
            detector = ChapterDetector()
            book = detector.detect_and_split(book)
            pipeline.normalize_book(book)

            if not self._skip_stress:
                self.progress.emit("Annotating stress...")
                from book_normalizer.config import AppConfig
                from book_normalizer.memory.stress_store import StressStore
                from book_normalizer.stress.annotator import StressAnnotator
                from book_normalizer.stress.dictionary import StressDictionary

                config = AppConfig()
                stress_store = StressStore(config.stress_dict_path)
                stress_dict = StressDictionary(store=stress_store)
                annotator = StressAnnotator(stress_dict)
                annotator.annotate_book(book)

            self.progress.emit(f"Done: {len(book.chapters)} chapters")
            self.finished.emit(book)

        except Exception as exc:
            self.error.emit(str(exc))
