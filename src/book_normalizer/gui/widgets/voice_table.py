"""Interactive voice assignment table for segments/chunks."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

try:
    from PyQt6.QtMultimedia import QSoundEffect
except ImportError:  # pragma: no cover - depends on local PyQt6 multimedia build
    QSoundEffect = None  # type: ignore[assignment]

from book_normalizer.chunking.manifest import chunks_to_v2_manifest, flatten_v2_manifest
from book_normalizer.gui.i18n import t, voice_category_label, voice_preset_label
from book_normalizer.gui.ui_scaler import apply_combo_content_width
from book_normalizer.gui.voice_presets import VOICE_PRESETS
from book_normalizer.tts.voice_library import default_voice_library_dir, list_saved_voices
from book_normalizer.tts.voice_mapping import (
    auto_builtin_voice_id_for_segment,
    segment_speaker,
)

INTONATION_KEYS = [
    "neutral", "calm", "excited", "joyful", "sad", "angry", "whisper",
]
SAVED_VOICE_PREFIX = "saved:"

_DIALOGUE_BG = QColor(14, 165, 233, 28)

_CANONICAL_ROLE_KEYS = {
    "narrator": "voice.role_narrator",
    "male": "voice.role_male",
    "female": "voice.role_female",
    "unknown": "voice.role_unknown",
}

_SECTION_ROLE_KEYS = {
    "annotation": "voice.role_annotation",
    "preface": "voice.role_preface",
    "epilogue": "voice.role_epilogue",
    "chapter_title": "voice.role_chapter_title",
}


def _editor_style() -> str:
    return (
        "QPlainTextEdit {"
        "  background: rgba(255,255,255,0.90);"
        "  border: 1px solid rgba(91,115,142,0.18);"
        "  border-radius: 8px;"
        "  padding: 8px;"
        "  color: rgba(30,41,59,0.92);"
        "  font-size: 12px;"
        "}"
    )


def _role_from_voice_id(voice_id: str, fallback: str = "narrator") -> str:
    """Infer canonical role from a GUI voice preset id."""
    normalized = (voice_id or "").strip().lower()
    if normalized.startswith(SAVED_VOICE_PREFIX):
        return fallback if fallback in {"narrator", "male", "female", "unknown"} else "narrator"
    if normalized == "male" or normalized.startswith("male_"):
        return "male"
    if normalized == "female" or normalized.startswith("female_"):
        return "female"
    if normalized == "narrator" or normalized.startswith("narrator_"):
        return "narrator"
    return fallback if fallback in {"narrator", "male", "female", "unknown"} else "narrator"


def _segment_role_display(segment: dict[str, Any]) -> str:
    """Return the human-facing role label for one segment."""
    speaker = segment_speaker(segment)
    if speaker:
        return speaker
    section = str(segment.get("section_kind") or "").strip().lower()
    if section in _SECTION_ROLE_KEYS:
        return t(_SECTION_ROLE_KEYS[section])
    role = str(segment.get("role") or "narrator").strip().lower()
    return t(_CANONICAL_ROLE_KEYS.get(role, "voice.role_narrator"))


def _make_voice_combo(current: str = "narrator_calm") -> QComboBox:
    """Create a QComboBox with all voice presets, grouped by category."""
    combo = QComboBox()
    _populate_voice_combo(combo, current)
    return combo


def _populate_voice_combo(combo: QComboBox, current: str = "narrator_calm") -> None:
    """Refresh voice combo labels for the active UI language."""
    combo.blockSignals(True)
    combo.clear()
    categories = ["narrator", "male", "female"]

    for cat_id in categories:
        combo.addItem(f"--- {voice_category_label(cat_id)} ---", "")
        idx = combo.count() - 1
        model = combo.model()
        item = model.item(idx)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        item.setForeground(QBrush(QColor(2, 132, 199, 190)))

        presets = [p for p in VOICE_PRESETS if p.category == cat_id]
        for p in presets:
            combo.addItem(f"  {voice_preset_label(p)}", p.id)

    saved_voices = list_saved_voices(default_voice_library_dir())
    if saved_voices:
        combo.addItem(f"--- {voice_category_label('custom')} ---", "")
        idx = combo.count() - 1
        model = combo.model()
        item = model.item(idx)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        item.setForeground(QBrush(QColor(15, 118, 110, 190)))
        for voice in saved_voices:
            combo.addItem(f"  {voice.name}", f"{SAVED_VOICE_PREFIX}{voice.voice_id}")

    for i in range(combo.count()):
        if combo.itemData(i) == current:
            combo.setCurrentIndex(i)
            break
    combo.blockSignals(False)
    apply_combo_content_width(combo)


def _voice_display(voice_id: str) -> str:
    """Return the visible label for a voice preset id."""
    if voice_id.startswith(SAVED_VOICE_PREFIX):
        saved_id = voice_id.removeprefix(SAVED_VOICE_PREFIX)
        for voice in list_saved_voices(default_voice_library_dir()):
            if voice.voice_id == saved_id:
                return voice.name
        return saved_id
    for preset in VOICE_PRESETS:
        if preset.id == voice_id:
            return voice_preset_label(preset)
    return voice_id


def _intonation_display(key: str) -> str:
    """Return the visible label for an intonation key."""
    label = t(f"inton.{key}")
    return label if label != f"inton.{key}" else key


def _make_intonation_combo(current: str = "neutral") -> QComboBox:
    """Create a QComboBox with translated intonation options."""
    combo = QComboBox()

    for key in INTONATION_KEYS:
        combo.addItem(t(f"inton.{key}"), key)

    for i in range(combo.count()):
        if combo.itemData(i) == current:
            combo.setCurrentIndex(i)
            break

    apply_combo_content_width(combo)
    return combo


class VoiceTableWidget(QWidget):
    """Table for assigning voices and intonation to text segments."""

    data_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._segments: list[dict[str, Any]] = []
        self._manifest_meta: dict[str, Any] = {}
        self._manifest_is_v2 = False
        self._compact_mode = False
        self._dense_mode = False
        self._ultra_dense_mode = False
        self._ui_scale = 1.0
        self._row_to_segment_index: list[int] = []
        self._cached_role_options: list[tuple[str, str]] = []
        self._language_dirty_rows: set[int] = set()
        self._pending_delete_segment_index: int | None = None
        self._populating = False
        self._loading_editor = False
        self._player = QSoundEffect(self) if QSoundEffect is not None else None
        self._setup_ui()

    # ── UI setup ──

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Chapter navigation.
        self._chapter_nav_panel = QWidget()
        nav = QHBoxLayout(self._chapter_nav_panel)
        nav.setContentsMargins(0, 0, 0, 0)
        nav.setSpacing(6)
        self._chapter_filter_label = QLabel()
        nav.addWidget(self._chapter_filter_label)
        self._chapter_filter = QComboBox()
        self._chapter_filter.currentIndexChanged.connect(
            lambda _idx: self._apply_chapter_filter(),
        )
        nav.addWidget(self._chapter_filter)
        self._btn_prev_segment = QPushButton()
        self._btn_prev_segment.setProperty("compactActionButton", True)
        self._btn_prev_segment.clicked.connect(lambda: self._select_visible_row(-1))
        nav.addWidget(self._btn_prev_segment)
        self._btn_next_segment = QPushButton()
        self._btn_next_segment.setProperty("compactActionButton", True)
        self._btn_next_segment.clicked.connect(lambda: self._select_visible_row(1))
        nav.addWidget(self._btn_next_segment)
        nav.addStretch()
        layout.addWidget(self._chapter_nav_panel)

        # Toolbar row 1: preset quick-assign.
        self._preset_toolbar_panel = QWidget()
        toolbar1 = QHBoxLayout(self._preset_toolbar_panel)
        toolbar1.setContentsMargins(0, 0, 0, 0)
        toolbar1.setSpacing(4)

        self._btn_all_narrator = QPushButton()
        self._btn_all_narrator.clicked.connect(
            lambda: self._set_all_voice("narrator_calm"),
        )
        toolbar1.addWidget(self._btn_all_narrator)

        self._btn_all_male = QPushButton()
        self._btn_all_male.clicked.connect(
            lambda: self._set_all_voice("male_confident"),
        )
        toolbar1.addWidget(self._btn_all_male)

        self._btn_all_female = QPushButton()
        self._btn_all_female.clicked.connect(
            lambda: self._set_all_voice("female_warm"),
        )
        toolbar1.addWidget(self._btn_all_female)

        self._btn_auto = QPushButton()
        self._btn_auto.clicked.connect(self._auto_detect)
        toolbar1.addWidget(self._btn_auto)

        # Custom quick-assign lives on the same row as common presets on
        # desktop-width layouts, preserving vertical room for the text editor.
        self._quick_apply_panel = QWidget()
        toolbar2 = QHBoxLayout(self._quick_apply_panel)
        toolbar2.setContentsMargins(0, 0, 0, 0)
        toolbar2.setSpacing(4)

        self._quick_combo = _make_voice_combo("narrator_calm")
        toolbar2.addWidget(self._quick_combo)

        self._btn_apply_all = QPushButton()
        self._btn_apply_all.clicked.connect(self._apply_quick_all)
        toolbar2.addWidget(self._btn_apply_all)

        self._btn_apply_dialogue = QPushButton()
        self._btn_apply_dialogue.clicked.connect(
            self._apply_quick_dialogue,
        )
        toolbar2.addWidget(self._btn_apply_dialogue)

        self._btn_apply_narrator = QPushButton()
        self._btn_apply_narrator.clicked.connect(
            self._apply_quick_narrator,
        )
        toolbar2.addWidget(self._btn_apply_narrator)

        self._quick_intonation_panel = QWidget()
        toolbar3 = QHBoxLayout(self._quick_intonation_panel)
        toolbar3.setContentsMargins(0, 0, 0, 0)
        toolbar3.setSpacing(4)

        self._quick_intonation_combo = _make_intonation_combo("calm")
        self._quick_intonation_combo.setToolTip(t("voice.quick_intonation_tip"))
        toolbar3.addWidget(self._quick_intonation_combo)

        self._btn_apply_intonation_all = QPushButton()
        self._btn_apply_intonation_all.setToolTip(t("voice.apply_intonation_all_tip"))
        self._btn_apply_intonation_all.clicked.connect(self._apply_intonation_all)
        toolbar3.addWidget(self._btn_apply_intonation_all)

        self._btn_apply_intonation_dialogue = QPushButton()
        self._btn_apply_intonation_dialogue.setToolTip(t("voice.apply_intonation_dialogue_tip"))
        self._btn_apply_intonation_dialogue.clicked.connect(
            self._apply_intonation_dialogue,
        )
        toolbar3.addWidget(self._btn_apply_intonation_dialogue)

        self._btn_apply_intonation_narrator = QPushButton()
        self._btn_apply_intonation_narrator.setToolTip(t("voice.apply_intonation_narrator_tip"))
        self._btn_apply_intonation_narrator.clicked.connect(
            self._apply_intonation_narrator,
        )
        toolbar3.addWidget(self._btn_apply_intonation_narrator)

        toolbar1.addWidget(self._quick_apply_panel)
        toolbar1.addWidget(self._quick_intonation_panel)
        toolbar1.addStretch()
        layout.addWidget(self._preset_toolbar_panel)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self._splitter = splitter
        splitter.setChildrenCollapsible(False)

        # Table.
        self._table = QTableWidget()
        self._table.setMinimumHeight(108)
        self._table.setColumnCount(10)
        self._table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch,
        )
        self._table.setColumnWidth(0, 42)
        self._table.setColumnWidth(1, 72)
        self._table.setColumnWidth(2, 72)
        self._table.setColumnWidth(4, 170)
        self._table.setColumnWidth(5, 220)
        self._table.setColumnWidth(6, 145)
        self._table.setColumnWidth(7, 104)
        self._table.setColumnWidth(8, 112)
        self._table.setColumnWidth(9, 104)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows,
        )
        self._table.setAlternatingRowColors(True)
        self._table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._table.verticalHeader().setVisible(False)
        self._table.itemChanged.connect(self._on_table_item_changed)
        self._table.itemSelectionChanged.connect(
            self._on_table_selection_changed,
        )
        self._table.verticalScrollBar().valueChanged.connect(
            lambda _value: self._sync_visible_row_widgets(),
        )
        splitter.addWidget(self._table)

        self._editor_tabs = QTabWidget()
        self._editor_tabs.setObjectName("voiceTextEditorTabs")
        self._editor_tabs.setMinimumHeight(148)
        self._editor_tabs.setStyleSheet(
        "QTabWidget::pane {"
            "  border: 1px solid rgba(91,115,142,0.16);"
            "  border-radius: 8px;"
            "  background: rgba(255,255,255,0.66);"
            "}"
            "QTabBar::tab {"
            "  padding: 6px 12px;"
            "  margin-right: 4px;"
            "  border-radius: 7px;"
            "  color: rgba(51,65,85,0.70);"
            "}"
            "QTabBar::tab:selected {"
            "  color: #0f172a;"
            "  background: rgba(224,242,254,0.82);"
            "}"
        )
        self._editor_tabs.addTab(self._build_segment_editor(), "")
        self._editor_tabs.addTab(self._build_full_text_editor(), "")
        splitter.addWidget(self._editor_tabs)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        self.retranslate()
        self._apply_table_layout()
        self._sync_editor_visibility()

    def _build_segment_editor(self) -> QWidget:
        """Build the focused editor for the currently selected segment."""
        panel = QWidget()
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(8, 6, 8, 6)
        outer.setSpacing(4)

        header = QHBoxLayout()
        header.setSpacing(8)
        self._segment_editor_title = QLabel()
        self._segment_editor_title.setStyleSheet(
            "font-weight: 800; color: rgba(30,41,59,0.88);",
        )
        header.addWidget(self._segment_editor_title)
        header.addStretch()
        self._segment_char_label = QLabel()
        self._segment_char_label.setStyleSheet(
            "color: rgba(51,65,85,0.60); font-size: 11px;",
        )
        header.addWidget(self._segment_char_label)
        outer.addLayout(header)

        self._segment_editor = QPlainTextEdit()
        self._segment_editor.setMinimumHeight(44)
        self._segment_editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._segment_editor.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )
        self._segment_editor.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded,
        )
        self._segment_editor.setStyleSheet(_editor_style())
        self._segment_editor.textChanged.connect(
            self._on_segment_editor_text_changed,
        )
        outer.addWidget(self._segment_editor, 1)

        actions = QHBoxLayout()
        actions.setSpacing(6)
        self._btn_segment_split = QPushButton()
        self._btn_segment_split.clicked.connect(self._split_selected_segment)
        actions.addWidget(self._btn_segment_split)
        self._btn_segment_merge = QPushButton()
        self._btn_segment_merge.clicked.connect(self._merge_next_segment)
        actions.addWidget(self._btn_segment_merge)
        self._btn_segment_delete_empty = QPushButton()
        self._btn_segment_delete_empty.clicked.connect(self._delete_empty_segment)
        actions.addWidget(self._btn_segment_delete_empty)
        self._btn_segment_delete = QPushButton()
        self._btn_segment_delete.setObjectName("dangerBtn")
        self._btn_segment_delete.clicked.connect(self._delete_selected_segment)
        actions.addWidget(self._btn_segment_delete)
        self._btn_segment_restore = QPushButton()
        self._btn_segment_restore.clicked.connect(self._restore_selected_segment)
        actions.addWidget(self._btn_segment_restore)
        for button in (
            self._btn_segment_split,
            self._btn_segment_merge,
            self._btn_segment_delete_empty,
            self._btn_segment_delete,
            self._btn_segment_restore,
        ):
            button.setProperty("compactActionButton", True)
        actions.addStretch()
        outer.addLayout(actions)
        return panel

    def _build_full_text_editor(self) -> QWidget:
        """Build the full-text editor that can rewrite the segment list."""
        panel = QWidget()
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(8, 6, 8, 6)
        outer.setSpacing(4)

        header = QHBoxLayout()
        header.setSpacing(8)
        self._full_text_title = QLabel()
        self._full_text_title.setStyleSheet(
            "font-weight: 800; color: rgba(30,41,59,0.88);",
        )
        header.addWidget(self._full_text_title)
        header.addStretch()
        self._full_char_label = QLabel()
        self._full_char_label.setStyleSheet(
            "color: rgba(51,65,85,0.60); font-size: 11px;",
        )
        header.addWidget(self._full_char_label)
        outer.addLayout(header)

        self._full_text_editor = QPlainTextEdit()
        self._full_text_editor.setMinimumHeight(64)
        self._full_text_editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._full_text_editor.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )
        self._full_text_editor.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded,
        )
        self._full_text_editor.setStyleSheet(_editor_style())
        self._full_text_editor.textChanged.connect(self._update_full_char_count)
        outer.addWidget(self._full_text_editor, 1)

        actions = QHBoxLayout()
        actions.setSpacing(6)
        self._btn_full_refresh = QPushButton()
        self._btn_full_refresh.clicked.connect(self._sync_full_text_from_segments)
        actions.addWidget(self._btn_full_refresh)
        self._btn_full_apply = QPushButton()
        self._btn_full_apply.setObjectName("primaryBtn")
        self._btn_full_apply.clicked.connect(self._apply_full_text_to_segments)
        actions.addWidget(self._btn_full_apply)
        for button in (self._btn_full_refresh, self._btn_full_apply):
            button.setProperty("compactActionButton", True)
        actions.addStretch()
        outer.addLayout(actions)
        return panel

    def retranslate(self) -> None:
        """Update translatable strings."""
        self._cached_role_options = self._role_options()

        self._table.setHorizontalHeaderLabels([
            t("voice.col_num"),
            t("voice.col_type"),
            t("voice.col_chapter"),
            t("voice.col_text"),
            t("voice.col_role"),
            t("voice.col_voice"),
            t("voice.col_intonation"),
            t("voice.col_audio"),
            t("voice.col_retry"),
            t("voice.col_action"),
        ])
        self._chapter_filter_label.setText(t("voice.chapter_filter"))
        self._btn_prev_segment.setText(t("voice.prev_segment"))
        self._btn_prev_segment.setToolTip(t("voice.prev_segment_tip"))
        self._btn_next_segment.setText(t("voice.next_segment"))
        self._btn_next_segment.setToolTip(t("voice.next_segment_tip"))
        self._editor_tabs.setTabText(0, t("voice.editor_segment_tab"))
        self._editor_tabs.setTabText(1, t("voice.editor_full_tab"))
        self._segment_editor_title.setText(t("voice.editor_segment_title"))
        self._segment_editor.setPlaceholderText(t("voice.editor_segment_placeholder"))
        self._quick_intonation_combo.setToolTip(t("voice.quick_intonation_tip"))
        self._btn_apply_intonation_all.setToolTip(t("voice.apply_intonation_all_tip"))
        self._btn_apply_intonation_dialogue.setToolTip(t("voice.apply_intonation_dialogue_tip"))
        self._btn_apply_intonation_narrator.setToolTip(t("voice.apply_intonation_narrator_tip"))
        self._btn_segment_split.setText(t("voice.editor_split"))
        self._btn_segment_split.setToolTip(t("voice.editor_split_tip"))
        self._btn_segment_merge.setText(t("voice.editor_merge_next"))
        self._btn_segment_delete_empty.setText(t("voice.editor_delete_empty"))
        self._btn_segment_delete.setText(t("voice.editor_delete"))
        self._btn_segment_restore.setText(t("voice.editor_restore"))
        self._full_text_title.setText(t("voice.editor_full_title"))
        self._full_text_editor.setPlaceholderText(t("voice.editor_full_placeholder"))
        self._btn_full_refresh.setText(t("voice.editor_refresh_full"))
        self._btn_full_apply.setText(t("voice.editor_apply_full"))
        self._apply_toolbar_labels()
        self._sync_editor_action_button_metrics()
        self._update_segment_char_count()
        self._update_full_char_count()
        if self._segments:
            self._refresh_chapter_filter()
            self._language_dirty_rows = set(range(self._table.rowCount()))
            self._refresh_voice_combo_labels()
            self._sync_visible_row_widgets()

    def _refresh_voice_combo_labels(self) -> None:
        """Refresh all voice combo labels after language changes."""
        quick_current = self._quick_combo.currentData() or "narrator_calm"
        _populate_voice_combo(self._quick_combo, str(quick_current))
        intonation_current = self._quick_intonation_combo.currentData() or "calm"
        self._quick_intonation_combo.blockSignals(True)
        self._quick_intonation_combo.clear()
        for key in INTONATION_KEYS:
            self._quick_intonation_combo.addItem(t(f"inton.{key}"), key)
        self._select_combo_data(self._quick_intonation_combo, str(intonation_current))
        self._quick_intonation_combo.blockSignals(False)
        apply_combo_content_width(self._quick_intonation_combo)
        self._cached_role_options = self._role_options()
        for row in self._visible_viewport_rows():
            self._refresh_row_language(row)
            self._language_dirty_rows.discard(row)

    def _refresh_row_language(self, row: int) -> None:
        """Refresh translated labels for one table row without rebuilding it."""
        segment_index = self._segment_index_for_table_row(row)
        if not 0 <= segment_index < len(self._segments):
            return
        segment = self._segments[segment_index]
        self._refresh_row_type_item(row, segment)

        role_combo = self._table.cellWidget(row, 4)
        if isinstance(role_combo, QComboBox):
            current = _segment_role_display(segment)
            self._populate_role_combo(role_combo, current, self._cached_role_options)
            self._clear_widget_backed_item(row, 4, tooltip=current)
        else:
            self._set_readonly_item(row, 4, _segment_role_display(segment))

        combo = self._table.cellWidget(row, 5)
        if isinstance(combo, QComboBox):
            current = combo.currentData() or "narrator_calm"
            _populate_voice_combo(combo, str(current))
            self._clear_widget_backed_item(row, 5, tooltip=combo.currentText())
        else:
            voice_id = str(segment.get("voice_id") or "narrator_calm")
            self._set_readonly_item(row, 5, _voice_display(voice_id))

        intonation_combo = self._table.cellWidget(row, 6)
        if isinstance(intonation_combo, QComboBox):
            current = intonation_combo.currentData() or "neutral"
            intonation_combo.blockSignals(True)
            intonation_combo.clear()
            for key in INTONATION_KEYS:
                intonation_combo.addItem(t(f"inton.{key}"), key)
            idx = intonation_combo.findData(current)
            intonation_combo.setCurrentIndex(idx if idx >= 0 else 0)
            intonation_combo.blockSignals(False)
            apply_combo_content_width(intonation_combo)
            self._clear_widget_backed_item(row, 6, tooltip=intonation_combo.currentText())
        else:
            intonation = str(segment.get("intonation") or "neutral")
            self._set_readonly_item(row, 6, _intonation_display(intonation))

        play_btn = self._table.cellWidget(row, 7)
        play_enabled, play_tooltip = self._audio_button_state(segment)
        if isinstance(play_btn, QPushButton):
            play_btn.setText(t("voice.play_audio"))
            play_btn.setEnabled(play_enabled)
            play_btn.setToolTip(play_tooltip)
            self._clear_widget_backed_item(
                row,
                7,
                tooltip=play_tooltip,
                alignment=Qt.AlignmentFlag.AlignCenter,
            )
        else:
            item = self._set_readonly_item(
                row,
                7,
                t("voice.play_audio"),
                alignment=Qt.AlignmentFlag.AlignCenter,
            )
            item.setToolTip(play_tooltip)

        retry_btn = self._table.cellWidget(row, 8)
        retry_enabled, retry_tooltip = self._retry_button_state()
        if isinstance(retry_btn, QPushButton):
            retry_btn.setText(t("voice.mark_retry"))
            retry_btn.setEnabled(retry_enabled)
            retry_btn.setToolTip(retry_tooltip)
            self._clear_widget_backed_item(
                row,
                8,
                tooltip=retry_tooltip,
                alignment=Qt.AlignmentFlag.AlignCenter,
            )
        else:
            item = self._set_readonly_item(
                row,
                8,
                t("voice.mark_retry"),
                alignment=Qt.AlignmentFlag.AlignCenter,
            )
            item.setToolTip(retry_tooltip)

        self._refresh_row_action_item(row, segment)

    def resizeEvent(self, event) -> None:  # noqa: N802
        """Fallback compact switching when the table is used outside VoicesPage."""
        super().resizeEvent(event)
        threshold = max(960, round(1060 * self._ui_scale * self._ui_scale))
        self.set_compact_mode(self.width() < threshold)
        self._sync_visible_row_widgets()
        self._sync_splitter_layout()

    def set_ui_scale(self, scale: float) -> None:
        """Keep table row and editor heights in step with global UI zoom."""
        self._ui_scale = max(0.8, min(1.45, scale))
        self._segment_editor.setMinimumHeight(
            max(44, min(76, round(52 * self._ui_scale))),
        )
        self._full_text_editor.setMinimumHeight(
            max(58, min(92, round(68 * self._ui_scale))),
        )
        self._editor_tabs.setMinimumHeight(
            max(148, min(190, round(150 * self._ui_scale))),
        )
        self._sync_editor_action_button_metrics()
        self._apply_table_layout()
        self._sync_splitter_layout()

    def set_compact_mode(self, compact: bool) -> None:
        """Reduce columns and labels for small windows."""
        if self._compact_mode == compact:
            return
        self._compact_mode = compact
        self._apply_toolbar_labels()
        self._apply_table_layout()

    def set_dense_mode(self, dense: bool, *, ultra_dense: bool = False) -> None:
        """Hide secondary editing chrome when the host page is height-constrained."""
        if self._dense_mode == dense and self._ultra_dense_mode == ultra_dense:
            return
        self._dense_mode = dense
        self._ultra_dense_mode = ultra_dense
        self._apply_table_layout()
        self._sync_editor_visibility()

    def _apply_toolbar_labels(self) -> None:
        """Use shorter toolbar labels in compact mode."""
        if not self._compact_mode:
            self._btn_all_narrator.setText(t("voice.all_narrator"))
            self._btn_all_male.setText(t("voice.all_male"))
            self._btn_all_female.setText(t("voice.all_female"))
            self._btn_auto.setText(t("voice.auto_detect"))
            self._btn_apply_all.setText(t("voice.apply_all"))
            self._btn_apply_dialogue.setText(t("voice.apply_dialogue"))
            self._btn_apply_narrator.setText(t("voice.apply_narrator"))
            self._btn_apply_intonation_all.setText(t("voice.apply_all"))
            self._btn_apply_intonation_dialogue.setText(t("voice.apply_dialogue"))
            self._btn_apply_intonation_narrator.setText(t("voice.apply_narrator"))
            self._btn_segment_split.setText(t("voice.editor_split"))
            self._btn_segment_merge.setText(t("voice.editor_merge_next"))
            self._btn_segment_delete_empty.setText(t("voice.editor_delete_empty"))
            self._btn_segment_delete.setText(t("voice.editor_delete"))
            self._btn_segment_restore.setText(t("voice.editor_restore"))
            self._sync_editor_action_button_metrics()
            return

        self._btn_all_narrator.setText(t("voice.compact_narrator"))
        self._btn_all_male.setText(t("voice.compact_male"))
        self._btn_all_female.setText(t("voice.compact_female"))
        self._btn_auto.setText(t("voice.compact_auto"))
        self._btn_apply_all.setText(t("voice.compact_all"))
        self._btn_apply_dialogue.setText(t("voice.compact_dialogue"))
        self._btn_apply_narrator.setText(t("voice.compact_author"))
        self._btn_apply_intonation_all.setText(t("voice.compact_all"))
        self._btn_apply_intonation_dialogue.setText(t("voice.compact_dialogue"))
        self._btn_apply_intonation_narrator.setText(t("voice.compact_author"))
        self._btn_segment_split.setText(t("voice.compact_split"))
        self._btn_segment_merge.setText(t("voice.compact_merge"))
        self._btn_segment_delete_empty.setText(t("voice.compact_empty"))
        self._btn_segment_delete.setText(t("voice.compact_delete"))
        self._btn_segment_restore.setText(t("voice.compact_restore"))
        self._sync_editor_action_button_metrics()

    def _sync_editor_action_button_metrics(self) -> None:
        """Keep editor action buttons tall enough for styled text."""
        buttons = (
            self._btn_segment_split,
            self._btn_segment_merge,
            self._btn_segment_delete_empty,
            self._btn_segment_delete,
            self._btn_segment_restore,
            self._btn_full_refresh,
            self._btn_full_apply,
        )
        for button in buttons:
            target = max(round(34 * self._ui_scale), button.sizeHint().height())
            button.setMinimumHeight(target)
            button.setMaximumHeight(target)

    def _apply_table_layout(self) -> None:
        """Apply column visibility and widget widths for the current mode."""
        hidden_cols = {0, 1, 2, 6, 7, 8, 9} if self._compact_mode else set()
        for col in range(self._table.columnCount()):
            self._table.setColumnHidden(col, col in hidden_cols)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        if self._compact_mode:
            self._table.setMinimumHeight(108)
            apply_combo_content_width(self._quick_combo)
            apply_combo_content_width(self._quick_intonation_combo)
            self._table.setColumnWidth(4, 170)
            self._table.setColumnWidth(5, 260)
            self._table.setColumnWidth(7, 68)
            self._table.setColumnWidth(8, 72)
            self._table.setColumnWidth(9, 76)
            self._table.verticalHeader().setDefaultSectionSize(
                self._scaled_table_row_height(32),
            )
        else:
            self._table.setMinimumHeight(112)
            apply_combo_content_width(self._quick_combo)
            apply_combo_content_width(self._quick_intonation_combo)
            self._table.setColumnWidth(0, 42)
            self._table.setColumnWidth(1, 72)
            self._table.setColumnWidth(2, 72)
            self._table.setColumnWidth(4, 170)
            self._table.setColumnWidth(5, 220)
            self._table.setColumnWidth(6, 145)
            self._table.setColumnWidth(7, 104)
            self._table.setColumnWidth(8, 112)
            self._table.setColumnWidth(9, 104)
            self._table.verticalHeader().setDefaultSectionSize(
                self._scaled_table_row_height(34),
            )

        for row in range(self._table.rowCount()):
            role_combo = self._table.cellWidget(row, 4)
            if isinstance(role_combo, QComboBox):
                apply_combo_content_width(role_combo)
            voice_combo = self._table.cellWidget(row, 5)
            if isinstance(voice_combo, QComboBox):
                apply_combo_content_width(voice_combo)
            intonation_combo = self._table.cellWidget(row, 6)
            if isinstance(intonation_combo, QComboBox):
                apply_combo_content_width(intonation_combo)
        self._sync_splitter_layout()

    def _sync_editor_visibility(self) -> None:
        """Hide the chunk editor until there is something meaningful to edit."""
        has_segments = bool(self._segments)
        has_multiple_visible_rows = self._visible_row_count() > 1
        self._chapter_nav_panel.setVisible(has_segments and not self._ultra_dense_mode)
        self._preset_toolbar_panel.setVisible(has_segments and not self._ultra_dense_mode)
        self._quick_apply_panel.setVisible(has_segments and not self._ultra_dense_mode)
        self._quick_intonation_panel.setVisible(has_segments and not self._ultra_dense_mode)
        self._editor_tabs.setVisible(has_segments and not self._dense_mode)
        self._btn_prev_segment.setEnabled(has_multiple_visible_rows)
        self._btn_next_segment.setEnabled(has_multiple_visible_rows)
        self._sync_splitter_layout()

    def _sync_splitter_layout(self) -> None:
        """Reserve a stable editor area while letting the table scroll."""
        if not hasattr(self, "_splitter"):
            return
        if not self._editor_tabs.isVisible():
            self._table.setMaximumHeight(16777215)
            return

        table_min = self._table.minimumHeight()
        editor_min = self._editor_tabs.minimumHeight()
        table_cap = max(table_min, min(round(260 * self._ui_scale), 260))
        self._table.setMaximumHeight(table_cap)

        total = self._splitter.height()
        if total <= 0:
            total = table_cap + editor_min
        table_size = min(table_cap, max(table_min, round(total * 0.42)))
        editor_size = max(editor_min, total - table_size)
        self._splitter.setSizes([table_size, editor_size])

    def _scaled_table_row_height(self, base_height: int) -> int:
        return max(
            round(base_height * self._ui_scale),
            self._table.fontMetrics().height() + round(12 * self._ui_scale),
        )

    # ── Data loading ──

    def load_manifest(self, manifest_path: Path) -> None:
        """Load segments from a manifest JSON file."""
        self._pending_delete_segment_index = None
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        self._manifest_is_v2 = isinstance(data, dict) and data.get("version") == 2
        self._manifest_meta = data if isinstance(data, dict) else {}
        self._segments = flatten_v2_manifest(data) if self._manifest_is_v2 else data
        self._migrate_legacy()
        self._refresh_chapter_filter()
        self._populate_table()

    def set_segments(self, segments: list[dict[str, Any]]) -> None:
        """Set segments directly from worker output."""
        self._pending_delete_segment_index = None
        self._manifest_is_v2 = False
        self._manifest_meta = {}
        self._segments = segments
        self._migrate_legacy()
        self._refresh_chapter_filter()
        self._populate_table()

    def _migrate_legacy(self) -> None:
        """Convert old voice ids and ensure required fields exist."""
        from book_normalizer.gui.voice_presets import LEGACY_VOICE_MAP
        for seg in self._segments:
            vid = seg.get("voice_id", "narrator")
            if vid in LEGACY_VOICE_MAP:
                seg["voice_id"] = LEGACY_VOICE_MAP[vid]
            if "intonation" not in seg:
                seg["intonation"] = seg.get("voice_tone", "neutral")
            if "role" not in seg:
                voice = seg.get("voice", "narrator")
                seg["role"] = {"male": "male", "female": "female"}.get(voice, "narrator")
            if "is_dialogue" not in seg:
                seg["is_dialogue"] = seg.get(
                    "role", "narrator",
                ) in ("male", "female")
            seg["deleted"] = bool(seg.get("deleted") or seg.get("excluded_from_tts", False))

    def _refresh_chapter_filter(self) -> None:
        """Refresh chapter choices while preserving the current selection."""
        selected = self._chapter_filter.currentData()
        chapters = sorted({
            int(seg.get("chapter_index", 0))
            for seg in self._segments
        })
        self._chapter_filter.blockSignals(True)
        self._chapter_filter.clear()
        self._chapter_filter.addItem(t("voice.chapter_all"), None)
        for chapter_index in chapters:
            self._chapter_filter.addItem(
                t("voice.chapter_item", chapter=chapter_index + 1),
                chapter_index,
            )
        idx = self._chapter_filter.findData(selected)
        self._chapter_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self._chapter_filter.blockSignals(False)

    def _visible_segment_pairs(self) -> list[tuple[int, dict[str, Any]]]:
        chapter = self._chapter_filter.currentData()
        pairs = list(enumerate(self._segments))
        if chapter is None:
            return pairs
        return [
            (index, segment)
            for index, segment in pairs
            if int(segment.get("chapter_index", 0)) == int(chapter)
        ]

    def _iter_visible_table_rows(self):
        """Yield table rows matching the active chapter filter."""
        chapter = self._chapter_filter.currentData()
        for table_row, segment_index in enumerate(self._row_to_segment_index):
            if not 0 <= segment_index < len(self._segments):
                continue
            segment = self._segments[segment_index]
            if chapter is None or int(segment.get("chapter_index", 0)) == int(chapter):
                yield table_row, segment_index, segment

    def _visible_row_count(self) -> int:
        """Return the number of rows currently exposed by the chapter filter."""
        return sum(1 for _row in self._iter_visible_table_rows())

    def _first_visible_table_row(self) -> int:
        """Return the first table row that passes the chapter filter."""
        return next((row for row, _index, _segment in self._iter_visible_table_rows()), -1)

    def _apply_chapter_filter(self, preferred_segment_index: int | None = None) -> None:
        """Filter rows by chapter without rebuilding thousands of row widgets."""
        if self._populating:
            return
        current_segment_index = (
            preferred_segment_index
            if preferred_segment_index is not None
            else self._current_row()
        )
        visible_rows = {
            row
            for row, _segment_index, _segment in self._iter_visible_table_rows()
        }

        self._table.setUpdatesEnabled(False)
        try:
            for row in range(self._table.rowCount()):
                self._table.setRowHidden(row, row not in visible_rows)
        finally:
            self._table.setUpdatesEnabled(True)

        selected_row = -1
        if current_segment_index is not None and current_segment_index >= 0:
            try:
                candidate = self._row_to_segment_index.index(current_segment_index)
            except ValueError:
                candidate = -1
            if candidate in visible_rows:
                selected_row = candidate
        if selected_row < 0:
            selected_row = min(visible_rows) if visible_rows else -1

        if selected_row >= 0:
            self._table.setCurrentCell(selected_row, 3)
            item = self._table.item(selected_row, 3)
            if item is not None:
                self._table.scrollToItem(
                    item,
                    QAbstractItemView.ScrollHint.PositionAtTop,
                )
        else:
            self._table.clearSelection()
            self._table.setCurrentCell(-1, -1)
            self._load_selected_segment()
        self._sync_editor_visibility()
        self._sync_visible_row_widgets()

    def _set_readonly_item(
        self,
        row: int,
        column: int,
        value: str,
        *,
        alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft,
    ) -> QTableWidgetItem:
        item = self._table.item(row, column)
        if item is None:
            item = QTableWidgetItem()
            self._table.setItem(row, column, item)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item.setText(value)
        item.setToolTip(value)
        item.setTextAlignment(alignment | Qt.AlignmentFlag.AlignVCenter)
        return item

    def _clear_widget_backed_item(
        self,
        row: int,
        column: int,
        *,
        tooltip: str = "",
        alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft,
    ) -> None:
        """Prevent fallback item text from painting under an interactive cell widget."""
        item = self._table.item(row, column)
        if item is None:
            item = QTableWidgetItem()
            self._table.setItem(row, column, item)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        item.setText("")
        item.setToolTip(tooltip)
        item.setTextAlignment(alignment | Qt.AlignmentFlag.AlignVCenter)

    def _audio_button_state(self, seg: dict[str, Any]) -> tuple[bool, str]:
        audio_path = str(seg.get("audio_file") or "")
        if not audio_path:
            return False, t("voice.play_audio_unavailable_missing")
        if not Path(audio_path).exists():
            return False, t("voice.play_audio_unavailable_not_found")
        if self._player is None:
            return False, t("voice.play_audio_unavailable_player")
        return True, t("voice.play_audio")

    def _retry_button_state(self) -> tuple[bool, str]:
        if self._manifest_is_v2:
            return True, t("voice.mark_retry")
        return False, t("voice.mark_retry_unavailable")

    def _refresh_row_display_items(self, row: int, seg: dict[str, Any]) -> None:
        """Refresh text fallbacks for rows whose heavy widgets are not built yet."""
        role = _segment_role_display(seg)
        voice_id = str(seg.get("voice_id") or "narrator_calm")
        intonation = str(seg.get("intonation") or "neutral")
        voice = _voice_display(voice_id)
        intonation_label = _intonation_display(intonation)
        if self._table.cellWidget(row, 4) is not None:
            self._clear_widget_backed_item(row, 4, tooltip=role)
        else:
            self._set_readonly_item(row, 4, role)
        if self._table.cellWidget(row, 5) is not None:
            self._clear_widget_backed_item(row, 5, tooltip=voice)
        else:
            self._set_readonly_item(row, 5, voice)
        if self._table.cellWidget(row, 6) is not None:
            self._clear_widget_backed_item(row, 6, tooltip=intonation_label)
        else:
            self._set_readonly_item(row, 6, intonation_label)
        if self._table.cellWidget(row, 7) is not None:
            self._clear_widget_backed_item(
                row,
                7,
                tooltip=self._audio_button_state(seg)[1],
                alignment=Qt.AlignmentFlag.AlignCenter,
            )
        else:
            item = self._set_readonly_item(
                row,
                7,
                t("voice.play_audio"),
                alignment=Qt.AlignmentFlag.AlignCenter,
            )
            item.setToolTip(self._audio_button_state(seg)[1])
        if self._table.cellWidget(row, 8) is not None:
            self._clear_widget_backed_item(
                row,
                8,
                tooltip=self._retry_button_state()[1],
                alignment=Qt.AlignmentFlag.AlignCenter,
            )
        else:
            item = self._set_readonly_item(
                row,
                8,
                t("voice.mark_retry"),
                alignment=Qt.AlignmentFlag.AlignCenter,
            )
            item.setToolTip(self._retry_button_state()[1])
        self._refresh_row_action_item(row, seg)

    def _row_delete_label(self, segment_index: int, seg: dict[str, Any]) -> str:
        """Return the action label for a row-level TTS exclusion button."""
        if seg.get("deleted") or seg.get("excluded_from_tts"):
            return t("voice.editor_restore")
        if self._pending_delete_segment_index == segment_index:
            return t("voice.row_delete_confirm")
        return t("voice.editor_delete")

    def _row_delete_tip(self, segment_index: int, seg: dict[str, Any]) -> str:
        """Return the tooltip for a row-level TTS exclusion button."""
        if seg.get("deleted") or seg.get("excluded_from_tts"):
            return t("voice.row_restore_tip")
        if self._pending_delete_segment_index == segment_index:
            return t("voice.row_delete_confirm_tip")
        return t("voice.row_delete_tip")

    def _refresh_row_action_item(self, row: int, seg: dict[str, Any]) -> None:
        """Refresh the delete/restore action for one row."""
        segment_index = self._segment_index_for_table_row(row)
        label = self._row_delete_label(segment_index, seg)
        tip = self._row_delete_tip(segment_index, seg)
        button = self._table.cellWidget(row, 9)
        if isinstance(button, QPushButton):
            button.setText(label)
            button.setToolTip(tip)
            self._clear_widget_backed_item(
                row,
                9,
                tooltip=tip,
                alignment=Qt.AlignmentFlag.AlignCenter,
            )
            return
        item = self._set_readonly_item(
            row,
            9,
            label,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        item.setToolTip(tip)

    def _refresh_row_type_item(self, row: int, seg: dict[str, Any]) -> None:
        """Refresh the translated type cell and its visual state."""
        is_dialogue = bool(seg.get("is_dialogue", False))
        role = seg.get("role", "narrator")
        is_speech = is_dialogue or role in ("male", "female")
        is_deleted = bool(seg.get("deleted"))
        type_text = (
            t("voice.type_deleted")
            if is_deleted
            else t("voice.type_speech")
            if is_speech
            else t("voice.type_narrator")
        )
        type_item = self._set_readonly_item(
            row,
            1,
            type_text,
            alignment=Qt.AlignmentFlag.AlignCenter,
        )
        type_item.setBackground(QBrush())
        type_item.setForeground(QBrush(QColor(71, 85, 105, 150)))
        if is_deleted:
            type_item.setBackground(QColor(248, 113, 113, 34))
            type_item.setForeground(QBrush(QColor(185, 28, 28, 210)))
        elif is_speech:
            type_item.setBackground(_DIALOGUE_BG)
            type_item.setForeground(QBrush(QColor(2, 132, 199, 210)))

    def _select_combo_data(self, combo: QComboBox, value: str) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.setCurrentIndex(index)
                return

    def _ensure_row_widgets(self, row: int) -> None:
        """Build expensive per-row controls only for visible rows."""
        segment_index = self._segment_index_for_table_row(row)
        if not 0 <= segment_index < len(self._segments):
            return
        seg = self._segments[segment_index]

        if not isinstance(self._table.cellWidget(row, 4), QComboBox):
            role_combo = QComboBox()
            role_combo.setEditable(True)
            role_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            role_combo.setToolTip(t("voice.col_role_tip"))
            self._populate_role_combo(
                role_combo,
                _segment_role_display(seg),
                self._cached_role_options,
            )
            role_combo.currentIndexChanged.connect(
                lambda _i, r=segment_index, c=role_combo: self._on_role_changed(
                    r,
                    c.currentData(),
                    c.currentText(),
                ),
            )
            if role_combo.lineEdit() is not None:
                role_combo.lineEdit().editingFinished.connect(
                    lambda r=segment_index, c=role_combo: self._on_role_changed(
                        r,
                        c.currentData(),
                        c.currentText(),
                    ),
                )
            self._table.setCellWidget(row, 4, role_combo)
            self._clear_widget_backed_item(row, 4, tooltip=role_combo.currentText())

        if not isinstance(self._table.cellWidget(row, 5), QComboBox):
            voice_combo = _make_voice_combo(str(seg.get("voice_id", "narrator_calm")))
            voice_combo.currentIndexChanged.connect(
                lambda _i, r=segment_index, c=voice_combo: (
                    self._on_voice_changed(r, c.currentData())
                ),
            )
            self._table.setCellWidget(row, 5, voice_combo)
            self._clear_widget_backed_item(row, 5, tooltip=voice_combo.currentText())

        if not isinstance(self._table.cellWidget(row, 6), QComboBox):
            inton_combo = _make_intonation_combo(str(seg.get("intonation", "neutral")))
            inton_combo.currentIndexChanged.connect(
                lambda _i, r=segment_index, c=inton_combo: (
                    self._on_intonation_changed(r, c.currentData())
                ),
            )
            self._table.setCellWidget(row, 6, inton_combo)
            self._clear_widget_backed_item(row, 6, tooltip=inton_combo.currentText())

        if self._table.cellWidget(row, 7) is None:
            play_btn = QPushButton(t("voice.play_audio"))
            audio_path = str(seg.get("audio_file") or "")
            play_enabled, play_tooltip = self._audio_button_state(seg)
            play_btn.setEnabled(play_enabled)
            play_btn.setToolTip(play_tooltip)
            play_btn.clicked.connect(lambda _checked=False, p=audio_path: self._play_audio(p))
            self._table.setCellWidget(row, 7, play_btn)
            self._clear_widget_backed_item(
                row,
                7,
                tooltip=play_tooltip,
                alignment=Qt.AlignmentFlag.AlignCenter,
            )

        if self._table.cellWidget(row, 8) is None:
            retry_btn = QPushButton(t("voice.mark_retry"))
            retry_enabled, retry_tooltip = self._retry_button_state()
            retry_btn.setEnabled(retry_enabled)
            retry_btn.setToolTip(retry_tooltip)
            retry_btn.clicked.connect(lambda _checked=False, r=segment_index: self._mark_retry(r))
            self._table.setCellWidget(row, 8, retry_btn)
            self._clear_widget_backed_item(
                row,
                8,
                tooltip=retry_tooltip,
                alignment=Qt.AlignmentFlag.AlignCenter,
            )

        if self._table.cellWidget(row, 9) is None:
            delete_btn = QPushButton()
            delete_btn.setObjectName("dangerBtn")
            delete_btn.clicked.connect(
                lambda _checked=False, r=segment_index: self._toggle_segment_deleted(r),
            )
            self._table.setCellWidget(row, 9, delete_btn)
        self._refresh_row_action_item(row, seg)

    def _visible_viewport_rows(self) -> set[int]:
        """Return rows near the current viewport that should have live widgets."""
        if self._table.rowCount() <= 0:
            return set()
        visible_rows = [row for row, _index, _segment in self._iter_visible_table_rows()]
        if not visible_rows:
            return set()

        top = self._table.rowAt(0)
        bottom = self._table.rowAt(max(0, self._table.viewport().height() - 1))
        if top < 0:
            top = visible_rows[0]
        if bottom < 0:
            bottom = top
            default_height = max(1, self._table.verticalHeader().defaultSectionSize())
            bottom += max(6, self._table.viewport().height() // default_height + 4)

        start = max(0, top - 8)
        end = min(self._table.rowCount() - 1, bottom + 16)
        rows = {
            row
            for row in visible_rows
            if start <= row <= end
        }
        current = self._table.currentRow()
        if current in visible_rows:
            rows.add(current)
        return rows

    def _sync_visible_row_widgets(self) -> None:
        """Ensure currently visible rows have interactive controls."""
        if self._populating:
            return
        rows = self._visible_viewport_rows()
        for row in rows:
            self._ensure_row_widgets(row)
            if row in self._language_dirty_rows:
                self._refresh_row_language(row)
                self._language_dirty_rows.discard(row)
        if rows:
            self._apply_table_layout()

    # ── Table population ──

    def _populate_table(self) -> None:
        selected_segment_index = self._current_row()
        self._populating = True
        segment_rows = list(enumerate(self._segments))
        self._row_to_segment_index = [index for index, _segment in segment_rows]
        self._table.clearContents()
        self._table.setRowCount(len(segment_rows))
        self._cached_role_options = self._role_options()

        for row, (segment_index, seg) in enumerate(segment_rows):
            is_dlg = seg.get("is_dialogue", False)
            role = seg.get("role", "narrator")
            is_speech = is_dlg or role in ("male", "female")
            is_deleted = bool(seg.get("deleted"))

            # Column 0: row number.
            idx_item = QTableWidgetItem(str(segment_index + 1))
            idx_item.setFlags(
                idx_item.flags() & ~Qt.ItemFlag.ItemIsEditable,
            )
            idx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 0, idx_item)

            # Column 1: segment type.
            self._refresh_row_type_item(row, seg)

            # Column 2: chapter number.
            ch_item = QTableWidgetItem(
                str(seg.get("chapter_index", 0) + 1),
            )
            ch_item.setFlags(
                ch_item.flags() & ~Qt.ItemFlag.ItemIsEditable,
            )
            ch_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 2, ch_item)

            # Column 3: text preview.
            text = str(seg.get("text", ""))
            text_item = QTableWidgetItem(text)
            text_item.setToolTip(text)
            if is_deleted:
                text_item.setBackground(QColor(248, 113, 113, 24))
                text_item.setForeground(QBrush(QColor(100, 116, 139, 190)))
            elif is_speech:
                text_item.setBackground(_DIALOGUE_BG)
            self._table.setItem(row, 3, text_item)

            self._refresh_row_display_items(row, seg)

        self._populating = False
        self._language_dirty_rows.clear()
        self._apply_table_layout()
        self._sync_full_text_from_segments()
        self._apply_chapter_filter(selected_segment_index)

    # ── Data change handlers ──

    def _on_table_item_changed(self, item: QTableWidgetItem) -> None:
        if self._populating or item.column() != 3:
            return
        row = self._segment_index_for_table_row(item.row())
        if 0 <= row < len(self._segments):
            text = item.text()
            self._segments[row]["text"] = text
            item.setToolTip(text)
            self._load_selected_segment()
            self._sync_full_text_from_segments()
            self.data_changed.emit()

    def _on_table_selection_changed(self) -> None:
        self._load_selected_segment()

    def _current_row(self) -> int:
        return self._segment_index_for_table_row(self._table.currentRow())

    def _segment_index_for_table_row(self, table_row: int) -> int:
        if 0 <= table_row < len(self._row_to_segment_index):
            return self._row_to_segment_index[table_row]
        return -1

    def _table_row_for_segment_index(self, segment_index: int) -> int:
        try:
            return self._row_to_segment_index.index(segment_index)
        except ValueError:
            return -1

    def _select_segment_index(self, segment_index: int) -> None:
        table_row = self._table_row_for_segment_index(segment_index)
        if table_row < 0 and self._row_to_segment_index:
            table_row = 0
        if table_row >= 0 and not self._table.isRowHidden(table_row):
            self._table.setCurrentCell(table_row, 3)
            item = self._table.item(table_row, 3)
            if item is not None:
                self._table.scrollToItem(
                    item,
                    QAbstractItemView.ScrollHint.PositionAtCenter,
                )

    def _select_visible_row(self, delta: int) -> None:
        """Move selection through the currently visible chunk rows."""
        if self._table.rowCount() <= 0:
            return
        visible_rows = [row for row, _index, _segment in self._iter_visible_table_rows()]
        if not visible_rows:
            return
        current = self._table.currentRow()
        if current not in visible_rows:
            next_row = visible_rows[0 if delta >= 0 else -1]
        else:
            current_index = visible_rows.index(current)
            next_index = max(0, min(len(visible_rows) - 1, current_index + delta))
            next_row = visible_rows[next_index]
        self._table.setCurrentCell(next_row, 3)
        item = self._table.item(next_row, 3)
        if item is not None:
            self._table.scrollToItem(
                item,
                QAbstractItemView.ScrollHint.PositionAtCenter,
            )

    def _load_selected_segment(self) -> None:
        row = self._current_row()
        self._loading_editor = True
        if row < 0:
            self._segment_editor.clear()
        else:
            self._segment_editor.setPlainText(str(self._segments[row].get("text", "")))
        self._loading_editor = False
        self._update_segment_char_count()

    def _on_segment_editor_text_changed(self) -> None:
        if self._loading_editor:
            self._update_segment_char_count()
            return
        row = self._current_row()
        if row < 0:
            return
        text = self._segment_editor.toPlainText()
        self._segments[row]["text"] = text
        item = self._table.item(self._table.currentRow(), 3)
        if item is not None:
            self._table.blockSignals(True)
            item.setText(text)
            item.setToolTip(text)
            self._table.blockSignals(False)
        self._update_segment_char_count()
        self._sync_full_text_from_segments()
        self.data_changed.emit()

    def _role_options(self) -> list[tuple[str, str]]:
        """Return visible role choices from canonical roles and LLM speakers."""
        options: list[tuple[str, str]] = []
        seen: set[str] = set()

        def add(label: str, data: str) -> None:
            key = f"{data}\0{label}".casefold()
            if label and key not in seen:
                seen.add(key)
                options.append((label, data))

        add(t("voice.role_narrator"), "role:narrator")
        add(t("voice.role_male"), "role:male")
        add(t("voice.role_female"), "role:female")
        for seg in self._segments:
            section = str(seg.get("section_kind") or "").strip().lower()
            key = _SECTION_ROLE_KEYS.get(section)
            if key:
                add(t(key), f"section:{section}")
            speaker = segment_speaker(seg)
            if speaker:
                add(speaker, f"speaker:{speaker}")
        return options

    def _populate_role_combo(
        self,
        combo: QComboBox,
        current: str,
        options: list[tuple[str, str]] | None = None,
    ) -> None:
        """Refresh one role selector while preserving custom typed names."""
        combo.blockSignals(True)
        combo.clear()
        for label, data in options or self._role_options():
            combo.addItem(label, data)
        if current and combo.findText(current) < 0:
            combo.addItem(current, f"speaker:{current}")
        idx = combo.findText(current) if current else -1
        combo.setCurrentIndex(idx if idx >= 0 else 0)
        combo.blockSignals(False)
        apply_combo_content_width(combo)

    def _on_role_changed(self, row: int, data: object, text: str) -> None:
        """Update role/speaker metadata from the editable role selector."""
        if self._populating or row >= len(self._segments):
            return
        display = (text or "").strip()
        if not display:
            return
        encoded = str(data or "")
        segment = self._segments[row]
        if encoded.startswith("role:"):
            role = encoded.split(":", 1)[1] or "narrator"
            segment["role"] = role
            segment["is_dialogue"] = role in {"male", "female"}
            segment["speaker"] = ""
            segment.pop("character", None)
            segment.pop("role_display_name", None)
        elif encoded.startswith("section:"):
            section = encoded.split(":", 1)[1]
            segment["role"] = "narrator"
            segment["is_dialogue"] = False
            segment["section_kind"] = section
            segment["speaker"] = ""
            segment.pop("character", None)
            segment.pop("role_display_name", None)
        else:
            segment["speaker"] = display
            segment["character"] = display
            segment["role_display_name"] = display
            if str(segment.get("role") or "narrator").lower() not in {"male", "female"}:
                segment["role"] = "male"
            segment["is_dialogue"] = True
        self._cached_role_options = self._role_options()
        table_row = self._table_row_for_segment_index(row)
        if table_row >= 0:
            self._refresh_row_display_items(table_row, segment)
        self.data_changed.emit()

    def _on_voice_changed(self, row: int, voice_id: str) -> None:
        if voice_id and row < len(self._segments):
            segment = self._segments[row]
            segment["voice_id"] = voice_id
            if segment_speaker(segment):
                segment["is_dialogue"] = True
            else:
                role = _role_from_voice_id(
                    voice_id,
                    str(segment.get("role") or "narrator"),
                )
                segment["role"] = role
                segment["is_dialogue"] = role in ("male", "female")
            table_row = self._table_row_for_segment_index(row)
            if table_row >= 0:
                self._refresh_row_display_items(table_row, segment)
            self.data_changed.emit()

    def _on_intonation_changed(self, row: int, intonation: str) -> None:
        if intonation and row < len(self._segments):
            self._segments[row]["intonation"] = intonation
            self._segments[row]["voice_tone"] = intonation
            table_row = self._table_row_for_segment_index(row)
            if table_row >= 0:
                self._refresh_row_display_items(table_row, self._segments[row])
            self.data_changed.emit()

    def _play_audio(self, audio_path: str) -> None:
        """Play a synthesized WAV/AIFF chunk from the table."""
        if not audio_path or self._player is None:
            return
        path = Path(audio_path)
        if not path.exists():
            return
        self._player.stop()
        self._player.setSource(QUrl.fromLocalFile(str(path)))
        self._player.play()

    def _mark_retry(self, row: int) -> None:
        """Mark a v2 manifest row for retry-failed synthesis."""
        if row >= len(self._segments):
            return
        self._segments[row]["synthesized"] = False
        self._segments[row]["failed"] = True
        self._segments[row]["error"] = "Marked for retry in GUI."
        self.data_changed.emit()

    def _toggle_segment_deleted(self, row: int) -> None:
        """Toggle whether a segment is excluded from TTS output."""
        if not 0 <= row < len(self._segments):
            return
        is_deleted = bool(
            self._segments[row].get("deleted")
            or self._segments[row].get("excluded_from_tts")
        )
        if is_deleted:
            self._set_segment_deleted(row, False)
            return
        if self._pending_delete_segment_index != row:
            self._select_segment_index(row)
            self._set_pending_delete_segment(row)
            return
        self._set_segment_deleted(row, True)

    def _set_pending_delete_segment(self, row: int | None) -> None:
        old_row = self._pending_delete_segment_index
        self._pending_delete_segment_index = row
        for segment_index in {old_row, row}:
            if segment_index is None or not 0 <= segment_index < len(self._segments):
                continue
            table_row = self._table_row_for_segment_index(segment_index)
            if table_row >= 0:
                self._refresh_row_action_item(table_row, self._segments[segment_index])

    # ── Bulk operations ──

    def _split_selected_segment(self) -> None:
        row = self._current_row()
        if row < 0:
            return
        text = self._segment_editor.toPlainText()
        cursor = self._segment_editor.textCursor().position()
        if cursor <= 0 or cursor >= len(text):
            return

        before = text[:cursor].strip()
        after = text[cursor:].strip()
        if not before or not after:
            return

        current = self._segments[row]
        new_segment = dict(current)
        current["text"] = before
        new_segment["text"] = after
        new_segment["pause_after_ms"] = current.get("pause_after_ms", 0)
        new_segment["boundary_after"] = current.get("boundary_after", "")
        current["pause_after_ms"] = 0
        current["boundary_after"] = ""
        self._segments.insert(row + 1, new_segment)
        self._renumber_segments()
        self._refresh_chapter_filter()
        self._populate_table()
        self._select_segment_index(row + 1)
        self.data_changed.emit()

    def _merge_next_segment(self) -> None:
        row = self._current_row()
        if row < 0 or row + 1 >= len(self._segments):
            return
        current = self._segments[row]
        next_segment = self._segments[row + 1]
        left = str(current.get("text") or "").strip()
        right = str(next_segment.get("text") or "").strip()
        current["text"] = " ".join(part for part in (left, right) if part)
        if next_segment.get("pause_after_ms"):
            current["pause_after_ms"] = next_segment.get("pause_after_ms", 0)
        if next_segment.get("boundary_after"):
            current["boundary_after"] = next_segment.get("boundary_after", "")
        del self._segments[row + 1]
        self._renumber_segments()
        self._refresh_chapter_filter()
        self._populate_table()
        self._select_segment_index(row)
        self.data_changed.emit()

    def _delete_empty_segment(self) -> None:
        row = self._current_row()
        if row < 0:
            return
        if str(self._segments[row].get("text") or "").strip():
            return
        del self._segments[row]
        self._renumber_segments()
        self._refresh_chapter_filter()
        self._populate_table()
        if self._segments:
            self._select_segment_index(min(row, len(self._segments) - 1))
        self.data_changed.emit()

    def _delete_selected_segment(self) -> None:
        row = self._current_row()
        if row < 0:
            return
        self._set_segment_deleted(row, True)

    def _restore_selected_segment(self) -> None:
        row = self._current_row()
        if row < 0:
            return
        self._set_segment_deleted(row, False)

    def _set_segment_deleted(self, row: int, deleted: bool) -> None:
        if not 0 <= row < len(self._segments):
            return
        self._pending_delete_segment_index = None
        self._segments[row]["deleted"] = deleted
        self._segments[row]["excluded_from_tts"] = deleted
        self._populate_table()
        self._select_segment_index(row)
        self.data_changed.emit()

    def _sync_full_text_from_segments(self) -> None:
        text = "\n\n".join(str(seg.get("text") or "") for seg in self._segments)
        self._full_text_editor.blockSignals(True)
        self._full_text_editor.setPlainText(text)
        self._full_text_editor.blockSignals(False)
        self._update_full_char_count()

    def _apply_full_text_to_segments(self) -> None:
        text = self._full_text_editor.toPlainText()
        blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
        if not blocks:
            return

        existing = self._segments or [{
            "chapter_index": 0,
            "role": "narrator",
            "voice_id": "narrator_calm",
            "intonation": "neutral",
            "is_dialogue": False,
        }]
        rebuilt: list[dict[str, Any]] = []
        for idx, block in enumerate(blocks):
            source = existing[min(idx, len(existing) - 1)]
            item = dict(source)
            item["text"] = block
            item["segment_index"] = idx
            rebuilt.append(item)

        self._segments = rebuilt
        self._migrate_legacy()
        self._renumber_segments()
        self._refresh_chapter_filter()
        self._populate_table()
        self.data_changed.emit()

    def _renumber_segments(self) -> None:
        for index, segment in enumerate(self._segments):
            segment["segment_index"] = index

    def _update_segment_char_count(self) -> None:
        if not hasattr(self, "_segment_char_label"):
            return
        row = self._current_row()
        text = self._segment_editor.toPlainText() if row >= 0 else ""
        self._segment_char_label.setText(
            t("voice.editor_chars", chars=len(text)),
        )

    def _update_full_char_count(self) -> None:
        if not hasattr(self, "_full_char_label"):
            return
        text = self._full_text_editor.toPlainText()
        blocks = [block for block in re.split(r"\n\s*\n", text) if block.strip()]
        self._full_char_label.setText(
            t("voice.editor_full_stats", segments=len(blocks), chars=len(text)),
        )

    def _set_all_voice(self, voice_id: str) -> None:
        """Set all rows to a specific voice preset."""
        self._table.blockSignals(True)
        for row, segment_index, segment in self._iter_visible_table_rows():
            self._apply_voice_to_segment(segment_index, voice_id)
            self._refresh_row_display_items(row, segment)
            combo = self._table.cellWidget(row, 5)
            if isinstance(combo, QComboBox):
                combo.blockSignals(True)
                self._select_combo_data(combo, voice_id)
                combo.blockSignals(False)
        self._table.blockSignals(False)
        self.data_changed.emit()

    def _apply_voice_to_segment(self, segment_index: int, voice_id: str) -> None:
        """Apply a voice id to one segment without relying on visible widgets."""
        if not voice_id or not 0 <= segment_index < len(self._segments):
            return
        segment = self._segments[segment_index]
        segment["voice_id"] = voice_id
        if segment_speaker(segment):
            segment["is_dialogue"] = True
        else:
            role = _role_from_voice_id(
                voice_id,
                str(segment.get("role") or "narrator"),
            )
            segment["role"] = role
            segment["is_dialogue"] = role in ("male", "female")

    def _apply_intonation_to_segment(self, segment_index: int, intonation: str) -> None:
        """Apply an intonation key to one segment without relying on visible widgets."""
        if not intonation or not 0 <= segment_index < len(self._segments):
            return
        segment = self._segments[segment_index]
        segment["intonation"] = intonation
        segment["voice_tone"] = intonation

    @staticmethod
    def _is_dialogue_segment(segment: dict[str, Any]) -> bool:
        return bool(segment.get("is_dialogue", False)) or segment.get(
            "role", "narrator",
        ) in ("male", "female")

    def _apply_quick_all(self) -> None:
        """Apply the quick-combo voice to ALL segments."""
        vid = self._quick_combo.currentData()
        if vid:
            self._set_all_voice(vid)

    def _apply_quick_dialogue(self) -> None:
        """Apply the quick-combo voice to dialogue segments only."""
        vid = self._quick_combo.currentData()
        if not vid:
            return
        for table_row, _segment_index, seg in self._iter_visible_table_rows():
            if self._is_dialogue_segment(seg):
                self._apply_voice_to_segment(_segment_index, str(vid))
                self._refresh_row_display_items(table_row, seg)
                combo = self._table.cellWidget(table_row, 5)
                if isinstance(combo, QComboBox):
                    combo.blockSignals(True)
                    self._select_combo_data(combo, str(vid))
                    combo.blockSignals(False)
        self.data_changed.emit()

    def _apply_quick_narrator(self) -> None:
        """Apply the quick-combo voice to narrator segments only."""
        vid = self._quick_combo.currentData()
        if not vid:
            return
        for table_row, _segment_index, seg in self._iter_visible_table_rows():
            if not self._is_dialogue_segment(seg):
                self._apply_voice_to_segment(_segment_index, str(vid))
                self._refresh_row_display_items(table_row, seg)
                combo = self._table.cellWidget(table_row, 5)
                if isinstance(combo, QComboBox):
                    combo.blockSignals(True)
                    self._select_combo_data(combo, str(vid))
                    combo.blockSignals(False)
        self.data_changed.emit()

    def _apply_intonation_scope(self, scope: str) -> None:
        """Apply the quick intonation to visible rows matching scope."""
        intonation = self._quick_intonation_combo.currentData()
        if not intonation:
            return
        for table_row, segment_index, seg in self._iter_visible_table_rows():
            is_dialogue = self._is_dialogue_segment(seg)
            if scope == "dialogue" and not is_dialogue:
                continue
            if scope == "narrator" and is_dialogue:
                continue
            self._apply_intonation_to_segment(segment_index, str(intonation))
            self._refresh_row_display_items(table_row, seg)
            combo = self._table.cellWidget(table_row, 6)
            if isinstance(combo, QComboBox):
                combo.blockSignals(True)
                self._select_combo_data(combo, str(intonation))
                combo.blockSignals(False)
        self.data_changed.emit()

    def _apply_intonation_all(self) -> None:
        """Apply the quick intonation to ALL visible segments."""
        self._apply_intonation_scope("all")

    def _apply_intonation_dialogue(self) -> None:
        """Apply the quick intonation to visible dialogue segments only."""
        self._apply_intonation_scope("dialogue")

    def _apply_intonation_narrator(self) -> None:
        """Apply the quick intonation to visible narrator segments only."""
        self._apply_intonation_scope("narrator")

    def _auto_detect(self) -> None:
        """Re-run heuristic voice mapping based on detected roles."""
        for table_row, _segment_index, seg in self._iter_visible_table_rows():
            target = auto_builtin_voice_id_for_segment(seg)
            self._apply_voice_to_segment(_segment_index, target)
            self._refresh_row_display_items(table_row, seg)
            combo = self._table.cellWidget(table_row, 5)
            if isinstance(combo, QComboBox):
                combo.blockSignals(True)
                self._select_combo_data(combo, target)
                combo.blockSignals(False)
        self.data_changed.emit()

    # ── Getters / save ──

    def get_segments(self) -> list[dict[str, Any]]:
        """Return the current segment data with voice assignments."""
        return self._segments

    def get_active_segments(self) -> list[dict[str, Any]]:
        """Return segments that should still be sent to synthesis/chunking."""
        return [
            segment
            for segment in self._segments
            if not segment.get("deleted") and not segment.get("excluded_from_tts")
        ]

    def get_chunks(self) -> list[dict[str, Any]]:
        """Alias for backward compatibility."""
        return self._segments

    def save_to_file(self, path: Path) -> None:
        """Save current voice assignments to a manifest file."""
        data: object = self._segments
        if self._manifest_is_v2 or path.name.endswith("_v2.json"):
            data = chunks_to_v2_manifest(
                self._segments,
                book_title=str(self._manifest_meta.get("book_title") or path.parent.name),
                chunker=str(self._manifest_meta.get("chunker") or "gui"),
                model=str(self._manifest_meta.get("model") or ""),
                max_chunk_chars=self._manifest_meta.get("max_chunk_chars"),
            )
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
