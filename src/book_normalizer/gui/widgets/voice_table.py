"""Interactive voice assignment table for paragraphs/chunks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
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


VOICE_OPTIONS = ["narrator", "male", "female"]
INTONATION_OPTIONS = ["neutral", "calm", "excited", "sad", "angry", "whisper"]


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

        toolbar = QHBoxLayout()
        self._btn_all_narrator = QPushButton("All → Narrator")
        self._btn_all_narrator.clicked.connect(lambda: self._set_all_voice("narrator"))
        self._btn_auto = QPushButton("Auto-detect")
        self._btn_auto.clicked.connect(self._auto_detect)
        self._btn_save = QPushButton("Save")
        self._btn_save.clicked.connect(self._save)
        toolbar.addWidget(self._btn_all_narrator)
        toolbar.addWidget(self._btn_auto)
        toolbar.addWidget(self._btn_save)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels([
            "Chapter", "Chunk", "Text Preview", "Voice", "Intonation",
        ])
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

    def load_manifest(self, manifest_path: Path) -> None:
        """Load chunks from a manifest JSON file."""
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        self._chunks = data
        self._populate_table()

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
            is_dialogue = chunk.get("role", "") in ("male", "female")
            if is_dialogue:
                text_item.setBackground(Qt.GlobalColor.cyan)
            self._table.setItem(row, 2, text_item)

            voice_combo = QComboBox()
            voice_combo.addItems(VOICE_OPTIONS)
            current_voice = chunk.get("voice_id", "narrator")
            if current_voice in VOICE_OPTIONS:
                voice_combo.setCurrentText(current_voice)
            voice_combo.currentTextChanged.connect(
                lambda v, r=row: self._on_voice_changed(r, v)
            )
            self._table.setCellWidget(row, 3, voice_combo)

            inton_combo = QComboBox()
            inton_combo.addItems(INTONATION_OPTIONS)
            inton_combo.currentTextChanged.connect(
                lambda v, r=row: self._on_intonation_changed(r, v)
            )
            self._table.setCellWidget(row, 4, inton_combo)

    def _on_voice_changed(self, row: int, voice: str) -> None:
        if row < len(self._chunks):
            self._chunks[row]["voice_id"] = voice
            self.data_changed.emit()

    def _on_intonation_changed(self, row: int, intonation: str) -> None:
        if row < len(self._chunks):
            self._chunks[row]["intonation"] = intonation
            self.data_changed.emit()

    def _set_all_voice(self, voice: str) -> None:
        for row in range(self._table.rowCount()):
            combo = self._table.cellWidget(row, 3)
            if isinstance(combo, QComboBox):
                combo.setCurrentText(voice)

    def _auto_detect(self) -> None:
        """Re-run heuristic detection on loaded chunks."""
        for row, chunk in enumerate(self._chunks):
            role = chunk.get("role", "narrator")
            combo = self._table.cellWidget(row, 3)
            if isinstance(combo, QComboBox):
                combo.setCurrentText(role if role in VOICE_OPTIONS else "narrator")

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
