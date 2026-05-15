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
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QToolButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from book_normalizer.gui.i18n import t
from book_normalizer.gui.widgets.progress_widget import ProgressWidget
from book_normalizer.gui.workers.tts_worker import (
    TTSSynthesisWorker,
    VoicePromptSaveWorker,
)
from book_normalizer.tts.model_paths import default_comfyui_models_dir
from book_normalizer.tts.voice_library import (
    default_voice_library_dir,
    list_saved_voices,
    normalize_voice_library_dir,
)

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

_TEST_FRAGMENT_MAX_CHARS = 420
_TEST_CHUNK_LABEL_MAX_CHARS = 64


def _make_combo_compact(combo: QComboBox, min_chars: int = 18) -> None:
    """Keep long combo entries from increasing the whole page width."""
    combo.setMinimumContentsLength(min_chars)
    combo.setSizeAdjustPolicy(
        QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon,
    )
    combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


def _make_text_edit_compact(edit: QPlainTextEdit) -> None:
    """Wrap long lines and prevent horizontal scrolling inside text boxes."""
    edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
    edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)


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


def _shorten_test_fragment(text: str, max_chars: int = _TEST_FRAGMENT_MAX_CHARS) -> str:
    """Return a compact, sentence-ish fragment suitable for a quick TTS check."""
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= max_chars:
        return normalized

    sentence_cut = max(
        normalized.rfind(".", 0, max_chars),
        normalized.rfind("!", 0, max_chars),
        normalized.rfind("?", 0, max_chars),
    )
    if sentence_cut >= 120:
        return normalized[: sentence_cut + 1].strip()

    word_cut = normalized.rfind(" ", 0, max_chars)
    if word_cut >= 120:
        return normalized[:word_cut].strip() + "..."

    return normalized[:max_chars].strip() + "..."


def _build_test_manifest_chunks(data: object, chapter: int | None = None) -> list[dict]:
    """Pick one non-empty manifest chunk and trim it for preview synthesis.

    ``chapter`` is 1-based to match the GUI combo and CLI argument.
    """
    chunks = _iter_manifest_chunks(data)
    if chapter is not None:
        target = chapter - 1
        chunks = [c for c in chunks if int(c.get("chapter_index", 0)) == target]

    for chunk in chunks:
        text = _shorten_test_fragment(str(chunk.get("text") or ""))
        if not text:
            continue
        preview = dict(chunk)
        preview["text"] = text
        preview["chapter_index"] = int(preview.get("chapter_index", 0))
        preview["chunk_index"] = 0
        preview["voice_id"] = str(preview.get("voice_id") or "narrator_calm")
        return [preview]

    return []


def _role_for_voice_id(voice_id: str) -> str:
    """Infer a manifest role from a Qwen voice preset id."""
    normalized = (voice_id or "").strip().lower()
    if normalized.startswith("male_") or normalized in {"male", "men"}:
        return "male"
    if normalized.startswith("female_") or normalized in {"female", "women"}:
        return "female"
    return "narrator"


def _chunk_preview_text(text: str, max_chars: int = _TEST_CHUNK_LABEL_MAX_CHARS) -> str:
    """Return a single-line preview for chunk selectors."""
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rstrip() + "..."


def _test_manifest_chunk_from_chunk(chunk: dict) -> dict:
    """Build a single-chunk preview manifest entry from an existing chunk."""
    preview = dict(chunk)
    preview["text"] = str(preview.get("text") or "").strip()
    preview["chapter_index"] = int(preview.get("chapter_index", 0))
    preview["chunk_index"] = int(preview.get("chunk_index", 0))
    voice_id = str(preview.get("voice_id") or "narrator_calm")
    preview["voice_id"] = voice_id
    preview["role"] = str(preview.get("role") or _role_for_voice_id(voice_id))
    return preview


