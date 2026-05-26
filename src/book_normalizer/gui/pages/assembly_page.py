"""Assembly page — merge audio chunks into full chapters/book."""

from __future__ import annotations

import wave
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
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
from book_normalizer.gui.widgets.help_button import label_with_help, set_help_text
from book_normalizer.gui.widgets.progress_widget import ProgressWidget
from book_normalizer.tts.assembler import AudioAssembler
from book_normalizer.tts.manifest_assembly import (
    ChapterAssemblyResult,
    assemble_from_manifest,
    load_manifest_v2,
)


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
            self.progress.emit(t("asm.assembling"))
            if self._manifest_path:
                manifest = load_manifest_v2(self._manifest_path)
                results = assemble_from_manifest(
                    manifest,
                    self._output_dir,
                    pause_same_voice_ms=self._pause_same,
                    pause_voice_change_ms=self._pause_change,
                    strict_missing=False,
                )
                output = _format_manifest_results(results)
            else:
                assembler = AudioAssembler(
                    self._output_dir,
                    pause_phrase_ms=self._pause_same,
                    pause_speaker_ms=self._pause_change,
                    strict_missing=False,
                )
                output = _format_legacy_results(
                    assembler.assemble(),
                    audio_dir=self._audio_dir,
                )

            self.finished.emit(output)

        except Exception as exc:
            self.error.emit(str(exc))


class AssemblyPage(QWidget):
    """Page for assembling audio chunks into full chapter/book files."""

    assembly_finished = pyqtSignal(str)
    assembly_failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._audio_dir: Path | None = None
        self._manifest_path: Path | None = None
        self._output_dir: Path | None = None
        self._worker: AssemblyWorker | None = None
        self._help_buttons: dict[str, object] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Directory selection ──
        dir_row = QHBoxLayout()
        dir_row.setSpacing(8)
        self._dir_label = QLabel()
        self._dir_label.setWordWrap(True)
        self._dir_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse,
        )
        self._dir_label.setStyleSheet(
            "font-weight: 700; font-size: 13px; padding: 6px 12px;"
            "background: rgba(255,255,255,0.86);"
            "border: 1px solid rgba(91,115,142,0.18);"
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
        settings.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow,
        )
        settings.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)

        self._pause_same = QSpinBox()
        self._pause_same.setRange(0, 5000)
        self._pause_same.setValue(300)
        self._pause_same.setSuffix(" ms")
        _make_pause_spin_compact(self._pause_same)
        self._pause_same_label = QLabel()
        settings.addRow(
            self._label_with_help(self._pause_same_label, "asm.pause_same_help"),
            self._pause_same,
        )

        self._pause_change = QSpinBox()
        self._pause_change.setRange(0, 5000)
        self._pause_change.setValue(600)
        self._pause_change.setSuffix(" ms")
        _make_pause_spin_compact(self._pause_change)
        self._pause_change_label = QLabel()
        settings.addRow(
            self._label_with_help(
                self._pause_change_label,
                "asm.pause_change_help",
            ),
            self._pause_change,
        )
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
            "color: rgba(51,65,85,0.70); font-size: 12px; padding: 4px 0;"
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
        self._pause_same.setToolTip(t("asm.pause_same_help"))
        self._pause_change.setToolTip(t("asm.pause_change_help"))
        self._update_help_buttons()
        self._btn_run.setText(t("asm.run"))

    def _label_with_help(self, label: QLabel, help_key: str) -> QWidget:
        """Create a form label with a reusable help button."""
        wrap, button = label_with_help(label, t(help_key))
        self._help_buttons[help_key] = button
        return wrap

    def _update_help_buttons(self) -> None:
        """Refresh tooltip text after language changes."""
        for help_key, button in self._help_buttons.items():
            set_help_text(button, t(help_key))

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
        self.assembly_finished.emit(output)

    def _on_error(self, msg: str) -> None:
        self._btn_run.setEnabled(True)
        self._progress.set_status(f"❌ {msg}")

        self.assembly_failed.emit(msg)

    @staticmethod
    def _translate_output(text: str) -> str:
        """Replace known English phrases from assembly tooling with i18n."""
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


def _format_manifest_results(results: list[ChapterAssemblyResult]) -> str:
    """Return user-facing assembly details for v2 manifest output."""
    lines: list[str] = []
    for result in results:
        lines.extend(f"  {message}" for message in result.messages)
        if result.output_path:
            duration = _wav_duration(result.output_path)
            size_mb = result.output_path.stat().st_size / 1024 / 1024
            lines.append(
                f"  {result.output_path.name}: "
                f"{result.chunks} chunks -> {duration:.1f}s ({size_mb:.1f} MB)"
            )
        elif result.skipped:
            lines.append(
                f"  Chapter {result.chapter_number:03d}: "
                "no synthesized chunks found, skipping."
            )
    return "\n".join(lines) if lines else "No WAV chunks in manifest"


def _format_legacy_results(result: dict[str, Path], *, audio_dir: Path) -> str:
    """Return user-facing assembly details for legacy synthesis_manifest output."""
    if not result:
        return f"No WAV chunks in {audio_dir}"
    lines = []
    for label, path in sorted(result.items()):
        duration = _wav_duration(path)
        size_mb = path.stat().st_size / 1024 / 1024
        lines.append(f"  {label}: {path.name} -> {duration:.1f}s ({size_mb:.1f} MB)")
    return "\n".join(lines)


def _make_pause_spin_compact(spin: QSpinBox) -> None:
    """Match pause fields to compact centered numeric controls."""
    spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
    spin.lineEdit().setAlignment(Qt.AlignmentFlag.AlignCenter)
    spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
    spin.setFixedWidth(128)
    spin.setFixedHeight(38)


def _wav_duration(path: Path) -> float:
    """Return WAV duration in seconds for assembly summaries."""
    try:
        with wave.open(str(path), "rb") as wav:
            return wav.getnframes() / wav.getframerate()
    except (OSError, wave.Error, ZeroDivisionError):
        return 0.0
