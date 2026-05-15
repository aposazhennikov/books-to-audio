"""Interactive voice assignment table for segments/chunks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QBrush, QColor
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

try:
    from PyQt6.QtMultimedia import QSoundEffect
except ImportError:  # pragma: no cover - depends on local PyQt6 multimedia build
    QSoundEffect = None  # type: ignore[assignment]

from book_normalizer.chunking.manifest import chunks_to_v2_manifest, flatten_v2_manifest
from book_normalizer.gui.i18n import get_language, t
from book_normalizer.gui.voice_presets import VOICE_PRESETS

INTONATION_KEYS = [
    "neutral", "calm", "excited", "joyful", "sad", "angry", "whisper",
]

_DIALOGUE_BG = QColor(124, 92, 252, 25)


def _make_voice_combo(current: str = "narrator_calm") -> QComboBox:
    """Create a QComboBox with all voice presets, grouped by category."""
    combo = QComboBox()
    combo.setMinimumWidth(190)
    lang = get_language()

    categories = [
        (
            "narrator",
            "--- Narrators ---" if lang == "en" else "--- Дикторы ---",
        ),
        (
            "male",
            "--- Male ---" if lang == "en" else "--- Мужские ---",
        ),
        (
            "female",
            "--- Female ---" if lang == "en" else "--- Женские ---",
        ),
    ]

    for cat_id, cat_label in categories:
        combo.addItem(cat_label, "")
        idx = combo.count() - 1
        model = combo.model()
        item = model.item(idx)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        item.setForeground(QBrush(QColor(124, 92, 252, 180)))

        presets = [p for p in VOICE_PRESETS if p.category == cat_id]
        for p in presets:
            label = p.label_ru if lang == "ru" else p.label_en
            combo.addItem(f"  {label}", p.id)

    for i in range(combo.count()):
        if combo.itemData(i) == current:
            combo.setCurrentIndex(i)
            break

    combo.view().setMinimumWidth(260)
    return combo


def _make_intonation_combo(current: str = "neutral") -> QComboBox:
    """Create a QComboBox with translated intonation options."""
    combo = QComboBox()
    combo.setMinimumWidth(130)

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
        self._player = QSoundEffect(self) if QSoundEffect is not None else None
        self._setup_ui()

    # ── UI setup ──

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Toolbar row 1: preset quick-assign.
        toolbar1 = QHBoxLayout()
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
        layout.addLayout(toolbar1)

        # Toolbar row 2: custom quick-assign via combo.
        toolbar2 = QHBoxLayout()
        toolbar2.setSpacing(4)

        self._quick_combo = _make_voice_combo("narrator_calm")
        self._quick_combo.setMinimumWidth(220)
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
        layout.addLayout(toolbar2)

        # Table.
        self._table = QTableWidget()
        self._table.setColumnCount(8)
        self._table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch,
        )
        self._table.setColumnWidth(0, 36)
        self._table.setColumnWidth(1, 60)
        self._table.setColumnWidth(2, 36)
        self._table.setColumnWidth(4, 220)
        self._table.setColumnWidth(5, 145)
        self._table.setColumnWidth(6, 80)
        self._table.setColumnWidth(7, 80)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows,
        )
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

        self.retranslate()

    def retranslate(self) -> None:
        """Update translatable strings."""
        self._btn_all_narrator.setText(t("voice.all_narrator"))
        self._btn_all_male.setText(t("voice.all_male"))
        self._btn_all_female.setText(t("voice.all_female"))
        self._btn_auto.setText(t("voice.auto_detect"))

        self._btn_apply_all.setText(t("voice.apply_all"))
        self._btn_apply_dialogue.setText(t("voice.apply_dialogue"))
        self._btn_apply_narrator.setText(t("voice.apply_narrator"))

        self._table.setHorizontalHeaderLabels([
            t("voice.col_num"),
            t("voice.col_type"),
            t("voice.col_chapter"),
            t("voice.col_text"),
            t("voice.col_voice"),
            t("voice.col_intonation"),
            t("voice.col_audio"),
            t("voice.col_retry"),
        ])

    # ── Data loading ──

    def load_manifest(self, manifest_path: Path) -> None:
        """Load segments from a manifest JSON file."""
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        self._manifest_is_v2 = isinstance(data, dict) and data.get("version") == 2
        self._manifest_meta = data if isinstance(data, dict) else {}
        self._segments = flatten_v2_manifest(data) if self._manifest_is_v2 else data
        self._migrate_legacy()
        self._populate_table()

    def set_segments(self, segments: list[dict[str, Any]]) -> None:
        """Set segments directly from worker output."""
        self._manifest_is_v2 = False
        self._manifest_meta = {}
        self._segments = segments
        self._migrate_legacy()
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

    # ── Table population ──

    def _populate_table(self) -> None:
        self._table.setRowCount(len(self._segments))

        for row, seg in enumerate(self._segments):
            is_dlg = seg.get("is_dialogue", False)
            role = seg.get("role", "narrator")
            is_speech = is_dlg or role in ("male", "female")

            # Column 0: row number.
            idx_item = QTableWidgetItem(str(row + 1))
            idx_item.setFlags(
                idx_item.flags() & ~Qt.ItemFlag.ItemIsEditable,
            )
            idx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 0, idx_item)

            # Column 1: segment type.
            type_text = (
                t("voice.type_speech")
                if is_speech
                else t("voice.type_narrator")
            )
            type_item = QTableWidgetItem(type_text)
            type_item.setFlags(
                type_item.flags() & ~Qt.ItemFlag.ItemIsEditable,
            )
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if is_speech:
                type_item.setBackground(QColor(124, 92, 252, 25))
                type_item.setForeground(
                    QBrush(QColor(124, 92, 252, 200)),
                )
            else:
                type_item.setForeground(
                    QBrush(QColor(255, 255, 255, 100)),
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
            text = seg.get("text", "")[:200]
            text_item = QTableWidgetItem(text)
            text_item.setFlags(
                text_item.flags() & ~Qt.ItemFlag.ItemIsEditable,
            )
            if is_speech:
                text_item.setBackground(_DIALOGUE_BG)
            self._table.setItem(row, 3, text_item)

            # Column 4: voice combo.
            current_voice = seg.get("voice_id", "narrator_calm")
            voice_combo = _make_voice_combo(current_voice)
            voice_combo.currentIndexChanged.connect(
                lambda _i, r=row, c=voice_combo: (
                    self._on_voice_changed(r, c.currentData())
                ),
            )
            self._table.setCellWidget(row, 4, voice_combo)

            # Column 5: intonation combo.
            current_inton = seg.get("intonation", "neutral")
            inton_combo = _make_intonation_combo(current_inton)
            inton_combo.currentIndexChanged.connect(
                lambda _i, r=row, c=inton_combo: (
                    self._on_intonation_changed(r, c.currentData())
                ),
            )
            self._table.setCellWidget(row, 5, inton_combo)

            # Column 6: play synthesized chunk audio when available.
            play_btn = QPushButton(t("voice.play_audio"))
            audio_path = str(seg.get("audio_file") or "")
            play_btn.setEnabled(bool(audio_path and Path(audio_path).exists() and self._player is not None))
            play_btn.clicked.connect(lambda _checked=False, p=audio_path: self._play_audio(p))
            self._table.setCellWidget(row, 6, play_btn)

            # Column 7: mark a synthesized chunk for retry in ComfyUI failed-only mode.
            retry_btn = QPushButton(t("voice.mark_retry"))
            retry_btn.setEnabled(self._manifest_is_v2)
            retry_btn.clicked.connect(lambda _checked=False, r=row: self._mark_retry(r))
            self._table.setCellWidget(row, 7, retry_btn)

    # ── Data change handlers ──

    def _on_voice_changed(self, row: int, voice_id: str) -> None:
        if voice_id and row < len(self._segments):
            self._segments[row]["voice_id"] = voice_id
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

    def _set_all_voice(self, voice_id: str) -> None:
        """Set all rows to a specific voice preset."""
        for row in range(self._table.rowCount()):
            combo = self._table.cellWidget(row, 4)
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
        for row, seg in enumerate(self._segments):
            is_speech = seg.get("is_dialogue", False) or seg.get(
                "role", "narrator",
            ) in ("male", "female")
            if is_speech:
                combo = self._table.cellWidget(row, 4)
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
        for row, seg in enumerate(self._segments):
            is_speech = seg.get("is_dialogue", False) or seg.get(
                "role", "narrator",
            ) in ("male", "female")
            if not is_speech:
                combo = self._table.cellWidget(row, 4)
                if isinstance(combo, QComboBox):
                    for i in range(combo.count()):
                        if combo.itemData(i) == vid:
                            combo.setCurrentIndex(i)
                            break

    def _auto_detect(self) -> None:
        """Re-run heuristic voice mapping based on detected roles."""
        from book_normalizer.gui.voice_presets import LEGACY_VOICE_MAP
        for row, seg in enumerate(self._segments):
            role = seg.get("role", "narrator")
            target = LEGACY_VOICE_MAP.get(role, "narrator_calm")
            combo = self._table.cellWidget(row, 4)
            if isinstance(combo, QComboBox):
                for i in range(combo.count()):
                    if combo.itemData(i) == target:
                        combo.setCurrentIndex(i)
                        break

    # ── Getters / save ──

    def get_segments(self) -> list[dict[str, Any]]:
        """Return the current segment data with voice assignments."""
        return self._segments

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
