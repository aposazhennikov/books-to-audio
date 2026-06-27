"""ASR QA and quality actions for the synthesis page."""

from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

from book_normalizer.chunking.manifest_v2 import save_manifest
from book_normalizer.gui.i18n import t
from book_normalizer.gui.pages.synthesis_manifest import _iter_manifest_chunks
from book_normalizer.gui.workers.tts_worker import AsrQaWorker, TTSSynthesisWorker
from book_normalizer.tts.quality_gate import chunk_quality_status


class SynthesisAsrMixin:
    """Run ASR QA and quality follow-up actions."""

    def _selected_asr_model(self) -> str:
        return self._asr_model_combo.currentText().strip() or "small"

    def _selected_asr_device(self) -> str:
        return str(self._asr_device_combo.currentData() or "auto")

    def _run_asr_qa_now(self) -> None:
        self._start_asr_qa_worker()

    def run_asr_qa(
        self,
        pending_finish: tuple[str, int, int] | None = None,
    ) -> None:
        """Run ASR quality checks for the loaded manifest."""
        self._start_asr_qa_worker(pending_finish)

    def _start_failed_resynthesis(self) -> None:
        """Resynthesize chunks reset or marked bad by QA."""
        output_dir = self._current_output_dir()
        if not self._manifest_path or not output_dir:
            return
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            self._set_output_dir(output_dir)
            clone_config_path = self._build_temp_sample_voice_config()
            self._reset_quality_bad_chunks(max_attempts=2)
        except (OSError, ValueError) as exc:
            self._status.setText(str(exc))
            self._progress.set_status(str(exc))
            return

        self._run_kind = "full"
        self._worker_handles_asr = self._asr_enable_check.isChecked()
        self._set_run_buttons_active(True)
        self._progress.reset()
        workflow = (
            self._workflow_path_edit.text().strip()
            if hasattr(self, "_workflow_path_edit")
            else ""
        )
        self._worker = TTSSynthesisWorker(
            manifest_path=self._manifest_path,
            output_dir=output_dir,
            model=self._selected_tts_engine_id_or_model(),
            chapter=self._selected_chapter(),
            batch_size=self._batch_size.value(),
            chunk_timeout=self._chunk_timeout.value(),
            clone_config=clone_config_path,
            models_dir=self._models_dir_edit.text().strip(),
            comfyui_url=self._comfyui_url_edit.text().strip() if hasattr(self, "_comfyui_url_edit") else "http://localhost:8188",
            workflow_path=workflow,
            failed_only=True,
            temperature=self._temperature_spin.value(),
            top_p=self._top_p_spin.value(),
            top_k=self._top_k_spin.value(),
            repetition_penalty=self._repetition_penalty_spin.value(),
            max_new_tokens=self._max_new_tokens_spin.value(),
            seed=self._seed_spin.value(),
            speech_rate=self._speech_rate_value(),
            output_format=str(self._output_format_combo.currentData() or "flac"),
            merge_chapters=self._merge_chapters_check.isChecked(),
            quality_loop=True,
            artifact_qa=True,
            asr_qa_after_synthesis=self._worker_handles_asr,
            asr_model=self._selected_asr_model(),
            asr_device=self._selected_asr_device(),
            max_resynthesis_attempts=2,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.status.connect(self._on_status)
        self._worker.log_line.connect(self._on_log_line)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()
        self._show_runtime_feedback(show_log=True)
        self._status.setText(t("synth.quality_resynthesizing"))

    def _reset_quality_bad_chunks(self, *, max_attempts: int) -> None:
        if not self._manifest_path or not self._manifest_path.exists():
            return
        from book_normalizer.tts.quality_gate import (
            reset_chunk_for_resynthesis,
        )

        data = json.loads(self._manifest_path.read_text(encoding="utf-8"))
        changed = False
        for chunk in _iter_manifest_chunks(data):
            status = chunk_quality_status(chunk)
            if status not in {"failed", "warning"}:
                continue
            reason = str(chunk.get("resynthesis_reason") or f"quality dashboard: {status}")
            changed = reset_chunk_for_resynthesis(
                chunk,
                reason=reason,
                max_attempts=max_attempts,
            ) or changed
        if changed:
            save_manifest(self._manifest_path, data)
            self._load_chapters_from_manifest()

    def _start_asr_qa_worker(
        self,
        pending_finish: tuple[str, int, int] | None = None,
    ) -> None:
        if not self._manifest_path or not self._manifest_path.exists():
            return
        self._show_runtime_feedback(show_log=True)
        self._pending_synthesis_finish = pending_finish
        self._btn_asr_run.setEnabled(False)
        self._btn_asr_open_report.setEnabled(False)
        self._btn_asr_open_diff.setEnabled(False)
        self._asr_status.setText(t("synth.asr_running"))
        self._progress.set_busy(t("synth.asr_running"))

        self._asr_worker = AsrQaWorker(
            self._manifest_path,
            model=self._selected_asr_model(),
            device=self._selected_asr_device(),
            timeout_seconds=float(self._asr_timeout_spin.value()),
            run_artifact=True,
        )
        self._asr_worker.status.connect(self._asr_status.setText)
        self._asr_worker.log_line.connect(self._on_log_line)
        self._asr_worker.finished.connect(self._on_asr_finished)
        self._asr_worker.error.connect(self._on_asr_error)
        self._asr_worker.start()

    def _on_asr_finished(
        self,
        report_path: str,
        status: str,
        failed: int,
        warning: int,
        error: int,
    ) -> None:
        self._last_asr_report_path = Path(report_path)
        self._btn_asr_run.setEnabled(bool(self._manifest_path))
        self._btn_asr_open_report.setEnabled(True)
        self._btn_asr_open_diff.setEnabled(True)
        message = t(
            "synth.asr_done",
            status=status,
            failed=failed,
            warning=warning,
            error=error,
            path=report_path,
        )
        self._asr_status.setText(message)
        self._progress.set_status(message)
        self._load_chapters_from_manifest()
        self._finish_pending_synthesis_after_asr()

    def _on_asr_error(self, msg: str) -> None:
        self._btn_asr_run.setEnabled(bool(self._manifest_path))
        self._asr_status.setText(t("synth.asr_error", msg=msg))
        self._progress.set_status(t("synth.asr_error", msg=msg))
        self._finish_pending_synthesis_after_asr()

    def _finish_pending_synthesis_after_asr(self) -> None:
        pending = self._pending_synthesis_finish
        self._pending_synthesis_finish = None
        if pending is None:
            return
        output_dir, synthesized, skipped = pending
        self.synthesis_finished.emit(output_dir, synthesized, skipped)

    def _open_asr_report(self) -> None:
        self._open_local_file(self._last_asr_report_path)

    def _open_asr_diff(self) -> None:
        diff_path = (
            self._last_asr_report_path.with_suffix(".diff.txt")
            if self._last_asr_report_path
            else None
        )
        self._open_local_file(diff_path)

    def _master_passed_chapters(self) -> None:
        if not self._manifest_path:
            return
        output_dir = self._current_output_dir() or self._manifest_path.parent
        try:
            from book_normalizer.tts.mastering import master_manifest

            result = master_manifest(
                self._manifest_path,
                output_dir=output_dir,
                output_format=self._selected_master_format(),
                chapter_filter=self._selected_chapter(),
            )
        except Exception as exc:
            self._status.setText(str(exc))
            self._progress.set_status(str(exc))
            return
        message = t("synth.quality_master_done", n=len(result.files), path=result.output_dir)
        self._status.setText(message)
        self._progress.set_status(message)
        self._on_log_line(t("synth.quality_master_report", path=result.report_path))

    def _selected_master_format(self) -> str:
        value = str(self._output_format_combo.currentData() or "both").lower()
        return value if value in {"wav", "mp3", "both"} else "both"

    def _open_local_file(self, path: Path | None) -> None:
        if path and path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _select_first_asr_issue(self) -> None:
        for chunk in self._manifest_chunks:
            if not isinstance(chunk, dict):
                continue
            status = str((chunk.get("asr_qa") or {}).get("status") or "")
            if status not in {"failed", "warning", "error"}:
                continue
            chapter_index = int(chunk.get("chapter_index", 0))
            chunk_index = int(chunk.get("chunk_index", 0))
            bad_idx = self._asr_filter_combo.findData("bad")
            if bad_idx >= 0:
                self._asr_filter_combo.setCurrentIndex(bad_idx)
            self._select_test_chunk(chapter_index, chunk_index)
            self._status.setText(t("synth.asr_selected_issue"))
            return
        self._status.setText(t("synth.asr_no_issues"))

