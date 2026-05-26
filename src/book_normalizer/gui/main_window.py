"""Main application window with tabbed interface."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from book_normalizer.gui.i18n import SUPPORTED_LANGUAGES, set_language, t
from book_normalizer.gui.pages.assembly_page import AssemblyPage
from book_normalizer.gui.pages.normalize_page import NormalizePage
from book_normalizer.gui.pages.roles_page import RolesPage
from book_normalizer.gui.pages.synthesis_page import SynthesisPage
from book_normalizer.gui.pages.voices_page import VoicesPage
from book_normalizer.gui.resources import application_icon
from book_normalizer.gui.ui_scaler import apply_widget_scale_metrics, make_app_font
from book_normalizer.gui.widgets.progress_widget import ProgressWidget


class MainWindow(QMainWindow):
    """Main application window for Books-to-Audio pipeline."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Books to Audio")
        self._ui_scale = 1.0
        self.setMinimumSize(760, 520)
        self.resize(1180, 760)
        self.setWindowIcon(application_icon())
        self._output_dir: Path | None = None
        self._auto_pipeline_active = False
        self._setup_ui()
        self._connect_signals()
        self._retranslate()

    def _setup_ui(self) -> None:
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(14, 12, 14, 8)
        layout.setSpacing(10)

        # ── Header row ──
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        self._title = QLabel()
        self._title.setFont(make_app_font(22, QFont.Weight.Bold))
        self._title.setStyleSheet("color: #14233a;")
        header_row.addWidget(self._title)

        self._btn_auto_pipeline = QPushButton()
        self._btn_auto_pipeline.setObjectName("successBtn")
        self._btn_auto_pipeline.setMinimumHeight(34)
        self._btn_auto_pipeline.setMinimumWidth(220)
        self._btn_auto_pipeline.clicked.connect(self._start_auto_pipeline)
        header_row.addWidget(self._btn_auto_pipeline)

        header_row.addStretch()

        # Language switcher.
        self._lang_label = QLabel()
        self._lang_label.setStyleSheet(
            "color: rgba(51,65,85,0.70); font-size: 12px; font-weight: 600;"
        )
        header_row.addWidget(self._lang_label)

        self._lang_combo = QComboBox()
        for code, label in SUPPORTED_LANGUAGES:
            self._lang_combo.addItem(label, code)
        self._lang_combo.setMinimumWidth(164)
        self._lang_combo.setMaximumWidth(240)
        self._lang_combo.setStyleSheet(
            "QComboBox { font-size: 13px; font-weight: 600; }"
        )
        self._lang_combo.currentIndexChanged.connect(self._on_language_changed)
        header_row.addWidget(self._lang_combo)

        layout.addLayout(header_row)

        # ── Tabs ──
        self._tabs = QTabWidget()
        self._tabs.tabBar().setUsesScrollButtons(False)
        self._normalize_page = NormalizePage()
        self._roles_page = RolesPage()
        self._voices_page = VoicesPage()
        self._synthesis_page = SynthesisPage()
        self._assembly_page = AssemblyPage()

        self._tabs.addTab(self._normalize_page, "")
        self._tabs.addTab(self._roles_page, "")
        self._tabs.addTab(self._voices_page, "")
        self._tabs.addTab(self._synthesis_page, "")
        self._tabs.addTab(self._assembly_page, "")

        layout.addWidget(self._tabs, stretch=1)

        # ── Status bar ──
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)

    def set_ui_scale(self, scale: float) -> None:
        """Apply global UI scale to window-specific sizing."""

        self._ui_scale = scale
        self.setMinimumSize(
            max(700, round(760 * min(scale, 1.0))),
            max(480, round(520 * min(scale, 1.0))),
        )
        self._title.setFont(make_app_font(max(16, round(22 * scale)), QFont.Weight.Bold))
        self._lang_combo.setMinimumWidth(max(148, round(164 * scale)))
        self._lang_combo.setMaximumWidth(max(190, round(240 * scale)))
        for child in self.findChildren(QWidget):
            if child is not self and hasattr(child, "set_ui_scale"):
                child.set_ui_scale(scale)
        apply_widget_scale_metrics(self, scale)
        self._sync_tab_labels()

    def resizeEvent(self, event) -> None:  # noqa: N802
        """Use shorter tab titles on narrow windows."""
        super().resizeEvent(event)
        self._sync_tab_labels()

    def _connect_signals(self) -> None:
        """Wire up page transitions."""
        original_finished = self._normalize_page._on_finished

        def patched_finished(book):
            original_finished(book)
            self._on_normalization_done(book)

        self._normalize_page._on_finished = patched_finished

        self._roles_page.segments_ready.connect(self._on_roles_segments_ready)
        self._normalize_page.normalization_failed.connect(self._on_auto_pipeline_failed)
        self._roles_page.role_extraction_failed.connect(self._on_auto_pipeline_failed)
        self._voices_page.chunks_built.connect(self._on_chunks_built)
        self._synthesis_page.output_dir_changed.connect(
            self._on_synthesis_output_dir_changed,
        )
        self._synthesis_page.synthesis_finished.connect(self._on_synthesis_done)
        self._synthesis_page.synthesis_failed.connect(self._on_auto_pipeline_failed)
        self._assembly_page.assembly_finished.connect(self._on_assembly_done)
        self._assembly_page.assembly_failed.connect(self._on_auto_pipeline_failed)

    def _on_language_changed(self, _index: int) -> None:
        """Handle language combo change."""
        lang = self._lang_combo.currentData()
        set_language(lang)
        self._retranslate()
        self._normalize_page.retranslate()
        self._roles_page.retranslate()
        self._voices_page.retranslate()
        self._synthesis_page.retranslate()
        self._assembly_page.retranslate()
        for progress in self.findChildren(ProgressWidget):
            progress.retranslate()

    def _retranslate(self) -> None:
        """Update all translatable strings in the main window."""
        self.setWindowTitle(t("app.title"))
        self._title.setText(t("app.title"))
        self._lang_label.setText(t("app.lang_label"))
        self._btn_auto_pipeline.setToolTip(t("auto.tooltip"))
        self._statusbar.showMessage(t("app.ready"))

        self._sync_tab_labels()

    def _sync_tab_labels(self) -> None:
        """Keep the main tabs readable without scroll arrows at small widths."""
        if not hasattr(self, "_tabs"):
            return

        very_compact = self.width() < 820 and self._ui_scale >= 1.2
        compact = self.width() < 860
        if very_compact:
            self._btn_auto_pipeline.setText(t("auto.button_tiny"))
        elif compact:
            self._btn_auto_pipeline.setText(t("auto.button_short"))
        else:
            self._btn_auto_pipeline.setText(t("auto.button"))
        suffix = "_short" if compact else ""
        full_keys = [
            "tab.normalize",
            "tab.roles",
            "tab.chunks",
            "tab.voices",
            "tab.assemble",
        ]
        for index, key in enumerate(full_keys):
            label = str(index + 1) if very_compact else t(f"{key}{suffix}")
            self._tabs.setTabText(index, label)
            self._tabs.setTabToolTip(index, t(key))

    def _selected_book_path(self) -> Path | None:
        """Return the selected source book path when it exists."""
        raw = self._normalize_page._selected_path or self._normalize_page._path_label.text()
        if not raw or raw == t("norm.no_file"):
            return None
        path = Path(raw)
        return path if path.exists() else None

    def _start_auto_pipeline(self) -> None:
        """Run the complete overnight audiobook pipeline with quality-first settings."""
        source = self._selected_book_path()
        if source is None:
            self._tabs.setCurrentIndex(0)
            self._statusbar.showMessage(t("auto.need_file"))
            return
        if self._auto_pipeline_active:
            return

        self._auto_pipeline_active = True
        self._btn_auto_pipeline.setEnabled(False)
        self._tabs.setCurrentIndex(0)
        self._apply_auto_quality_settings()
        self._statusbar.showMessage(t("auto.normalizing"))
        self._normalize_page.run_normalization(cache_choice="restore")

    def _apply_auto_quality_settings(self) -> None:
        """Configure pages for highest-quality unattended generation."""
        normalize = self._normalize_page
        normalize._llm_normalize.setChecked(True)
        normalize._ocr_dpi.setValue(600)
        ocr_idx = normalize._ocr_mode.findText("compare")
        if ocr_idx >= 0:
            normalize._ocr_mode.setCurrentIndex(ocr_idx)
        psm_idx = normalize._ocr_psm.findData(6)
        if psm_idx >= 0:
            normalize._ocr_psm.setCurrentIndex(psm_idx)

        roles = self._roles_page
        roles._llm_endpoint.setText(normalize._llm_endpoint.text())
        roles._llm_model.setText(normalize._llm_model.text())

        voices = self._voices_page
        mode_idx = voices._speaker_mode.findData("llm")
        if mode_idx >= 0:
            voices._speaker_mode.setCurrentIndex(mode_idx)
        stress_idx = voices._stress_mode.findData("double_vowel")
        if stress_idx >= 0:
            voices._stress_mode.setCurrentIndex(stress_idx)
        voices._chunk_size.setValue(400)

        synthesis = self._synthesis_page
        synthesis._mode_tabs.setCurrentIndex(1)
        synthesis._model_combo.setCurrentIndex(0)
        synthesis._batch_size.setValue(1)
        synthesis._resume_check.setChecked(True)
        synthesis._chunk_timeout.setValue(900)
        synthesis._compile_check.setChecked(False)
        synthesis._sage_check.setChecked(False)
        synthesis._merge_chapters_check.setChecked(True)
        format_idx = synthesis._output_format_combo.findData("wav")
        if format_idx >= 0:
            synthesis._output_format_combo.setCurrentIndex(format_idx)
        synthesis._temperature_spin.setValue(1.0)
        synthesis._top_p_spin.setValue(0.8)
        synthesis._top_k_spin.setValue(20)
        synthesis._repetition_penalty_spin.setValue(1.05)
        synthesis._max_new_tokens_spin.setValue(4096)
        synthesis._seed_spin.setValue(-1)
        synthesis._set_speech_rate_value(1.0)

        self._assembly_page._pause_same.setValue(300)
        self._assembly_page._pause_change.setValue(600)

    def _on_normalization_done(self, book: object) -> None:
        """Called when normalization completes."""
        path_text = self._normalize_page._path_label.text()
        no_file = t("norm.no_file")
        if path_text and path_text != no_file:
            from book_normalizer.cli import _build_output_dir
            self._output_dir = _build_output_dir(Path(path_text), Path("output")).resolve()
            self._output_dir.mkdir(parents=True, exist_ok=True)

            self._roles_page.set_book(book, self._output_dir)
            self._voices_page.set_book(book, self._output_dir)
            self._statusbar.showMessage(
                t("status.norm_done", n=len(book.chapters))
            )
            self._tabs.setCurrentIndex(1)
            if self._auto_pipeline_active:
                self._statusbar.showMessage(t("auto.roles"))
                QTimer.singleShot(
                    0,
                    lambda: self._roles_page.run_role_extraction(cache_choice="restore"),
                )

    def _on_roles_segments_ready(self, segments_path: str, _roles_path: str) -> None:
        """Load LLM segments into the chunk editor."""
        self._voices_page.load_segments_manifest(Path(segments_path))
        self._statusbar.showMessage(t("status.roles_done"))
        self._tabs.setCurrentIndex(2)
        if self._auto_pipeline_active:
            self._statusbar.showMessage(t("auto.chunks"))
            QTimer.singleShot(0, self._voices_page._build_tts_chunks)

    def _on_chunks_built(self, chunks_path: str) -> None:
        """Called when TTS chunks are built from segments."""
        mp = Path(chunks_path)
        out_dir = self._output_dir or mp.parent
        self._synthesis_page.set_manifest(mp, out_dir)
        self._set_assembly_target(mp, out_dir)
        self._statusbar.showMessage(t("status.voices_done"))
        if self._auto_pipeline_active:
            self._tabs.setCurrentIndex(3)
            self._apply_auto_quality_settings()
            self._statusbar.showMessage(t("auto.synthesis"))
            QTimer.singleShot(0, self._synthesis_page._start_synthesis)

    def _on_synthesis_done(
        self,
        _audio_dir: str,
        _synthesized: int,
        _skipped: int,
    ) -> None:
        """Continue an active auto pipeline after TTS synthesis."""
        if not self._auto_pipeline_active:
            return
        self._tabs.setCurrentIndex(4)
        self._statusbar.showMessage(t("auto.assembly"))
        QTimer.singleShot(0, self._assembly_page._run_assembly)

    def _on_assembly_done(self, _output: str) -> None:
        """Finish an active auto pipeline after assembly."""
        if not self._auto_pipeline_active:
            return
        self._auto_pipeline_active = False
        self._btn_auto_pipeline.setEnabled(True)
        self._tabs.setCurrentIndex(4)
        self._statusbar.showMessage(t("auto.complete"))

    def _on_auto_pipeline_failed(self, msg: str) -> None:
        """Stop the auto pipeline when any background stage reports an error."""
        if not self._auto_pipeline_active:
            return
        self._auto_pipeline_active = False
        self._btn_auto_pipeline.setEnabled(True)
        self._statusbar.showMessage(t("auto.failed", msg=msg))

    def _on_synthesis_output_dir_changed(
        self,
        output_dir_text: str,
        manifest_path_text: str,
    ) -> None:
        """Keep assembly target in sync with the synthesis output folder."""
        out_dir = Path(output_dir_text)
        self._output_dir = out_dir
        if manifest_path_text:
            self._set_assembly_target(Path(manifest_path_text), out_dir)

    def _set_assembly_target(self, manifest_path: Path, output_dir: Path) -> None:
        """Point the assembly page at the folder used by synthesis."""
        mp = manifest_path
        out_dir = output_dir
        audio_dir = out_dir / "audio_chunks"
        if mp.name.endswith("_v2.json") or mp.name == "chunks_manifest_v2.json":
            self._assembly_page.set_manifest(mp, out_dir)
        else:
            self._assembly_page.set_audio_dir(audio_dir, out_dir)
