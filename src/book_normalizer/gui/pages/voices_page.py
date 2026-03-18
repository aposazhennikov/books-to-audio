"""Voices page — dialogue detection, voice preview, and interactive assignment."""

from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
from book_normalizer.gui.workers.tts_worker import ExportSegmentsWorker


class VoicesPage(QWidget):
    """Page for dialogue detection, voice preview, and voice assignment."""

    chunks_built = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._book = None
        self._output_dir: Path | None = None
        self._manifest_path: Path | None = None
        self._worker: ExportSegmentsWorker | None = None
        self._setup_ui()

    # ── UI setup ──

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Top: settings + voice preview side by side.
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

        # Left panel: settings + actions.
        left_panel = QWidget()
        left_panel.setMinimumWidth(360)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        settings = QFormLayout()
        settings.setHorizontalSpacing(16)
        settings.setVerticalSpacing(6)

        # Speaker mode.
        self._speaker_mode = QComboBox()
        self._speaker_mode.addItems(["heuristic", "llm", "manual"])
        self._speaker_mode.currentTextChanged.connect(
            self._on_speaker_mode_changed,
        )
        self._speaker_mode_label = QLabel()
        self._speaker_mode_label.setToolTip(t("voice.speaker_mode_hint"))
        settings.addRow(self._speaker_mode_label, self._speaker_mode)

        self._speaker_mode_hint = QLabel()
        self._speaker_mode_hint.setWordWrap(True)
        self._speaker_mode_hint.setStyleSheet(
            "color: rgba(255,255,255,0.4); font-size: 10px;"
            "padding: 0 0 4px 0;",
        )
        settings.addRow("", self._speaker_mode_hint)

        # Max chunk chars.
        self._chunk_size = QSpinBox()
        self._chunk_size.setRange(100, 2000)
        self._chunk_size.setValue(600)
        self._chunk_size.setSingleStep(50)
        self._chunk_size_label = QLabel()
        settings.addRow(self._chunk_size_label, self._chunk_size)

        left_layout.addLayout(settings)

        # LLM config panel (hidden by default).
        self._llm_panel = QWidget()
        llm_layout = QFormLayout(self._llm_panel)
        llm_layout.setContentsMargins(0, 0, 0, 8)
        llm_layout.setHorizontalSpacing(12)
        llm_layout.setVerticalSpacing(6)

        self._llm_provider = QComboBox()
        self._llm_provider_label = QLabel()
        self._llm_provider.currentIndexChanged.connect(
            self._on_llm_provider_changed,
        )
        llm_layout.addRow(self._llm_provider_label, self._llm_provider)

        self._llm_endpoint_label = QLabel()
        self._llm_endpoint = QLineEdit("http://localhost:11434/v1")
        self._llm_endpoint.setMinimumHeight(28)
        llm_layout.addRow(self._llm_endpoint_label, self._llm_endpoint)

        self._llm_model_label = QLabel()
        self._llm_model = QLineEdit("qwen3:8b")
        self._llm_model.setMinimumHeight(28)
        llm_layout.addRow(self._llm_model_label, self._llm_model)

        self._llm_api_key_label = QLabel()
        self._llm_api_key = QLineEdit()
        self._llm_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._llm_api_key.setMinimumHeight(28)
        self._llm_api_key.setPlaceholderText("sk-...")
        llm_layout.addRow(self._llm_api_key_label, self._llm_api_key)

        self._llm_panel.setVisible(False)
        left_layout.addWidget(self._llm_panel)

        # Action buttons.
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

        # Build TTS chunks button.
        btn_row2 = QHBoxLayout()
        btn_row2.setSpacing(8)

        self._btn_build = QPushButton()
        self._btn_build.setMinimumHeight(36)
        self._btn_build.clicked.connect(self._build_tts_chunks)
        self._btn_build.setEnabled(False)
        self._btn_build.setStyleSheet(
            "QPushButton {"
            "  background: rgba(0,184,148,0.15);"
            "  color: rgba(0,184,148,0.9);"
            "  border: 1px solid rgba(0,184,148,0.3);"
            "  border-radius: 8px; font-weight: 700;"
            "  padding: 6px 16px;"
            "}"
            "QPushButton:hover {"
            "  background: rgba(0,184,148,0.25);"
            "}"
            "QPushButton:disabled {"
            "  color: rgba(255,255,255,0.2);"
            "  background: rgba(255,255,255,0.03);"
            "  border-color: rgba(255,255,255,0.06);"
            "}",
        )
        btn_row2.addWidget(self._btn_build)
        btn_row2.addStretch()
        left_layout.addLayout(btn_row2)

        self._progress = ProgressWidget()
        left_layout.addWidget(self._progress)

        # Manifest path display.
        self._manifest_label = QLabel("")
        self._manifest_label.setWordWrap(True)
        self._manifest_label.setStyleSheet(
            "color: rgba(255,255,255,0.45); font-size: 10px;"
            "padding: 2px 0;",
        )
        self._manifest_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse,
        )
        left_layout.addWidget(self._manifest_label)

        left_layout.addStretch()
        splitter.addWidget(left_panel)

        # Right panel: voice preview (scrollable, vertical only).
        right_panel = QWidget()
        right_panel.setMinimumWidth(300)
        right_panel.setMaximumWidth(520)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 0, 0, 0)
        right_layout.setSpacing(4)

        self._preview_title = QLabel()
        self._preview_title.setStyleSheet(
            "font-weight: 700; font-size: 14px;"
            "color: rgba(255,255,255,0.8); padding: 4px 0;",
        )
        right_layout.addWidget(self._preview_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )
        scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded,
        )
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }",
        )
        self._voice_preview = VoicePreviewPanel()
        self._voice_preview.setMaximumWidth(500)
        scroll.setWidget(self._voice_preview)
        right_layout.addWidget(scroll)

        splitter.addWidget(right_panel)
        splitter.setSizes([480, 420])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)

        layout.addWidget(splitter, stretch=2)

        # Bottom: voice assignment table.
        self._voice_table = VoiceTableWidget()
        self._voice_table.data_changed.connect(
            lambda: self._btn_save.setEnabled(True),
        )
        self._voice_table.data_changed.connect(
            lambda: self._btn_build.setEnabled(True),
        )
        layout.addWidget(self._voice_table, stretch=3)

        # Stats.
        self._stats_label = QLabel("")
        self._stats_label.setStyleSheet(
            "color: rgba(255,255,255,0.6); font-size: 12px;"
            "font-weight: 600; padding: 4px 0;",
        )
        layout.addWidget(self._stats_label)

        self.retranslate()

    # ── Translations ──

    def retranslate(self) -> None:
        """Update translatable strings."""
        self._speaker_mode_label.setText(t("voice.speaker_mode"))
        self._speaker_mode_label.setToolTip(t("voice.speaker_mode_hint"))
        self._update_speaker_mode_hint()
        self._chunk_size_label.setText(t("voice.max_chunk"))
        self._btn_detect.setText(t("voice.detect"))
        self._btn_load.setText(t("voice.load_manifest"))
        self._btn_save.setText(t("voice.save_manifest"))
        self._btn_build.setText(t("voice.build_chunks"))
        self._preview_title.setText(t("voice.preview_panel"))

        self._llm_provider_label.setText(t("voice.llm_provider"))
        self._llm_provider.clear()
        self._llm_provider.addItem(t("voice.llm_local"), "local")
        self._llm_provider.addItem(t("voice.llm_openai"), "openai")
        self._llm_endpoint_label.setText(t("voice.llm_endpoint"))
        self._llm_model_label.setText(t("voice.llm_model"))
        self._llm_api_key_label.setText(t("voice.llm_api_key"))

        self._voice_table.retranslate()
        self._voice_preview.retranslate()

    def _update_speaker_mode_hint(self) -> None:
        """Show inline hint for currently selected speaker mode."""
        mode = self._speaker_mode.currentText()
        hints = {
            "heuristic": t("voice.speaker_mode_hint").split("\n")[0],
            "llm": t("voice.speaker_mode_hint").split("\n")[1],
            "manual": t("voice.speaker_mode_hint").split("\n")[2],
        }
        self._speaker_mode_hint.setText(hints.get(mode, ""))

    # ── Event handlers ──

    def _on_speaker_mode_changed(self, mode: str) -> None:
        """Show/hide LLM config when speaker mode changes."""
        self._llm_panel.setVisible(mode == "llm")
        self._update_speaker_mode_hint()

    def _on_llm_provider_changed(self, _idx: int) -> None:
        """Toggle endpoint vs API key fields based on provider."""
        provider = self._llm_provider.currentData()
        is_local = provider == "local"
        self._llm_endpoint.setVisible(is_local)
        self._llm_endpoint_label.setVisible(is_local)
        self._llm_api_key.setVisible(not is_local)
        self._llm_api_key_label.setVisible(not is_local)
        if not is_local:
            self._llm_endpoint.setText("https://api.openai.com/v1")
            self._llm_model.setText("gpt-4o-mini")
        else:
            self._llm_endpoint.setText("http://localhost:11434/v1")
            self._llm_model.setText("qwen3:8b")

    def set_book(self, book: object, output_dir: Path) -> None:
        """Set the book object from normalization page."""
        self._book = book
        self._output_dir = output_dir
        self._btn_detect.setEnabled(True)

    # ── Detection ──

    def _run_detection(self) -> None:
        if not self._book or not self._output_dir:
            return

        self._btn_detect.setEnabled(False)
        self._progress.set_status(t("voice.detecting"))

        llm_endpoint = self._llm_endpoint.text().strip()
        llm_model = self._llm_model.text().strip()
        llm_api_key = self._llm_api_key.text().strip()

        self._worker = ExportSegmentsWorker(
            book=self._book,
            output_dir=self._output_dir,
            speaker_mode=self._speaker_mode.currentText(),
            llm_endpoint=llm_endpoint,
            llm_model=llm_model,
            llm_api_key=llm_api_key,
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
        self._btn_build.setEnabled(True)

        segments = self._voice_table.get_segments()
        self._update_stats(segments)
        self._manifest_label.setText(
            t("voice.manifest_path", path=str(self._manifest_path)),
        )
        self._progress.set_status(
            t("voice.segments_ready", n=len(segments)),
        )

    def _update_stats(self, segments: list) -> None:
        """Update the stats label with segment distribution."""
        speech = sum(
            1 for s in segments
            if s.get("is_dialogue") or s.get("role") in ("male", "female")
        )
        narr = len(segments) - speech
        self._stats_label.setText(
            t(
                "voice.stats_segments",
                total=len(segments),
                speech=speech,
                narr=narr,
            ),
        )

    def _on_error(self, msg: str) -> None:
        self._btn_detect.setEnabled(True)
        self._progress.set_status(f"Error: {msg}")

    # ── Build TTS chunks from segments ──

    def _build_tts_chunks(self) -> None:
        """Group user-assigned segments into TTS-ready chunks."""
        from book_normalizer.chunking.voice_splitter import (
            build_chunks_from_segments,
        )

        segments = self._voice_table.get_segments()
        if not segments:
            return

        self._progress.set_busy(
            t("voice.building_chunks", n=len(segments)),
        )

        chunks = build_chunks_from_segments(
            segments,
            max_chunk_chars=self._chunk_size.value(),
        )

        if not self._output_dir:
            self._output_dir = Path(".")

        self._output_dir.mkdir(parents=True, exist_ok=True)
        chunks_path = self._output_dir / "chunks_manifest.json"
        chunks_path.write_text(
            json.dumps(chunks, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self._progress.set_status(
            t("voice.chunks_done", n=len(chunks)),
        )
        self._manifest_label.setText(
            t("voice.manifest_path", path=str(chunks_path)),
        )
        self.chunks_built.emit(str(chunks_path))

    # ── Load / Save ──

    def _load_manifest(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("voice.load_manifest"),
            "",
            "JSON (*.json);;All Files (*)",
        )
        if path:
            self._manifest_path = Path(path)
            self._voice_table.load_manifest(self._manifest_path)
            self._btn_save.setEnabled(True)
            self._btn_build.setEnabled(True)
            self._manifest_label.setText(
                t("voice.manifest_path", path=str(self._manifest_path)),
            )

    def _save_manifest(self) -> None:
        if not self._manifest_path:
            path, _ = QFileDialog.getSaveFileName(
                self,
                t("voice.save_manifest"),
                "segments_manifest.json",
                "JSON (*.json);;All Files (*)",
            )
            if path:
                self._manifest_path = Path(path)
            else:
                return
        self._voice_table.save_to_file(self._manifest_path)
        self._progress.set_status(
            t("voice.saved", path=str(self._manifest_path)),
        )
        self._manifest_label.setText(
            t("voice.manifest_path", path=str(self._manifest_path)),
        )

    def get_manifest_path(self) -> Path | None:
        """Return path to the current manifest file."""
        return self._manifest_path
