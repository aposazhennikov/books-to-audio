"""Normalization page — load book, run OCR and normalization."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from book_normalizer.gui.i18n import t
from book_normalizer.gui.widgets.help_button import label_with_help, set_help_text
from book_normalizer.gui.widgets.progress_widget import ProgressWidget
from book_normalizer.gui.workers.normalize_worker import NormalizeWorker

_PDF_EXTENSIONS = {".pdf"}


def _book_preview_lines(book: object, limit: int = 30) -> tuple[list[str], list[str]]:
    """Return raw/normalized preview lines across chapters, not only chapter zero."""
    raw_lines: list[str] = []
    norm_lines: list[str] = []
    paragraph_count = 0

    for chapter in getattr(book, "chapters", []):
        if paragraph_count >= limit:
            break

        title = getattr(chapter, "title", "").strip()
        if title:
            header = f"=== {title} ==="
            raw_lines.append(header)
            norm_lines.append(header)

        for para in getattr(chapter, "paragraphs", []):
            raw = getattr(para, "raw_text", "")
            norm = getattr(para, "normalized_text", "") or raw
            if not raw.strip() and not norm.strip():
                continue

            raw_lines.append(raw)
            norm_lines.append(norm)
            paragraph_count += 1
            if paragraph_count >= limit:
                break

    return raw_lines, norm_lines


class NormalizePage(QWidget):
    """Page for book loading and text normalization."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._book = None
        self._worker: NormalizeWorker | None = None
        self._selected_path: str = ""
        self._help_buttons: dict[str, object] = {}
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
            "background: rgba(15,23,42,0.62); border: 1px solid rgba(148,163,184,0.12);"
            "border-radius: 8px;"
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
        settings.addRow(
            self._label_with_help(self._ocr_mode_label, "norm.ocr_mode_tip"),
            self._ocr_mode,
        )
        self._ocr_widgets.extend([self._ocr_mode_label, self._ocr_mode])

        self._ocr_dpi = QSpinBox()
        self._ocr_dpi.setRange(72, 1200)
        self._ocr_dpi.setValue(400)
        self._ocr_dpi_label = QLabel()
        settings.addRow(
            self._label_with_help(self._ocr_dpi_label, "norm.ocr_dpi_tip"),
            self._ocr_dpi,
        )
        self._ocr_widgets.extend([self._ocr_dpi_label, self._ocr_dpi])

        self._ocr_psm = QSpinBox()
        self._ocr_psm.setRange(0, 13)
        self._ocr_psm.setValue(6)
        self._ocr_psm_label = QLabel()
        settings.addRow(
            self._label_with_help(self._ocr_psm_label, "norm.ocr_psm_tip"),
            self._ocr_psm,
        )
        self._ocr_widgets.extend([self._ocr_psm_label, self._ocr_psm])

        self._ocr_not_applicable_label = QLabel()
        self._ocr_not_applicable_label.setStyleSheet(
            "color: rgba(226,232,240,0.52); font-style: italic; font-size: 12px;"
            "padding: 4px 0;"
        )
        settings.addRow("", self._ocr_not_applicable_label)

        self._llm_normalize = QCheckBox()
        self._llm_normalize.stateChanged.connect(self._update_llm_visibility)
        self._llm_normalize_label = QLabel()
        settings.addRow(
            self._label_with_help(self._llm_normalize_label, "norm.llm_tip"),
            self._llm_normalize,
        )

        self._llm_endpoint = QLineEdit("http://localhost:11434/v1")
        self._llm_endpoint_label = QLabel()
        settings.addRow(
            self._label_with_help(self._llm_endpoint_label, "norm.llm_tip"),
            self._llm_endpoint,
        )

        self._llm_model = QLineEdit("qwen3:8b")
        self._llm_model_label = QLabel()
        settings.addRow(
            self._label_with_help(self._llm_model_label, "norm.llm_tip"),
            self._llm_model,
        )

        layout.addLayout(settings)

        # ── Run button ──
        self._btn_run = QPushButton()
        self._btn_run.setObjectName("primaryBtn")
        self._btn_run.setMinimumHeight(38)
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
            "font-weight: 800; font-size: 11px; color: rgba(226,232,240,0.62);"
            "text-transform: uppercase;"
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
            "font-weight: 800; font-size: 11px; color: rgba(226,232,240,0.62);"
            "text-transform: uppercase;"
        )
        norm_layout.addWidget(self._norm_label)
        self._norm_text = QPlainTextEdit()
        self._norm_text.setReadOnly(True)
        norm_layout.addWidget(self._norm_text)
        splitter.addWidget(norm_container)

        layout.addWidget(splitter, stretch=1)

        self._update_ocr_visibility()
        self._update_llm_visibility()
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

    def _update_llm_visibility(self) -> None:
        """Show local LLM settings only when LLM normalization is enabled."""
        enabled = self._llm_normalize.isChecked()
        for widget in (
            self._llm_endpoint_label,
            self._llm_endpoint,
            self._llm_model_label,
            self._llm_model,
        ):
            widget.setVisible(enabled)
            widget.setEnabled(enabled)

    def retranslate(self) -> None:
        """Update all translatable strings."""
        if not self._selected_path:
            self._path_label.setText(t("norm.no_file"))
        self._btn_browse.setText(t("norm.browse"))
        self._ocr_mode_label.setText(t("norm.ocr_mode"))
        self._ocr_mode.setToolTip(t("norm.ocr_mode_tip"))
        self._ocr_mode_label.setToolTip(t("norm.ocr_mode_tip"))
        self._ocr_dpi_label.setText(t("norm.ocr_dpi"))
        self._ocr_dpi.setToolTip(t("norm.ocr_dpi_tip"))
        self._ocr_dpi_label.setToolTip(t("norm.ocr_dpi_tip"))
        self._ocr_psm_label.setText(t("norm.ocr_psm"))
        self._ocr_psm.setToolTip(t("norm.ocr_psm_tip"))
        self._ocr_psm_label.setToolTip(t("norm.ocr_psm_tip"))
        self._ocr_not_applicable_label.setText(t("norm.ocr_not_applicable"))
        self._llm_normalize_label.setText(t("norm.llm_normalize"))
        self._llm_normalize.setText(t("norm.llm_normalize_check"))
        self._llm_normalize.setToolTip(t("norm.llm_tip"))
        self._llm_normalize_label.setToolTip(t("norm.llm_tip"))
        self._llm_endpoint_label.setText(t("norm.llm_endpoint"))
        self._llm_endpoint.setToolTip(t("norm.llm_tip"))
        self._llm_endpoint_label.setToolTip(t("norm.llm_tip"))
        self._llm_model_label.setText(t("norm.llm_model"))
        self._llm_model.setToolTip(t("norm.llm_tip"))
        self._llm_model_label.setToolTip(t("norm.llm_tip"))
        self._update_help_buttons()
        self._btn_run.setText(t("norm.run"))
        self._raw_text.setPlaceholderText(t("norm.raw_placeholder"))
        self._norm_text.setPlaceholderText(t("norm.norm_placeholder"))
        self._raw_label.setText(t("norm.raw_placeholder"))
        self._norm_label.setText(t("norm.norm_placeholder"))

    def _label_with_help(self, label: QLabel, help_key: str) -> QWidget:
        """Create a form label with a reusable help button."""
        wrap, button = label_with_help(label, t(help_key))
        self._help_buttons[help_key] = button
        return wrap

    def _update_help_buttons(self) -> None:
        """Refresh tooltip text after language changes."""
        for help_key, button in self._help_buttons.items():
            set_help_text(button, t(help_key))

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
            llm_normalize=self._llm_normalize.isChecked(),
            llm_endpoint=self._llm_endpoint.text().strip() or "http://localhost:11434/v1",
            llm_model=self._llm_model.text().strip() or "qwen3:8b",
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
            raw_lines, norm_lines = _book_preview_lines(book, limit=30)
            self._raw_text.setPlainText("\n\n".join(raw_lines))
            self._norm_text.setPlainText("\n\n".join(norm_lines))

    def _on_error(self, msg: str) -> None:
        self._btn_run.setEnabled(True)
        self._progress.set_status(f"Error: {msg}")

    def get_book(self) -> object | None:
        """Return the processed book object."""
        return self._book
