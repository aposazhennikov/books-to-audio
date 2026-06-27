"""Worker callbacks for the synthesis page."""

from __future__ import annotations

import json
import time
from pathlib import Path

from PyQt6.QtCore import QUrl

from book_normalizer.gui.i18n import t


class SynthesisCallbacksMixin:
    """Handle worker progress, finish, and error signals."""

    def _on_log_line(self, line: str) -> None:
        self._show_runtime_feedback(show_log=True)
        self._log_edit.appendPlainText(line)
        sb = self._log_edit.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_tick(self) -> None:
        """Update elapsed time display every second."""
        elapsed = int(time.time() - self._phase_start)
        m, s = divmod(elapsed, 60)
        time_str = f"{m}:{s:02d}" if m else t("time.seconds_short", sec=s)
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
        self._show_runtime_feedback()
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
        self._show_runtime_feedback()
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
                self._test_player.setPlaybackRate(1.0)
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
        self._load_chapters_from_manifest()
        if self._asr_enable_check.isChecked() and not self._worker_handles_asr:
            self._start_asr_qa_worker((output_dir, synthesized, skipped))
            return
        self._worker_handles_asr = False
        self.synthesis_finished.emit(output_dir, synthesized, skipped)

    def _on_error(self, msg: str) -> None:
        self._tick_timer.stop()
        self._phase = "idle"
        self._run_kind = "idle"
        self._worker_handles_asr = False
        self._set_run_buttons_active(False)
        self._show_runtime_feedback()
        self._progress.set_status(f"❌ {msg}")

        self.synthesis_failed.emit(msg)

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