def _test_manifest_chunk_from_text(text: str, voice_id: str) -> dict:
    """Build a one-off preview manifest entry from manually entered text."""
    selected_voice = voice_id or "narrator_calm"
    return {
        "chapter_index": 0,
        "chunk_index": 0,
        "role": _role_for_voice_id(selected_voice),
        "voice_id": selected_voice,
        "text": text.strip(),
    }


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
        self._voice_combo.setMinimumWidth(128)
        _make_combo_compact(self._voice_combo, min_chars=14)
        row1.addWidget(self._voice_combo)

        self._wav_edit = QLineEdit()
        self._wav_edit.setPlaceholderText("reference.wav")
        self._wav_edit.setReadOnly(True)
        self._wav_edit.setStyleSheet(
            "color: rgba(226,232,240,0.78); font-size: 11px; padding: 4px 6px;"
            "background: rgba(15,23,42,0.72); border-radius: 6px;"
            "border: 1px solid rgba(148,163,184,0.16);",
        )
        row1.addWidget(self._wav_edit, stretch=1)

        self._btn_wav = QPushButton("WAV…")
        self._btn_wav.setText("WAV...")
        self._btn_wav.setMaximumWidth(72)
        self._btn_wav.clicked.connect(self._browse_wav)
        row1.addWidget(self._btn_wav)

        self._btn_remove = QPushButton("✕")
        self._btn_remove.setText("x")
        self._btn_remove.setMaximumWidth(34)
        self._btn_remove.setStyleSheet(
            "QPushButton { color: rgba(252,165,165,0.86); font-weight: 700;"
            "background: rgba(239,68,68,0.08); border: 1px solid rgba(248,113,113,0.16);"
            "border-radius: 7px; padding: 2px; }"
            "QPushButton:hover { color: #ffffff; background: rgba(239,68,68,0.24); }",
        )
        self._btn_remove.clicked.connect(self._on_remove)
        row1.addWidget(self._btn_remove)

        layout.addLayout(row1)

        # Row 2: transcript text field.
        self._transcript = QLineEdit()
        self._transcript.setStyleSheet(
            "color: rgba(226,232,240,0.78); font-size: 11px; padding: 4px 6px;"
            "background: rgba(15,23,42,0.72); border-radius: 6px;"
            "border: 1px solid rgba(148,163,184,0.16);",
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
        self._save_voice_worker: VoicePromptSaveWorker | None = None
        self._chapter_map: dict[int, int] = {}
        self._manifest_chunks: list[dict] = []
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
        self._test_audio = QAudioOutput(self)
        self._test_audio.setVolume(0.8)
        self._test_player = QMediaPlayer(self)
        self._test_player.setAudioOutput(self._test_audio)
        self._test_player.playbackStateChanged.connect(self._on_test_playback_state)
        self._help_buttons: list[tuple[QToolButton, str]] = []
        self._voice_mode = "custom"
        self._saved_voices = []
        self._run_kind = "idle"
        self._preview_output_dir: Path | None = None
        self._last_test_audio_path: Path | None = None
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
        scroll.horizontalScrollBar().setEnabled(False)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setMinimumWidth(0)
        container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
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
            "background: rgba(15,23,42,0.62); border: 1px solid rgba(148,163,184,0.12);"
            "border-radius: 8px;",
        )
        file_row.addWidget(self._manifest_label, stretch=1)

        self._btn_load = QPushButton()
        self._btn_load.clicked.connect(self._browse_manifest)
        file_row.addWidget(self._btn_load)
        layout.addLayout(file_row)

        # ── Main settings form ────────────────────────────────────────────
        self._mode_tabs = QTabWidget()
        self._mode_tabs.setObjectName("synthesisModeTabs")
        self._mode_tabs.currentChanged.connect(self._on_mode_changed)
        self._mode_tabs.addTab(self._build_sample_voice_panel(), "")
        self._mode_tabs.addTab(self._build_preset_speakers_tab(), "")
        self._mode_tabs.addTab(self._build_advanced_tab(), "")
        layout.addWidget(self._mode_tabs)
        layout.addWidget(self._build_test_fragment_panel())


        # ── Action buttons ────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_test = QPushButton()
        self._btn_test.setObjectName("primaryBtn")
        self._btn_test.setMinimumHeight(38)
        self._btn_test.clicked.connect(self._start_test_synthesis)
        self._btn_test.setEnabled(False)
        btn_row.addWidget(self._btn_test)

        self._btn_play_test = QPushButton()
        self._btn_play_test.setMinimumHeight(38)
        self._btn_play_test.clicked.connect(self._toggle_test_playback)
        self._btn_play_test.setEnabled(False)
        btn_row.addWidget(self._btn_play_test)

        self._btn_start = QPushButton()
        self._btn_start.setObjectName("successBtn")
        self._btn_start.setMinimumHeight(38)
        self._btn_start.clicked.connect(self._start_synthesis)
        self._btn_start.setEnabled(False)
        btn_row.addWidget(self._btn_start)

        self._btn_stop = QPushButton()
        self._btn_stop.setObjectName("dangerBtn")
        self._btn_stop.setMinimumHeight(38)
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
        self._log_edit.setMaximumHeight(104)
        _make_text_edit_compact(self._log_edit)
        self._log_edit.setStyleSheet(
            "font-family: 'Cascadia Code', Consolas, monospace;"
            "font-size: 11px; background: rgba(9,14,24,0.86);"
            "border: 1px solid rgba(148,163,184,0.12); border-radius: 8px; padding: 6px;",
        )
        bottom.addWidget(self._log_edit)

        self._status = QLabel()
        self._status.setWordWrap(True)
        self._status.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse,
        )
        self._status.setStyleSheet(
            "color: rgba(226,232,240,0.62); font-size: 12px; padding: 2px 0;",
        )
        bottom.addWidget(self._status)

        outer.addLayout(bottom)

        self.retranslate()
        self._refresh_saved_voices()
        self._update_custom_voice_controls()

    def _build_test_fragment_panel(self) -> QFrame:
        """Build controls for selecting the exact preview text."""
        frame = QFrame()
        frame.setObjectName("testFragmentPanel")
        frame.setStyleSheet(
            "QFrame#testFragmentPanel {"
            "  background: rgba(15,23,42,0.72);"
            "  border: 1px solid rgba(148,163,184,0.14);"
            "  border-radius: 12px;"
            "}"
        )
        outer = QVBoxLayout(frame)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(8)

        self._test_source_title = QLabel()
        self._test_source_title.setStyleSheet(
            "font-weight: 800; font-size: 13px; color: #ddd6fe;",
        )
        outer.addWidget(self._test_source_title)

        self._test_source_desc = QLabel()
        self._test_source_desc.setWordWrap(True)
        self._test_source_desc.setStyleSheet(
            "color: rgba(226,232,240,0.62); font-size: 11px;",
        )
        outer.addWidget(self._test_source_desc)

        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(7)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)

        self._test_source_combo = QComboBox()
        _make_combo_compact(self._test_source_combo, min_chars=18)
        self._test_source_combo.currentIndexChanged.connect(
            self._update_test_source_controls,
        )
        self._test_source_label = QLabel()
        form.addRow(
            self._label_with_help(
                self._test_source_label,
                "synth.test_source_help",
            ),
            self._test_source_combo,
        )

        chunk_row = QHBoxLayout()
        chunk_row.setSpacing(6)
        self._test_chapter_combo = QComboBox()
        _make_combo_compact(self._test_chapter_combo, min_chars=14)
        self._test_chapter_combo.currentIndexChanged.connect(
            self._refresh_test_chunk_combo,
        )
        chunk_row.addWidget(self._test_chapter_combo)
        self._test_chunk_combo = QComboBox()
        _make_combo_compact(self._test_chunk_combo, min_chars=20)
        self._test_chunk_combo.currentIndexChanged.connect(
            self._update_test_chunk_preview,
        )
        chunk_row.addWidget(self._test_chunk_combo, stretch=1)
        self._test_chunk_controls = QWidget()
        self._test_chunk_controls.setLayout(chunk_row)
        self._test_chunk_label = QLabel()
        form.addRow(self._test_chunk_label, self._test_chunk_controls)

        self._test_voice_combo = QComboBox()
        self._test_voice_combo.addItems(VOICE_IDS)
        _make_combo_compact(self._test_voice_combo, min_chars=18)
        self._test_voice_label = QLabel()
        form.addRow(self._test_voice_label, self._test_voice_combo)

        self._test_chunk_preview = QPlainTextEdit()
        self._test_chunk_preview.setReadOnly(True)
        self._test_chunk_preview.setMaximumHeight(94)
        _make_text_edit_compact(self._test_chunk_preview)
        self._test_chunk_preview.setStyleSheet(
            "color: rgba(226,232,240,0.76); font-size: 12px;"
        )
        self._test_custom_text_edit = QPlainTextEdit()
        self._test_custom_text_edit.setMaximumHeight(118)
        _make_text_edit_compact(self._test_custom_text_edit)
        self._test_text_stack = QStackedWidget()
        self._test_text_stack.setMinimumWidth(0)
        self._test_text_stack.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        self._test_text_stack.addWidget(self._test_chunk_preview)
        self._test_text_stack.addWidget(self._test_custom_text_edit)
        self._test_text_label = QLabel()
        form.addRow(self._test_text_label, self._test_text_stack)

        outer.addLayout(form)
        return frame

    def _build_sample_voice_panel(self) -> QFrame:
        """Build the direct CustomVoice sample panel."""
        frame = QFrame()
        frame.setObjectName("sampleVoicePanel")
        frame.setStyleSheet(
            "QFrame#sampleVoicePanel {"
            "  background: rgba(18,24,36,0.94);"
            "  border: 1px solid rgba(139,92,246,0.24);"
            "  border-radius: 14px;"
            "}"
        )
        outer = QVBoxLayout(frame)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(9)

        self._sample_title = QLabel()
        self._sample_title.setStyleSheet(
            "font-weight: 800; font-size: 14px; color: #ddd6fe;"
        )
        outer.addWidget(self._sample_title)

        self._sample_desc = QLabel()
        self._sample_desc.setWordWrap(True)
        self._sample_desc.setStyleSheet(
            "color: rgba(226,232,240,0.62); font-size: 11px;"
        )
        outer.addWidget(self._sample_desc)

        mode_form = QFormLayout()
        mode_form.setHorizontalSpacing(14)
        mode_form.setVerticalSpacing(6)
        mode_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        mode_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)

        self._custom_strategy_combo = QComboBox()
        _make_combo_compact(self._custom_strategy_combo, min_chars=20)
        self._custom_strategy_combo.currentIndexChanged.connect(
            self._update_custom_voice_controls,
        )
        self._custom_strategy_label = QLabel()
        mode_form.addRow(self._custom_strategy_label, self._custom_strategy_combo)

        saved_row = QHBoxLayout()
        saved_row.setSpacing(6)
        self._saved_voice_combo = QComboBox()
        _make_combo_compact(self._saved_voice_combo, min_chars=22)
        self._saved_voice_combo.currentIndexChanged.connect(
            self._apply_selected_saved_voice_rate,
        )
        saved_row.addWidget(self._saved_voice_combo, stretch=1)
        self._btn_refresh_saved_voices = QPushButton()
        self._btn_refresh_saved_voices.clicked.connect(self._refresh_saved_voices)
        saved_row.addWidget(self._btn_refresh_saved_voices)
        self._saved_voice_label = QLabel()
        mode_form.addRow(self._saved_voice_label, saved_row)

        outer.addLayout(mode_form)

        self._role_mapping_widget = QWidget()
        role_form = QFormLayout(self._role_mapping_widget)
        role_form.setHorizontalSpacing(14)
        role_form.setVerticalSpacing(6)
        role_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        role_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self._role_voice_combos: dict[str, QComboBox] = {}
        self._role_voice_labels: dict[str, QLabel] = {}
        for role in ("narrator", "male", "female"):
            combo = QComboBox()
            _make_combo_compact(combo, min_chars=22)
            self._role_voice_combos[role] = combo
            label = QLabel()
            self._role_voice_labels[role] = label
            role_form.addRow(label, combo)
        outer.addWidget(self._role_mapping_widget)

        self._sample_fields = QWidget()
        form = QFormLayout(self._sample_fields)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(6)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)

        audio_row = QHBoxLayout()
        audio_row.setSpacing(6)
        self._sample_audio_edit = QLineEdit()
        self._sample_audio_edit.setReadOnly(True)
        audio_row.addWidget(self._sample_audio_edit, stretch=1)
        self._btn_sample_audio = QPushButton()
        self._btn_sample_audio.clicked.connect(self._browse_sample_audio)
        audio_row.addWidget(self._btn_sample_audio)
        self._sample_audio_label = QLabel()
        form.addRow(
            self._label_with_help(self._sample_audio_label, "synth.sample_audio_help"),
            audio_row,
        )

        playback_row = QHBoxLayout()
        playback_row.setSpacing(8)
        self._btn_sample_play = QPushButton()
        self._btn_sample_play.setEnabled(False)
        self._btn_sample_play.clicked.connect(self._toggle_sample_playback)
        playback_row.addWidget(self._btn_sample_play)
        self._sample_duration_label = QLabel("0:00 / 0:00")
        self._sample_duration_label.setStyleSheet(
            "color: rgba(226,232,240,0.76); font-size: 12px;"
        )
        playback_row.addWidget(self._sample_duration_label)
        playback_row.addStretch()
        self._sample_player.durationChanged.connect(self._on_sample_duration_changed)
        self._sample_player.positionChanged.connect(self._on_sample_position_changed)
        self._sample_player.playbackStateChanged.connect(self._on_sample_playback_state)
        self._sample_preview_label = QLabel()
        form.addRow(
            self._label_with_help(self._sample_preview_label, "synth.sample_preview_help"),
            playback_row,
        )

        self._sample_transcript_edit = QPlainTextEdit()
        self._sample_transcript_edit.setMaximumHeight(110)
        _make_text_edit_compact(self._sample_transcript_edit)
        self._sample_transcript_label = QLabel()
        form.addRow(
            self._label_with_help(
                self._sample_transcript_label,
                "synth.sample_transcript_help",
            ),
            self._sample_transcript_edit,
        )

        save_row = QHBoxLayout()
        save_row.setSpacing(6)
        self._voice_name_edit = QLineEdit()
        self._voice_name_edit.setPlaceholderText("voice_name")
        save_row.addWidget(self._voice_name_edit, stretch=1)
        self._btn_save_sample_voice = QPushButton()
        self._btn_save_sample_voice.clicked.connect(self._save_sample_voice)
        save_row.addWidget(self._btn_save_sample_voice)
        self._save_voice_label = QLabel()
        form.addRow(self._save_voice_label, save_row)

        outer.addWidget(self._sample_fields)

        self._voice_tuning_toggle = QToolButton()
        self._voice_tuning_toggle.setCheckable(True)
        self._voice_tuning_toggle.setProperty("secondaryToggle", True)
        self._voice_tuning_toggle.toggled.connect(self._on_voice_tuning_toggled)
        outer.addWidget(self._voice_tuning_toggle)

        self._voice_tuning_panel = QWidget()
        controls = QFormLayout(self._voice_tuning_panel)
        controls.setHorizontalSpacing(14)
        controls.setVerticalSpacing(6)
        controls.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        controls.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)

        self._temperature_spin = QDoubleSpinBox()
        self._temperature_spin.setRange(0.1, 2.0)
        self._temperature_spin.setSingleStep(0.05)
        self._temperature_spin.setDecimals(2)
        self._temperature_spin.setValue(1.0)
        self._temperature_label = QLabel()
        controls.addRow(
            self._label_with_help(self._temperature_label, "synth.temperature_help"),
            self._temperature_spin,
        )

        self._top_p_spin = QDoubleSpinBox()
        self._top_p_spin.setRange(0.1, 1.0)
        self._top_p_spin.setSingleStep(0.05)
        self._top_p_spin.setDecimals(2)
        self._top_p_spin.setValue(0.80)
        self._top_p_label = QLabel()
        controls.addRow(
            self._label_with_help(self._top_p_label, "synth.top_p_help"),
            self._top_p_spin,
        )

        self._top_k_spin = QSpinBox()
        self._top_k_spin.setRange(1, 200)
        self._top_k_spin.setValue(20)
        self._top_k_label = QLabel()
        controls.addRow(
            self._label_with_help(self._top_k_label, "synth.top_k_help"),
            self._top_k_spin,
        )

        self._repetition_penalty_spin = QDoubleSpinBox()
        self._repetition_penalty_spin.setRange(0.8, 2.0)
        self._repetition_penalty_spin.setSingleStep(0.01)
        self._repetition_penalty_spin.setDecimals(2)
        self._repetition_penalty_spin.setValue(1.05)
        self._repetition_penalty_label = QLabel()
        controls.addRow(
            self._label_with_help(
                self._repetition_penalty_label,
                "synth.repetition_penalty_help",
            ),
            self._repetition_penalty_spin,
        )

        self._max_new_tokens_spin = QSpinBox()
        self._max_new_tokens_spin.setRange(128, 8192)
        self._max_new_tokens_spin.setSingleStep(128)
        self._max_new_tokens_spin.setValue(2048)
        self._max_new_tokens_label = QLabel()
        controls.addRow(
            self._label_with_help(
                self._max_new_tokens_label,
                "synth.max_new_tokens_help",
            ),
            self._max_new_tokens_spin,
        )

        speech_rate_row = QHBoxLayout()
        speech_rate_row.setSpacing(8)
        self._speech_rate_slider = QSlider(Qt.Orientation.Horizontal)
        self._speech_rate_slider.setRange(50, 150)
        self._speech_rate_slider.setSingleStep(5)
        self._speech_rate_slider.setPageStep(5)
        self._speech_rate_slider.setTickInterval(10)
        self._speech_rate_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._speech_rate_slider.setValue(100)
        self._speech_rate_slider.valueChanged.connect(
            self._on_speech_rate_changed,
        )
        speech_rate_row.addWidget(self._speech_rate_slider, stretch=1)
        self._speech_rate_value_label = QLabel("1.00x")
        self._speech_rate_value_label.setMinimumWidth(96)
        self._speech_rate_value_label.setStyleSheet(
            "color: rgba(226,232,240,0.76); font-size: 12px;"
        )
        speech_rate_row.addWidget(self._speech_rate_value_label)
        self._speech_rate_label = QLabel()
        controls.addRow(
            self._label_with_help(
                self._speech_rate_label,
                "synth.speech_rate_help",
            ),
            speech_rate_row,
        )

        self._seed_spin = QSpinBox()
        self._seed_spin.setRange(-1, 2_147_483_647)
        self._seed_spin.setValue(-1)
        self._seed_spin.setSpecialValueText("-1 (random)")
        self._seed_label = QLabel()
        controls.addRow(
            self._label_with_help(self._seed_label, "synth.seed_help"),
            self._seed_spin,
        )

        outer.addWidget(self._voice_tuning_panel)
        self._voice_tuning_panel.setVisible(False)

        self._sample_status = QLabel()
        self._sample_status.setWordWrap(True)
        self._sample_status.setStyleSheet(
            "color: rgba(226,232,240,0.62); font-size: 11px;"
        )
        outer.addWidget(self._sample_status)
        return frame

    def _build_preset_speakers_tab(self) -> QWidget:
        """Build the built-in speaker synthesis mode."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        self._preset_title = QLabel()
        self._preset_title.setStyleSheet(
            "font-weight: 800; font-size: 14px; color: #ddd6fe;"
        )
        layout.addWidget(self._preset_title)

        self._preset_desc = QLabel()
        self._preset_desc.setWordWrap(True)
        self._preset_desc.setStyleSheet(
            "color: rgba(226,232,240,0.62); font-size: 11px;"
        )
        layout.addWidget(self._preset_desc)

        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(8)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self._model_combo = QComboBox()
        self._model_combo.addItems(MODELS[:2])
        _make_combo_compact(self._model_combo, min_chars=24)
        self._model_label = QLabel()
        form.addRow(
            self._label_with_help(self._model_label, "synth.model_help"),
            self._model_combo,
        )
        layout.addLayout(form)
        layout.addStretch()
        return tab

    def _build_advanced_tab(self) -> QWidget:
        """Build advanced settings shared by all synthesis modes."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        self._advanced_title = QLabel()
        self._advanced_title.setStyleSheet(
            "font-weight: 800; font-size: 14px; color: #ddd6fe;"
        )
        layout.addWidget(self._advanced_title)

        self._advanced_desc = QLabel()
        self._advanced_desc.setWordWrap(True)
        self._advanced_desc.setStyleSheet(
            "color: rgba(226,232,240,0.62); font-size: 11px;"
        )
        layout.addWidget(self._advanced_desc)

        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(8)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)

        model_dir_row = QHBoxLayout()
        model_dir_row.setSpacing(6)
        self._models_dir_edit = QLineEdit(str(default_comfyui_models_dir()))
        self._models_dir_edit.setMinimumWidth(180)
        model_dir_row.addWidget(self._models_dir_edit, stretch=1)
        self._btn_models_dir = QPushButton()
        self._btn_models_dir.clicked.connect(self._browse_models_dir)
        model_dir_row.addWidget(self._btn_models_dir)
        self._models_dir_label = QLabel()
        form.addRow(
            self._label_with_help(self._models_dir_label, "synth.models_dir_help"),
            model_dir_row,
        )

        voice_lib_row = QHBoxLayout()
        voice_lib_row.setSpacing(6)
        self._voice_library_dir_edit = QLineEdit(str(default_voice_library_dir()))
        self._voice_library_dir_edit.setMinimumWidth(180)
        self._voice_library_dir_edit.editingFinished.connect(self._refresh_saved_voices)
        voice_lib_row.addWidget(self._voice_library_dir_edit, stretch=1)
        self._btn_voice_library_dir = QPushButton()
        self._btn_voice_library_dir.clicked.connect(self._browse_voice_library_dir)
        voice_lib_row.addWidget(self._btn_voice_library_dir)
        self._voice_library_dir_label = QLabel()
        form.addRow(
            self._label_with_help(
                self._voice_library_dir_label,
                "synth.voice_library_dir_help",
            ),
            voice_lib_row,
        )

        self._output_format_combo = QComboBox()
        self._output_format_combo.addItem("FLAC", "flac")
        self._output_format_combo.addItem("WAV", "wav")
        _make_combo_compact(self._output_format_combo, min_chars=8)
        self._output_format_label = QLabel()
        form.addRow(
            self._label_with_help(self._output_format_label, "synth.output_format_help"),
            self._output_format_combo,
        )

        self._merge_chapters_check = QCheckBox()
        self._merge_chapters_check.setChecked(True)
        self._merge_chapters_label = QLabel()
        form.addRow(
            self._label_with_help(self._merge_chapters_label, "synth.merge_chapters_help"),
            self._merge_chapters_check,
        )

        self._chapter_combo = QComboBox()
        self._chapter_combo.setMinimumWidth(150)
        _make_combo_compact(self._chapter_combo, min_chars=16)
        self._chapter_label = QLabel()
        form.addRow(
            self._label_with_help(self._chapter_label, "synth.chapter_help"),
            self._chapter_combo,
        )

        self._resume_check = QCheckBox()
        self._resume_label = QLabel()
        form.addRow(
            self._label_with_help(self._resume_label, "synth.resume_help"),
            self._resume_check,
        )

        self._batch_size = QSpinBox()
        self._batch_size.setRange(1, 8)
        self._batch_size.setValue(1)
        self._batch_size.setMaximumWidth(140)
        self._batch_label = QLabel()
        form.addRow(
            self._label_with_help(self._batch_label, "synth.batch_help"),
            self._batch_size,
        )

        self._chunk_timeout = QSpinBox()
        self._chunk_timeout.setRange(30, 1800)
        self._chunk_timeout.setValue(300)
        self._chunk_timeout.setSingleStep(30)
        self._chunk_timeout.setSuffix(" s")
        self._chunk_timeout.setMaximumWidth(150)
        self._chunk_timeout_label = QLabel()
        form.addRow(
            self._label_with_help(
                self._chunk_timeout_label,
                "synth.chunk_timeout_help",
            ),
            self._chunk_timeout,
        )

        self._compile_check = QCheckBox()
        self._compile_label = QLabel()
        form.addRow(
            self._label_with_help(self._compile_label, "synth.compile_help"),
            self._compile_check,
        )

        self._sage_check = QCheckBox()
        self._sage_label = QLabel()
        form.addRow(
            self._label_with_help(self._sage_label, "synth.sage_help"),
            self._sage_check,
        )

        layout.addLayout(form)
        self._chapter_info = QLabel()
        self._chapter_info.setStyleSheet(
            "color: rgba(226,232,240,0.48); font-size: 11px;"
        )
        layout.addWidget(self._chapter_info)
        layout.addStretch()
        return tab

    def _label_with_help(self, label: QLabel, help_key: str) -> QWidget:
        """Return a compact form label with a hover help button."""
        wrap = QWidget()
        row = QHBoxLayout(wrap)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.addWidget(label)
        row.addWidget(self._help_button(help_key))
        row.addStretch()
        return wrap

    def _help_button(self, help_key: str) -> QToolButton:
        btn = QToolButton()
        btn.setText("?")
        btn.setProperty("helpButton", True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setMinimumSize(20, 20)
        btn.setMaximumSize(24, 24)
        btn.setToolTip(t(help_key))
        btn.setStatusTip(t(help_key))
        btn.setToolTipDuration(12000)
        btn.clicked.connect(
            lambda _checked=False, b=btn, key=help_key: self._show_help_tooltip(b, key),
        )
        self._help_buttons.append((btn, help_key))
        return btn

    def _show_help_tooltip(self, button: QToolButton, help_key: str) -> None:
        """Show help text immediately on click as well as on hover."""

        text = t(help_key)
        button.setToolTip(text)
        QToolTip.showText(
            button.mapToGlobal(button.rect().bottomRight()),
            text,
            button,
            button.rect(),
            12000,
        )

    def _on_voice_tuning_toggled(self, checked: bool) -> None:
        """Show or hide advanced voice generation controls."""
        self._voice_tuning_panel.setVisible(checked)
        self._update_voice_tuning_toggle_text()

    def _update_voice_tuning_toggle_text(self) -> None:
        """Update the collapsed/expanded label for tuning controls."""
        key = (
            "synth.voice_tuning_hide"
            if self._voice_tuning_toggle.isChecked()
            else "synth.voice_tuning_show"
        )
        self._voice_tuning_toggle.setText(t(key))

    def _speech_rate_value(self) -> float:
        """Return the selected speech rate multiplier."""
        return self._speech_rate_slider.value() / 100.0

    def _set_speech_rate_value(self, value: float) -> None:
        """Set speech rate slider from a saved voice or default."""
        bounded = min(1.50, max(0.50, float(value or 1.0)))
        self._speech_rate_slider.setValue(int(round(bounded * 100)))

    def _on_speech_rate_changed(self, _value: int) -> None:
        rate = self._speech_rate_value()
        if rate < 0.97:
            label_key = "synth.speech_rate_slow"
        elif rate > 1.03:
            label_key = "synth.speech_rate_fast"
        else:
            label_key = "synth.speech_rate_normal"
        self._speech_rate_value_label.setText(f"{rate:.2f}x  {t(label_key)}")
        self._test_player.setPlaybackRate(rate)

    def _saved_voice_rate(self, voice_id: str) -> float | None:
        for voice in self._saved_voices:
            if voice.voice_id == voice_id:
                return voice.speech_rate
        return None

    def _apply_selected_saved_voice_rate(self) -> None:
        """Load the saved rate for the globally selected voice."""
        voice_id = self._selected_saved_voice()
        rate = self._saved_voice_rate(voice_id)
        if rate is not None:
            self._set_speech_rate_value(rate)

    def _build_clone_panel(self) -> QFrame:
        """Build the voice cloning expandable panel."""
        frame = QFrame()
        frame.setObjectName("clonePanel")
        frame.setStyleSheet(
            "QFrame#clonePanel {"
            "  background: rgba(16,185,129,0.08);"
            "  border: 1px solid rgba(45,212,191,0.22);"
            "  border-radius: 14px;"
            "  padding: 0px;"
            "}"
        )
        outer = QVBoxLayout(frame)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(8)

        # Header row: checkbox + title.
        header = QHBoxLayout()
        self._clone_enable = QCheckBox()
        self._clone_enable.toggled.connect(self._on_clone_toggled)
        header.addWidget(self._clone_enable)

        self._clone_title = QLabel()
        self._clone_title.setStyleSheet(
            "font-weight: 800; font-size: 14px; color: #99f6e4;"
        )
        header.addWidget(self._clone_title, stretch=1)
        outer.addLayout(header)

        # Explanation label.
        self._clone_desc = QLabel()
        self._clone_desc.setWordWrap(True)
        self._clone_desc.setStyleSheet(
            "color: rgba(226,232,240,0.58); font-size: 11px; padding: 0 0 4px 0;"
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
            "color: rgba(226,232,240,0.42); font-size: 10px; font-weight: 600;"
        )
        lbl_role.setMinimumWidth(128)
        lbl_role.setMaximumWidth(180)
        col_header.addWidget(lbl_role)
        lbl_wav = QLabel()
        lbl_wav.setObjectName("cloneColWav")
        lbl_wav.setStyleSheet(
            "color: rgba(226,232,240,0.42); font-size: 10px; font-weight: 600;"
        )
        col_header.addWidget(lbl_wav, stretch=1)
        col_header.addSpacing(72 + 34 + 6)  # WAV btn + remove btn width.
        body_layout.addLayout(col_header)

        # Separator.
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(148,163,184,0.12);")
        body_layout.addWidget(sep)

        # Transcript column hint.
        col_transcript = QLabel()
        col_transcript.setObjectName("cloneColTranscript")
        col_transcript.setStyleSheet(
            "color: rgba(226,232,240,0.42); font-size: 10px; padding: 0 0 2px 0;"
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
            "  background: rgba(16,185,129,0.14);"
            "  color: #99f6e4;"
            "  border: 1px dashed rgba(45,212,191,0.45);"
            "  border-radius: 8px; padding: 5px 14px; font-size: 12px;"
            "}"
            "QPushButton:hover { background: rgba(16,185,129,0.24); }"
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
        self._mode_tabs.setTabText(0, t("synth.mode_custom_voice"))
        self._mode_tabs.setTabText(1, t("synth.mode_preset_speakers"))
        self._mode_tabs.setTabText(2, t("synth.mode_advanced"))

        self._model_label.setText(t("synth.model"))
        self._model_combo.setToolTip(t("synth.model_help"))
        self._models_dir_label.setText(t("synth.models_dir"))
        self._models_dir_edit.setToolTip(t("synth.models_dir_help"))
        self._btn_models_dir.setText(t("synth.choose_dir"))
        self._voice_library_dir_label.setText(t("synth.voice_library_dir"))
        self._voice_library_dir_edit.setToolTip(t("synth.voice_library_dir_help"))
        self._btn_voice_library_dir.setText(t("synth.choose_dir"))
        self._batch_label.setText(t("synth.batch_size"))
        self._batch_size.setToolTip(t("synth.batch_help"))
        self._chunk_timeout_label.setText(t("synth.chunk_timeout"))
        self._chunk_timeout.setToolTip(t("synth.chunk_timeout_help"))
        self._output_format_label.setText(t("synth.output_format"))
        self._merge_chapters_label.setText(t("synth.merge_chapters"))
        self._merge_chapters_check.setText(t("synth.merge_chapters_check"))
        self._chapter_label.setText(t("synth.chapter"))
        self._resume_label.setText(t("synth.resume"))
        self._resume_check.setText(t("synth.resume_check"))
        self._compile_label.setText(t("synth.compile"))
        self._compile_check.setText(t("synth.compile_check"))
        self._sage_label.setText(t("synth.sage_attention"))
        self._sage_check.setText(t("synth.sage_check"))

        self._sample_title.setText(t("synth.sample_title"))
        self._sample_desc.setText(t("synth.sample_desc"))
        self._update_voice_tuning_toggle_text()
        self._populate_custom_strategy_combo()
        self._custom_strategy_label.setText(t("synth.custom_strategy"))
        self._saved_voice_label.setText(t("synth.saved_voice"))
        self._btn_refresh_saved_voices.setText(t("synth.refresh_saved_voices"))
        self._role_voice_labels["narrator"].setText(t("synth.role_narrator"))
        self._role_voice_labels["male"].setText(t("synth.role_male"))
        self._role_voice_labels["female"].setText(t("synth.role_female"))
        self._sample_audio_label.setText(t("synth.sample_audio"))
        self._btn_sample_audio.setText(t("synth.browse_audio"))
        self._sample_preview_label.setText(t("synth.sample_preview"))
        self._btn_sample_play.setText(t("synth.sample_play"))
        self._sample_transcript_label.setText(t("synth.sample_transcript"))
        self._sample_transcript_edit.setPlaceholderText(
            t("synth.clone_transcript_ph"),
        )
        self._save_voice_label.setText(t("synth.saved_voice_name"))
        self._btn_save_sample_voice.setText(t("synth.save_local_voice"))
        self._temperature_label.setText(t("synth.temperature"))
        self._top_p_label.setText(t("synth.top_p"))
        self._top_k_label.setText(t("synth.top_k"))
        self._repetition_penalty_label.setText(t("synth.repetition_penalty"))
        self._max_new_tokens_label.setText(t("synth.max_new_tokens"))
        self._speech_rate_label.setText(t("synth.speech_rate"))
        self._seed_label.setText(t("synth.seed"))
        self._temperature_spin.setToolTip(t("synth.temperature_help"))
        self._top_p_spin.setToolTip(t("synth.top_p_help"))
        self._top_k_spin.setToolTip(t("synth.top_k_help"))
        self._repetition_penalty_spin.setToolTip(t("synth.repetition_penalty_help"))
        self._max_new_tokens_spin.setToolTip(t("synth.max_new_tokens_help"))
        self._speech_rate_slider.setToolTip(t("synth.speech_rate_help"))
        self._seed_spin.setToolTip(t("synth.seed_help"))
        self._on_speech_rate_changed(self._speech_rate_slider.value())
        self._test_source_title.setText(t("synth.test_source_title"))
        self._test_source_desc.setText(t("synth.test_source_desc"))
        self._test_source_label.setText(t("synth.test_source"))
        self._test_chunk_label.setText(t("synth.test_chunk"))
        self._test_voice_label.setText(t("synth.test_voice"))
        self._test_custom_text_edit.setPlaceholderText(
            t("synth.test_custom_placeholder"),
        )
        self._populate_test_source_combo()
        self._refresh_test_chapter_combo()
        if not self._sample_status.text():
            self._sample_status.setText(t("synth.sample_idle"))
        self._preset_title.setText(t("synth.preset_title"))
        self._preset_desc.setText(t("synth.preset_desc"))
        self._advanced_title.setText(t("synth.advanced_title"))
        self._advanced_desc.setText(t("synth.advanced_desc"))
        for btn, help_key in self._help_buttons:
            btn.setToolTip(t(help_key))
            btn.setStatusTip(t(help_key))

        self._btn_test.setText(t("synth.test_start"))
        self._btn_test.setToolTip(t("synth.test_help"))
        self._btn_play_test.setText(t("synth.test_play"))
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

    # Saved/sample voice logic

    def _populate_custom_strategy_combo(self) -> None:
        """Populate Custom Voice strategy choices without losing selection."""
        current = self._custom_strategy_combo.currentData() or "sample_all"
        self._custom_strategy_combo.blockSignals(True)
        self._custom_strategy_combo.clear()
        self._custom_strategy_combo.addItem(
            t("synth.strategy_sample_all"),
            "sample_all",
        )
        self._custom_strategy_combo.addItem(
            t("synth.strategy_saved_all"),
            "saved_all",
        )
        self._custom_strategy_combo.addItem(
            t("synth.strategy_saved_roles"),
            "saved_roles",
        )
        idx = self._custom_strategy_combo.findData(current)
        self._custom_strategy_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._custom_strategy_combo.blockSignals(False)

    def _voice_library_dir(self) -> Path:
        """Return the configured voice library directory."""
        text = self._voice_library_dir_edit.text().strip()
        return normalize_voice_library_dir(text or default_voice_library_dir())

    def _browse_voice_library_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            t("synth.voice_library_dir"),
            str(self._voice_library_dir()),
        )
        if path:
            self._voice_library_dir_edit.setText(path)
            self._refresh_saved_voices()

    def _refresh_saved_voices(self) -> None:
        """Reload saved voice metadata from disk and refresh all selectors."""
        current_global = self._saved_voice_combo.currentData() or ""
        current_roles = {
            role: combo.currentData() or ""
            for role, combo in getattr(self, "_role_voice_combos", {}).items()
        }
        self._saved_voices = list_saved_voices(self._voice_library_dir())
        self._populate_saved_voice_combo(self._saved_voice_combo, current_global)
        for role, combo in self._role_voice_combos.items():
            self._populate_saved_voice_combo(
                combo,
                current_roles.get(role, ""),
                include_builtin=True,
            )
        self._update_custom_voice_controls()

    def _populate_saved_voice_combo(
        self,
        combo: QComboBox,
        selected: str = "",
        include_builtin: bool = False,
    ) -> None:
        """Populate one saved voice selector."""
        combo.blockSignals(True)
        combo.clear()
        if include_builtin:
            combo.addItem(t("synth.role_builtin"), "")
        elif not self._saved_voices:
            combo.addItem(t("synth.no_saved_voices"), "")
        for voice in self._saved_voices:
            combo.addItem(f"{voice.name} ({voice.voice_id})", voice.voice_id)
        idx = combo.findData(selected)
        combo.setCurrentIndex(idx if idx >= 0 else 0)
        combo.blockSignals(False)

    def _update_custom_voice_controls(self) -> None:
        """Show controls relevant to the selected Custom Voice strategy."""
        if not hasattr(self, "_custom_strategy_combo"):
            return
        strategy = self._custom_strategy_combo.currentData() or "sample_all"
        sample_mode = strategy == "sample_all"
        saved_all_mode = strategy == "saved_all"
        saved_roles_mode = strategy == "saved_roles"
        self._sample_fields.setVisible(sample_mode)
        self._saved_voice_combo.setVisible(saved_all_mode)
        self._saved_voice_label.setVisible(saved_all_mode)
        self._btn_refresh_saved_voices.setVisible(
            saved_all_mode or saved_roles_mode,
        )
        self._role_mapping_widget.setVisible(saved_roles_mode)
        if sample_mode and not self._sample_status.text():
            self._sample_status.setText(t("synth.sample_idle"))
        elif saved_all_mode:
            self._apply_selected_saved_voice_rate()
            self._sample_status.setText(t("synth.saved_voice_all_hint"))
        elif saved_roles_mode:
            self._sample_status.setText(t("synth.saved_voice_roles_hint"))

    def _selected_saved_voice(self) -> str:
        """Return the globally selected saved voice id."""
        return str(self._saved_voice_combo.currentData() or "")

    def _save_sample_voice(self) -> None:
        """Save the current sample as a reusable local voice prompt."""
        audio = self._sample_audio_edit.text().strip()
        ref_text = self._sample_transcript_edit.toPlainText().strip()
        name = self._voice_name_edit.text().strip()
        if not audio or not ref_text or not name:
            self._sample_status.setText(t("synth.saved_voice_missing"))
            return

        self._btn_save_sample_voice.setEnabled(False)
        self._save_voice_worker = VoicePromptSaveWorker(
            audio_path=Path(audio),
            voice_name=name,
            ref_text=ref_text,
            voice_library_dir=self._voice_library_dir(),
            models_dir=self._models_dir_edit.text().strip(),
            speech_rate=self._speech_rate_value(),
        )
        self._save_voice_worker.status.connect(self._sample_status.setText)
        self._save_voice_worker.finished.connect(self._on_sample_voice_saved)
        self._save_voice_worker.error.connect(self._on_sample_voice_save_error)
        self._save_voice_worker.start()

    def _on_sample_voice_saved(self, name: str, _library_dir: str) -> None:
        self._btn_save_sample_voice.setEnabled(True)
        self._refresh_saved_voices()
        saved_id = ""
        for i in range(self._saved_voice_combo.count()):
            item_text = self._saved_voice_combo.itemText(i)
            if name in item_text:
                saved_id = str(self._saved_voice_combo.itemData(i) or "")
                self._saved_voice_combo.setCurrentIndex(i)
                break
        if saved_id:
            idx = self._custom_strategy_combo.findData("saved_all")
            if idx >= 0:
                self._custom_strategy_combo.setCurrentIndex(idx)
        self._sample_status.setText(t("synth.saved_voice_saved", name=name))

    def _on_sample_voice_save_error(self, msg: str) -> None:
        self._btn_save_sample_voice.setEnabled(True)
        self._sample_status.setText(t("synth.saved_voice_error", msg=msg))

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

    def _build_temp_sample_voice_config(self, include_speech_rate: bool = True) -> str:
        """Serialize the selected Custom Voice strategy as a clone config."""
        if not self._is_custom_voice_mode():
            return ""

        strategy = self._custom_strategy_combo.currentData() or "sample_all"
        if strategy == "sample_all":
            audio = self._sample_audio_edit.text().strip()
            ref_text = self._sample_transcript_edit.toPlainText().strip()
            if not audio or not ref_text:
                raise ValueError(t("synth.sample_missing"))
            cfg = {
                "__all__": {
                    "ref_audio": audio,
                    "ref_text": ref_text,
                }
            }
            if include_speech_rate:
                cfg["__all__"]["speech_rate"] = self._speech_rate_value()
        elif strategy == "saved_all":
            saved_voice = self._selected_saved_voice()
            if not saved_voice:
                raise ValueError(t("synth.saved_voice_missing"))
            cfg = {
                "__all__": {
                    "saved_voice": saved_voice,
                }
            }
            if include_speech_rate:
                cfg["__all__"]["speech_rate"] = (
                    self._saved_voice_rate(saved_voice)
                    or self._speech_rate_value()
                )
        else:
            cfg = {}
            for role, combo in self._role_voice_combos.items():
                saved_voice = str(combo.currentData() or "")
                if saved_voice:
                    cfg[role] = {"saved_voice": saved_voice}
                    if include_speech_rate:
                        cfg[role]["speech_rate"] = (
                            self._saved_voice_rate(saved_voice)
                            or self._speech_rate_value()
                        )
            if not cfg:
                raise ValueError(t("synth.saved_voice_missing"))

        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8",
        )
        json.dump(cfg, tmp, ensure_ascii=False, indent=2)
        tmp.close()
        return tmp.name

    def _is_custom_voice_mode(self) -> bool:
        return self._voice_mode == "custom"

    def _on_mode_changed(self, index: int) -> None:
        if index == 0:
            self._voice_mode = "custom"
        elif index == 1:
            self._voice_mode = "preset"
        if self._sample_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._sample_player.pause()

    # ── Manifest ──────────────────────────────────────────────────────────────

    def set_manifest(self, manifest_path: Path, output_dir: Path) -> None:
        """Set the manifest file and output directory."""
        self._manifest_path = manifest_path
        self._output_dir = output_dir
        self._manifest_label.setText(str(manifest_path))
        self._btn_start.setEnabled(True)
        self._btn_test.setEnabled(True)
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
            self._btn_test.setEnabled(True)
            self._load_chapters_from_manifest()

    def _load_chapters_from_manifest(self) -> None:
        """Parse manifest and populate chapter combo with real data."""
        if not self._manifest_path or not self._manifest_path.exists():
            return
        try:
            data = json.loads(self._manifest_path.read_text(encoding="utf-8"))
            chapter_chunks: dict[int, int] = {}
            chunks = _iter_manifest_chunks(data)
            for item in chunks:
                ch = item.get("chapter_index", 0)
                chapter_chunks[ch] = chapter_chunks.get(ch, 0) + 1
            self._chapter_map = chapter_chunks
            self._manifest_chunks = chunks
            self._refresh_chapter_combo()
            self._refresh_test_chapter_combo()
        except (json.JSONDecodeError, OSError, TypeError, AttributeError):
            self._manifest_chunks = []
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

    def _populate_test_source_combo(self) -> None:
        """Populate the test source selector without losing the current mode."""
        if not hasattr(self, "_test_source_combo"):
            return
        current = self._test_source_combo.currentData() or "chunk"
        self._test_source_combo.blockSignals(True)
        self._test_source_combo.clear()
        self._test_source_combo.addItem(t("synth.test_source_chunk"), "chunk")
        self._test_source_combo.addItem(t("synth.test_source_custom"), "custom")
        idx = self._test_source_combo.findData(current)
        self._test_source_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._test_source_combo.blockSignals(False)
        self._update_test_source_controls()

    def _refresh_test_chapter_combo(self) -> None:
        """Populate the chapter selector used by test preview chunks."""
        if not hasattr(self, "_test_chapter_combo"):
            return
        current = self._test_chapter_combo.currentData()
        chapters = sorted({
            int(chunk.get("chapter_index", 0))
            for chunk in self._manifest_chunks
            if isinstance(chunk, dict)
        })
        counts = {
            chapter: sum(
                1
                for chunk in self._manifest_chunks
                if int(chunk.get("chapter_index", 0)) == chapter
            )
            for chapter in chapters
        }

        self._test_chapter_combo.blockSignals(True)
        self._test_chapter_combo.clear()
        if not chapters:
            self._test_chapter_combo.addItem(t("synth.no_test_chunks"), None)
        else:
            for chapter in chapters:
                self._test_chapter_combo.addItem(
                    t(
                        "synth.chapter_item",
                        num=chapter + 1,
                        chunks=counts.get(chapter, 0),
                    ),
                    chapter,
                )
        idx = self._test_chapter_combo.findData(current)
        self._test_chapter_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._test_chapter_combo.blockSignals(False)
        self._refresh_test_chunk_combo()

    def _chunks_for_test_chapter(self, chapter_index: int | None) -> list[dict]:
        """Return manifest chunks for the selected preview chapter."""
        if chapter_index is None:
            return []
        return sorted(
            [
                chunk
                for chunk in self._manifest_chunks
                if int(chunk.get("chapter_index", 0)) == chapter_index
            ],
            key=lambda chunk: int(chunk.get("chunk_index", 0)),
        )

    def _refresh_test_chunk_combo(self) -> None:
        """Populate the test chunk selector for the selected chapter."""
        if not hasattr(self, "_test_chunk_combo"):
            return
        current = self._test_chunk_combo.currentData()
        chapter_data = self._test_chapter_combo.currentData()
        chapter = int(chapter_data) if chapter_data is not None else None
        chunks = self._chunks_for_test_chapter(chapter)

        self._test_chunk_combo.blockSignals(True)
        self._test_chunk_combo.clear()
        if not chunks:
            self._test_chunk_combo.addItem(t("synth.no_test_chunks"), None)
        else:
            for chunk in chunks:
                chunk_index = int(chunk.get("chunk_index", 0))
                text = str(chunk.get("text") or "")
                voice_id = str(chunk.get("voice_id") or "narrator_calm")
                self._test_chunk_combo.addItem(
                    t(
                        "synth.test_chunk_item",
                        num=chunk_index + 1,
                        voice=voice_id,
                        chars=len(text),
                        preview=_chunk_preview_text(text),
                    ),
                    (chapter, chunk_index),
                )
        idx = self._test_chunk_combo.findData(current)
        self._test_chunk_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._test_chunk_combo.blockSignals(False)
        self._update_test_chunk_preview()

    def _selected_test_chunk(self) -> dict | None:
        """Return the selected manifest chunk for preview synthesis."""
        data = self._test_chunk_combo.currentData()
        if not isinstance(data, tuple) or len(data) != 2:
            return None
        chapter, chunk_index = data
        for chunk in self._manifest_chunks:
            if (
                int(chunk.get("chapter_index", 0)) == int(chapter)
                and int(chunk.get("chunk_index", 0)) == int(chunk_index)
            ):
                return chunk
        return None

    def _update_test_chunk_preview(self) -> None:
        """Show the exact selected chunk text in the preview field."""
        if not hasattr(self, "_test_chunk_preview"):
            return
        chunk = self._selected_test_chunk()
        self._test_chunk_preview.setPlainText(
            str(chunk.get("text") or "") if chunk else "",
        )

    def _update_test_source_controls(self) -> None:
        """Switch the test panel between manifest chunk and custom text modes."""
        if not hasattr(self, "_test_source_combo"):
            return
        is_custom = (self._test_source_combo.currentData() or "chunk") == "custom"
        self._test_chunk_controls.setVisible(not is_custom)
        self._test_chunk_label.setVisible(not is_custom)
        self._test_voice_combo.setVisible(is_custom)
        self._test_voice_label.setVisible(is_custom)
        self._test_text_stack.setCurrentIndex(1 if is_custom else 0)
        self._test_text_label.setText(
            t("synth.test_custom_text") if is_custom else t("synth.test_chunk_text"),
        )
        if not is_custom:
            self._update_test_chunk_preview()

    def _build_selected_test_chunks(self) -> list[dict]:
        """Build the one-entry manifest for the chosen test source."""
        source = self._test_source_combo.currentData() or "chunk"
        if source == "custom":
            text = self._test_custom_text_edit.toPlainText().strip()
            if not text:
                raise ValueError(t("synth.test_custom_missing"))
            return [
                _test_manifest_chunk_from_text(
                    text,
                    self._test_voice_combo.currentText(),
                )
            ]

        chunk = self._selected_test_chunk()
        if not chunk or not str(chunk.get("text") or "").strip():
            raise ValueError(t("synth.test_no_chunk"))
        return [_test_manifest_chunk_from_chunk(chunk)]

    def _selected_chapter(self) -> int | None:
        selected = self._chapter_combo.currentData()
        return selected if selected and selected > 0 else None

    def _start_synthesis(self) -> None:
        if not self._manifest_path or not self._output_dir:
            return

        chapter = self._selected_chapter()

        try:
            clone_config_path = self._build_temp_sample_voice_config()
        except ValueError as exc:
            self._status.setText(str(exc))
            self._progress.set_status(str(exc))
            return

        self._run_kind = "full"
        self._set_run_buttons_active(True)
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
            voice_library_dir=str(self._voice_library_dir()),
            temperature=self._temperature_spin.value(),
            top_p=self._top_p_spin.value(),
            top_k=self._top_k_spin.value(),
            repetition_penalty=self._repetition_penalty_spin.value(),
            max_new_tokens=self._max_new_tokens_spin.value(),
            seed=self._seed_spin.value(),
            speech_rate=self._speech_rate_value(),
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

    def _start_test_synthesis(self) -> None:
        if not self._manifest_path or not self._output_dir:
            return

        try:
            test_chunks = self._build_selected_test_chunks()
            if not test_chunks:
                raise ValueError(t("synth.test_no_chunk"))
            clone_config_path = self._build_temp_sample_voice_config(
                include_speech_rate=False,
            )
        except ValueError as exc:
            self._status.setText(str(exc))
            self._progress.set_status(str(exc))
            return

        self._preview_output_dir = self._output_dir / "tts_test_preview"
        self._preview_output_dir.mkdir(parents=True, exist_ok=True)
        test_manifest = self._preview_output_dir / "test_manifest.json"
        test_manifest.write_text(
            json.dumps(test_chunks, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self._last_test_audio_path = None
        self._btn_play_test.setEnabled(False)
        self._test_player.stop()
        self._test_player.setSource(QUrl())

        self._run_kind = "test"
        self._set_run_buttons_active(True)
        self._progress.reset()

        self._worker = TTSSynthesisWorker(
            manifest_path=test_manifest,
            output_dir=self._preview_output_dir,
            model=self._model_combo.currentText(),
            chapter=None,
            batch_size=1,
            resume=False,
            chunk_timeout=self._chunk_timeout.value(),
            use_compile=self._compile_check.isChecked(),
            clone_config=clone_config_path,
            use_sage_attention=self._sage_check.isChecked(),
            models_dir=self._models_dir_edit.text().strip(),
            voice_library_dir=str(self._voice_library_dir()),
            temperature=self._temperature_spin.value(),
            top_p=self._top_p_spin.value(),
            top_k=self._top_k_spin.value(),
            repetition_penalty=self._repetition_penalty_spin.value(),
            max_new_tokens=self._max_new_tokens_spin.value(),
            seed=self._seed_spin.value(),
            # Test playback applies the slider live through QMediaPlayer so the
            # user can adjust tempo while listening. Full synthesis persists it.
            speech_rate=1.0,
            output_format=str(self._output_format_combo.currentData() or "flac"),
            merge_chapters=False,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.status.connect(self._on_status)
        self._worker.log_line.connect(self._on_log_line)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

        self._log_edit.clear()
        self._log_edit.appendPlainText(
            t("synth.test_log_path", path=str(self._preview_output_dir)),
        )
        self._phase = "loading"
        self._phase_start = time.time()
        self._tick_timer.start()
        self._status.setText(t("synth.test_in_progress"))
        self._on_tick()

    def _stop_synthesis(self) -> None:
        self._tick_timer.stop()
        if self._worker:
            self._worker.cancel()
        self._btn_stop.setEnabled(False)

    def _set_run_buttons_active(self, active: bool) -> None:
        has_manifest = bool(self._manifest_path)
        self._btn_start.setEnabled(has_manifest and not active)
        self._btn_test.setEnabled(has_manifest and not active)
        self._btn_stop.setEnabled(active)
        self._btn_save_sample_voice.setEnabled(not active)

    def _toggle_test_playback(self) -> None:
        if not self._last_test_audio_path:
            return
        if self._test_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._test_player.pause()
        else:
            self._test_player.setPlaybackRate(self._speech_rate_value())
            self._test_player.play()

    def _on_test_playback_state(self, state: QMediaPlayer.PlaybackState) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._btn_play_test.setText(t("synth.test_pause"))
        else:
            self._btn_play_test.setText(t("synth.test_play"))

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
            key = "synth.test_loading_model" if self._run_kind == "test" else "synth.loading_model"
            self._progress.set_busy(t(key) + f"  [{time_str}]")
        elif self._phase == "synth":
            key = "synth.test_synthesizing" if self._run_kind == "test" else "synth.synthesizing"
            self._progress.set_busy(t(key) + f"  [{time_str}]")

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
            key = "synth.test_model_ready" if self._run_kind == "test" else "synth.model_ready"
            self._progress.set_busy(t(key, sec=elapsed))
        else:
            self._tick_timer.stop()
            self._progress.set_busy(msg)

    def _on_finished(self, output_dir: str, synthesized: int, skipped: int) -> None:
        self._tick_timer.stop()
        self._phase = "idle"
        run_kind = self._run_kind
        self._run_kind = "idle"
        self._set_run_buttons_active(False)
        self._progress.set_progress(1, 1, "")
        if run_kind == "test":
            audio_path = self._find_test_audio_path()
            if audio_path:
                self._last_test_audio_path = audio_path
                self._test_player.setSource(QUrl.fromLocalFile(str(audio_path)))
                self._test_player.setPlaybackRate(self._speech_rate_value())
                self._btn_play_test.setEnabled(True)
                self._status.setText(t("synth.test_done", path=str(audio_path)))
                self._sample_status.setText(t("synth.test_next_step"))
            else:
                self._status.setText(t("synth.test_done_no_file", path=output_dir))
            return
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
        self._run_kind = "idle"
        self._set_run_buttons_active(False)
        self._progress.set_status(f"❌ {msg}")

    def _find_test_audio_path(self) -> Path | None:
        if not self._preview_output_dir:
            return None
        manifest = self._preview_output_dir / "synthesis_manifest.json"
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(data, list):
            return None
        for item in data:
            if not isinstance(item, dict):
                continue
            rel = item.get("file")
            if not rel:
                continue
            path = self._preview_output_dir / str(rel)
            if path.exists():
                return path
        return None
