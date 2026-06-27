"""Manifest and preview helpers for the synthesis page."""

from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import QFileDialog, QTableWidgetItem

from book_normalizer.chunking.manifest_v2 import save_manifest
from book_normalizer.gui.i18n import t
from book_normalizer.gui.pages.synthesis_manifest import (
    _chunk_preview_text,
    _iter_manifest_chunks,
    _merge_manifest_chunk_with_next,
    _split_manifest_chunk_text,
    _test_manifest_chunk_from_chunk,
    _test_manifest_chunk_from_text,
    _update_manifest_chunk_text,
)
from book_normalizer.tts.quality_gate import quality_summary_by_chapter


class SynthesisManifestMixin:
    """Manifest loading, preview selection, and chunk edit behavior."""

    def set_manifest(self, manifest_path: Path, output_dir: Path) -> None:
        """Set the manifest file and output directory."""
        self._manifest_path = manifest_path
        self._set_output_dir(output_dir, emit=False)
        self._set_manifest_label(manifest_path)
        self._btn_start.setEnabled(True)
        self._btn_test.setEnabled(True)
        self._btn_asr_run.setEnabled(True)
        self._load_chapters_from_manifest()
        self._prefer_simple_voice_mode()
        self._set_manifest_ready_status()

    def _browse_manifest(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("synth.load_manifest"), "", "JSON (*.json)",
        )
        if path:
            p = Path(path)
            self._manifest_path = p
            self._set_output_dir(p.parent)
            self._set_manifest_label(p)
            self._btn_start.setEnabled(True)
            self._btn_test.setEnabled(True)
            self._btn_asr_run.setEnabled(True)
            self._load_chapters_from_manifest()
            self._prefer_simple_voice_mode()
            self._set_manifest_ready_status()

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
            self._sync_last_asr_report_from_manifest()
            self._refresh_manifest_role_entries()
            self._refresh_chapter_combo()
            self._refresh_test_chapter_combo()
            self._refresh_quality_dashboard(data)
        except (json.JSONDecodeError, OSError, TypeError, AttributeError, ValueError):
            self._manifest_chunks = []
            self._refresh_manifest_role_entries()
            self._refresh_quality_dashboard(None)
            pass

    def _sync_last_asr_report_from_manifest(self) -> None:
        """Pick up the latest ASR report path from manifest annotations."""
        for chunk in self._manifest_chunks:
            asr_block = chunk.get("asr_qa") if isinstance(chunk, dict) else None
            if not isinstance(asr_block, dict):
                continue
            report_path = str(asr_block.get("report_path") or "").strip()
            if report_path:
                self._last_asr_report_path = Path(report_path)
                self._btn_asr_open_report.setEnabled(True)
                self._btn_asr_open_diff.setEnabled(True)
                return

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

    def _refresh_quality_dashboard(self, data: object | None = None) -> None:
        """Refresh green/yellow/red chapter QA counts."""
        if not hasattr(self, "_quality_table"):
            return
        manifest = data
        if manifest is None and self._manifest_path and self._manifest_path.exists():
            try:
                manifest = json.loads(self._manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                manifest = None
        if not isinstance(manifest, dict):
            self._quality_table.setRowCount(0)
            self._quality_summary_label.setText(t("synth.quality_no_manifest"))
            self._set_quality_buttons(False, False, False)
            return

        summary = quality_summary_by_chapter(manifest)
        self._quality_table.setRowCount(len(summary))
        totals = {"total": 0, "passed": 0, "warning": 0, "failed": 0, "unchecked": 0}
        has_bad = False
        all_ready = bool(summary)
        for row, chapter_index in enumerate(sorted(summary)):
            counts = summary[chapter_index]
            for key in totals:
                totals[key] += int(counts.get(key, 0))
            status = "green"
            brush = QBrush(QColor("#dcfce7"))
            if counts.get("failed", 0):
                status = "red"
                brush = QBrush(QColor("#fee2e2"))
            elif counts.get("warning", 0) or counts.get("unchecked", 0):
                status = "yellow"
                brush = QBrush(QColor("#fef9c3"))
            if status != "green":
                has_bad = True
                all_ready = False
            values = [
                f"{chapter_index + 1:03d}",
                t(f"synth.quality_status_{status}"),
                str(counts.get("passed", 0)),
                str(counts.get("warning", 0)),
                str(counts.get("failed", 0)),
                str(counts.get("unchecked", 0)),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setBackground(brush)
                self._quality_table.setItem(row, column, item)
        self._quality_summary_label.setText(
            t(
                "synth.quality_summary",
                passed=totals["passed"],
                warning=totals["warning"],
                failed=totals["failed"],
                unchecked=totals["unchecked"],
            )
        )
        self._set_quality_buttons(bool(summary), has_bad, all_ready)

    def _set_quality_buttons(self, has_manifest: bool, has_bad: bool, all_ready: bool) -> None:
        active = self._phase != "idle"
        self._btn_quality_run.setEnabled(has_manifest and not active)
        self._btn_quality_resynth.setEnabled(has_manifest and has_bad and not active)
        self._btn_quality_open_issue.setEnabled(has_manifest and has_bad and not active)
        self._btn_quality_open_report.setEnabled(bool(self._last_asr_report_path) and not active)
        self._btn_quality_master.setEnabled(has_manifest and all_ready and not active)

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

    def _asr_filter_accepts(self, chunk: dict) -> bool:
        if not hasattr(self, "_asr_filter_combo"):
            return True
        selected = self._asr_filter_combo.currentData() or "all"
        if selected == "all":
            return True
        status = str((chunk.get("asr_qa") or {}).get("status") or "")
        if selected == "bad":
            return status in {"failed", "warning", "error"}
        return status == selected

    def _refresh_test_chapter_combo(self) -> None:
        """Populate the chapter selector used by test preview chunks."""
        if not hasattr(self, "_test_chapter_combo"):
            return
        current = self._test_chapter_combo.currentData()
        chapters = sorted({
            int(chunk.get("chapter_index", 0))
            for chunk in self._manifest_chunks
            if isinstance(chunk, dict) and self._asr_filter_accepts(chunk)
        })
        counts = {
            chapter: sum(
                1
                for chunk in self._manifest_chunks
                if int(chunk.get("chapter_index", 0)) == chapter and self._asr_filter_accepts(chunk)
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
                and self._asr_filter_accepts(chunk)
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
                effective_voice = self._effective_test_voice_label_for_chunk(chunk)
                self._test_chunk_combo.addItem(
                    t(
                        "synth.test_chunk_item",
                        num=chunk_index + 1,
                        voice=effective_voice,
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
        self._test_chunk_preview.blockSignals(True)
        self._test_chunk_preview.setPlainText(
            str(chunk.get("text") or "") if chunk else "",
        )
        self._test_chunk_preview.blockSignals(False)

    def _update_test_source_controls(self) -> None:
        """Switch the test panel between manifest chunk and custom text modes."""
        if not hasattr(self, "_test_source_combo"):
            return
        is_custom = (self._test_source_combo.currentData() or "chunk") == "custom"
        self._test_chunk_controls.setVisible(not is_custom)
        self._test_chunk_label.setVisible(not is_custom)
        self._chunk_edit_controls.setVisible(
            not is_custom and not self._dense_vertical_mode,
        )
        self._test_voice_combo.setVisible(is_custom)
        self._test_voice_label.setVisible(is_custom)
        self._test_text_stack.setCurrentIndex(1 if is_custom else 0)
        self._test_text_label.setText(
            t("synth.test_custom_text") if is_custom else t("synth.test_chunk_text"),
        )
        if not is_custom:
            self._update_test_chunk_preview()

    def _selected_test_chunk_identity(self) -> tuple[int, int] | None:
        data = self._test_chunk_combo.currentData()
        if not isinstance(data, tuple) or len(data) != 2:
            return None
        return int(data[0]), int(data[1])

    def _apply_manifest_editor_change(
        self,
        action,
        chapter_index: int,
        chunk_index: int,
        *,
        next_chunk_index: int | None = None,
    ) -> None:
        if not self._manifest_path or not self._manifest_path.exists():
            return
        try:
            data = json.loads(self._manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, TypeError):
            return
        try:
            changed = action(data)
        except ValueError as exc:
            self._status.setText(str(exc))
            return
        if not changed:
            return
        try:
            save_manifest(self._manifest_path, data)
        except (OSError, ValueError) as exc:
            self._status.setText(str(exc))
            return
        target_chunk = chunk_index if next_chunk_index is None else next_chunk_index
        self._load_chapters_from_manifest()
        self._select_test_chunk(chapter_index, target_chunk)
        self._status.setText(t("synth.chunk_editor_saved"))

    def _select_test_chunk(self, chapter_index: int, chunk_index: int) -> None:
        chapter_idx = self._test_chapter_combo.findData(chapter_index)
        if chapter_idx >= 0:
            self._test_chapter_combo.setCurrentIndex(chapter_idx)
        self._refresh_test_chunk_combo()
        chunk_idx = self._test_chunk_combo.findData((chapter_index, chunk_index))
        if chunk_idx >= 0:
            self._test_chunk_combo.setCurrentIndex(chunk_idx)
        self._update_test_chunk_preview()

    def _save_selected_chunk_text(self) -> None:
        identity = self._selected_test_chunk_identity()
        if identity is None:
            return
        chapter_index, chunk_index = identity
        text = self._test_chunk_preview.toPlainText().strip()
        if not text:
            return
        self._apply_manifest_editor_change(
            lambda data: _update_manifest_chunk_text(
                data,
                chapter_index,
                chunk_index,
                text,
            ),
            chapter_index,
            chunk_index,
        )

    def _split_selected_chunk(self) -> None:
        identity = self._selected_test_chunk_identity()
        if identity is None:
            return
        chapter_index, chunk_index = identity
        split_at = self._test_chunk_preview.textCursor().position()
        self._apply_manifest_editor_change(
            lambda data: _split_manifest_chunk_text(
                data,
                chapter_index,
                chunk_index,
                split_at,
            ),
            chapter_index,
            chunk_index,
            next_chunk_index=chunk_index + 1,
        )

    def _merge_selected_chunk(self) -> None:
        identity = self._selected_test_chunk_identity()
        if identity is None:
            return
        chapter_index, chunk_index = identity
        self._apply_manifest_editor_change(
            lambda data: _merge_manifest_chunk_with_next(
                data,
                chapter_index,
                chunk_index,
            ),
            chapter_index,
            chunk_index,
        )

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
        preview = _test_manifest_chunk_from_chunk(chunk)
        edited_text = self._test_chunk_preview.toPlainText().strip()
        if edited_text:
            preview["text"] = edited_text
        return [preview]

