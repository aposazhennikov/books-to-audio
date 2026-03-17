"""Voices page — dialogue detection and interactive voice assignment."""

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
from book_normalizer.gui.widgets.voice_table import VoiceTableWidget
from book_normalizer.gui.workers.tts_worker import ExportChunksWorker


class VoicesPage(QWidget):
    """Page for dialogue detection and voice assignment."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._book = None
        self._output_dir: Path | None = None
        self._manifest_path: Path | None = None
        self._worker: ExportChunksWorker | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Settings row.
        settings = QFormLayout()

        self._speaker_mode = QComboBox()
        self._speaker_mode.addItems(["heuristic", "llm", "manual"])
        settings.addRow("Speaker Mode:", self._speaker_mode)

        self._chunk_size = QSpinBox()
        self._chunk_size.setRange(100, 2000)
        self._chunk_size.setValue(600)
        self._chunk_size.setSingleStep(50)
        settings.addRow("Max Chunk Chars:", self._chunk_size)

        layout.addLayout(settings)

        # Action buttons.
        btn_row = QHBoxLayout()
        self._btn_detect = QPushButton("Detect & Chunk")
        self._btn_detect.setMinimumHeight(36)
        self._btn_detect.clicked.connect(self._run_detection)
        self._btn_detect.setEnabled(False)
        btn_row.addWidget(self._btn_detect)

        self._btn_load = QPushButton("Load Existing Manifest")
        self._btn_load.clicked.connect(self._load_manifest)
        btn_row.addWidget(self._btn_load)

        self._btn_save = QPushButton("Save Manifest")
        self._btn_save.clicked.connect(self._save_manifest)
        self._btn_save.setEnabled(False)
        btn_row.addWidget(self._btn_save)

        layout.addLayout(btn_row)

        # Progress.
        self._progress = ProgressWidget()
        layout.addWidget(self._progress)

        # Voice table.
        self._voice_table = VoiceTableWidget()
        self._voice_table.data_changed.connect(lambda: self._btn_save.setEnabled(True))
        layout.addWidget(self._voice_table, stretch=1)

        # Stats.
        self._stats_label = QLabel("")
        layout.addWidget(self._stats_label)

    def set_book(self, book: object, output_dir: Path) -> None:
        """Set the book object from normalization page."""
        self._book = book
        self._output_dir = output_dir
        self._btn_detect.setEnabled(True)

    def _run_detection(self) -> None:
        if not self._book or not self._output_dir:
            return

        self._btn_detect.setEnabled(False)
        self._progress.set_status("Running dialogue detection and chunking...")

        self._worker = ExportChunksWorker(
            book=self._book,
            output_dir=self._output_dir,
            speaker_mode=self._speaker_mode.currentText(),
            max_chunk_chars=self._chunk_size.value(),
        )
        self._worker.progress.connect(self._progress.set_status)
        self._worker.finished.connect(self._on_detection_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_detection_done(self, manifest_path: str) -> None:
        self._manifest_path = Path(manifest_path)
        self._voice_table.load_manifest(self._manifest_path)
        self._btn_detect.setEnabled(True)
        self._btn_save.setEnabled(True)

        chunks = self._voice_table.get_chunks()
        narrator = sum(1 for c in chunks if c.get("voice_id") == "narrator")
        male = sum(1 for c in chunks if c.get("voice_id") == "male")
        female = sum(1 for c in chunks if c.get("voice_id") == "female")
        self._stats_label.setText(
            f"Total: {len(chunks)} chunks | "
            f"Narrator: {narrator} | Male: {male} | Female: {female}"
        )
        self._progress.set_status("Ready")

    def _on_error(self, msg: str) -> None:
        self._btn_detect.setEnabled(True)
        self._progress.set_status(f"Error: {msg}")

    def _load_manifest(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Manifest", "", "JSON (*.json);;All Files (*)",
        )
        if path:
            self._manifest_path = Path(path)
            self._voice_table.load_manifest(self._manifest_path)
            self._btn_save.setEnabled(True)

    def _save_manifest(self) -> None:
        if not self._manifest_path:
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Manifest", "chunks_manifest.json",
                "JSON (*.json);;All Files (*)",
            )
            if path:
                self._manifest_path = Path(path)
            else:
                return
        self._voice_table.save_to_file(self._manifest_path)
        self._progress.set_status(f"Saved: {self._manifest_path.name}")

    def get_manifest_path(self) -> Path | None:
        """Return path to the current manifest file."""
        return self._manifest_path
