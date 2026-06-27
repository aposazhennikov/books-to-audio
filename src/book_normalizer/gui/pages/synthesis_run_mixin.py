"""Synthesis run controls for the synthesis page."""

from __future__ import annotations

import time
from importlib import import_module

from PyQt6.QtCore import QUrl
from PyQt6.QtMultimedia import QMediaPlayer

from book_normalizer.chunking.manifest_v2 import chunks_to_manifest, save_manifest
from book_normalizer.gui.i18n import t
from book_normalizer.gui.workers.tts_worker import TTSSynthesisWorker


def _tts_synthesis_worker_cls():
    """Return the worker via synthesis_page so existing monkeypatches still apply."""
    page_module = import_module("book_normalizer.gui.pages.synthesis_page")
    return getattr(page_module, "TTSSynthesisWorker", TTSSynthesisWorker)


class SynthesisRunMixin:
    """Start, stop, and label synthesis runs."""

    def _selected_chapter(self) -> int | None:
        selected = self._chapter_combo.currentData()
        return selected if selected and selected > 0 else None

    def run_synthesis(self) -> None:
        """Start full TTS synthesis for the loaded manifest."""
        self._start_synthesis()

    def _start_synthesis(self) -> None:
        output_dir = self._current_output_dir()
        if not self._manifest_path or not output_dir:
            return

        chapter = self._selected_chapter()

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            self._set_output_dir(output_dir)
            clone_config_path = self._build_temp_sample_voice_config()
        except (OSError, ValueError) as exc:
            self._status.setText(str(exc))
            self._progress.set_status(str(exc))
            return

        self._run_kind = "full"
        self._worker_handles_asr = self._asr_enable_check.isChecked()
        self._set_run_buttons_active(True)
        self._progress.reset()

        self._worker = _tts_synthesis_worker_cls()(
            manifest_path=self._manifest_path,
            output_dir=output_dir,
            model=self._selected_tts_engine_id_or_model(),
            chapter=chapter,
            batch_size=self._batch_size.value(),
            chunk_timeout=self._chunk_timeout.value(),
            clone_config=clone_config_path,
            models_dir=self._models_dir_edit.text().strip(),
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
        self._log_edit.clear()
        log_path = output_dir / "synthesis_log.txt"
        self._log_edit.appendPlainText(t("synth.log_path", path=str(log_path)))

        self._phase = "loading"
        self._phase_start = time.time()
        self._tick_timer.start()
        self._status.setText(t("synth.in_progress"))
        self._on_tick()

    def _start_test_synthesis(self) -> None:
        output_dir = self._current_output_dir()
        if not self._manifest_path or not output_dir:
            return

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            self._set_output_dir(output_dir)
            test_chunks = self._build_selected_test_chunks()
            if not test_chunks:
                raise ValueError(t("synth.test_no_chunk"))
            clone_config_path = self._build_temp_sample_voice_config()
        except (OSError, ValueError) as exc:
            self._status.setText(str(exc))
            self._progress.set_status(str(exc))
            return

        self._preview_output_dir = output_dir / "tts_test_preview"
        self._preview_output_dir.mkdir(parents=True, exist_ok=True)
        test_manifest = self._preview_output_dir / "test_manifest.json"
        preview_manifest = chunks_to_manifest(
            test_chunks,
            book_title="tts_test_preview",
            chunker="gui_test",
        )
        save_manifest(test_manifest, preview_manifest)

        self._last_test_audio_path = None
        self._btn_play_test.setEnabled(False)
        self._test_player.stop()
        self._test_player.setSource(QUrl())

        self._run_kind = "test"
        self._worker_handles_asr = False
        self._set_run_buttons_active(True)
        self._progress.reset()

        self._worker = _tts_synthesis_worker_cls()(
            manifest_path=test_manifest,
            output_dir=self._preview_output_dir,
            model=self._selected_tts_engine_id_or_model(),
            chapter=None,
            batch_size=1,
            chunk_timeout=self._chunk_timeout.value(),
            clone_config=clone_config_path,
            models_dir=self._models_dir_edit.text().strip(),
            temperature=self._temperature_spin.value(),
            top_p=self._top_p_spin.value(),
            top_k=self._top_k_spin.value(),
            repetition_penalty=self._repetition_penalty_spin.value(),
            max_new_tokens=self._max_new_tokens_spin.value(),
            seed=self._seed_spin.value(),
            speech_rate=self._speech_rate_value(),
            output_format=str(self._output_format_combo.currentData() or "flac"),
            merge_chapters=False,
            quality_loop=False,
            artifact_qa=False,
            asr_qa_after_synthesis=False,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.status.connect(self._on_status)
        self._worker.log_line.connect(self._on_log_line)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

        self._show_runtime_feedback(show_log=True)
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
        self._output_dir_edit.setEnabled(not active)
        self._btn_output_dir.setEnabled(not active)
        self._btn_install_models.setEnabled(not active)
        self._btn_asr_run.setEnabled(has_manifest and not active)
        self._refresh_quality_dashboard()

    def _set_model_install_active(self, active: bool) -> None:
        has_manifest = bool(self._manifest_path)
        self._btn_install_models.setEnabled(not active)
        self._btn_start.setEnabled(has_manifest and not active)
        self._btn_test.setEnabled(has_manifest and not active)
        self._btn_save_sample_voice.setEnabled(not active)
        self._btn_stop.setEnabled(False)
        self._models_dir_edit.setEnabled(not active)
        self._btn_models_dir.setEnabled(not active)
        self._btn_asr_run.setEnabled(has_manifest and not active)
        self._refresh_quality_dashboard()

    def _apply_action_labels(self) -> None:
        """Use short command labels on narrow windows."""
        if self._compact_mode:
            self._btn_test.setText(t("synth.compact_test_start"))
            self._btn_play_test.setText(t("synth.compact_test_play"))
            self._btn_start.setText(t("synth.compact_start"))
            self._btn_load.setText(t("synth.compact_load_manifest"))
            self._btn_save_sample_voice.setText(t("synth.compact_save_local_voice"))
            self._btn_save_chunk_text.setText(t("synth.compact_chunk_editor_save"))
            self._btn_merge_chunk.setText(t("synth.compact_chunk_editor_merge"))
            self._btn_asr_run.setText(t("synth.compact_asr_run_now"))
            self._btn_stop.setText(t("synth.stop"))
            return

        self._btn_load.setText(t("synth.load_manifest"))
        self._btn_test.setText(t("synth.test_start"))
        self._btn_play_test.setText(t("synth.test_play"))
        self._btn_start.setText(t("synth.start"))
        self._btn_save_sample_voice.setText(t("synth.save_local_voice"))
        self._btn_save_chunk_text.setText(t("synth.chunk_editor_save"))
        self._btn_merge_chunk.setText(t("synth.chunk_editor_merge"))
        self._btn_asr_run.setText(t("synth.asr_run_now"))
        self._btn_stop.setText(t("synth.stop"))

    def _toggle_test_playback(self) -> None:
        if not self._last_test_audio_path:
            return
        if self._test_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._test_player.pause()
        else:
            self._test_player.setPlaybackRate(1.0)
            self._test_player.play()

    def _on_test_playback_state(self, state: QMediaPlayer.PlaybackState) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._btn_play_test.setText(t("synth.test_pause"))
        else:
            self._btn_play_test.setText(
                t("synth.compact_test_play") if self._compact_mode else t("synth.test_play")
            )

