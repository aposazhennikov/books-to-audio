"""Assembly page — merge audio chunks into full chapters/book."""

from __future__ import annotations

import wave
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from book_normalizer.chunking.manifest_v2 import chunk_is_excluded
from book_normalizer.gui.i18n import t
from book_normalizer.gui.widgets.help_button import label_with_help, set_help_text
from book_normalizer.gui.widgets.progress_widget import ProgressWidget
from book_normalizer.tts.assembler import AudioAssembler
from book_normalizer.tts.manifest_assembly import (
    ChapterAssemblyResult,
    assemble_from_manifest,
    load_manifest_v2,
)

_MANUAL_REVIEW_GATE_KEY = "asm.production_gate_manual_review"
_MANUAL_REVIEW_GATE_MESSAGE = (
    "Package locked: listen to the assembled chapters and explicitly accept the "
    "release package."
)
_MANUAL_REVIEW_CHECK_TEXT = (
    "I listened to the assembled chapters and accept this package for production."
)


@dataclass(frozen=True)
class ProductionPackageReadiness:
    """Current GUI gate state for release package generation."""

    ready: bool
    message_key: str


@dataclass(frozen=True)
class AssemblyRunResult:
    """Structured assembly outcome for GUI status decisions."""

    output: str
    assembled_files: int
    skipped_chapters: int = 0
    missing_chunks: int = 0

    @property
    def has_audio(self) -> bool:
        return self.assembled_files > 0


class AssemblyWorker(QThread):
    """Background worker for audio assembly."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(object)
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
                result = _manifest_run_result(results)
            else:
                assembler = AudioAssembler(
                    self._output_dir,
                    pause_phrase_ms=self._pause_same,
                    pause_speaker_ms=self._pause_change,
                    strict_missing=False,
                )
                result = _legacy_run_result(assembler.assemble(), audio_dir=self._audio_dir)

            self.finished.emit(result)

        except Exception as exc:
            self.error.emit(str(exc))


class ProductionPreflightWorker(QThread):
    """Background worker for production metadata and packaging preflight."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(
        self,
        manifest_path: Path,
        output_dir: Path,
        *,
        package_outputs: bool = False,
        chapter_audio_dir: Path | None = None,
        dry_run_package: bool = True,
        allow_review_package: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self._manifest_path = manifest_path
        self._output_dir = output_dir
        self._package_outputs = package_outputs
        self._chapter_audio_dir = chapter_audio_dir
        self._dry_run_package = dry_run_package
        self._allow_review_package = allow_review_package

    def run(self) -> None:
        try:
            self.progress.emit(t("asm.production_running"))
            from book_normalizer.production.pipeline import run_production_preflight

            result = run_production_preflight(
                self._manifest_path,
                output_dir=self._output_dir / "production",
                package=self._package_outputs,
                chapter_audio_dir=self._chapter_audio_dir,
                dry_run_package=self._dry_run_package,
                allow_review_package=self._allow_review_package,
            )
            if result.package_report_path:
                self.finished.emit(
                    t(
                        "asm.production_package_done",
                        run=result.run_report_path,
                        package=result.package_report_path,
                        book=_package_book_path(result.package_report_path),
                    )
                )
            else:
                self.finished.emit(t("asm.production_done", path=result.run_report_path))
        except Exception as exc:
            self.error.emit(str(exc))


