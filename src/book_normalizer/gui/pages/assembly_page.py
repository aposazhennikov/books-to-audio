"""Assembly page — merge audio chunks into full chapters/book."""

from __future__ import annotations

import subprocess
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

from book_normalizer.gui.widgets.progress_widget import ProgressWidget


class AssemblyWorker(QThread):
    """Background worker for audio assembly."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, audio_dir: Path, output_dir: Path, pause_same: int, pause_change: int, parent=None):
        super().__init__(parent)
        self._audio_dir = audio_dir
        self._output_dir = output_dir
        self._pause_same = pause_same
        self._pause_change = pause_change

    def run(self) -> None:
        try:
            script = Path(__file__).resolve().parent.parent.parent.parent.parent / "scripts" / "assemble_chapter.py"

            wsl_script = self._to_wsl(script)
            wsl_audio = self._to_wsl(self._audio_dir)
            wsl_out = self._to_wsl(self._output_dir)

            cmd = [
                "wsl", "-e", "bash", "-c",
                f"source ~/venvs/qwen3tts/bin/activate && "
                f"python {wsl_script} "
                f"--audio-dir {wsl_audio} "
                f"--out {wsl_out} "
                f"--all "
                f"--pause-same {self._pause_same} "
                f"--pause-change {self._pause_change}",
            ]

            self.progress.emit("Assembling chapters...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if result.returncode == 0:
                self.finished.emit(result.stdout)
            else:
                self.error.emit(result.stderr or "Assembly failed")

        except Exception as exc:
            self.error.emit(str(exc))

    @staticmethod
    def _to_wsl(path: Path) -> str:
        p = str(path.resolve()).replace("\\", "/")
        if len(p) >= 2 and p[1] == ":":
            drive = p[0].lower()
            p = f"/mnt/{drive}{p[2:]}"
        return p


class AssemblyPage(QWidget):
    """Page for assembling audio chunks into full chapter/book files."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._audio_dir: Path | None = None
        self._output_dir: Path | None = None
        self._worker: AssemblyWorker | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Directory selection.
        dir_row = QHBoxLayout()
        self._dir_label = QLabel("No audio directory selected")
        self._dir_label.setStyleSheet("font-weight: bold;")
        dir_row.addWidget(self._dir_label, stretch=1)
        btn = QPushButton("Select Audio Dir")
        btn.clicked.connect(self._browse_dir)
        dir_row.addWidget(btn)
        layout.addLayout(dir_row)

        # Pause settings.
        settings = QFormLayout()
        self._pause_same = QSpinBox()
        self._pause_same.setRange(0, 5000)
        self._pause_same.setValue(300)
        self._pause_same.setSuffix(" ms")
        settings.addRow("Pause (same voice):", self._pause_same)

        self._pause_change = QSpinBox()
        self._pause_change.setRange(0, 5000)
        self._pause_change.setValue(600)
        self._pause_change.setSuffix(" ms")
        settings.addRow("Pause (voice change):", self._pause_change)
        layout.addLayout(settings)

        # Run button.
        self._btn_run = QPushButton("Assemble All Chapters")
        self._btn_run.setMinimumHeight(40)
        self._btn_run.setStyleSheet("font-size: 14px; font-weight: bold;")
        self._btn_run.clicked.connect(self._run_assembly)
        self._btn_run.setEnabled(False)
        layout.addWidget(self._btn_run)

        # Progress.
        self._progress = ProgressWidget()
        layout.addWidget(self._progress)

        # Output.
        self._output_label = QLabel("")
        self._output_label.setWordWrap(True)
        layout.addWidget(self._output_label)
        layout.addStretch()

    def set_audio_dir(self, audio_dir: Path, output_dir: Path) -> None:
        """Set audio chunks directory and output directory."""
        self._audio_dir = audio_dir
        self._output_dir = output_dir
        self._dir_label.setText(str(audio_dir))
        self._btn_run.setEnabled(True)

    def _browse_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select Audio Chunks Directory")
        if d:
            self._audio_dir = Path(d)
            self._output_dir = Path(d).parent
            self._dir_label.setText(d)
            self._btn_run.setEnabled(True)

    def _run_assembly(self) -> None:
        if not self._audio_dir or not self._output_dir:
            return

        self._btn_run.setEnabled(False)
        self._progress.set_status("Assembling...")

        self._worker = AssemblyWorker(
            self._audio_dir, self._output_dir,
            self._pause_same.value(), self._pause_change.value(),
        )
        self._worker.progress.connect(self._progress.set_status)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_finished(self, output: str) -> None:
        self._btn_run.setEnabled(True)
        self._progress.set_status("Assembly complete!")
        self._output_label.setText(output)

    def _on_error(self, msg: str) -> None:
        self._btn_run.setEnabled(True)
        self._progress.set_status(f"Error: {msg}")
