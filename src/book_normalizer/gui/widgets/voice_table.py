"""Interactive voice assignment table for paragraphs/chunks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from book_normalizer.gui.i18n import get_language, t
from book_normalizer.gui.voice_presets import VOICE_PRESETS, VoicePreset


VOICE_OPTIONS = [p.id for p in VOICE_PRESETS]
INTONATION_OPTIONS = ["neutral", "calm", "excited", "sad", "angry", "whisper"]

LEGACY_VOICES = {"narrator", "male", "female"}

_DIALOGUE_BG = QColor(124, 92, 252, 30)


def _voice_display_name(voice_id: str) -> str:
    """Return localized display name for a voice preset."""
    for p in VOICE_PRESETS:
        if p.id == voice_id:
            lang = get_language()
            return p.label_ru if lang == "ru" else p.label_en
    return voice_id


def _make_voice_combo(current: str = "narrator_calm") -> QComboBox:
    """Create a QComboBox populated with all voice presets, grouped by category."""
    combo = QComboBox()
    lang = get_language()

    categories = [
        ("narrator", "--- Narrators ---" if lang == "en" else "--- Дикторы ---"),
        ("male", "--- Male ---" if lang == "en" else "--- Мужские ---"),
        ("female", "--- Female ---" if lang == "en" else "--- Женские ---"),
    ]

    for cat_id, cat_label in categories:
        combo.addItem(cat_label, "")
        idx = combo.count() - 1
        model = combo.model()
        item = model.item(idx)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        item.setData(
            Qt.ItemDataRole.ForegroundRole,
            QColor(124, 92, 252, 180),
        )

        presets = [p for p in VOICE_PRESETS if p.category == cat_id]
        for p in presets:
            label = p.label_ru if lang == "ru" else p.label_en
            combo.addItem(f"  {label}", p.id)

    # Set current.
    for i in range(combo.count()):
        if combo.itemData(i) == current:
            combo.setCurrentIndex(i)
            break

    return combo


class VoiceTableWidget(QWidget):
    """Table for assigning voices and intonation to text chunks."""

    data_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._chunks: list[dict[str, Any]] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        self._btn_all_narrator = QPushButton()
        self._btn_all_narrator.clicked.connect(
            lambda: self._set_all_voice("narrator_calm")
        )
        self._btn_auto = QPushButton()
        self._btn_auto.clicked.connect(self._auto_detect)
        self._btn_save = QPushButton()
        self._btn_save.clicked.connect(self._save)
        toolbar.addWidget(self._btn_all_narrator)
        toolbar.addWidget(self._btn_auto)
        toolbar.addWidget(self._btn_save)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

        self.retranslate()

    def retranslate(self) -> None:
        """Update translatable strings."""
        self._btn_all_narrator.setText(t("voice.all_narrator"))
        self._btn_auto.setText(t("voice.auto_detect"))
        self._btn_save.setText(t("voice.save"))
        self._table.setHorizontalHeaderLabels([
            t("voice.col_chapter"),
            t("voice.col_chunk"),
            t("voice.col_text"),
            t("voice.col_voice"),
            t("voice.col_intonation"),
        ])

    def load_manifest(self, manifest_path: Path) -> None:
        """Load chunks from a manifest JSON file."""
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        self._chunks = data
        self._migrate_legacy_voices()
        self._populate_table()

    def _migrate_legacy_voices(self) -> None:
        """Convert old 3-voice ids to new preset ids."""
        from book_normalizer.gui.voice_presets import LEGACY_VOICE_MAP
        for chunk in self._chunks:
            vid = chunk.get("voice_id", "narrator")
            if vid in LEGACY_VOICE_MAP:
                chunk["voice_id"] = LEGACY_VOICE_MAP[vid]

    def _populate_table(self) -> None:
        self._table.setRowCount(len(self._chunks))
        for row, chunk in enumerate(self._chunks):
            ch_item = QTableWidgetItem(str(chunk.get("chapter_index", 0) + 1))
            ch_item.setFlags(ch_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 0, ch_item)

            ck_item = QTableWidgetItem(str(chunk.get("chunk_index", 0) + 1))
            ck_item.setFlags(ck_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 1, ck_item)

            text = chunk.get("text", "")[:150]
            text_item = QTableWidgetItem(text)
            text_item.setFlags(text_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            role = chunk.get("role", "")
            if role in ("male", "female"):
                text_item.setBackground(_DIALOGUE_BG)
            self._table.setItem(row, 2, text_item)

            current_voice = chunk.get("voice_id", "narrator_calm")
            voice_combo = _make_voice_combo(current_voice)
            voice_combo.currentIndexChanged.connect(
                lambda _idx, r=row, c=voice_combo: self._on_voice_changed(
                    r, c.currentData()
                )
            )
            self._table.setCellWidget(row, 3, voice_combo)

            inton_combo = QComboBox()
            inton_combo.addItems(INTONATION_OPTIONS)
            current_inton = chunk.get("intonation", "neutral")
            if current_inton in INTONATION_OPTIONS:
                inton_combo.setCurrentText(current_inton)
            inton_combo.currentTextChanged.connect(
                lambda v, r=row: self._on_intonation_changed(r, v)
            )
            self._table.setCellWidget(row, 4, inton_combo)

    def _on_voice_changed(self, row: int, voice_id: str) -> None:
        if voice_id and row < len(self._chunks):
            self._chunks[row]["voice_id"] = voice_id
            self.data_changed.emit()

    def _on_intonation_changed(self, row: int, intonation: str) -> None:
        if row < len(self._chunks):
            self._chunks[row]["intonation"] = intonation
            self.data_changed.emit()

    def _set_all_voice(self, voice_id: str) -> None:
        for row in range(self._table.rowCount()):
            combo = self._table.cellWidget(row, 3)
            if isinstance(combo, QComboBox):
                for i in range(combo.count()):
                    if combo.itemData(i) == voice_id:
                        combo.setCurrentIndex(i)
                        break

    def _auto_detect(self) -> None:
        """Re-run heuristic detection on loaded chunks."""
        from book_normalizer.gui.voice_presets import LEGACY_VOICE_MAP
        for row, chunk in enumerate(self._chunks):
            role = chunk.get("role", "narrator")
            target = LEGACY_VOICE_MAP.get(role, "narrator_calm")
            combo = self._table.cellWidget(row, 3)
            if isinstance(combo, QComboBox):
                for i in range(combo.count()):
                    if combo.itemData(i) == target:
                        combo.setCurrentIndex(i)
                        break

    def _save(self) -> None:
        self.data_changed.emit()

    def get_chunks(self) -> list[dict[str, Any]]:
        """Return the current chunk data with voice assignments."""
        return self._chunks

    def save_to_file(self, path: Path) -> None:
        """Save current voice assignments to a manifest file."""
        path.write_text(
            json.dumps(self._chunks, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
