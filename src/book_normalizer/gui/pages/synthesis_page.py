"""Synthesis page — TTS generation with progress and ETA."""

from __future__ import annotations

import json
import time
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from book_normalizer.gui.i18n import t
from book_normalizer.gui.widgets.progress_widget import ProgressWidget
from book_normalizer.gui.workers.tts_worker import TTSSynthesisWorker


MODELS = [
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
]


class SynthesisPage(QWidget):
    """Page for running TTS synthesis with progress tracking."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._manifest_path: Path | None = None
        self._output_dir: Path | None = None
        self._worker: TTSSynthesisWorker | None = None
        self._chapter_map: dict[int, int] = {}
        self._phase = "idle"
        self._phase_start = 0.0
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(1000)
        self._tick_timer.timeout.connect(self._on_tick)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Manifest selection.
        file_row = QHBoxLayout()
        file_row.setSpacing(8)
        self._manifest_label = QLabel()
        self._manifest_label.setWordWrap(True)
        self._manifest_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse,
        )
        self._manifest_label.setStyleSheet(
            "font-weight: 700; font-size: 13px; padding: 6px 12px;"
            "background: rgba(255,255,255,0.04); border-radius: 6px;",
        )
        file_row.addWidget(self._manifest_label, stretch=1)

        self._btn_load = QPushButton()
        self._btn_load.clicked.connect(self._browse_manifest)
        file_row.addWidget(self._btn_load)
        layout.addLayout(file_row)

        # Settings.
        settings = QFormLayout()
        settings.setHorizontalSpacing(16)
        settings.setVerticalSpacing(8)

        self._model_combo = QComboBox()
        self._model_combo.addItems(MODELS)
        self._model_label = QLabel()
        settings.addRow(self._model_label, self._model_combo)

        self._model_hint = QLabel()
        self._model_hint.setWordWrap(True)
        self._model_hint.setStyleSheet(
            "color: rgba(255,255,255,0.4); font-size: 11px;"
            "background: transparent; border: none;"
            "padding: 0 0 4px 0;",
        )
        settings.addRow("", self._model_hint)

        self._batch_size = QSpinBox()
        self._batch_size.setRange(1, 8)
        self._batch_size.setValue(1)
        self._batch_size.setMaximumWidth(120)
        self._batch_label = QLabel()
        settings.addRow(self._batch_label, self._batch_size)

        self._batch_hint = QLabel()
        self._batch_hint.setWordWrap(True)
        self._batch_hint.setStyleSheet(
            "color: rgba(255,255,255,0.4); font-size: 11px;"
            "background: transparent; border: none;"
            "padding: 0 0 4px 0;",
        )
        settings.addRow("", self._batch_hint)

        self._chunk_timeout = QSpinBox()
        self._chunk_timeout.setRange(30, 1800)
        self._chunk_timeout.setValue(300)
        self._chunk_timeout.setSingleStep(30)
        self._chunk_timeout.setSuffix(" с")
        self._chunk_timeout.setMaximumWidth(120)
        self._chunk_timeout_label = QLabel()
        settings.addRow(self._chunk_timeout_label, self._chunk_timeout)

        self._chapter_combo = QComboBox()
        self._chapter_combo.setMinimumWidth(200)
        self._chapter_label = QLabel()
        settings.addRow(self._chapter_label, self._chapter_combo)

        self._chapter_info = QLabel()
        self._chapter_info.setStyleSheet(
            "color: rgba(255,255,255,0.4); font-size: 11px;"
            "background: transparent; border: none;"
            "padding: 0 0 4px 0;",
        )
        settings.addRow("", self._chapter_info)

        self._resume_check = QCheckBox()
        self._resume_label = QLabel()
        settings.addRow(self._resume_label, self._resume_check)

        self._resume_hint = QLabel()
        self._resume_hint.setWordWrap(True)
        self._resume_hint.setStyleSheet(
            "color: rgba(255,255,255,0.4); font-size: 11px;"
            "background: transparent; border: none;"
            "padding: 0 0 4px 0;",
        )
        settings.addRow("", self._resume_hint)

        self._compile_check = QCheckBox()
        self._compile_label = QLabel()
        settings.addRow(self._compile_label, self._compile_check)

        self._compile_hint = QLabel()
        self._compile_hint.setWordWrap(True)
        self._compile_hint.setStyleSheet(
            "color: rgba(255,255,255,0.4); font-size: 11px;"
            "background: transparent; border: none;"
            "padding: 0 0 4px 0;",
        )
        settings.addRow("", self._compile_hint)

        layout.addLayout(settings)

        # Action buttons.
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_start = QPushButton()
        self._btn_start.setObjectName("successBtn")
        self._btn_start.setMinimumHeight(44)
        self._btn_start.clicked.connect(self._start_synthesis)
        self._btn_start.setEnabled(False)
        btn_row.addWidget(self._btn_start)

        self._btn_stop = QPushButton()
        self._btn_stop.setObjectName("dangerBtn")
        self._btn_stop.setMinimumHeight(44)
        self._btn_stop.clicked.connect(self._stop_synthesis)
        self._btn_stop.setEnabled(False)
        btn_row.addWidget(self._btn_stop)

        layout.addLayout(btn_row)

        # Progress.
        self._progress = ProgressWidget()
        layout.addWidget(self._progress)

        # Log (collapsible).
        self._log_edit = QPlainTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setMaximumHeight(120)
        self._log_edit.setStyleSheet(
            "font-family: 'Cascadia Code', Consolas, monospace;"
            "font-size: 11px; background: rgba(0,0,0,0.3);"
            "border-radius: 4px; padding: 6px;",
        )
        self._log_edit.setPlaceholderText(t("synth.log_placeholder"))
        layout.addWidget(self._log_edit)

        # Status.
        self._status = QLabel()
        self._status.setWordWrap(True)
        self._status.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse,
        )
        self._status.setStyleSheet(
            "color: rgba(255,255,255,0.6); font-size: 12px;"
            "padding: 4px 0;",
        )
        layout.addWidget(self._status)
        layout.addStretch()

        self.retranslate()

    def retranslate(self) -> None:
        """Update translatable strings."""
        if not self._manifest_path:
            self._manifest_label.setText(t("synth.no_manifest"))
        self._btn_load.setText(t("synth.load_manifest"))
        self._model_label.setText(t("synth.model"))
        self._model_hint.setText(t("synth.model_hint"))
        self._model_combo.setToolTip(t("synth.model_hint"))
        self._batch_label.setText(t("synth.batch_size"))
        self._batch_hint.setText(t("synth.batch_hint"))
        self._batch_size.setToolTip(t("synth.batch_hint"))
        self._chunk_timeout_label.setText(t("synth.chunk_timeout"))
        self._chunk_timeout.setToolTip(t("synth.chunk_timeout_hint"))
        self._chapter_label.setText(t("synth.chapter"))
        self._resume_label.setText(t("synth.resume"))
        self._resume_check.setText(t("synth.resume_check"))
        self._resume_hint.setText(t("synth.resume_hint"))
        self._compile_label.setText(t("synth.compile"))
        self._compile_check.setText(t("synth.compile_check"))
        self._compile_hint.setText(t("synth.compile_hint"))
        self._btn_start.setText(t("synth.start"))
        self._btn_stop.setText(t("synth.stop"))
        self._status.setText(t("synth.waiting"))
        self._refresh_chapter_combo()

    def set_manifest(self, manifest_path: Path, output_dir: Path) -> None:
        """Set the manifest file and output directory."""
        self._manifest_path = manifest_path
        self._output_dir = output_dir
        self._manifest_label.setText(str(manifest_path))
        self._btn_start.setEnabled(True)
        self._load_chapters_from_manifest()

    def _browse_manifest(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("synth.load_manifest"),
            "",
            "JSON (*.json)",
        )
        if path:
            p = Path(path)
            self._manifest_path = p
            self._output_dir = p.parent
            self._manifest_label.setText(str(p))
            self._btn_start.setEnabled(True)
            self._load_chapters_from_manifest()

    def _load_chapters_from_manifest(self) -> None:
        """Parse manifest and populate chapter combo with real data."""
        if not self._manifest_path or not self._manifest_path.exists():
            return
        try:
            data = json.loads(
                self._manifest_path.read_text(encoding="utf-8"),
            )
            chapter_chunks: dict[int, int] = {}
            for item in data:
                ch = item.get("chapter_index", 0)
                chapter_chunks[ch] = chapter_chunks.get(ch, 0) + 1
            self._chapter_map = chapter_chunks
            self._refresh_chapter_combo()
        except (json.JSONDecodeError, OSError):
            pass

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
            label = t(
                "synth.chapter_item",
                num=ch_idx + 1,
                chunks=cnt,
            )
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

    def _start_synthesis(self) -> None:
        if not self._manifest_path or not self._output_dir:
            return

        selected = self._chapter_combo.currentData()
        chapter = selected if selected and selected > 0 else None

        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._progress.reset()

        self._worker = TTSSynthesisWorker(
            manifest_path=self._manifest_path,
            output_dir=self._output_dir,
            model=self._model_combo.currentText(),
            chapter=chapter,
            batch_size=self._batch_size.value(),
            resume=self._resume_check.isChecked(),
            chunk_timeout=self._chunk_timeout.value(),
            use_compile=self._compile_check.isChecked(),
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.status.connect(self._on_status)
        self._worker.log_line.connect(self._on_log_line)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()
        self._log_edit.clear()
        if self._output_dir:
            log_path = self._output_dir / "synthesis_log.txt"
            self._log_edit.appendPlainText(
                t("synth.log_path", path=str(log_path)),
            )
        self._phase = "loading"
        self._phase_start = time.time()
        self._tick_timer.start()
        self._status.setText(t("synth.in_progress"))
        self._on_tick()

    def _stop_synthesis(self) -> None:
        self._tick_timer.stop()
        if self._worker:
            self._worker.cancel()
        self._btn_stop.setEnabled(False)

    def _on_log_line(self, line: str) -> None:
        self._log_edit.appendPlainText(line)
        sb = self._log_edit.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_tick(self) -> None:
        """Update elapsed time display every second."""
        elapsed = int(time.time() - self._phase_start)
        m, s = divmod(elapsed, 60)
        time_str = f"{m}:{s:02d}" if m else f"{s} сек"
        if self._phase == "loading":
            self._progress.set_busy(
                t("synth.loading_model") + f"  [{time_str}]",
            )
        elif self._phase == "synth":
            self._progress.set_busy(
                t("synth.synthesizing") + f"  [{time_str}]",
            )

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
        if self._phase == "loading":
            self._phase = "synth"
        self._tick_timer.stop()
        self._progress.set_progress(current, total, eta)
        parts = [t("synth.progress_done", current=current, total=total)]
        if remaining or (total - current) > 0:
            parts.append(
                t("synth.progress_remaining", n=remaining or (total - current)),
            )
        if chunk_chars > 0 and chunk_sec > 0:
            parts.append(
                t(
                    "synth.progress_last_chunk",
                    chars=chunk_chars,
                    sec=chunk_sec,
                ),
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
            self._progress.set_busy(
                t("synth.model_ready", sec=elapsed),
            )
        else:
            self._progress.set_busy(msg)

    def _on_finished(
        self,
        output_dir: str,
        synthesized: int,
        skipped: int,
    ) -> None:
        self._tick_timer.stop()
        self._phase = "idle"
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._progress.set_progress(1, 1, "")
        self._status.setText(
            t(
                "synth.done_detail",
                synthesized=synthesized,
                skipped=skipped,
                path=output_dir,
            ),
        )

    def _on_error(self, msg: str) -> None:
        self._tick_timer.stop()
        self._phase = "idle"
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._progress.set_status(f"❌ {msg}")
