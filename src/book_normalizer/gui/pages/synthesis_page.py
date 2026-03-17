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

        # Manifest selection.
        file_row = QHBoxLayout()
        self._manifest_label = QLabel("No manifest loaded")
        self._manifest_label.setStyleSheet("font-weight: bold;")
        file_row.addWidget(self._manifest_label, stretch=1)
        btn = QPushButton("Load Manifest")
        btn.clicked.connect(self._browse_manifest)
        file_row.addWidget(btn)
        layout.addLayout(file_row)

        # Settings.
        settings = QFormLayout()

        self._model_combo = QComboBox()
        self._model_combo.addItems(MODELS)
        settings.addRow("Model:", self._model_combo)

        self._batch_size = QSpinBox()
        self._batch_size.setRange(1, 8)
        self._batch_size.setValue(1)
        settings.addRow("Batch Size:", self._batch_size)

        self._chapter_spin = QSpinBox()
        self._chapter_spin.setRange(0, 999)
        self._chapter_spin.setValue(0)
        self._chapter_spin.setSpecialValueText("All chapters")
        settings.addRow("Chapter (0=all):", self._chapter_spin)

        layout.addLayout(settings)

        # Action buttons.
        btn_row = QHBoxLayout()
        self._btn_start = QPushButton("Start Synthesis")
        self._btn_start.setMinimumHeight(40)
        self._btn_start.setStyleSheet("font-size: 14px; font-weight: bold; background-color: #2ecc71; color: white;")
        self._btn_start.clicked.connect(self._start_synthesis)
        self._btn_start.setEnabled(False)
        btn_row.addWidget(self._btn_start)

        self._btn_stop = QPushButton("Stop")
        self._btn_stop.setMinimumHeight(40)
        self._btn_stop.setStyleSheet("font-size: 14px; background-color: #e74c3c; color: white;")
        self._btn_stop.clicked.connect(self._stop_synthesis)
        self._btn_stop.setEnabled(False)
        btn_row.addWidget(self._btn_stop)

        layout.addLayout(btn_row)

        # Progress.
        self._progress = ProgressWidget()
        layout.addWidget(self._progress)

        # Status log.
        self._status = QLabel("Waiting for manifest...")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)
        layout.addStretch()

    def set_manifest(self, manifest_path: Path, output_dir: Path) -> None:
        """Set the manifest file and output directory."""
        self._manifest_path = manifest_path
        self._output_dir = output_dir
        self._manifest_label.setText(str(manifest_path))
        self._btn_start.setEnabled(True)

    def _browse_manifest(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Chunks Manifest", "", "JSON (*.json)",
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
        self._progress.set_status("Synthesis complete!")
        self._status.setText(f"Output: {manifest}")

    def _on_error(self, msg: str) -> None:
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._progress.set_status(f"Error: {msg}")
