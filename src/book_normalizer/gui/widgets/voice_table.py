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
from book_normalizer.gui.voice_presets import VOICE_PRESETS
from book_normalizer.tts.voice_mapping import segment_speaker

INTONATION_KEYS = [
    "neutral", "calm", "excited", "joyful", "sad", "angry", "whisper",
]

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
    combo.setMinimumWidth(160)
    _populate_voice_combo(combo, current)
    combo.view().setMinimumWidth(230)
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

    for i in range(combo.count()):
        if combo.itemData(i) == current:
            combo.setCurrentIndex(i)
            break
    combo.blockSignals(False)


def _make_intonation_combo(current: str = "neutral") -> QComboBox:
    """Create a QComboBox with translated intonation options."""
    combo = QComboBox()
    combo.setMinimumWidth(118)

    for key in INTONATION_KEYS:
        combo.addItem(t(f"inton.{key}"), key)

    for i in range(combo.count()):
        if combo.itemData(i) == current:
            combo.setCurrentIndex(i)
            break

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
        self._ui_scale = 1.0
        self._row_to_segment_index: list[int] = []
        self._populating = False
        self._loading_editor = False
        self._player = QSoundEffect(self) if QSoundEffect is not None else None
        self._setup_ui()

    # ── UI setup ──

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Chapter navigation.
        self._chapter_nav_panel = QWidget()
        nav = QHBoxLayout(self._chapter_nav_panel)
        nav.setContentsMargins(0, 0, 0, 0)
        nav.setSpacing(6)
        self._chapter_filter_label = QLabel()
        nav.addWidget(self._chapter_filter_label)
        self._chapter_filter = QComboBox()
        self._chapter_filter.currentIndexChanged.connect(lambda _idx: self._populate_table())
        nav.addWidget(self._chapter_filter)
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

        toolbar1.addStretch()
        layout.addWidget(self._preset_toolbar_panel)

        # Toolbar row 2: custom quick-assign via combo.
        self._quick_apply_panel = QWidget()
        toolbar2 = QHBoxLayout(self._quick_apply_panel)
        toolbar2.setContentsMargins(0, 0, 0, 0)
        toolbar2.setSpacing(4)

        self._quick_combo = _make_voice_combo("narrator_calm")
        self._quick_combo.setMinimumWidth(190)
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

        toolbar2.addStretch()
        layout.addWidget(self._quick_apply_panel)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        # Table.
        self._table = QTableWidget()
        self._table.setColumnCount(9)
        self._table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch,
        )
        self._table.setColumnWidth(0, 36)
        self._table.setColumnWidth(1, 60)
        self._table.setColumnWidth(2, 36)
        self._table.setColumnWidth(4, 170)
        self._table.setColumnWidth(5, 220)
        self._table.setColumnWidth(6, 145)
        self._table.setColumnWidth(7, 80)
        self._table.setColumnWidth(8, 80)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows,
        )
        self._table.setAlternatingRowColors(True)
        self._table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._table.verticalHeader().setVisible(False)
        self._table.itemChanged.connect(self._on_table_item_changed)
        self._table.itemSelectionChanged.connect(
            self._on_table_selection_changed,
        )
        splitter.addWidget(self._table)

        self._editor_tabs = QTabWidget()
        self._editor_tabs.setObjectName("voiceTextEditorTabs")
        self._editor_tabs.setMinimumHeight(170)
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
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)

        self.retranslate()
        self._apply_table_layout()
        self._sync_editor_visibility()

    def _build_segment_editor(self) -> QWidget:
        """Build the focused editor for the currently selected segment."""
        panel = QWidget()
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(10, 8, 10, 10)
        outer.setSpacing(6)

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
        self._segment_editor.setMinimumHeight(64)
        self._segment_editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._segment_editor.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )
        self._segment_editor.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )
        self._segment_editor.setStyleSheet(_editor_style())
        self._segment_editor.textChanged.connect(
            self._on_segment_editor_text_changed,
        )
        outer.addWidget(self._segment_editor)

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
        actions.addStretch()
        outer.addLayout(actions)
        return panel

    def _build_full_text_editor(self) -> QWidget:
        """Build the full-text editor that can rewrite the segment list."""
        panel = QWidget()
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(10, 8, 10, 10)
        outer.setSpacing(6)

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
        self._full_text_editor.setMinimumHeight(88)
        self._full_text_editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._full_text_editor.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )
        self._full_text_editor.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )
        self._full_text_editor.setStyleSheet(_editor_style())
        self._full_text_editor.textChanged.connect(self._update_full_char_count)
        outer.addWidget(self._full_text_editor)

        actions = QHBoxLayout()
        actions.setSpacing(6)
        self._btn_full_refresh = QPushButton()
        self._btn_full_refresh.clicked.connect(self._sync_full_text_from_segments)
        actions.addWidget(self._btn_full_refresh)
        self._btn_full_apply = QPushButton()
        self._btn_full_apply.setObjectName("primaryBtn")
        self._btn_full_apply.clicked.connect(self._apply_full_text_to_segments)
        actions.addWidget(self._btn_full_apply)
        actions.addStretch()
        outer.addLayout(actions)
        return panel

    def retranslate(self) -> None:
        """Update translatable strings."""
        self._refresh_voice_combo_labels()

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
        ])
        self._chapter_filter_label.setText(t("voice.chapter_filter"))
        self._editor_tabs.setTabText(0, t("voice.editor_segment_tab"))
        self._editor_tabs.setTabText(1, t("voice.editor_full_tab"))
        self._segment_editor_title.setText(t("voice.editor_segment_title"))
        self._segment_editor.setPlaceholderText(t("voice.editor_segment_placeholder"))
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
        self._update_segment_char_count()
        self._update_full_char_count()

    def _refresh_voice_combo_labels(self) -> None:
        """Refresh all voice combo labels after language changes."""
        quick_current = self._quick_combo.currentData() or "narrator_calm"
        _populate_voice_combo(self._quick_combo, str(quick_current))
        for row in range(self._table.rowCount()):
            role_combo = self._table.cellWidget(row, 4)
            if isinstance(role_combo, QComboBox):
                segment_index = self._segment_index_for_table_row(row)
                if 0 <= segment_index < len(self._segments):
                    current = _segment_role_display(self._segments[segment_index])
                    self._populate_role_combo(role_combo, current)

            combo = self._table.cellWidget(row, 5)
            if isinstance(combo, QComboBox):
                current = combo.currentData() or "narrator_calm"
                _populate_voice_combo(combo, str(current))

    def resizeEvent(self, event) -> None:  # noqa: N802
        """Fallback compact switching when the table is used outside VoicesPage."""
        super().resizeEvent(event)
        self.set_compact_mode(self.width() < 960)

    def set_ui_scale(self, scale: float) -> None:
        """Keep table row and editor heights in step with global UI zoom."""
        self._ui_scale = max(0.8, min(1.45, scale))
        self._segment_editor.setMinimumHeight(
            max(58, min(96, round(64 * self._ui_scale))),
        )
        self._full_text_editor.setMinimumHeight(
            max(72, min(118, round(88 * self._ui_scale))),
        )
        self._editor_tabs.setMinimumHeight(
            max(164, min(230, round(170 * self._ui_scale))),
        )
        self._apply_table_layout()

    def set_compact_mode(self, compact: bool) -> None:
        """Reduce columns and labels for small windows."""
        if self._compact_mode == compact:
            return
        self._compact_mode = compact
        self._apply_toolbar_labels()
        self._apply_table_layout()

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
            self._btn_segment_split.setText(t("voice.editor_split"))
            self._btn_segment_merge.setText(t("voice.editor_merge_next"))
            self._btn_segment_delete_empty.setText(t("voice.editor_delete_empty"))
            self._btn_segment_delete.setText(t("voice.editor_delete"))
            self._btn_segment_restore.setText(t("voice.editor_restore"))
            return

        self._btn_all_narrator.setText(t("voice.compact_narrator"))
        self._btn_all_male.setText(t("voice.compact_male"))
        self._btn_all_female.setText(t("voice.compact_female"))
        self._btn_auto.setText(t("voice.compact_auto"))
        self._btn_apply_all.setText(t("voice.compact_all"))
        self._btn_apply_dialogue.setText(t("voice.compact_dialogue"))
        self._btn_apply_narrator.setText(t("voice.compact_author"))
        self._btn_segment_split.setText(t("voice.compact_split"))
        self._btn_segment_merge.setText(t("voice.compact_merge"))
        self._btn_segment_delete_empty.setText(t("voice.compact_empty"))
        self._btn_segment_delete.setText(t("voice.compact_delete"))
        self._btn_segment_restore.setText(t("voice.compact_restore"))

    def _apply_table_layout(self) -> None:
        """Apply column visibility and widget widths for the current mode."""
        hidden_cols = {0, 1, 2, 6, 7, 8} if self._compact_mode else set()
        for col in range(self._table.columnCount()):
            self._table.setColumnHidden(col, col in hidden_cols)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        if self._compact_mode:
            self._quick_combo.setMinimumWidth(150)
            self._table.setColumnWidth(4, 150)
            self._table.setColumnWidth(5, 170)
            self._table.setColumnWidth(7, 68)
            self._table.setColumnWidth(8, 72)
            self._table.verticalHeader().setDefaultSectionSize(
                self._scaled_table_row_height(38),
            )
        else:
            self._quick_combo.setMinimumWidth(190)
            self._table.setColumnWidth(0, 36)
            self._table.setColumnWidth(1, 60)
            self._table.setColumnWidth(2, 36)
            self._table.setColumnWidth(4, 170)
            self._table.setColumnWidth(5, 220)
            self._table.setColumnWidth(6, 145)
            self._table.setColumnWidth(7, 80)
            self._table.setColumnWidth(8, 80)
            self._table.verticalHeader().setDefaultSectionSize(
                self._scaled_table_row_height(34),
            )

        for row in range(self._table.rowCount()):
            role_combo = self._table.cellWidget(row, 4)
            if isinstance(role_combo, QComboBox):
                role_combo.setMinimumWidth(126 if self._compact_mode else 150)
                role_combo.view().setMinimumWidth(190 if self._compact_mode else 230)
            voice_combo = self._table.cellWidget(row, 5)
            if isinstance(voice_combo, QComboBox):
                voice_combo.setMinimumWidth(132 if self._compact_mode else 160)
                voice_combo.view().setMinimumWidth(210 if self._compact_mode else 230)
            intonation_combo = self._table.cellWidget(row, 6)
            if isinstance(intonation_combo, QComboBox):
                intonation_combo.setMinimumWidth(96 if self._compact_mode else 118)

    def _sync_editor_visibility(self) -> None:
        """Hide the chunk editor until there is something meaningful to edit."""
        has_segments = bool(self._segments)
        self._chapter_nav_panel.setVisible(has_segments)
        self._preset_toolbar_panel.setVisible(has_segments)
        self._quick_apply_panel.setVisible(has_segments)
        self._editor_tabs.setVisible(has_segments)

    def _scaled_table_row_height(self, base_height: int) -> int:
        return max(
            round(base_height * self._ui_scale),
            self._table.fontMetrics().height() + round(12 * self._ui_scale),
        )

    # ── Data loading ──

    def load_manifest(self, manifest_path: Path) -> None:
        """Load segments from a manifest JSON file."""
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        self._manifest_is_v2 = isinstance(data, dict) and data.get("version") == 2
        self._manifest_meta = data if isinstance(data, dict) else {}
        self._segments = flatten_v2_manifest(data) if self._manifest_is_v2 else data
        self._migrate_legacy()
        self._refresh_chapter_filter()
        self._populate_table()

    def set_segments(self, segments: list[dict[str, Any]]) -> None:
        """Set segments directly from worker output."""
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

    # ── Table population ──

    def _populate_table(self) -> None:
        self._populating = True
        visible_segments = self._visible_segment_pairs()
        self._row_to_segment_index = [index for index, _segment in visible_segments]
        self._table.setRowCount(len(visible_segments))

        for row, (segment_index, seg) in enumerate(visible_segments):
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
            type_text = (
                t("voice.type_deleted")
                if is_deleted
                else
                t("voice.type_speech")
                if is_speech
                else t("voice.type_narrator")
            )
            type_item = QTableWidgetItem(type_text)
            type_item.setFlags(
                type_item.flags() & ~Qt.ItemFlag.ItemIsEditable,
            )
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if is_deleted:
                type_item.setBackground(QColor(248, 113, 113, 34))
                type_item.setForeground(QBrush(QColor(185, 28, 28, 210)))
            elif is_speech:
                type_item.setBackground(QColor(14, 165, 233, 28))
                type_item.setForeground(
                    QBrush(QColor(2, 132, 199, 210)),
                )
            else:
                type_item.setForeground(
                    QBrush(QColor(71, 85, 105, 150)),
                )
            self._table.setItem(row, 1, type_item)

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

            # Column 4: editable character/system role.
            role_combo = QComboBox()
            role_combo.setEditable(True)
            role_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
            role_combo.setToolTip(t("voice.col_role_tip"))
            self._populate_role_combo(role_combo, _segment_role_display(seg))
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

            # Column 5: voice combo.
            current_voice = seg.get("voice_id", "narrator_calm")
            voice_combo = _make_voice_combo(current_voice)
            voice_combo.currentIndexChanged.connect(
                lambda _i, r=segment_index, c=voice_combo: (
                    self._on_voice_changed(r, c.currentData())
                ),
            )
            self._table.setCellWidget(row, 5, voice_combo)

            # Column 6: intonation combo.
            current_inton = seg.get("intonation", "neutral")
            inton_combo = _make_intonation_combo(current_inton)
            inton_combo.currentIndexChanged.connect(
                lambda _i, r=segment_index, c=inton_combo: (
                    self._on_intonation_changed(r, c.currentData())
                ),
            )
            self._table.setCellWidget(row, 6, inton_combo)

            # Column 7: play synthesized chunk audio when available.
            play_btn = QPushButton(t("voice.play_audio"))
            audio_path = str(seg.get("audio_file") or "")
            play_btn.setEnabled(bool(audio_path and Path(audio_path).exists() and self._player is not None))
            play_btn.clicked.connect(lambda _checked=False, p=audio_path: self._play_audio(p))
            self._table.setCellWidget(row, 7, play_btn)

            # Column 8: mark a synthesized chunk for retry in ComfyUI failed-only mode.
            retry_btn = QPushButton(t("voice.mark_retry"))
            retry_btn.setEnabled(self._manifest_is_v2)
            retry_btn.clicked.connect(lambda _checked=False, r=segment_index: self._mark_retry(r))
            self._table.setCellWidget(row, 8, retry_btn)

        self._populating = False
        self._apply_table_layout()
        self._sync_editor_visibility()
        self._sync_full_text_from_segments()
        if visible_segments and not self._table.selectedItems():
            self._table.setCurrentCell(0, 3)
        else:
            self._load_selected_segment()

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

    def _select_segment_index(self, segment_index: int) -> None:
        try:
            table_row = self._row_to_segment_index.index(segment_index)
        except ValueError:
            table_row = 0 if self._row_to_segment_index else -1
        if table_row >= 0:
            self._table.setCurrentCell(table_row, 3)

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

    def _populate_role_combo(self, combo: QComboBox, current: str) -> None:
        """Refresh one role selector while preserving custom typed names."""
        combo.blockSignals(True)
        combo.clear()
        for label, data in self._role_options():
            combo.addItem(label, data)
        if current and combo.findText(current) < 0:
            combo.addItem(current, f"speaker:{current}")
        idx = combo.findText(current) if current else -1
        combo.setCurrentIndex(idx if idx >= 0 else 0)
        combo.blockSignals(False)

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
        self.data_changed.emit()

    def _on_voice_changed(self, row: int, voice_id: str) -> None:
        if voice_id and row < len(self._segments):
            self._segments[row]["voice_id"] = voice_id
            role = _role_from_voice_id(
                voice_id,
                str(self._segments[row].get("role") or "narrator"),
            )
            self._segments[row]["role"] = role
            self._segments[row]["is_dialogue"] = role in ("male", "female")
            self.data_changed.emit()

    def _on_intonation_changed(self, row: int, intonation: str) -> None:
        if intonation and row < len(self._segments):
            self._segments[row]["intonation"] = intonation
            self._segments[row]["voice_tone"] = intonation
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
        self._segments[row]["deleted"] = True
        self._segments[row]["excluded_from_tts"] = True
        self._populate_table()
        self._select_segment_index(row)
        self.data_changed.emit()

    def _restore_selected_segment(self) -> None:
        row = self._current_row()
        if row < 0:
            return
        self._segments[row]["deleted"] = False
        self._segments[row]["excluded_from_tts"] = False
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
        for row in range(self._table.rowCount()):
            combo = self._table.cellWidget(row, 5)
            if isinstance(combo, QComboBox):
                for i in range(combo.count()):
                    if combo.itemData(i) == voice_id:
                        combo.setCurrentIndex(i)
                        break

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
        for table_row, (_segment_index, seg) in enumerate(self._visible_segment_pairs()):
            is_speech = seg.get("is_dialogue", False) or seg.get(
                "role", "narrator",
            ) in ("male", "female")
            if is_speech:
                combo = self._table.cellWidget(table_row, 5)
                if isinstance(combo, QComboBox):
                    for i in range(combo.count()):
                        if combo.itemData(i) == vid:
                            combo.setCurrentIndex(i)
                            break

    def _apply_quick_narrator(self) -> None:
        """Apply the quick-combo voice to narrator segments only."""
        vid = self._quick_combo.currentData()
        if not vid:
            return
        for table_row, (_segment_index, seg) in enumerate(self._visible_segment_pairs()):
            is_speech = seg.get("is_dialogue", False) or seg.get(
                "role", "narrator",
            ) in ("male", "female")
            if not is_speech:
                combo = self._table.cellWidget(table_row, 5)
                if isinstance(combo, QComboBox):
                    for i in range(combo.count()):
                        if combo.itemData(i) == vid:
                            combo.setCurrentIndex(i)
                            break

    def _auto_detect(self) -> None:
        """Re-run heuristic voice mapping based on detected roles."""
        from book_normalizer.gui.voice_presets import LEGACY_VOICE_MAP
        for table_row, (_segment_index, seg) in enumerate(self._visible_segment_pairs()):
            role = seg.get("role", "narrator")
            target = LEGACY_VOICE_MAP.get(role, "narrator_calm")
            combo = self._table.cellWidget(table_row, 5)
            if isinstance(combo, QComboBox):
                for i in range(combo.count()):
                    if combo.itemData(i) == target:
                        combo.setCurrentIndex(i)
                        break

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
