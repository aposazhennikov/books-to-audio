"""Assembly page — merge audio chunks into full chapters/book."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from book_normalizer.gui.i18n import t
from book_normalizer.gui.widgets.progress_widget import ProgressWidget


class AssemblyWorker(QThread):
    """Background worker for audio assembly."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(
        self,
        audio_dir: Path,
        output_dir: Path,
        pause_same: int,
        pause_change: int,
        manifest_path: Path | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._audio_dir = audio_dir
        self._output_dir = output_dir
        self._pause_same = pause_same
        self._pause_change = pause_change
        self._manifest_path = manifest_path

    def run(self) -> None:
        try:
            script = (
                Path(__file__).resolve().parent.parent.parent.parent.parent
                / "scripts"
                / "assemble_chapter.py"
            )

            source_args = (
                ["--manifest", str(self._manifest_path)]
                if self._manifest_path
                else ["--audio-dir", str(self._audio_dir)]
            )

            cmd = [
                sys.executable,
                "-u",
                str(script),
                *source_args,
                "--out",
                str(self._output_dir),
                "--all",
                "--pause-same",
                str(self._pause_same),
                "--pause-change",
                str(self._pause_change),
            ]

            self.progress.emit(t("asm.assembling"))
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if result.returncode == 0:
                self.finished.emit(result.stdout)
            else:
                self.error.emit(result.stderr or "Assembly failed")

        except Exception as exc:
            self.error.emit(str(exc))


class AssemblyPage(QWidget):
    """Page for assembling audio chunks into full chapter/book files."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._audio_dir: Path | None = None
        self._manifest_path: Path | None = None
        self._output_dir: Path | None = None
        self._worker: AssemblyWorker | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Directory selection ──
        dir_row = QHBoxLayout()
        dir_row.setSpacing(8)
        self._dir_label = QLabel()
        self._dir_label.setStyleSheet(
            "font-weight: 700; font-size: 13px; padding: 6px 12px;"
            "background: rgba(15,23,42,0.62); border: 1px solid rgba(148,163,184,0.12);"
            "border-radius: 8px;"
        )
        dir_row.addWidget(self._dir_label, stretch=1)

        self._btn_browse = QPushButton()
        self._btn_browse.clicked.connect(self._browse_dir)
        dir_row.addWidget(self._btn_browse)
        layout.addLayout(dir_row)

        # ── Pause settings ──
        settings = QFormLayout()
        settings.setHorizontalSpacing(16)
        settings.setVerticalSpacing(8)

        self._pause_same = QSpinBox()
        self._pause_same.setRange(0, 5000)
        self._pause_same.setValue(300)
        self._pause_same.setSuffix(" ms")
        self._pause_same_label = QLabel()
        settings.addRow(self._pause_same_label, self._pause_same)

        self._pause_change = QSpinBox()
        self._pause_change.setRange(0, 5000)
        self._pause_change.setValue(600)
        self._pause_change.setSuffix(" ms")
        self._pause_change_label = QLabel()
        settings.addRow(self._pause_change_label, self._pause_change)
        layout.addLayout(settings)

        # ── Run button ──
        self._btn_run = QPushButton()
        self._btn_run.setObjectName("primaryBtn")
        self._btn_run.setMinimumHeight(38)
        self._btn_run.clicked.connect(self._run_assembly)
        self._btn_run.setEnabled(False)
        layout.addWidget(self._btn_run)

        # ── Progress ──
        self._progress = ProgressWidget()
        layout.addWidget(self._progress)

        # ── Output ──
        self._output_label = QLabel("")
        self._output_label.setWordWrap(True)
        self._output_label.setStyleSheet(
            "color: rgba(226,232,240,0.62); font-size: 12px; padding: 4px 0;"
        )
        layout.addWidget(self._output_label)
        layout.addStretch()

        self.retranslate()

    def retranslate(self) -> None:
        """Update translatable strings."""
        if not self._audio_dir:
            self._dir_label.setText(t("asm.no_dir"))
        self._btn_browse.setText(t("asm.select_dir"))
        self._pause_same_label.setText(t("asm.pause_same"))
        self._pause_change_label.setText(t("asm.pause_change"))
        self._btn_run.setText(t("asm.run"))

    def set_audio_dir(self, audio_dir: Path, output_dir: Path) -> None:
        """Set audio chunks directory and output directory."""
        self._audio_dir = audio_dir
        self._manifest_path = None
        self._output_dir = output_dir
        self._dir_label.setText(str(audio_dir))
        self._btn_run.setEnabled(True)

    def set_manifest(self, manifest_path: Path, output_dir: Path) -> None:
        """Set a v2 manifest for manifest-ordered assembly."""
        self._manifest_path = manifest_path
        self._audio_dir = output_dir / "audio_chunks"
        self._output_dir = output_dir
        self._dir_label.setText(str(manifest_path))
        self._btn_run.setEnabled(True)

    def _browse_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, t("asm.select_dir"))
        if d:
            self._audio_dir = Path(d)
            self._manifest_path = None
            self._output_dir = Path(d).parent
            self._dir_label.setText(d)
            self._btn_run.setEnabled(True)

    def _run_assembly(self) -> None:
        if not self._audio_dir or not self._output_dir:
            return

        self._btn_run.setEnabled(False)
        self._progress.set_status(t("asm.assembling"))

        self._worker = AssemblyWorker(
            self._audio_dir,
            self._output_dir,
            self._pause_same.value(),
            self._pause_change.value(),
            manifest_path=self._manifest_path,
        )
        self._worker.progress.connect(self._progress.set_status)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_finished(self, output: str) -> None:
        self._btn_run.setEnabled(True)
        translated = self._translate_output(output)
        if "No WAV" in output or "No chapter" in output:
            self._progress.set_status(t("asm.no_wav_found"))
        else:
            self._progress.set_status(t("asm.complete"))
        self._output_label.setText(translated)

    def _on_error(self, msg: str) -> None:
        self._btn_run.setEnabled(True)
        self._progress.set_status(f"❌ {msg}")

    @staticmethod
    def _translate_output(text: str) -> str:
        """Replace known English phrases from WSL script with i18n."""
        import re
        text = text.replace("No WAV chunks in", t("asm.no_wav_in"))
        text = text.replace("No chapter dirs found in", t("asm.no_chapters_in"))
        text = re.sub(
            r"(\d+) chunks -> ([\d.]+)s",
            lambda m: t(
                "asm.chunk_stats",
                chunks=m.group(1),
                duration=m.group(2),
            ),
            text,
        )
        return text
