"""Normalization page — load book, run OCR and normalization."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from book_normalizer.gui.i18n import t
from book_normalizer.gui.widgets.help_button import label_with_help, set_help_text
from book_normalizer.gui.widgets.progress_widget import ProgressWidget
from book_normalizer.gui.workers.normalize_worker import NormalizeWorker
from book_normalizer.languages import DEFAULT_BOOK_LANGUAGE, SUPPORTED_LANGUAGE_CODES
from book_normalizer.llm.model_router import PRIMARY_QWEN3_MODEL
from book_normalizer.runtime_paths import configured_ollama_endpoint

_PDF_EXTENSIONS = {".pdf"}
_PSM_VALUES = (3, 4, 6, 11, 13)


def _book_preview_lines(book: object, limit: int | None = None) -> tuple[list[str], list[str]]:
    """Return raw/normalized preview lines across chapters, optionally capped."""
    raw_lines: list[str] = []
    norm_lines: list[str] = []
    paragraph_count = 0

    for chapter in getattr(book, "chapters", []):
        if limit is not None and paragraph_count >= limit:
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
            if limit is not None and paragraph_count >= limit:
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
        self._compact_mode = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── File selection card ──
        file_row = QHBoxLayout()
        file_row.setSpacing(8)
        self._path_label = QLabel()
        self._path_label.setWordWrap(True)
        self._path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse,
        )
        self._path_label.setStyleSheet(
            "font-weight: 700; font-size: 13px; padding: 6px 12px;"
            "background: rgba(255,255,255,0.70); border: 1px solid rgba(91,115,142,0.16);"
            "border-radius: 8px;"
        )
        file_row.addWidget(self._path_label, stretch=1)

        self._btn_browse = QPushButton()
        self._btn_browse.clicked.connect(self._browse_file)
        file_row.addWidget(self._btn_browse)
        layout.addLayout(file_row)

        # ── OCR settings (PDF only) ──
        self._ocr_widgets: list[QWidget] = []

        settings = QGridLayout()
        settings.setHorizontalSpacing(14)
        settings.setVerticalSpacing(8)
        for column in range(3):
            settings.setColumnStretch(column, 1)

        self._book_language = QComboBox()
        self._book_language_label = QLabel()
        self._book_language_label_wrap = self._label_with_help(
            self._book_language_label, "norm.book_language_tip"
        )
        self._add_setting(settings, 0, 0, self._book_language_label_wrap, self._book_language)

        self._ocr_mode = QComboBox()
        self._ocr_mode.addItems(["auto", "off", "force", "compare"])
        self._ocr_mode_label = QLabel()
        self._ocr_mode_label_wrap = self._label_with_help(
            self._ocr_mode_label, "norm.ocr_mode_tip"
        )
        self._add_setting(settings, 0, 1, self._ocr_mode_label_wrap, self._ocr_mode)
        self._ocr_widgets.extend([self._ocr_mode_label_wrap, self._ocr_mode])

        self._ocr_dpi = QSpinBox()
        self._ocr_dpi.setRange(72, 1200)
        self._ocr_dpi.setValue(400)
        self._ocr_dpi.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ocr_dpi.lineEdit().setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ocr_dpi.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._ocr_dpi.setFixedWidth(128)
        self._ocr_dpi.setFixedHeight(38)
        self._ocr_dpi_label = QLabel()
        self._ocr_dpi_label_wrap = self._label_with_help(
            self._ocr_dpi_label, "norm.ocr_dpi_tip"
        )
        self._add_setting(settings, 0, 2, self._ocr_dpi_label_wrap, self._ocr_dpi)
        self._ocr_widgets.extend([self._ocr_dpi_label_wrap, self._ocr_dpi])

        self._ocr_psm = QComboBox()
        self._populate_psm_combo()
        self._ocr_psm_label = QLabel()
        self._ocr_psm_label_wrap = self._label_with_help(
            self._ocr_psm_label, "norm.ocr_psm_tip"
        )
        self._add_setting(settings, 1, 1, self._ocr_psm_label_wrap, self._ocr_psm)
        self._ocr_widgets.extend([self._ocr_psm_label_wrap, self._ocr_psm])

        self._ocr_not_applicable_label = QLabel()
        self._ocr_not_applicable_label.setStyleSheet(
            "color: rgba(51,65,85,0.64); font-style: italic; font-size: 12px;"
            "padding: 4px 0;"
        )
        settings.addWidget(self._ocr_not_applicable_label, 4, 0, 1, 3)

        self._llm_normalize = QCheckBox()
        self._llm_normalize.stateChanged.connect(self._update_llm_visibility)
        self._llm_normalize_label = QLabel()
        self._llm_normalize_label_wrap = self._label_with_help(
            self._llm_normalize_label, "norm.llm_tip"
        )
        self._add_setting(settings, 1, 0, self._llm_normalize_label_wrap, self._llm_normalize)

        self._llm_endpoint = QLineEdit(configured_ollama_endpoint())
        self._llm_endpoint_label = QLabel()
        self._llm_endpoint_label_wrap = self._label_with_help(
            self._llm_endpoint_label, "norm.llm_tip"
        )
        self._add_setting(settings, 2, 0, self._llm_endpoint_label_wrap, self._llm_endpoint)

        self._llm_model = QLineEdit(PRIMARY_QWEN3_MODEL)
        self._llm_model_label = QLabel()
        self._llm_model_label_wrap = self._label_with_help(
            self._llm_model_label, "norm.llm_tip"
        )
        self._add_setting(settings, 2, 1, self._llm_model_label_wrap, self._llm_model)

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
        text_row = QHBoxLayout()
        text_row.setSpacing(14)

        self._raw_label = QLabel()
        self._raw_label.setStyleSheet(
            "font-weight: 800; font-size: 11px; color: rgba(51,65,85,0.64);"
            "text-transform: uppercase;"
        )
        raw_container = QWidget()
        raw_layout = QVBoxLayout(raw_container)
        raw_layout.setContentsMargins(0, 0, 0, 0)
        raw_layout.setSpacing(4)
        raw_layout.addWidget(self._raw_label)
        self._raw_text = QPlainTextEdit()
        self._raw_text.setReadOnly(True)
        self._raw_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._raw_text.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        raw_layout.addWidget(self._raw_text)
        text_row.addWidget(raw_container, stretch=1)

        norm_container = QWidget()
        norm_layout = QVBoxLayout(norm_container)
        norm_layout.setContentsMargins(0, 0, 0, 0)
        norm_layout.setSpacing(4)
        self._norm_label = QLabel()
        self._norm_label.setStyleSheet(
            "font-weight: 800; font-size: 11px; color: rgba(51,65,85,0.64);"
            "text-transform: uppercase;"
        )
        norm_header = QHBoxLayout()
        norm_header.setContentsMargins(0, 0, 0, 0)
        norm_header.setSpacing(8)
        norm_header.addWidget(self._norm_label)
        norm_header.addStretch()
        self._btn_apply_norm_edits = QPushButton()
        self._btn_apply_norm_edits.clicked.connect(self._apply_normalized_edits)
        self._btn_apply_norm_edits.setEnabled(False)
        norm_header.addWidget(self._btn_apply_norm_edits)
        norm_layout.addLayout(norm_header)
        self._norm_text = QPlainTextEdit()
        self._norm_text.setReadOnly(False)
        self._norm_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._norm_text.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        norm_layout.addWidget(self._norm_text)
        text_row.addWidget(norm_container, stretch=1)

        layout.addLayout(text_row, stretch=1)

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
            self._llm_endpoint_label_wrap,
            self._llm_endpoint,
            self._llm_model_label_wrap,
            self._llm_model,
        ):
            widget.setVisible(enabled)
            widget.setEnabled(enabled)

    def resizeEvent(self, event) -> None:  # noqa: N802
        """Keep action labels readable when the window is narrow or zoomed."""
        super().resizeEvent(event)
        self._sync_compact_mode()

    def _sync_compact_mode(self) -> None:
        compact = self.width() < 900
        if self._compact_mode == compact:
            return
        self._compact_mode = compact
        self._apply_action_labels()

    @staticmethod
    def _add_setting(
        grid: QGridLayout,
        row: int,
        column: int,
        label: QWidget,
        field: QWidget,
    ) -> None:
        if field.maximumWidth() == 16777215 and field.sizePolicy().horizontalPolicy() != QSizePolicy.Policy.Fixed:
            field.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )
        grid.addWidget(label, row * 2, column)
        grid.addWidget(field, row * 2 + 1, column)

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
        self._populate_psm_combo()
        self._ocr_psm.setToolTip(t("norm.ocr_psm_tip"))
        self._ocr_psm_label.setToolTip(t("norm.ocr_psm_tip"))
        self._ocr_not_applicable_label.setText(t("norm.ocr_not_applicable"))
        self._book_language_label.setText(t("norm.book_language"))
        self._book_language.setToolTip(t("norm.book_language_tip"))
        self._book_language_label.setToolTip(t("norm.book_language_tip"))
        self._populate_book_language_combo()
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
        self._apply_action_labels()
        self._btn_apply_norm_edits.setToolTip(t("norm.apply_manual_edits_tip"))
        self._raw_text.setPlaceholderText(t("norm.raw_placeholder"))
        self._norm_text.setPlaceholderText(t("norm.norm_placeholder"))
        self._raw_label.setText(t("norm.raw_placeholder"))
        self._norm_label.setText(t("norm.norm_placeholder"))

    def _apply_action_labels(self) -> None:
        self._btn_apply_norm_edits.setText(
            t("norm.apply_manual_edits_compact")
            if self._compact_mode
            else t("norm.apply_manual_edits")
        )

    def _populate_book_language_combo(self) -> None:
        """Populate supported book languages while preserving selection."""
        current = self._book_language.currentData() or DEFAULT_BOOK_LANGUAGE
        self._book_language.blockSignals(True)
        self._book_language.clear()
        for code in SUPPORTED_LANGUAGE_CODES:
            self._book_language.addItem(t(f"book_language.{code}"), code)
        idx = self._book_language.findData(current)
        if idx < 0:
            idx = self._book_language.findData(DEFAULT_BOOK_LANGUAGE)
        self._book_language.setCurrentIndex(idx if idx >= 0 else 0)
        self._book_language.blockSignals(False)

    def _populate_psm_combo(self) -> None:
        """Populate human-readable Tesseract PSM options."""
        current = self._ocr_psm.currentData() if hasattr(self, "_ocr_psm") else 6
        self._ocr_psm.blockSignals(True)
        self._ocr_psm.clear()
        for value in _PSM_VALUES:
            self._ocr_psm.addItem(t(f"norm.ocr_psm_{value}"), value)
        idx = self._ocr_psm.findData(current if current is not None else 6)
        if idx < 0:
            idx = self._ocr_psm.findData(6)
        self._ocr_psm.setCurrentIndex(idx if idx >= 0 else 0)
        self._ocr_psm.blockSignals(False)

    def _label_with_help(self, label: QLabel, help_key: str) -> QWidget:
        """Create a form label with a reusable help button."""
        label.setWordWrap(True)
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
        self._btn_apply_norm_edits.setEnabled(False)

        self._worker = NormalizeWorker(
            input_path=path,
            ocr_mode=self._ocr_mode.currentText(),
            ocr_dpi=self._ocr_dpi.value(),
            ocr_psm=int(self._ocr_psm.currentData() or 6),
            llm_normalize=self._llm_normalize.isChecked(),
            llm_endpoint=self._llm_endpoint.text().strip() or configured_ollama_endpoint(),
            llm_model=self._llm_model.text().strip() or PRIMARY_QWEN3_MODEL,
            book_language=str(self._book_language.currentData() or DEFAULT_BOOK_LANGUAGE),
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
            raw_lines, norm_lines = _book_preview_lines(book)
            self._raw_text.setPlainText("\n\n".join(raw_lines))
            self._norm_text.setPlainText("\n\n".join(norm_lines))
            self._btn_apply_norm_edits.setEnabled(True)

    def _apply_normalized_edits(self) -> None:
        """Apply the editable normalized preview back to the current Book."""
        if self._book is None:
            return

        edited_blocks = [
            block.strip()
            for block in self._norm_text.toPlainText().split("\n\n")
            if block.strip() and not block.strip().startswith("===")
        ]
        paragraphs = [
            para
            for chapter in getattr(self._book, "chapters", [])
            for para in getattr(chapter, "paragraphs", [])
            if (getattr(para, "raw_text", "") or getattr(para, "normalized_text", "")).strip()
        ]
        if len(edited_blocks) != len(paragraphs):
            self._progress.set_status(
                t(
                    "norm.manual_edit_mismatch",
                    edited=len(edited_blocks),
                    paragraphs=len(paragraphs),
                )
            )
            return

        for para, text in zip(paragraphs, edited_blocks, strict=True):
            para.normalized_text = text
        self._progress.set_status(t("norm.manual_edit_applied", n=len(paragraphs)))

    def _on_error(self, msg: str) -> None:
        self._btn_run.setEnabled(True)
        self._progress.set_status(f"Error: {msg}")

    def get_book(self) -> object | None:
        """Return the processed book object."""
        return self._book
