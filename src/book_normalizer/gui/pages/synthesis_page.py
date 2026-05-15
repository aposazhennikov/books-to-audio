"""Synthesis page — TTS generation with progress and ETA."""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from book_normalizer.gui.i18n import t
from book_normalizer.gui.widgets.progress_widget import ProgressWidget
from book_normalizer.gui.workers.tts_worker import TTSSynthesisWorker
from book_normalizer.tts.model_paths import default_comfyui_models_dir

MODELS = [
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
]

# All available voice preset IDs (must match tts_runner VOICE_PRESETS).
VOICE_IDS = [
    "narrator_calm",
    "narrator_energetic",
    "narrator_wise",
    "male_young",
    "male_confident",
    "male_deep",
    "male_lively",
    "male_regional",
    "female_warm",
    "female_bright",
    "female_playful",
    "female_gentle",
]


def _iter_manifest_chunks(data: object) -> list[dict]:
    """Return chunk records from v1 list or v2 grouped manifest."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        chunks: list[dict] = []
        for chapter in data.get("chapters", []):
            if not isinstance(chapter, dict):
                continue
            chapter_index = chapter.get("chapter_index", 0)
            for chunk in chapter.get("chunks", []):
                if isinstance(chunk, dict):
                    chunks.append({"chapter_index": chapter_index, **chunk})
        return chunks
    return []


class _CloneVoiceRow(QWidget):
    """A single voice clone entry: voice_id selector + WAV path + transcript."""

    # Emitted just before the widget is destroyed so the parent can update its list.
    about_to_remove: pyqtSignal = pyqtSignal(object)

    def __init__(self, voice_ids: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui(voice_ids)

    def _build_ui(self, voice_ids: list[str]) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(4)

        # Row 1: voice selector + WAV picker.
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        self._voice_combo = QComboBox()
        self._voice_combo.addItems(voice_ids)
        self._voice_combo.setMinimumWidth(160)
        row1.addWidget(self._voice_combo)

        self._wav_edit = QLineEdit()
        self._wav_edit.setPlaceholderText("reference.wav")
        self._wav_edit.setReadOnly(True)
        self._wav_edit.setStyleSheet(
            "color: rgba(255,255,255,0.7); font-size: 11px; padding: 4px 6px;"
            "background: rgba(255,255,255,0.06); border-radius: 4px;"
            "border: 1px solid rgba(255,255,255,0.1);",
        )
        row1.addWidget(self._wav_edit, stretch=1)

        self._btn_wav = QPushButton("WAV…")
        self._btn_wav.setMaximumWidth(60)
        self._btn_wav.clicked.connect(self._browse_wav)
        row1.addWidget(self._btn_wav)

        self._btn_remove = QPushButton("✕")
        self._btn_remove.setMaximumWidth(32)
        self._btn_remove.setStyleSheet(
            "QPushButton { color: rgba(255,100,100,0.8); font-weight: 700;"
            "background: transparent; border: none; padding: 2px; }"
            "QPushButton:hover { color: rgba(255,80,80,1); }",
        )
        self._btn_remove.clicked.connect(self._on_remove)
        row1.addWidget(self._btn_remove)

        layout.addLayout(row1)

        # Row 2: transcript text field.
        self._transcript = QLineEdit()
        self._transcript.setStyleSheet(
            "color: rgba(255,255,255,0.7); font-size: 11px; padding: 4px 6px;"
            "background: rgba(255,255,255,0.06); border-radius: 4px;"
            "border: 1px solid rgba(255,255,255,0.1);",
        )
        layout.addWidget(self._transcript)

    def _browse_wav(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Reference WAV", "", "Audio (*.wav *.mp3 *.flac *.ogg);;All (*)",
        )
        if path:
            self._wav_edit.setText(path)

    def _on_remove(self) -> None:
        # Notify parent page to remove this row from its tracking list
        # BEFORE setParent(None) destroys the C++ object reference.
        self.about_to_remove.emit(self)
        self.setParent(None)  # type: ignore[arg-type]
        self.deleteLater()

    def get_voice_id(self) -> str:
        """Return the selected voice preset ID."""
        return self._voice_combo.currentText()

    def get_wav_path(self) -> str:
        """Return the selected WAV file path."""
        return self._wav_edit.text().strip()

    def get_transcript(self) -> str:
        """Return the reference transcript."""
        return self._transcript.text().strip()

    def is_valid(self) -> bool:
        """Return True when both WAV path and transcript are filled in."""
        return bool(self.get_wav_path() and self.get_transcript())

    def retranslate(self) -> None:
        """Update translatable placeholder text."""
        self._transcript.setPlaceholderText(t("synth.clone_transcript_ph"))


class SynthesisPage(QWidget):
    """Page for running TTS synthesis with progress tracking."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._manifest_path: Path | None = None
        self._output_dir: Path | None = None
        self._worker: TTSSynthesisWorker | None = None
        self._chapter_map: dict[int, int] = {}
        self._phase = "idle"
        self._phase_start = 0.0
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(1000)
        self._tick_timer.timeout.connect(self._on_tick)
        self._clone_rows: list[_CloneVoiceRow] = []
        self._sample_audio = QAudioOutput(self)
        self._sample_audio.setVolume(0.8)
        self._sample_player = QMediaPlayer(self)
        self._sample_player.setAudioOutput(self._sample_audio)
        self._setup_ui()

    # ── UI construction ──────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 0, 0, 0)

        # Scrollable settings area.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 4, 6, 4)

        # ── Manifest row ──────────────────────────────────────────────────
        file_row = QHBoxLayout()
        file_row.setSpacing(8)
        self._manifest_label = QLabel()
        self._manifest_label.setWordWrap(True)
        self._manifest_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse,
        )
        self._manifest_label.setStyleSheet(
            "font-weight: 700; font-size: 13px; padding: 6px 12px;"
            "background: rgba(255,255,255,0.04); border-radius: 6px;",
        )
        file_row.addWidget(self._manifest_label, stretch=1)

        self._btn_load = QPushButton()
        self._btn_load.clicked.connect(self._browse_manifest)
        file_row.addWidget(self._btn_load)
        layout.addLayout(file_row)

        # ── Main settings form ────────────────────────────────────────────
        settings = QFormLayout()
        settings.setHorizontalSpacing(16)
        settings.setVerticalSpacing(6)

        self._model_combo = QComboBox()
        self._model_combo.addItems(MODELS)
        self._model_label = QLabel()
        settings.addRow(self._model_label, self._model_combo)

        self._model_hint = self._hint_label()
        settings.addRow("", self._model_hint)

        model_dir_row = QHBoxLayout()
        model_dir_row.setSpacing(6)
        self._models_dir_edit = QLineEdit(str(default_comfyui_models_dir()))
        self._models_dir_edit.setMinimumWidth(320)
        model_dir_row.addWidget(self._models_dir_edit, stretch=1)
        self._btn_models_dir = QPushButton()
        self._btn_models_dir.clicked.connect(self._browse_models_dir)
        model_dir_row.addWidget(self._btn_models_dir)
        self._models_dir_label = QLabel()
        settings.addRow(self._models_dir_label, model_dir_row)

        self._models_dir_hint = self._hint_label()
        settings.addRow("", self._models_dir_hint)

        self._batch_size = QSpinBox()
        self._batch_size.setRange(1, 8)
        self._batch_size.setValue(1)
        self._batch_size.setMaximumWidth(120)
        self._batch_label = QLabel()
        settings.addRow(self._batch_label, self._batch_size)

        self._batch_hint = self._hint_label()
        settings.addRow("", self._batch_hint)

        self._chunk_timeout = QSpinBox()
        self._chunk_timeout.setRange(30, 1800)
        self._chunk_timeout.setValue(300)
        self._chunk_timeout.setSingleStep(30)
        self._chunk_timeout.setSuffix(" с")
        self._chunk_timeout.setMaximumWidth(120)
        self._chunk_timeout_label = QLabel()
        settings.addRow(self._chunk_timeout_label, self._chunk_timeout)

        self._output_format_combo = QComboBox()
        self._output_format_combo.addItem("FLAC", "flac")
        self._output_format_combo.addItem("WAV", "wav")
        self._output_format_label = QLabel()
        settings.addRow(self._output_format_label, self._output_format_combo)

        self._merge_chapters_check = QCheckBox()
        self._merge_chapters_check.setChecked(True)
        self._merge_chapters_label = QLabel()
        settings.addRow(self._merge_chapters_label, self._merge_chapters_check)

        self._chapter_combo = QComboBox()
        self._chapter_combo.setMinimumWidth(200)
        self._chapter_label = QLabel()
        settings.addRow(self._chapter_label, self._chapter_combo)

        self._chapter_info = self._hint_label()
        settings.addRow("", self._chapter_info)

        self._resume_check = QCheckBox()
        self._resume_label = QLabel()
        settings.addRow(self._resume_label, self._resume_check)

        self._resume_hint = self._hint_label()
        settings.addRow("", self._resume_hint)

        self._compile_check = QCheckBox()
        self._compile_label = QLabel()
        settings.addRow(self._compile_label, self._compile_check)

        self._compile_hint = self._hint_label()
        settings.addRow("", self._compile_hint)

        self._sage_check = QCheckBox()
        self._sage_label = QLabel()
        settings.addRow(self._sage_label, self._sage_check)

        self._sage_hint = self._hint_label()
        settings.addRow("", self._sage_hint)

        layout.addLayout(settings)

        # ── Voice cloning panel ───────────────────────────────────────────
        layout.addWidget(self._build_sample_voice_panel())

        # ── Action buttons ────────────────────────────────────────────────
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
        layout.addStretch()

        scroll.setWidget(container)
        outer.addWidget(scroll, stretch=1)

        # ── Progress + log (outside scroll, always visible) ───────────────
        bottom = QVBoxLayout()
        bottom.setContentsMargins(0, 4, 0, 0)
        bottom.setSpacing(6)

        self._progress = ProgressWidget()
        bottom.addWidget(self._progress)

        self._log_edit = QPlainTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setMaximumHeight(110)
        self._log_edit.setStyleSheet(
            "font-family: 'Cascadia Code', Consolas, monospace;"
            "font-size: 11px; background: rgba(0,0,0,0.3);"
            "border-radius: 4px; padding: 6px;",
        )
        bottom.addWidget(self._log_edit)

        self._status = QLabel()
        self._status.setWordWrap(True)
        self._status.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse,
        )
        self._status.setStyleSheet(
            "color: rgba(255,255,255,0.6); font-size: 12px; padding: 2px 0;",
        )
        bottom.addWidget(self._status)

        outer.addLayout(bottom)

        self.retranslate()

    def _build_sample_voice_panel(self) -> QFrame:
        """Build the direct CustomVoice sample panel."""
        frame = QFrame()
        frame.setObjectName("sampleVoicePanel")
        frame.setStyleSheet(
            "QFrame#sampleVoicePanel {"
            "  background: rgba(124,92,252,0.07);"
            "  border: 1px solid rgba(124,92,252,0.25);"
            "  border-radius: 8px;"
            "}"
        )
        outer = QVBoxLayout(frame)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(8)

        header = QHBoxLayout()
        self._sample_enable = QCheckBox()
        header.addWidget(self._sample_enable)
        self._sample_title = QLabel()
        self._sample_title.setStyleSheet(
            "font-weight: 700; font-size: 13px; color: rgba(190,170,255,0.98);"
        )
        header.addWidget(self._sample_title, stretch=1)
        outer.addLayout(header)

        self._sample_desc = QLabel()
        self._sample_desc.setWordWrap(True)
        self._sample_desc.setStyleSheet(
            "color: rgba(255,255,255,0.55); font-size: 11px;"
        )
        outer.addWidget(self._sample_desc)

        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(6)

        audio_row = QHBoxLayout()
        audio_row.setSpacing(6)
        self._sample_audio_edit = QLineEdit()
        self._sample_audio_edit.setReadOnly(True)
        audio_row.addWidget(self._sample_audio_edit, stretch=1)
        self._btn_sample_audio = QPushButton()
        self._btn_sample_audio.clicked.connect(self._browse_sample_audio)
        audio_row.addWidget(self._btn_sample_audio)
        self._sample_audio_label = QLabel()
        form.addRow(self._sample_audio_label, audio_row)

        playback_row = QHBoxLayout()
        playback_row.setSpacing(8)
        self._btn_sample_play = QPushButton()
        self._btn_sample_play.setEnabled(False)
        self._btn_sample_play.clicked.connect(self._toggle_sample_playback)
        playback_row.addWidget(self._btn_sample_play)
        self._sample_duration_label = QLabel("0:00 / 0:00")
        self._sample_duration_label.setStyleSheet(
            "color: rgba(255,255,255,0.7); font-size: 12px;"
        )
        playback_row.addWidget(self._sample_duration_label)
        playback_row.addStretch()
        self._sample_player.durationChanged.connect(self._on_sample_duration_changed)
        self._sample_player.positionChanged.connect(self._on_sample_position_changed)
        self._sample_player.playbackStateChanged.connect(self._on_sample_playback_state)
        self._sample_preview_label = QLabel()
        form.addRow(self._sample_preview_label, playback_row)

        self._sample_transcript_edit = QPlainTextEdit()
        self._sample_transcript_edit.setMaximumHeight(92)
        self._sample_transcript_label = QLabel()
        form.addRow(self._sample_transcript_label, self._sample_transcript_edit)

        outer.addLayout(form)

        controls = QFormLayout()
        controls.setHorizontalSpacing(14)
        controls.setVerticalSpacing(6)

        self._temperature_spin = QDoubleSpinBox()
        self._temperature_spin.setRange(0.1, 2.0)
        self._temperature_spin.setSingleStep(0.05)
        self._temperature_spin.setDecimals(2)
        self._temperature_spin.setValue(1.0)
        self._temperature_label = QLabel()
        controls.addRow(self._temperature_label, self._temperature_spin)

        self._top_p_spin = QDoubleSpinBox()
        self._top_p_spin.setRange(0.1, 1.0)
        self._top_p_spin.setSingleStep(0.05)
        self._top_p_spin.setDecimals(2)
        self._top_p_spin.setValue(0.80)
        self._top_p_label = QLabel()
        controls.addRow(self._top_p_label, self._top_p_spin)

        self._top_k_spin = QSpinBox()
        self._top_k_spin.setRange(1, 200)
        self._top_k_spin.setValue(20)
        self._top_k_label = QLabel()
        controls.addRow(self._top_k_label, self._top_k_spin)

        self._repetition_penalty_spin = QDoubleSpinBox()
        self._repetition_penalty_spin.setRange(0.8, 2.0)
        self._repetition_penalty_spin.setSingleStep(0.01)
        self._repetition_penalty_spin.setDecimals(2)
        self._repetition_penalty_spin.setValue(1.05)
        self._repetition_penalty_label = QLabel()
        controls.addRow(self._repetition_penalty_label, self._repetition_penalty_spin)

        self._max_new_tokens_spin = QSpinBox()
        self._max_new_tokens_spin.setRange(128, 8192)
        self._max_new_tokens_spin.setSingleStep(128)
        self._max_new_tokens_spin.setValue(2048)
        self._max_new_tokens_label = QLabel()
        controls.addRow(self._max_new_tokens_label, self._max_new_tokens_spin)

        self._seed_spin = QSpinBox()
        self._seed_spin.setRange(-1, 2_147_483_647)
        self._seed_spin.setValue(-1)
        self._seed_label = QLabel()
        controls.addRow(self._seed_label, self._seed_spin)

        outer.addLayout(controls)

        self._sample_status = QLabel()
        self._sample_status.setWordWrap(True)
        self._sample_status.setStyleSheet(
            "color: rgba(255,255,255,0.62); font-size: 11px;"
        )
        outer.addWidget(self._sample_status)
        return frame

    def _build_clone_panel(self) -> QFrame:
        """Build the voice cloning expandable panel."""
        frame = QFrame()
        frame.setObjectName("clonePanel")
        frame.setStyleSheet(
            "QFrame#clonePanel {"
            "  background: rgba(0,184,148,0.06);"
            "  border: 1px solid rgba(0,184,148,0.2);"
            "  border-radius: 8px;"
            "  padding: 0px;"
            "}"
        )
        outer = QVBoxLayout(frame)
        outer.setContentsMargins(12, 8, 12, 8)
        outer.setSpacing(6)

        # Header row: checkbox + title.
        header = QHBoxLayout()
        self._clone_enable = QCheckBox()
        self._clone_enable.toggled.connect(self._on_clone_toggled)
        header.addWidget(self._clone_enable)

        self._clone_title = QLabel()
        self._clone_title.setStyleSheet(
            "font-weight: 700; font-size: 13px; color: rgba(0,220,170,0.9);"
        )
        header.addWidget(self._clone_title, stretch=1)
        outer.addLayout(header)

        # Explanation label.
        self._clone_desc = QLabel()
        self._clone_desc.setWordWrap(True)
        self._clone_desc.setStyleSheet(
            "color: rgba(255,255,255,0.5); font-size: 11px; padding: 0 0 4px 0;"
        )
        outer.addWidget(self._clone_desc)

        # Container for dynamic rows (hidden when cloning disabled).
        self._clone_body = QWidget()
        body_layout = QVBoxLayout(self._clone_body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(2)

        # Column headers.
        col_header = QHBoxLayout()
        col_header.setSpacing(6)
        lbl_role = QLabel()
        lbl_role.setObjectName("cloneColRole")
        lbl_role.setStyleSheet(
            "color: rgba(255,255,255,0.35); font-size: 10px; font-weight: 600;"
        )
        lbl_role.setFixedWidth(160)
        col_header.addWidget(lbl_role)
        lbl_wav = QLabel()
        lbl_wav.setObjectName("cloneColWav")
        lbl_wav.setStyleSheet(
            "color: rgba(255,255,255,0.35); font-size: 10px; font-weight: 600;"
        )
        col_header.addWidget(lbl_wav, stretch=1)
        col_header.addSpacing(60 + 32 + 6)  # WAV btn + remove btn width.
        body_layout.addLayout(col_header)

        # Separator.
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(255,255,255,0.08);")
        body_layout.addWidget(sep)

        # Transcript column hint.
        col_transcript = QLabel()
        col_transcript.setObjectName("cloneColTranscript")
        col_transcript.setStyleSheet(
            "color: rgba(255,255,255,0.35); font-size: 10px; padding: 0 0 2px 0;"
        )
        body_layout.addWidget(col_transcript)

        # Row container (rows added dynamically).
        self._clone_rows_widget = QWidget()
        self._clone_rows_layout = QVBoxLayout(self._clone_rows_widget)
        self._clone_rows_layout.setContentsMargins(0, 0, 0, 0)
        self._clone_rows_layout.setSpacing(4)
        body_layout.addWidget(self._clone_rows_widget)

        # "Add voice" button.
        add_row = QHBoxLayout()
        self._btn_add_clone = QPushButton()
        self._btn_add_clone.setStyleSheet(
            "QPushButton {"
            "  background: rgba(0,184,148,0.12);"
            "  color: rgba(0,220,170,0.9);"
            "  border: 1px dashed rgba(0,184,148,0.4);"
            "  border-radius: 6px; padding: 5px 14px; font-size: 12px;"
            "}"
            "QPushButton:hover { background: rgba(0,184,148,0.22); }"
        )
        self._btn_add_clone.clicked.connect(self._add_clone_row)
        add_row.addWidget(self._btn_add_clone)
        add_row.addStretch()
        body_layout.addLayout(add_row)

        # Store column header labels for retranslate.
        self._clone_col_role = lbl_role
        self._clone_col_wav = lbl_wav
        self._clone_col_transcript = col_transcript

        outer.addWidget(self._clone_body)
        self._clone_body.setVisible(False)
        return frame

    @staticmethod
    def _hint_label() -> QLabel:
        lbl = QLabel()
        lbl.setWordWrap(True)
        lbl.setStyleSheet(
            "color: rgba(255,255,255,0.4); font-size: 11px;"
            "background: transparent; border: none; padding: 0 0 4px 0;",
        )
        return lbl

    # ── Translations ─────────────────────────────────────────────────────────

    def retranslate(self) -> None:
        """Update translatable strings."""
        if not self._manifest_path:
            self._manifest_label.setText(t("synth.no_manifest"))
        self._btn_load.setText(t("synth.load_manifest"))
        self._model_label.setText(t("synth.model"))
        self._model_hint.setText(t("synth.model_hint"))
        self._model_combo.setToolTip(t("synth.model_hint"))
        self._models_dir_label.setText(t("synth.models_dir"))
        self._models_dir_hint.setText(t("synth.models_dir_hint"))
        self._models_dir_edit.setToolTip(t("synth.models_dir_hint"))
        self._btn_models_dir.setText(t("synth.choose_dir"))
        self._batch_label.setText(t("synth.batch_size"))
        self._batch_hint.setText(t("synth.batch_hint"))
        self._batch_size.setToolTip(t("synth.batch_hint"))
        self._chunk_timeout_label.setText(t("synth.chunk_timeout"))
        self._chunk_timeout.setToolTip(t("synth.chunk_timeout_hint"))
        self._output_format_label.setText(t("synth.output_format"))
        self._merge_chapters_label.setText(t("synth.merge_chapters"))
        self._merge_chapters_check.setText(t("synth.merge_chapters_check"))
        self._chapter_label.setText(t("synth.chapter"))
        self._resume_label.setText(t("synth.resume"))
        self._resume_check.setText(t("synth.resume_check"))
        self._resume_hint.setText(t("synth.resume_hint"))
        self._compile_label.setText(t("synth.compile"))
        self._compile_check.setText(t("synth.compile_check"))
        self._compile_hint.setText(t("synth.compile_hint"))
        self._sage_label.setText(t("synth.sage_attention"))
        self._sage_check.setText(t("synth.sage_check"))
        self._sage_hint.setText(t("synth.sage_hint"))

        self._sample_enable.setText(t("synth.sample_enable"))
        self._sample_title.setText(t("synth.sample_title"))
        self._sample_desc.setText(t("synth.sample_desc"))
        self._sample_audio_label.setText(t("synth.sample_audio"))
        self._btn_sample_audio.setText(t("synth.browse_audio"))
        self._sample_preview_label.setText(t("synth.sample_preview"))
        self._btn_sample_play.setText(t("synth.sample_play"))
        self._sample_transcript_label.setText(t("synth.sample_transcript"))
        self._sample_transcript_edit.setPlaceholderText(
            t("synth.clone_transcript_ph"),
        )
        self._temperature_label.setText(t("synth.temperature"))
        self._top_p_label.setText(t("synth.top_p"))
        self._top_k_label.setText(t("synth.top_k"))
        self._repetition_penalty_label.setText(t("synth.repetition_penalty"))
        self._max_new_tokens_label.setText(t("synth.max_new_tokens"))
        self._seed_label.setText(t("synth.seed"))
        if not self._sample_status.text():
            self._sample_status.setText(t("synth.sample_idle"))

        self._btn_start.setText(t("synth.start"))
        self._btn_stop.setText(t("synth.stop"))
        self._status.setText(t("synth.waiting"))
        self._log_edit.setPlaceholderText(t("synth.log_placeholder"))
        self._refresh_chapter_combo()

    # ── Clone panel logic ─────────────────────────────────────────────────────

    def _on_clone_toggled(self, checked: bool) -> None:
        """Show or hide the clone body when checkbox is toggled."""
        self._clone_body.setVisible(checked)
        if checked and not self._clone_rows:
            self._add_clone_row()

    def _add_clone_row(self) -> None:
        """Add a new voice clone entry row."""
        row = _CloneVoiceRow(VOICE_IDS, self._clone_rows_widget)
        # Remove from tracking list before C++ object gets destroyed.
        row.about_to_remove.connect(self._on_clone_row_removed)
        row.retranslate()
        self._clone_rows_layout.addWidget(row)
        self._clone_rows.append(row)

    def _on_clone_row_removed(self, row: object) -> None:
        """Remove a clone row from the tracking list when it signals removal."""
        if row in self._clone_rows:
            self._clone_rows.remove(row)  # type: ignore[arg-type]

    def _collect_clone_config(self) -> dict[str, dict]:
        """Collect valid clone entries into a config dict."""
        config: dict[str, dict] = {}
        for row in list(self._clone_rows):
            if row.is_valid():
                config[row.get_voice_id()] = {
                    "ref_audio": row.get_wav_path(),
                    "ref_text": row.get_transcript(),
                }
        return config

    def _build_temp_clone_config(self) -> str:
        """Serialize clone config to a temp JSON file; return its path."""
        cfg = self._collect_clone_config()
        if not cfg:
            return ""
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8",
        )
        json.dump(cfg, tmp, ensure_ascii=False, indent=2)
        tmp.close()
        return tmp.name

    # Sample voice logic

    def _browse_models_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            t("synth.models_dir"),
            self._models_dir_edit.text().strip() or str(default_comfyui_models_dir()),
        )
        if path:
            self._models_dir_edit.setText(path)

    def _browse_sample_audio(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("synth.sample_audio"),
            "",
            "Audio (*.wav *.mp3 *.flac *.ogg);;All (*)",
        )
        if path:
            self._sample_audio_edit.setText(path)
            self._sample_enable.setChecked(True)
            self._btn_sample_play.setEnabled(True)
            self._sample_player.setSource(QUrl.fromLocalFile(path))
            self._sample_status.setText(t("synth.sample_ready"))

    def _toggle_sample_playback(self) -> None:
        if not self._sample_audio_edit.text().strip():
            return
        if self._sample_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._sample_player.pause()
        else:
            self._sample_player.play()

    def _on_sample_duration_changed(self, _duration: int) -> None:
        self._update_sample_duration_label()

    def _on_sample_position_changed(self, _position: int) -> None:
        self._update_sample_duration_label()

    def _on_sample_playback_state(self, state: QMediaPlayer.PlaybackState) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._btn_sample_play.setText(t("synth.sample_pause"))
        else:
            self._btn_sample_play.setText(t("synth.sample_play"))

    def _update_sample_duration_label(self) -> None:
        pos = self._sample_player.position()
        duration = self._sample_player.duration()
        self._sample_duration_label.setText(
            f"{self._format_msec(pos)} / {self._format_msec(duration)}",
        )
        if duration > 0:
            sec = max(1, int(round(duration / 1000)))
            eta_min = max(20, sec * 2)
            eta_max = max(45, sec * 4)
            self._sample_status.setText(
                t("synth.sample_duration", sec=sec, eta=f"{eta_min}-{eta_max}s"),
            )

    @staticmethod
    def _format_msec(value: int) -> str:
        seconds = max(0, value // 1000)
        m, s = divmod(seconds, 60)
        return f"{m}:{s:02d}"

    def _build_temp_sample_voice_config(self) -> str:
        """Serialize the selected sample voice as a global clone config."""
        if not self._sample_enable.isChecked():
            return ""

        audio = self._sample_audio_edit.text().strip()
        ref_text = self._sample_transcript_edit.toPlainText().strip()
        if not audio or not ref_text:
            raise ValueError(t("synth.sample_missing"))

        cfg = {"__all__": {"ref_audio": audio, "ref_text": ref_text}}
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8",
        )
        json.dump(cfg, tmp, ensure_ascii=False, indent=2)
        tmp.close()
        return tmp.name

    # ── Manifest ──────────────────────────────────────────────────────────────

    def set_manifest(self, manifest_path: Path, output_dir: Path) -> None:
        """Set the manifest file and output directory."""
        self._manifest_path = manifest_path
        self._output_dir = output_dir
        self._manifest_label.setText(str(manifest_path))
        self._btn_start.setEnabled(True)
        self._load_chapters_from_manifest()

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
            self._load_chapters_from_manifest()

    def _load_chapters_from_manifest(self) -> None:
        """Parse manifest and populate chapter combo with real data."""
        if not self._manifest_path or not self._manifest_path.exists():
            return
        try:
            data = json.loads(self._manifest_path.read_text(encoding="utf-8"))
            chapter_chunks: dict[int, int] = {}
            for item in _iter_manifest_chunks(data):
                ch = item.get("chapter_index", 0)
                chapter_chunks[ch] = chapter_chunks.get(ch, 0) + 1
            self._chapter_map = chapter_chunks
            self._refresh_chapter_combo()
        except (json.JSONDecodeError, OSError, TypeError, AttributeError):
            pass

    def _refresh_chapter_combo(self) -> None:
        """Rebuild the chapter combo from loaded data."""
        self._chapter_combo.clear()
        total = sum(self._chapter_map.values())
        all_label = t("synth.all_chapters")
        if total:
            all_label += f"  ({total} " + t("synth.chunks_word") + ")"
        self._chapter_combo.addItem(all_label, 0)
        for ch_idx in sorted(self._chapter_map.keys()):
            cnt = self._chapter_map[ch_idx]
            label = t("synth.chapter_item", num=ch_idx + 1, chunks=cnt)
            self._chapter_combo.addItem(label, ch_idx + 1)

        if self._chapter_map:
            self._chapter_info.setText(
                t(
                    "synth.chapter_info",
                    chapters=len(self._chapter_map),
                    chunks=total,
                ),
            )
        else:
            self._chapter_info.setText("")

    # ── Synthesis control ─────────────────────────────────────────────────────

    def _start_synthesis(self) -> None:
        if not self._manifest_path or not self._output_dir:
            return

        selected = self._chapter_combo.currentData()
        chapter = selected if selected and selected > 0 else None

        try:
            clone_config_path = self._build_temp_sample_voice_config()
        except ValueError as exc:
            self._status.setText(str(exc))
            self._progress.set_status(str(exc))
            return

        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._progress.reset()

        self._worker = TTSSynthesisWorker(
            manifest_path=self._manifest_path,
            output_dir=self._output_dir,
            model=self._model_combo.currentText(),
            chapter=chapter,
            batch_size=self._batch_size.value(),
            resume=self._resume_check.isChecked(),
            chunk_timeout=self._chunk_timeout.value(),
            use_compile=self._compile_check.isChecked(),
            clone_config=clone_config_path,
            use_sage_attention=self._sage_check.isChecked(),
            models_dir=self._models_dir_edit.text().strip(),
            temperature=self._temperature_spin.value(),
            top_p=self._top_p_spin.value(),
            top_k=self._top_k_spin.value(),
            repetition_penalty=self._repetition_penalty_spin.value(),
            max_new_tokens=self._max_new_tokens_spin.value(),
            seed=self._seed_spin.value(),
            output_format=str(self._output_format_combo.currentData() or "flac"),
            merge_chapters=self._merge_chapters_check.isChecked(),
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.status.connect(self._on_status)
        self._worker.log_line.connect(self._on_log_line)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

        self._log_edit.clear()
        if self._output_dir:
            log_path = self._output_dir / "synthesis_log.txt"
            self._log_edit.appendPlainText(t("synth.log_path", path=str(log_path)))

        self._phase = "loading"
        self._phase_start = time.time()
        self._tick_timer.start()
        self._status.setText(t("synth.in_progress"))
        self._on_tick()

    def _stop_synthesis(self) -> None:
        self._tick_timer.stop()
        if self._worker:
            self._worker.cancel()
        self._btn_stop.setEnabled(False)

    # ── Signal handlers ───────────────────────────────────────────────────────

    def _on_log_line(self, line: str) -> None:
        self._log_edit.appendPlainText(line)
        sb = self._log_edit.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_tick(self) -> None:
        """Update elapsed time display every second."""
        elapsed = int(time.time() - self._phase_start)
        m, s = divmod(elapsed, 60)
        time_str = f"{m}:{s:02d}" if m else f"{s} сек"
        if self._phase == "loading":
            self._progress.set_busy(t("synth.loading_model") + f"  [{time_str}]")
        elif self._phase == "synth":
            self._progress.set_busy(t("synth.synthesizing") + f"  [{time_str}]")

    def _on_progress(
        self,
        current: int,
        total: int,
        eta: str,
        chapter: int = 0,
        chunk_chars: int = 0,
        chunk_sec: float = 0.0,
        remaining: int = 0,
        remaining_chars: int = 0,
        total_chars: int = 0,
    ) -> None:
        if self._phase == "loading":
            self._phase = "synth"
        self._tick_timer.stop()
        self._progress.set_progress(current, total, eta)
        parts = [t("synth.progress_done", current=current, total=total)]
        if remaining or (total - current) > 0:
            parts.append(t("synth.progress_remaining", n=remaining or (total - current)))
        if chunk_chars > 0 and chunk_sec > 0:
            parts.append(
                t("synth.progress_last_chunk", chars=chunk_chars, sec=chunk_sec),
            )
        if total_chars > 0 and remaining_chars >= 0:
            parts.append(
                t(
                    "synth.progress_chars",
                    done=total_chars - remaining_chars,
                    total=total_chars,
                    left=remaining_chars,
                ),
            )
        if eta:
            parts.append(t("synth.progress_eta", eta=eta))
        self._status.setText(" • ".join(parts))

    def _on_status(self, msg: str) -> None:
        if msg == "__loading__":
            self._phase = "loading"
            self._phase_start = time.time()
            self._tick_timer.start()
            self._on_tick()
        elif msg == "__model_ready__":
            elapsed = int(time.time() - self._phase_start)
            self._phase = "synth"
            self._phase_start = time.time()
            self._tick_timer.start()
            self._progress.set_busy(t("synth.model_ready", sec=elapsed))
        else:
            self._tick_timer.stop()
            self._progress.set_busy(msg)

    def _on_finished(self, output_dir: str, synthesized: int, skipped: int) -> None:
        self._tick_timer.stop()
        self._phase = "idle"
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._progress.set_progress(1, 1, "")
        self._status.setText(
            t(
                "synth.done_detail",
                synthesized=synthesized,
                skipped=skipped,
                path=output_dir,
            ),
        )

    def _on_error(self, msg: str) -> None:
        self._tick_timer.stop()
        self._phase = "idle"
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._progress.set_status(f"❌ {msg}")
