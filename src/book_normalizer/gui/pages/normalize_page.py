"""Normalization page — load book, run OCR and normalization."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from book_normalizer.gui.widgets.progress_widget import ProgressWidget
from book_normalizer.gui.workers.normalize_worker import NormalizeWorker


class NormalizePage(QWidget):
    """Page for book loading and text normalization."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._book = None
        self._worker: NormalizeWorker | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # File selection.
        file_row = QHBoxLayout()
        self._path_label = QLabel("No file selected")
        self._path_label.setStyleSheet("font-weight: bold;")
        file_row.addWidget(self._path_label, stretch=1)
        self._btn_browse = QPushButton("Browse...")
        self._btn_browse.clicked.connect(self._browse_file)
        file_row.addWidget(self._btn_browse)
        layout.addLayout(file_row)

        # Settings.
        settings = QFormLayout()
        self._ocr_mode = QComboBox()
        self._ocr_mode.addItems(["auto", "off", "force", "compare"])
        settings.addRow("OCR Mode:", self._ocr_mode)

        self._ocr_dpi = QSpinBox()
        self._ocr_dpi.setRange(72, 1200)
        self._ocr_dpi.setValue(400)
        settings.addRow("OCR DPI:", self._ocr_dpi)

        self._ocr_psm = QSpinBox()
        self._ocr_psm.setRange(0, 13)
        self._ocr_psm.setValue(6)
        settings.addRow("Tesseract PSM:", self._ocr_psm)
        layout.addLayout(settings)

        # Run button.
        self._btn_run = QPushButton("Run Normalization")
        self._btn_run.setMinimumHeight(40)
        self._btn_run.setStyleSheet("font-size: 14px; font-weight: bold;")
        self._btn_run.clicked.connect(self._run_normalization)
        self._btn_run.setEnabled(False)
        layout.addWidget(self._btn_run)

        # Progress.
        self._progress = ProgressWidget()
        layout.addWidget(self._progress)

        # Text preview.
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._raw_text = QPlainTextEdit()
        self._raw_text.setReadOnly(True)
        self._raw_text.setPlaceholderText("Raw text (before normalization)")
        splitter.addWidget(self._raw_text)

        self._norm_text = QPlainTextEdit()
        self._norm_text.setReadOnly(True)
        self._norm_text.setPlaceholderText("Normalized text (after)")
        splitter.addWidget(self._norm_text)
        layout.addWidget(splitter, stretch=1)

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Book File", "",
            "Books (*.pdf *.txt *.epub *.fb2 *.docx);;All Files (*)",
        )
        if path:
            self._path_label.setText(path)
            self._btn_run.setEnabled(True)

    def _run_normalization(self) -> None:
        path = Path(self._path_label.text())
        if not path.exists():
            return

        self._btn_run.setEnabled(False)
        self._progress.set_status("Starting...")
        self._raw_text.clear()
        self._norm_text.clear()

        self._worker = NormalizeWorker(
            input_path=path,
            ocr_mode=self._ocr_mode.currentText(),
            ocr_dpi=self._ocr_dpi.value(),
            ocr_psm=self._ocr_psm.value(),
        )
        self._worker.progress.connect(self._progress.set_status)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_finished(self, book: object) -> None:
        self._book = book
        self._btn_run.setEnabled(True)
        self._progress.set_status(f"Done: {len(book.chapters)} chapters")

        # Show text preview for the first chapter.
        if book.chapters:
            ch = book.chapters[0]
            raw_lines = [p.raw_text for p in ch.paragraphs[:30]]
            self._raw_text.setPlainText("\n\n".join(raw_lines))
            norm_lines = [p.normalized_text or p.raw_text for p in ch.paragraphs[:30]]
            self._norm_text.setPlainText("\n\n".join(norm_lines))

    def _on_error(self, msg: str) -> None:
        self._btn_run.setEnabled(True)
        self._progress.set_status(f"Error: {msg}")

    def get_book(self) -> object | None:
        """Return the processed book object."""
        return self._book
