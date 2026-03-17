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

from book_normalizer.gui.i18n import t
from book_normalizer.gui.widgets.progress_widget import ProgressWidget
from book_normalizer.gui.workers.normalize_worker import NormalizeWorker

_PDF_EXTENSIONS = {".pdf"}


class NormalizePage(QWidget):
    """Page for book loading and text normalization."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._book = None
        self._worker: NormalizeWorker | None = None
        self._selected_path: str = ""
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── File selection card ──
        file_row = QHBoxLayout()
        file_row.setSpacing(8)
        self._path_label = QLabel()
        self._path_label.setStyleSheet(
            "font-weight: 700; font-size: 13px; padding: 6px 12px;"
            "background: rgba(255,255,255,0.04); border-radius: 6px;"
        )
        file_row.addWidget(self._path_label, stretch=1)

        self._btn_browse = QPushButton()
        self._btn_browse.clicked.connect(self._browse_file)
        file_row.addWidget(self._btn_browse)
        layout.addLayout(file_row)

        # ── OCR settings (PDF only) ──
        self._ocr_widgets: list[QWidget] = []

        settings = QFormLayout()
        settings.setHorizontalSpacing(16)
        settings.setVerticalSpacing(6)

        self._ocr_mode = QComboBox()
        self._ocr_mode.addItems(["auto", "off", "force", "compare"])
        self._ocr_mode_label = QLabel()
        settings.addRow(self._ocr_mode_label, self._ocr_mode)
        self._ocr_widgets.extend([self._ocr_mode_label, self._ocr_mode])

        self._ocr_mode_hint = QLabel()
        self._ocr_mode_hint.setStyleSheet("color: rgba(255,255,255,0.35); font-size: 11px;")
        settings.addRow("", self._ocr_mode_hint)
        self._ocr_widgets.append(self._ocr_mode_hint)

        self._ocr_dpi = QSpinBox()
        self._ocr_dpi.setRange(72, 1200)
        self._ocr_dpi.setValue(400)
        self._ocr_dpi_label = QLabel()
        settings.addRow(self._ocr_dpi_label, self._ocr_dpi)
        self._ocr_widgets.extend([self._ocr_dpi_label, self._ocr_dpi])

        self._ocr_dpi_hint = QLabel()
        self._ocr_dpi_hint.setStyleSheet("color: rgba(255,255,255,0.35); font-size: 11px;")
        settings.addRow("", self._ocr_dpi_hint)
        self._ocr_widgets.append(self._ocr_dpi_hint)

        self._ocr_psm = QSpinBox()
        self._ocr_psm.setRange(0, 13)
        self._ocr_psm.setValue(6)
        self._ocr_psm_label = QLabel()
        settings.addRow(self._ocr_psm_label, self._ocr_psm)
        self._ocr_widgets.extend([self._ocr_psm_label, self._ocr_psm])

        self._ocr_psm_hint = QLabel()
        self._ocr_psm_hint.setStyleSheet("color: rgba(255,255,255,0.35); font-size: 11px;")
        settings.addRow("", self._ocr_psm_hint)
        self._ocr_widgets.append(self._ocr_psm_hint)

        self._ocr_not_applicable_label = QLabel()
        self._ocr_not_applicable_label.setStyleSheet(
            "color: rgba(255,255,255,0.4); font-style: italic; font-size: 12px;"
            "padding: 4px 0;"
        )
        settings.addRow("", self._ocr_not_applicable_label)

        layout.addLayout(settings)

        # ── Run button ──
        self._btn_run = QPushButton()
        self._btn_run.setObjectName("primaryBtn")
        self._btn_run.setMinimumHeight(44)
        self._btn_run.clicked.connect(self._run_normalization)
        self._btn_run.setEnabled(False)
        layout.addWidget(self._btn_run)

        # ── Progress ──
        self._progress = ProgressWidget()
        layout.addWidget(self._progress)

        # ── Text comparison panels ──
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._raw_label = QLabel()
        self._raw_label.setStyleSheet(
            "font-weight: 700; font-size: 11px; color: rgba(255,255,255,0.5);"
            "text-transform: uppercase; letter-spacing: 1px;"
        )
        raw_container = QWidget()
        raw_layout = QVBoxLayout(raw_container)
        raw_layout.setContentsMargins(0, 0, 0, 0)
        raw_layout.setSpacing(4)
        raw_layout.addWidget(self._raw_label)
        self._raw_text = QPlainTextEdit()
        self._raw_text.setReadOnly(True)
        raw_layout.addWidget(self._raw_text)
        splitter.addWidget(raw_container)

        norm_container = QWidget()
        norm_layout = QVBoxLayout(norm_container)
        norm_layout.setContentsMargins(0, 0, 0, 0)
        norm_layout.setSpacing(4)
        self._norm_label = QLabel()
        self._norm_label.setStyleSheet(
            "font-weight: 700; font-size: 11px; color: rgba(255,255,255,0.5);"
            "text-transform: uppercase; letter-spacing: 1px;"
        )
        norm_layout.addWidget(self._norm_label)
        self._norm_text = QPlainTextEdit()
        self._norm_text.setReadOnly(True)
        norm_layout.addWidget(self._norm_text)
        splitter.addWidget(norm_container)

        layout.addWidget(splitter, stretch=1)

        self._update_ocr_visibility()
        self.retranslate()

    def _update_ocr_visibility(self) -> None:
        """Show/hide OCR settings based on selected file type."""
        is_pdf = self._selected_path.lower().endswith(".pdf") if self._selected_path else False
        for w in self._ocr_widgets:
            w.setVisible(is_pdf)
            w.setEnabled(is_pdf)
        self._ocr_not_applicable_label.setVisible(
            bool(self._selected_path) and not is_pdf
        )

    def retranslate(self) -> None:
        """Update all translatable strings."""
        if not self._selected_path:
            self._path_label.setText(t("norm.no_file"))
        self._btn_browse.setText(t("norm.browse"))
        self._ocr_mode_label.setText(t("norm.ocr_mode"))
        self._ocr_mode.setToolTip(t("norm.ocr_mode_tip"))
        self._ocr_mode_label.setToolTip(t("norm.ocr_mode_tip"))
        self._ocr_mode_hint.setText(t("norm.ocr_mode_hint"))
        self._ocr_dpi_label.setText(t("norm.ocr_dpi"))
        self._ocr_dpi.setToolTip(t("norm.ocr_dpi_tip"))
        self._ocr_dpi_label.setToolTip(t("norm.ocr_dpi_tip"))
        self._ocr_dpi_hint.setText(t("norm.ocr_dpi_hint"))
        self._ocr_psm_label.setText(t("norm.ocr_psm"))
        self._ocr_psm.setToolTip(t("norm.ocr_psm_tip"))
        self._ocr_psm_label.setToolTip(t("norm.ocr_psm_tip"))
        self._ocr_psm_hint.setText(t("norm.ocr_psm_hint"))
        self._ocr_not_applicable_label.setText(t("norm.ocr_not_applicable"))
        self._btn_run.setText(t("norm.run"))
        self._raw_text.setPlaceholderText(t("norm.raw_placeholder"))
        self._norm_text.setPlaceholderText(t("norm.norm_placeholder"))
        self._raw_label.setText(t("norm.raw_placeholder"))
        self._norm_label.setText(t("norm.norm_placeholder"))

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("norm.select_file"), "",
            "Books (*.pdf *.txt *.epub *.fb2 *.docx);;All Files (*)",
        )
        if path:
            self._selected_path = path
            self._path_label.setText(path)
            self._btn_run.setEnabled(True)
            self._update_ocr_visibility()

    def _run_normalization(self) -> None:
        path = Path(self._path_label.text())
        if not path.exists():
            return

        self._btn_run.setEnabled(False)
        self._progress.set_status(t("norm.starting"))
        self._progress.reset()
        self._raw_text.clear()
        self._norm_text.clear()

        self._worker = NormalizeWorker(
            input_path=path,
            ocr_mode=self._ocr_mode.currentText(),
            ocr_dpi=self._ocr_dpi.value(),
            ocr_psm=self._ocr_psm.value(),
        )
        self._worker.progress.connect(self._progress.set_status)
        self._worker.progress_pct.connect(self._progress.set_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_finished(self, book: object) -> None:
        self._book = book
        self._btn_run.setEnabled(True)

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
