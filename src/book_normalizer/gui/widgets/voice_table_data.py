"""Data and bulk-edit actions for the voice assignment table."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QComboBox

from book_normalizer.chunking.manifest import chunks_to_v2_manifest
from book_normalizer.gui.i18n import t
from book_normalizer.gui.widgets.voice_table_helpers import _role_from_voice_id
from book_normalizer.tts.voice_mapping import (
    auto_builtin_voice_id_for_segment,
    segment_speaker,
)


class VoiceTableDataMixin:
    """Mixin with data transforms and bulk edit actions."""

    def _request_full_text_sync(self) -> None:
        """Queue the expensive full-text editor rebuild for the next UI turn."""
        if getattr(self, "_full_text_sync_pending", False):
            return
        self._full_text_sync_pending = True
        QTimer.singleShot(0, self._flush_pending_full_text_sync)

    def _flush_pending_full_text_sync(self) -> None:
        if not getattr(self, "_full_text_sync_pending", False):
            return
        self._full_text_sync_pending = False
        self._sync_full_text_from_segments()

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