class AssemblyPage(QWidget):
    """Page for assembling audio chunks into full chapter/book files."""

    assembly_finished = pyqtSignal(str)
    assembly_failed = pyqtSignal(str)
    production_finished = pyqtSignal(str)
    production_failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._audio_dir: Path | None = None
        self._manifest_path: Path | None = None
        self._output_dir: Path | None = None
        self._worker: AssemblyWorker | None = None
        self._production_worker: ProductionPreflightWorker | None = None
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

        self._production_title = QLabel()
        self._production_title.setStyleSheet("font-weight: 800; font-size: 13px; color: #334155;")
        layout.addWidget(self._production_title)

        self._production_desc = QLabel()
        self._production_desc.setWordWrap(True)
        self._production_desc.setStyleSheet("color: rgba(51,65,85,0.72); font-size: 12px;")
        layout.addWidget(self._production_desc)

        self._production_gate_status = QLabel()
        self._production_gate_status.setWordWrap(True)
        self._production_gate_status.setStyleSheet("color: rgba(51,65,85,0.74); font-size: 12px;")
        layout.addWidget(self._production_gate_status)

        self._manual_review_check = QCheckBox()
        self._manual_review_check.toggled.connect(self._update_production_buttons)
        layout.addWidget(self._manual_review_check)

        production_row = QHBoxLayout()
        production_row.setSpacing(8)
        self._btn_production_preflight = QPushButton()
        self._btn_production_preflight.clicked.connect(self._run_production_preflight)
        self._btn_production_preflight.setEnabled(False)
        production_row.addWidget(self._btn_production_preflight)

        self._btn_production_package = QPushButton()
        self._btn_production_package.clicked.connect(self._run_production_package)
        self._btn_production_package.setEnabled(False)
        production_row.addWidget(self._btn_production_package)
        layout.addLayout(production_row)

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
        self._production_title.setText(t("asm.production_title"))
        self._production_desc.setText(t("asm.production_desc"))
        self._manual_review_check.setText(_MANUAL_REVIEW_CHECK_TEXT)
        self._btn_production_preflight.setText(t("asm.production_preflight"))
        self._btn_production_package.setText(t("asm.production_package"))
        self._update_production_buttons()

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
        self._manual_review_check.setChecked(False)
        self._dir_label.setText(str(audio_dir))
        self._btn_run.setEnabled(True)
        self._update_production_buttons()

    def set_manifest(self, manifest_path: Path, output_dir: Path) -> None:
        """Set a v2 manifest for manifest-ordered assembly."""
        self._manifest_path = manifest_path
        self._audio_dir = output_dir / "audio_chunks"
        self._output_dir = output_dir
        self._manual_review_check.setChecked(False)
        self._dir_label.setText(str(manifest_path))
        self._btn_run.setEnabled(True)
        self._update_production_buttons()

    def _browse_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, t("asm.select_dir"))
        if d:
            self._audio_dir = Path(d)
            self._manifest_path = None
            self._output_dir = Path(d).parent
            self._manual_review_check.setChecked(False)
            self._dir_label.setText(d)
            self._btn_run.setEnabled(True)
            self._update_production_buttons()

    def run_assembly(self) -> None:
        """Assemble synthesized chunks into chapter audio."""
        self._run_assembly()

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

    def _on_finished(self, result: AssemblyRunResult | str) -> None:
        self._btn_run.setEnabled(True)
        if isinstance(result, AssemblyRunResult):
            output = result.output
            has_audio = result.has_audio
        else:
            output = result
            has_audio = True
        translated = self._translate_output(output)
        self._progress.set_status(t("asm.complete") if has_audio else t("asm.no_wav_found"))
        self._output_label.setText(translated)
        self._update_production_buttons()
        self.assembly_finished.emit(output)

    def _on_error(self, msg: str) -> None:
        self._btn_run.setEnabled(True)
        self._progress.set_status(f"❌ {msg}")

        self.assembly_failed.emit(msg)

    def _production_package_readiness(self) -> ProductionPackageReadiness:
        if not self._manifest_path or not self._output_dir:
            return ProductionPackageReadiness(False, "asm.production_gate_no_manifest")
        try:
            manifest = load_manifest_v2(self._manifest_path)
        except Exception:
            return ProductionPackageReadiness(False, "asm.production_gate_manifest_error")

        chunks = list(_package_gate_chunks(manifest))
        if not chunks:
            return ProductionPackageReadiness(False, "asm.production_gate_no_chunks")
        if not all(bool(chunk.get("synthesized")) for chunk in chunks):
            return ProductionPackageReadiness(False, "asm.production_gate_audio_not_synthesized")
        if not all(_chunk_audio_exists(chunk, self._manifest_path) for chunk in chunks):
            return ProductionPackageReadiness(False, "asm.production_gate_audio_missing")
        if not all(_chunk_asr_passed(chunk) for chunk in chunks):
            return ProductionPackageReadiness(False, "asm.production_gate_asr")
        if not all(_chunk_production_qa_passed(chunk) for chunk in chunks):
            return ProductionPackageReadiness(False, "asm.production_gate_qa")
        if not _assembled_chapters_ready(manifest, self._output_dir):
            return ProductionPackageReadiness(False, "asm.production_gate_not_assembled")
        if not self._manual_review_check.isChecked():
            return ProductionPackageReadiness(False, _MANUAL_REVIEW_GATE_KEY)
        return ProductionPackageReadiness(True, "asm.production_gate_ready")

    def _update_production_buttons(self) -> None:
        can_run_preflight = bool(self._manifest_path and self._output_dir)
        readiness = self._production_package_readiness()
        self._btn_production_preflight.setEnabled(can_run_preflight)
        self._btn_production_package.setEnabled(readiness.ready)
        message = _production_gate_message(readiness.message_key)
        self._production_gate_status.setText(message)
        self._btn_production_package.setToolTip(message)

    def _run_production_preflight(self) -> None:
        self._start_production_preflight(
            package_outputs=False,
            dry_run_package=True,
            allow_review_package=False,
        )

    def run_production_package(self, *, require_ready: bool = True) -> None:
        """Run production preflight and package outputs."""
        self._run_production_package(require_ready=require_ready)

    def _run_production_package(self, *, require_ready: bool = True) -> None:
        if require_ready:
            readiness = self._production_package_readiness()
            if not readiness.ready:
                self._update_production_buttons()
                self._progress.set_status(_production_gate_message(readiness.message_key))
                return
        self._start_production_preflight(
            package_outputs=True,
            dry_run_package=False,
            allow_review_package=False,
        )

    def _start_production_preflight(
        self,
        *,
        package_outputs: bool,
        dry_run_package: bool,
        allow_review_package: bool,
    ) -> None:
        if not self._manifest_path or not self._output_dir:
            return
        self._btn_production_preflight.setEnabled(False)
        self._btn_production_package.setEnabled(False)
        self._progress.set_status(t("asm.production_running"))
        self._production_worker = ProductionPreflightWorker(
            self._manifest_path,
            self._output_dir,
            package_outputs=package_outputs,
            chapter_audio_dir=self._output_dir,
            dry_run_package=dry_run_package,
            allow_review_package=allow_review_package,
        )
        self._production_worker.progress.connect(self._progress.set_status)
        self._production_worker.finished.connect(self._on_production_finished)
        self._production_worker.error.connect(self._on_production_error)
        self._production_worker.start()

    def _on_production_finished(self, output: str) -> None:
        self._update_production_buttons()
        self._progress.set_status(t("asm.production_complete"))
        self._output_label.setText(output)
        self.production_finished.emit(output)

    def _on_production_error(self, msg: str) -> None:
        self._update_production_buttons()
        self._progress.set_status(f"вќЊ {msg}")
        self.production_failed.emit(msg)

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


