"""Voices page — dialogue detection, voice preview, and interactive assignment."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from book_normalizer.gui.i18n import t
from book_normalizer.gui.widgets.progress_widget import ProgressWidget
from book_normalizer.gui.widgets.voice_preview import VoicePreviewPanel
from book_normalizer.gui.widgets.voice_table import VoiceTableWidget
from book_normalizer.gui.workers.tts_worker import ExportChunksWorker


class VoicesPage(QWidget):
    """Page for dialogue detection, voice preview, and voice assignment."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._book = None
        self._output_dir: Path | None = None
        self._manifest_path: Path | None = None
        self._worker: ExportChunksWorker | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # ── Top: settings + voice preview side by side ──
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: settings + actions.
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        settings = QFormLayout()
        settings.setHorizontalSpacing(16)
        settings.setVerticalSpacing(8)

        self._speaker_mode = QComboBox()
        self._speaker_mode.addItems(["heuristic", "llm", "manual"])
        self._speaker_mode_label = QLabel()
        settings.addRow(self._speaker_mode_label, self._speaker_mode)

        self._chunk_size = QSpinBox()
        self._chunk_size.setRange(100, 2000)
        self._chunk_size.setValue(600)
        self._chunk_size.setSingleStep(50)
        self._chunk_size_label = QLabel()
        settings.addRow(self._chunk_size_label, self._chunk_size)

        left_layout.addLayout(settings)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_detect = QPushButton()
        self._btn_detect.setObjectName("primaryBtn")
        self._btn_detect.setMinimumHeight(40)
        self._btn_detect.clicked.connect(self._run_detection)
        self._btn_detect.setEnabled(False)
        btn_row.addWidget(self._btn_detect)

        self._btn_load = QPushButton()
        self._btn_load.clicked.connect(self._load_manifest)
        btn_row.addWidget(self._btn_load)

        self._btn_save = QPushButton()
        self._btn_save.clicked.connect(self._save_manifest)
        self._btn_save.setEnabled(False)
        btn_row.addWidget(self._btn_save)

        left_layout.addLayout(btn_row)

        self._progress = ProgressWidget()
        left_layout.addWidget(self._progress)

        left_layout.addStretch()
        splitter.addWidget(left_panel)

        # Right: voice preview panel (scrollable).
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)

        self._preview_title = QLabel()
        self._preview_title.setStyleSheet(
            "font-weight: 700; font-size: 14px; color: rgba(255,255,255,0.8);"
            "padding: 4px 0;"
        )
        right_layout.addWidget(self._preview_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )
        self._voice_preview = VoicePreviewPanel()
        scroll.setWidget(self._voice_preview)
        right_layout.addWidget(scroll)

        splitter.addWidget(right_panel)
        splitter.setSizes([350, 550])

        layout.addWidget(splitter, stretch=2)

        # ── Bottom: voice assignment table ──
        self._voice_table = VoiceTableWidget()
        self._voice_table.data_changed.connect(
            lambda: self._btn_save.setEnabled(True)
        )
        layout.addWidget(self._voice_table, stretch=3)

        # Stats.
        self._stats_label = QLabel("")
        self._stats_label.setStyleSheet(
            "color: rgba(255,255,255,0.6); font-size: 12px; font-weight: 600;"
            "padding: 4px 0;"
        )
        layout.addWidget(self._stats_label)

        self.retranslate()

    def retranslate(self) -> None:
        """Update translatable strings."""
        self._speaker_mode_label.setText(t("voice.speaker_mode"))
        self._chunk_size_label.setText(t("voice.max_chunk"))
        self._btn_detect.setText(t("voice.detect"))
        self._btn_load.setText(t("voice.load_manifest"))
        self._btn_save.setText(t("voice.save_manifest"))
        self._preview_title.setText(t("voice.preview_panel"))
        self._voice_table.retranslate()
        self._voice_preview.retranslate()

    def set_book(self, book: object, output_dir: Path) -> None:
        """Set the book object from normalization page."""
        self._book = book
        self._output_dir = output_dir
        self._btn_detect.setEnabled(True)

    def _run_detection(self) -> None:
        if not self._book or not self._output_dir:
            return

        self._btn_detect.setEnabled(False)
        self._progress.set_status(t("voice.detecting"))

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
        self._update_stats(chunks)
        self._progress.set_status(t("progress.ready"))

    def _update_stats(self, chunks: list) -> None:
        """Update the stats label with voice distribution."""
        from collections import Counter
        from book_normalizer.gui.voice_presets import PRESET_BY_ID

        counter = Counter(c.get("voice_id", "narrator_calm") for c in chunks)
        parts = []
        for vid, cnt in counter.most_common():
            preset = PRESET_BY_ID.get(vid)
            name = preset.label_ru if preset else vid
            parts.append(f"{name}: {cnt}")
        self._stats_label.setText(
            f"Total: {len(chunks)} chunks | " + " | ".join(parts)
        )

    def _on_error(self, msg: str) -> None:
        self._btn_detect.setEnabled(True)
        self._progress.set_status(f"Error: {msg}")

    def _load_manifest(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("voice.load_manifest"), "", "JSON (*.json);;All Files (*)",
        )
        if path:
            self._manifest_path = Path(path)
            self._voice_table.load_manifest(self._manifest_path)
            self._btn_save.setEnabled(True)

    def _save_manifest(self) -> None:
        if not self._manifest_path:
            path, _ = QFileDialog.getSaveFileName(
                self, t("voice.save_manifest"), "chunks_manifest.json",
                "JSON (*.json);;All Files (*)",
            )
            if path:
                self._manifest_path = Path(path)
            else:
                return
        self._voice_table.save_to_file(self._manifest_path)
        self._progress.set_status(t("voice.saved", name=self._manifest_path.name))

    def get_manifest_path(self) -> Path | None:
        """Return path to the current manifest file."""
        return self._manifest_path
