"""Synthesis page — TTS generation with progress and ETA."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from book_normalizer.gui.i18n import t
from book_normalizer.gui.widgets.progress_widget import ProgressWidget
from book_normalizer.gui.workers.tts_worker import TTSSynthesisWorker


MODELS = [
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
]


class SynthesisPage(QWidget):
    """Page for running TTS synthesis with progress tracking."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._manifest_path: Path | None = None
        self._output_dir: Path | None = None
        self._worker: TTSSynthesisWorker | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Manifest selection ──
        file_row = QHBoxLayout()
        file_row.setSpacing(8)
        self._manifest_label = QLabel()
        self._manifest_label.setStyleSheet(
            "font-weight: 700; font-size: 13px; padding: 6px 12px;"
            "background: rgba(255,255,255,0.04); border-radius: 6px;"
        )
        file_row.addWidget(self._manifest_label, stretch=1)

        self._btn_load = QPushButton()
        self._btn_load.clicked.connect(self._browse_manifest)
        file_row.addWidget(self._btn_load)
        layout.addLayout(file_row)

        # ── Settings ──
        settings = QFormLayout()
        settings.setHorizontalSpacing(16)
        settings.setVerticalSpacing(8)

        self._model_combo = QComboBox()
        self._model_combo.addItems(MODELS)
        self._model_label = QLabel()
        settings.addRow(self._model_label, self._model_combo)

        self._model_hint = QLabel()
        self._model_hint.setWordWrap(True)
        self._model_hint.setStyleSheet(
            "color: rgba(255,255,255,0.4); font-size: 11px;"
            "background: transparent; border: none;"
            "padding: 0 0 4px 0;"
        )
        settings.addRow("", self._model_hint)

        self._batch_size = QSpinBox()
        self._batch_size.setRange(1, 8)
        self._batch_size.setValue(1)
        self._batch_label = QLabel()
        settings.addRow(self._batch_label, self._batch_size)

        self._batch_hint = QLabel()
        self._batch_hint.setWordWrap(True)
        self._batch_hint.setStyleSheet(
            "color: rgba(255,255,255,0.4); font-size: 11px;"
            "background: transparent; border: none;"
            "padding: 0 0 4px 0;"
        )
        settings.addRow("", self._batch_hint)

        self._chapter_spin = QSpinBox()
        self._chapter_spin.setRange(0, 999)
        self._chapter_spin.setValue(0)
        self._chapter_label = QLabel()
        settings.addRow(self._chapter_label, self._chapter_spin)

        layout.addLayout(settings)

        # ── Action buttons ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_start = QPushButton()
        self._btn_start.setObjectName("successBtn")
        self._btn_start.setMinimumHeight(44)
        self._btn_start.clicked.connect(self._start_synthesis)
        self._btn_start.setEnabled(False)
        btn_row.addWidget(self._btn_start)

        self._btn_stop = QPushButton()
        self._btn_stop.setObjectName("dangerBtn")
        self._btn_stop.setMinimumHeight(44)
        self._btn_stop.clicked.connect(self._stop_synthesis)
        self._btn_stop.setEnabled(False)
        btn_row.addWidget(self._btn_stop)

        layout.addLayout(btn_row)

        # ── Progress ──
        self._progress = ProgressWidget()
        layout.addWidget(self._progress)

        # ── Status ──
        self._status = QLabel()
        self._status.setWordWrap(True)
        self._status.setStyleSheet(
            "color: rgba(255,255,255,0.6); font-size: 12px; padding: 4px 0;"
        )
        layout.addWidget(self._status)
        layout.addStretch()

        self.retranslate()

    def retranslate(self) -> None:
        """Update translatable strings."""
        if not self._manifest_path:
            self._manifest_label.setText(t("synth.no_manifest"))
        self._btn_load.setText(t("synth.load_manifest"))
        self._model_label.setText(t("synth.model"))
        self._model_hint.setText(t("synth.model_hint"))
        self._model_combo.setToolTip(t("synth.model_hint"))
        self._batch_label.setText(t("synth.batch_size"))
        self._batch_hint.setText(t("synth.batch_hint"))
        self._batch_size.setToolTip(t("synth.batch_hint"))
        self._chapter_label.setText(t("synth.chapter"))
        self._chapter_spin.setSpecialValueText(t("synth.all_chapters"))
        self._btn_start.setText(t("synth.start"))
        self._btn_stop.setText(t("synth.stop"))
        self._status.setText(t("synth.waiting"))

    def set_manifest(self, manifest_path: Path, output_dir: Path) -> None:
        """Set the manifest file and output directory."""
        self._manifest_path = manifest_path
        self._output_dir = output_dir
        self._manifest_label.setText(str(manifest_path))
        self._btn_start.setEnabled(True)

    def _browse_manifest(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("synth.load_manifest"), "", "JSON (*.json)",
        )
        if path:
            p = Path(path)
            self._manifest_path = p
            self._output_dir = p.parent
            self._manifest_label.setText(str(p))
            self._btn_start.setEnabled(True)

    def _start_synthesis(self) -> None:
        if not self._manifest_path or not self._output_dir:
            return

        chapter = self._chapter_spin.value() if self._chapter_spin.value() > 0 else None

        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._progress.reset()

        self._worker = TTSSynthesisWorker(
            manifest_path=self._manifest_path,
            output_dir=self._output_dir,
            model=self._model_combo.currentText(),
            chapter=chapter,
            batch_size=self._batch_size.value(),
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _stop_synthesis(self) -> None:
        if self._worker:
            self._worker.cancel()
        self._btn_stop.setEnabled(False)

    def _on_progress(self, current: int, total: int, eta: str) -> None:
        self._progress.set_progress(current, total, eta)

    def _on_finished(self, manifest: str) -> None:
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._progress.set_status(t("synth.complete"))
        self._status.setText(f"Output: {manifest}")

    def _on_error(self, msg: str) -> None:
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._progress.set_status(f"Error: {msg}")