def _manifest_run_result(results: list[ChapterAssemblyResult]) -> AssemblyRunResult:
    """Return structured GUI result for manifest assembly."""
    return AssemblyRunResult(
        output=_format_manifest_results(results),
        assembled_files=sum(1 for result in results if result.output_path),
        skipped_chapters=sum(1 for result in results if result.skipped),
        missing_chunks=sum(result.missing for result in results),
    )


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


def _legacy_run_result(result: dict[str, Path], *, audio_dir: Path) -> AssemblyRunResult:
    """Return structured GUI result for legacy manifest assembly."""
    return AssemblyRunResult(
        output=_format_legacy_results(result, audio_dir=audio_dir),
        assembled_files=len(result),
    )


def _package_gate_chunks(manifest: dict) -> list[dict]:
    """Return non-excluded chunks that must pass the release package gate."""
    chunks: list[dict] = []
    for chapter in manifest.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        for chunk in chapter.get("chunks", []):
            if isinstance(chunk, dict) and not chunk_is_excluded(chunk):
                chunks.append(chunk)
    return chunks


def _production_gate_message(message_key: str) -> str:
    """Return user-facing package gate text, including local manual-review copy."""
    if message_key == _MANUAL_REVIEW_GATE_KEY:
        return _MANUAL_REVIEW_GATE_MESSAGE
    return t(message_key)


def _chunk_audio_exists(chunk: dict, manifest_path: Path) -> bool:
    audio_file = str(chunk.get("audio_file") or "").strip()
    if not audio_file:
        return False
    audio_path = Path(audio_file)
    if not audio_path.is_absolute():
        audio_path = manifest_path.parent / audio_path
    return audio_path.exists()


def _chunk_asr_passed(chunk: dict) -> bool:
    asr = chunk.get("asr_qa")
    return isinstance(asr, dict) and str(asr.get("status") or "").strip().lower() == "passed"


def _chunk_production_qa_passed(chunk: dict) -> bool:
    if bool(chunk.get("failed")):
        return False
    status = str(chunk.get("qa_status") or "").strip().lower()
    perceptual = chunk.get("perceptual_qa")
    perceptual_status = (
        str(perceptual.get("status") or "").strip().lower()
        if isinstance(perceptual, dict)
        else ""
    )
    return status == "passed" and (not perceptual_status or perceptual_status == "passed")


def _assembled_chapters_ready(manifest: dict, output_dir: Path) -> bool:
    chapter_numbers: list[int] = []
    for chapter in manifest.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chunks = [
            chunk
            for chunk in chapter.get("chunks", [])
            if isinstance(chunk, dict) and not chunk_is_excluded(chunk)
        ]
        if chunks:
            chapter_numbers.append(int(chapter.get("chapter_index") or 0) + 1)
    return bool(chapter_numbers) and all(
        _assembled_chapter_exists(output_dir, chapter_number)
        for chapter_number in chapter_numbers
    )


def _assembled_chapter_exists(output_dir: Path, chapter_number: int) -> bool:
    return any(
        (output_dir / pattern).exists()
        for pattern in (
            f"chapter_{chapter_number:03d}_mastered.mp3",
            f"chapter_{chapter_number:03d}_mastered.wav",
            f"chapter_{chapter_number:03d}.mp3",
            f"chapter_{chapter_number:03d}.wav",
        )
    )


def _make_pause_spin_compact(spin: QSpinBox) -> None:
    """Match pause fields to compact centered numeric controls."""
    spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
    line_edit = spin.lineEdit()
    line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
    line_edit.setMinimumHeight(0)
    spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
    spin.setFixedWidth(128)
    spin.setFixedHeight(38)


def _package_book_path(report_path: Path) -> str:
    """Return the final M4B path from a package report when available."""
    try:
        import json

        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return ""
    return str(report.get("m4b_path") or "")


def _wav_duration(path: Path) -> float:
    """Return WAV duration in seconds for assembly summaries."""
    try:
        with wave.open(str(path), "rb") as wav:
            return wav.getnframes() / wav.getframerate()
    except (OSError, wave.Error, ZeroDivisionError):
        return 0.0
