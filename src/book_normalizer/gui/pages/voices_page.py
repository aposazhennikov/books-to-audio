"""Chunk editing page — segment review, role assignment, and TTS chunk export."""

from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from book_normalizer.gui.i18n import t
from book_normalizer.gui.ui_scaler import apply_combo_content_width
from book_normalizer.gui.widgets.progress_widget import ProgressWidget
from book_normalizer.gui.widgets.voice_preview import VoicePreviewPanel
from book_normalizer.gui.widgets.voice_table import VoiceTableWidget
from book_normalizer.gui.workers.tts_worker import ExportSegmentsWorker
from book_normalizer.languages import normalize_book_language
from book_normalizer.llm.model_router import PRIMARY_QWEN3_MODEL
from book_normalizer.runtime_paths import configured_ollama_endpoint


class SaveVoiceManifestWorker(QThread):
    """Save a segment/chunk manifest without blocking the GUI thread."""

    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(
        self,
        *,
        path: Path,
        segments: list[dict],
        manifest_is_v2: bool,
        manifest_meta: dict,
        parent=None,
    ):
        super().__init__(parent)
        self._path = path
        self._segments = segments
        self._manifest_is_v2 = manifest_is_v2
        self._manifest_meta = manifest_meta

    def run(self) -> None:
        try:
            data: object = self._segments
            if self._manifest_is_v2 or self._path.name.endswith("_v2.json"):
                from book_normalizer.chunking.manifest import chunks_to_v2_manifest

                data = chunks_to_v2_manifest(
                    self._segments,
                    book_title=str(
                        self._manifest_meta.get("book_title") or self._path.parent.name,
                    ),
                    chunker=str(self._manifest_meta.get("chunker") or "gui"),
                    model=str(self._manifest_meta.get("model") or ""),
                    max_chunk_chars=self._manifest_meta.get("max_chunk_chars"),
                )
            self._path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.finished.emit(str(self._path))
        except Exception as exc:
            self.error.emit(str(exc))


class BuildTtsChunksWorker(QThread):
    """Build TTS chunks and write the v2 manifest off the GUI thread."""

    finished = pyqtSignal(str, int)
    error = pyqtSignal(str)

    def __init__(
        self,
        *,
        segments: list[dict],
        output_dir: Path,
        book_title: str,
        language: str,
        max_chunk_chars: int,
        parent=None,
    ):
        super().__init__(parent)
        self._segments = segments
        self._output_dir = output_dir
        self._book_title = book_title
        self._language = language
        self._max_chunk_chars = max_chunk_chars

    def run(self) -> None:
        try:
            from book_normalizer.chunking.manifest import chunks_to_v2_manifest
            from book_normalizer.chunking.voice_splitter import (
                build_chunks_from_segments,
            )

            chunks = build_chunks_from_segments(
                self._segments,
                max_chunk_chars=self._max_chunk_chars,
            )
            self._output_dir.mkdir(parents=True, exist_ok=True)
            chunks_path = self._output_dir / "chunks_manifest_v2.json"
            manifest = chunks_to_v2_manifest(
                chunks,
                book_title=self._book_title,
                language=self._language,
                chunker="gui",
                max_chunk_chars=self._max_chunk_chars,
            )
            chunks_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.finished.emit(str(chunks_path), len(chunks))
        except Exception as exc:
            self.error.emit(str(exc))


class VoicesPage(QWidget):
    """Page for smart segment review, role assignment, and TTS chunk export."""

    chunks_built = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._book = None
        self._output_dir: Path | None = None
        self._manifest_path: Path | None = None
        self._worker: ExportSegmentsWorker | None = None
        self._save_worker: SaveVoiceManifestWorker | None = None
        self._build_worker: BuildTtsChunksWorker | None = None
        self._ui_scale = 1.0
        self._compact_mode = False
        self._llm_layout_compact: bool | None = None
        self._setup_ui()

    # ── UI setup ──

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Top: settings and preview are separated so the page stays usable on
        # small screens and high DPI scaling.
        self._top_tabs = QTabWidget()
        self._top_tabs.setObjectName("voiceTopTabs")
        self._top_tabs.currentChanged.connect(self._on_top_tab_changed)

        # Left panel: settings + actions.
        left_panel = QWidget()
        self._settings_panel = left_panel
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        settings_strip_panel = QWidget()
        settings_strip = QHBoxLayout(settings_strip_panel)
        settings_strip.setContentsMargins(0, 0, 0, 0)
        settings_strip.setSpacing(10)
        self._settings_strip = settings_strip

        settings_fields_panel = QWidget()
        self._settings_fields_panel = settings_fields_panel
        settings = QGridLayout(settings_fields_panel)
        self._settings_layout = settings
        settings.setContentsMargins(0, 0, 0, 0)
        settings.setHorizontalSpacing(16)
        settings.setVerticalSpacing(6)
        settings.setColumnStretch(0, 0)
        settings.setColumnStretch(1, 0)

        # Speaker mode.
        self._speaker_mode = QComboBox()
        self._speaker_mode.currentIndexChanged.connect(
            self._on_speaker_mode_changed,
        )
        self._speaker_mode_label = QLabel()
        self._speaker_mode_label.setToolTip(t("voice.speaker_mode_hint"))
        settings.addWidget(self._speaker_mode_label, 0, 0)
        settings.addWidget(self._speaker_mode, 1, 0)

        self._speaker_mode_hint = QLabel()
        self._speaker_mode_hint.setWordWrap(True)
        self._speaker_mode_hint.setStyleSheet(
            "color: rgba(51,65,85,0.62); font-size: 10px;"
            "padding: 0 0 4px 0;",
        )
        settings.addWidget(self._speaker_mode_hint, 2, 0, 1, 2)

        # Advanced TTS chunk size. Kept as a hidden value so automated runs can
        # still tune it without exposing a confusing bare number in the review UI.
        self._chunk_size = QSpinBox(self)
        self._chunk_size.setRange(30, 2000)
        self._chunk_size.setValue(600)
        self._chunk_size.setSingleStep(10)
        self._chunk_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._chunk_size.lineEdit().setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._chunk_size.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._chunk_size.setFixedWidth(128)
        self._chunk_size.setFixedHeight(38)
        self._chunk_size.setVisible(False)
        self._chunk_size_label = QLabel(self)
        self._chunk_size_label.setVisible(False)

        self._stress_mode = QComboBox()
        self._stress_mode_label = QLabel()
        settings.addWidget(self._stress_mode_label, 0, 1)
        settings.addWidget(self._stress_mode, 1, 1)

        settings_strip.addWidget(settings_fields_panel, 0, Qt.AlignmentFlag.AlignVCenter)

        # LLM config panel (hidden by default).
        self._llm_panel = QWidget()
        llm_layout = QGridLayout(self._llm_panel)
        self._llm_layout = llm_layout
        llm_layout.setContentsMargins(0, 0, 0, 0)
        llm_layout.setHorizontalSpacing(8)
        llm_layout.setVerticalSpacing(0)
        llm_layout.setColumnStretch(0, 0)
        llm_layout.setColumnStretch(1, 1)

        self._llm_provider = QComboBox()
        self._llm_provider_label = QLabel()
        self._llm_provider.currentIndexChanged.connect(
            self._on_llm_provider_changed,
        )
        self._llm_provider.setMinimumHeight(28)
        self._llm_provider.setMinimumWidth(220)
        self._llm_provider.setMaximumWidth(420)
        self._llm_provider.setProperty("skipContentWidth", True)

        self._llm_endpoint_label = QLabel()
        self._llm_endpoint = QLineEdit(configured_ollama_endpoint())
        self._llm_endpoint.setMinimumHeight(28)

        self._llm_model_label = QLabel()
        self._llm_model = QLineEdit(PRIMARY_QWEN3_MODEL)
        self._llm_model.setMinimumHeight(28)

        self._llm_api_key_label = QLabel()
        self._llm_api_key = QLineEdit()
        self._llm_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._llm_api_key.setMinimumHeight(28)
        self._llm_api_key.setPlaceholderText("sk-...")
        self._apply_llm_layout(compact=False)

        self._llm_panel.setVisible(False)
        settings_strip.addWidget(self._llm_panel, 0, Qt.AlignmentFlag.AlignVCenter)
        settings_strip.addStretch(1)
        left_layout.addWidget(settings_strip_panel)

        # Action buttons.
        self._action_panel = QWidget()
        action_row = QHBoxLayout(self._action_panel)
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(8)

        self._btn_detect = QPushButton()
        self._btn_detect.setObjectName("primaryBtn")
        self._btn_detect.setMinimumHeight(38)
        self._btn_detect.setMinimumWidth(260)
        self._btn_detect.setMaximumWidth(360)
        self._btn_detect.clicked.connect(self._run_detection)
        self._btn_detect.setEnabled(False)
        action_row.addWidget(self._btn_detect)
        self._load_gap = QSpacerItem(32, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        action_row.addItem(self._load_gap)

        self._btn_load = QPushButton()
        self._btn_load.setMaximumWidth(150)
        self._btn_load.clicked.connect(self._load_manifest)
        action_row.addWidget(self._btn_load)

        self._btn_save = QPushButton()
        self._btn_save.setMaximumWidth(150)
        self._btn_save.clicked.connect(self._save_manifest)
        self._btn_save.setEnabled(False)
        action_row.addWidget(self._btn_save)

        self._btn_build = QPushButton()
        self._btn_build.setMinimumHeight(34)
        self._btn_build.setMaximumWidth(300)
        self._btn_build.clicked.connect(self._build_tts_chunks)
        self._btn_build.setEnabled(False)
        self._btn_build.setStyleSheet(
            "QPushButton {"
            "  background: rgba(204,251,241,0.78);"
            "  color: #0f766e;"
            "  border: 1px solid rgba(20,184,166,0.30);"
            "  border-radius: 8px; font-weight: 700;"
            "  padding: 6px 16px;"
            "}"
            "QPushButton:hover {"
            "  background: rgba(153,246,228,0.86);"
            "}"
            "QPushButton:disabled {"
            "  color: rgba(71,85,105,0.42);"
            "  background: rgba(226,232,240,0.56);"
            "  border-color: rgba(148,163,184,0.14);"
            "}",
        )
        action_row.addWidget(self._btn_build)
        action_row.addStretch(1)
        left_layout.addWidget(self._action_panel)

        self._action_status = QLabel("")
        self._action_status.setWordWrap(False)
        self._action_status.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self._action_status.setStyleSheet(
            "color: rgba(15,118,110,0.92); font-size: 11px;"
            "font-weight: 700; padding: 0 2px;",
        )
        self._action_status.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse,
        )
        self._action_status.setVisible(False)
        left_layout.addWidget(self._action_status)

        self._progress = ProgressWidget()
        left_layout.addWidget(self._progress)

        # Manifest path display.
        self._manifest_label = QLabel("")
        self._manifest_label.setWordWrap(False)
        self._manifest_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self._manifest_label.setStyleSheet(
            "color: rgba(51,65,85,0.62); font-size: 10px;"
            "padding: 2px 0;",
        )
        self._manifest_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse,
        )
        self._manifest_label.setVisible(False)
        left_layout.addWidget(self._manifest_label)

        left_layout.addStretch()

        # Right panel: voice preview. Content remains wheel/touchpad scrollable,
        # but the visual bar stays hidden to keep the tab clean at high zoom.
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)

        self._preview_title = QLabel()
        self._preview_title.setStyleSheet(
            "font-weight: 700; font-size: 14px;"
            "color: rgba(30,41,59,0.86); padding: 4px 0;",
        )
        right_layout.addWidget(self._preview_title)

        scroll = QScrollArea()
        scroll.setObjectName("voicePreviewScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )
        scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }",
        )
        self._voice_preview = VoicePreviewPanel()
        scroll.setWidget(self._voice_preview)
        right_layout.addWidget(scroll)

        left_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        self._top_tabs.addTab(left_panel, "")
        self._top_tabs.addTab(right_panel, "")
        layout.addWidget(self._top_tabs, stretch=2)

        # Bottom: voice assignment table.
        self._voice_table = VoiceTableWidget()
        self._voice_table.data_changed.connect(
            lambda: self._btn_save.setEnabled(True),
        )
        self._voice_table.data_changed.connect(
            lambda: self._btn_build.setEnabled(True),
        )
        self._voice_table.data_changed.connect(
            lambda: self._update_stats(self._voice_table.get_segments()),
        )
        layout.addWidget(self._voice_table, stretch=3)

        # Stats.
        self._stats_label = QLabel("")
        self._stats_label.setStyleSheet(
            "color: rgba(51,65,85,0.70); font-size: 12px;"
            "font-weight: 600; padding: 4px 0;",
        )
        layout.addWidget(self._stats_label)

        self.retranslate()
        self._sync_compact_mode()
        self._sync_chunk_review_visibility()

    # ── Translations ──

    def retranslate(self) -> None:
        """Update translatable strings."""
        selected_mode = self._current_speaker_mode()
        selected_stress_mode = self._current_stress_mode()
        self._populate_speaker_mode_combo(selected_mode)
        self._populate_stress_mode_combo(selected_stress_mode)
        self._speaker_mode_label.setText(t("voice.speaker_mode"))
        self._speaker_mode_label.setToolTip(t("voice.speaker_mode_hint"))
        self._update_speaker_mode_hint()
        self._chunk_size_label.setText(t("voice.max_chunk"))
        self._chunk_size.setToolTip(t("voice.max_chunk_hint"))
        self._stress_mode_label.setText(t("voice.stress_mode"))
        self._stress_mode.setToolTip(t("voice.stress_mode_hint"))
        self._btn_detect.setText(t("voice.detect"))
        self._btn_load.setText(t("voice.load_manifest"))
        self._btn_load.setToolTip(t("voice.load_manifest_tip"))
        self._btn_save.setText(t("voice.save_manifest"))
        self._btn_save.setToolTip(t("voice.save_manifest_tip"))
        self._btn_build.setText(t("voice.build_chunks"))
        if self._action_status.text():
            self._sync_action_status_visibility()
        self._preview_title.setText(t("chunks.preset_panel"))
        self._top_tabs.setTabText(0, t("chunks.settings_panel"))
        self._top_tabs.setTabText(1, t("chunks.preset_panel"))

        self._llm_provider_label.setText(t("voice.llm_provider"))
        self._llm_provider.clear()
        self._llm_provider.addItem(t("voice.llm_local"), "local")
        self._llm_provider.addItem(t("voice.llm_openai"), "openai")
        self._sync_llm_provider_width()
        self._llm_endpoint_label.setText(t("voice.llm_endpoint"))
        self._llm_model_label.setText(t("voice.llm_model"))
        self._llm_api_key_label.setText(t("voice.llm_api_key"))
        self._update_llm_placeholders()
        self._sync_llm_field_visibility()

        self._voice_table.retranslate()
        self._voice_preview.retranslate()
        self._sync_compact_mode()

    def resizeEvent(self, event) -> None:  # noqa: N802
        """Keep the voice table readable as the page width changes."""
        super().resizeEvent(event)
        self._sync_compact_mode()
        self._sync_settings_panel_height()

    def set_ui_scale(self, scale: float) -> None:
        """Keep the settings panel tall enough when global UI zoom changes."""
        self._ui_scale = max(0.8, min(1.45, scale))
        self._voice_table.set_ui_scale(self._ui_scale)
        self._sync_compact_mode()
        self._sync_settings_panel_height()

    def _sync_settings_panel_height(self) -> None:
        """Balance the scrollable settings area against the assignment table."""
        if self._top_tabs.currentIndex() == 1:
            self._top_tabs.setMinimumHeight(max(320, round(280 * self._ui_scale)))
            self._top_tabs.setMaximumHeight(16777215)
            return

        width_compact = self._is_width_compact()
        height_compact = self.height() < 760
        ultra_dense = self.height() < 430
        content_needed = self._settings_panel.sizeHint().height()
        if self._top_tabs.tabBar().isVisible():
            content_needed += self._top_tabs.tabBar().sizeHint().height()
        content_needed += round((8 if height_compact else 18) * self._ui_scale)
        if ultra_dense:
            target = max(164, round(112 * self._ui_scale))
            minimum = 164
        elif width_compact:
            target = max(224, round(178 * self._ui_scale), content_needed)
            minimum = 224
        elif height_compact:
            target = max(176, round(154 * self._ui_scale), content_needed)
            minimum = 176
        else:
            target = max(188, round(188 * self._ui_scale), content_needed)
            minimum = 188
        if self.height() > 0:
            has_segments = bool(self._voice_table.get_segments())
            if has_segments and self._worker is None:
                target = min(
                    target,
                    max(
                        content_needed,
                        round((146 if height_compact else 158) * self._ui_scale),
                    ),
                )
            editor_visible = has_segments and not self._voice_table._dense_mode
            if ultra_dense:
                table_reserve = 145
            elif editor_visible and height_compact:
                table_reserve = max(330, round(280 * self._ui_scale))
            elif editor_visible:
                table_reserve = max(430, round(300 * self._ui_scale))
            elif height_compact:
                table_reserve = 360
            else:
                table_reserve = max(260, round(260 * self._ui_scale))
            target = min(target, max(minimum, self.height() - table_reserve))
        self._top_tabs.setMinimumHeight(target)
        self._top_tabs.setMaximumHeight(target)

    def _on_top_tab_changed(self, _index: int) -> None:
        """Show chunk review widgets only inside the review subtab."""
        if not hasattr(self, "_voice_table"):
            return
        self._sync_chunk_review_visibility()
        self._refresh_loaded_layout()
        if self._top_tabs.currentIndex() == 1 and hasattr(self, "_voice_preview"):
            self._voice_preview.refresh_library()

    def _sync_chunk_review_visibility(self) -> None:
        """Keep the preset library free from chunk-review controls."""
        if not hasattr(self, "_voice_table") or not hasattr(self, "_stats_label"):
            return
        review_visible = self._top_tabs.currentIndex() == 0
        self._voice_table.setVisible(review_visible)
        self._stats_label.setVisible(review_visible and not self._compact_mode and not self._voice_table._dense_mode)

    def _sync_compact_mode(self) -> None:
        """Switch heavy table controls into compact mode on narrow widths."""
        width_compact = self._is_width_compact()
        height_compact = self.height() < 760
        editor_dense = self.height() < 600
        controls_compact = width_compact or height_compact
        ultra_dense = self.height() < 430
        dense = ultra_dense or (
            editor_dense and not width_compact and self.width() >= 1500
        )
        table_width = self._voice_table.width() if self._voice_table.width() > 0 else self.width()
        table_compact_threshold = max(960, round(1060 * self._ui_scale * self._ui_scale))
        table_width_compact = table_width < table_compact_threshold
        self._compact_mode = controls_compact
        self._voice_table.set_compact_mode(table_width_compact)
        self._voice_table.set_dense_mode(dense, ultra_dense=ultra_dense)
        self._apply_llm_layout(compact=controls_compact)
        self._llm_panel.setVisible(self._current_speaker_mode() == "llm" and not ultra_dense)
        self._settings_layout.setVerticalSpacing(4 if height_compact else 6)
        self._action_panel.layout().setContentsMargins(0, 4 if controls_compact else 0, 0, 0)
        self._chunk_size.setFixedHeight(42 if controls_compact else 38)
        self._chunk_size.setFixedWidth(118 if width_compact else 128)
        self._chunk_size.setVisible(False)
        self._chunk_size_label.setVisible(False)
        has_loaded_segments = bool(self._voice_table.get_segments())
        show_secondary_status = not controls_compact and (
            self._worker is not None or not has_loaded_segments
        )
        self._progress.setVisible(show_secondary_status)
        self._manifest_label.setVisible(
            bool(self._manifest_label.text()) and show_secondary_status,
        )
        self._load_gap.changeSize(
            0 if has_loaded_segments else 32,
            0,
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Minimum,
        )
        self._action_panel.layout().invalidate()
        self._sync_action_status_visibility()
        for button in (
            self._btn_detect,
            self._btn_load,
            self._btn_save,
            self._btn_build,
        ):
            if controls_compact:
                button.setFixedHeight(42)
            else:
                button.setMaximumHeight(16777215)
                button.setMinimumHeight(max(38, round(38 * self._ui_scale)))
        for label in (
            self._speaker_mode_label,
            self._stress_mode_label,
        ):
            label.setVisible(not controls_compact)
        self._speaker_mode_hint.setVisible(not controls_compact)
        self._stress_mode.setVisible(not controls_compact)
        self._stats_label.setVisible(
            self._top_tabs.currentIndex() == 0 and not controls_compact and not dense
        )
        self._btn_detect.setMinimumWidth(0 if width_compact else 260)
        self._btn_detect.setMaximumWidth(16777215 if width_compact else 360)
        self._btn_detect.setText(t("voice.compact_detect") if width_compact else t("voice.detect"))
        self._btn_load.setText(
            t("voice.compact_load_manifest") if width_compact else t("voice.load_manifest")
        )
        self._btn_save.setText(
            t("voice.compact_save_manifest") if width_compact else t("voice.save_manifest")
        )
        self._btn_build.setText(t("voice.compact_build_chunks") if width_compact else t("voice.build_chunks"))
        self._sync_llm_field_visibility()

    def _is_width_compact(self) -> bool:
        """Return true for truly narrow logical widths, independent of DPI scale."""
        return self.width() < 960

    def _llm_rows(self) -> tuple[tuple[QLabel, QWidget], ...]:
        """Return LLM config rows in stable visual order."""
        return (
            (self._llm_provider_label, self._llm_provider),
            (self._llm_endpoint_label, self._llm_endpoint),
            (self._llm_model_label, self._llm_model),
            (self._llm_api_key_label, self._llm_api_key),
        )

    def _apply_llm_layout(self, *, compact: bool) -> None:
        """Use deterministic rows so high DPI wrapping cannot overlap fields."""
        same_layout = self._llm_layout_compact == compact
        self._llm_layout_compact = compact
        if same_layout:
            self._sync_llm_field_metrics()
            self._update_llm_placeholders()
            self._sync_llm_field_visibility()
            return
        while self._llm_layout.count():
            self._llm_layout.takeAt(0)
        self._sync_llm_provider_width()
        self._sync_llm_field_metrics()
        for column, (label, field) in enumerate(self._llm_rows()):
            label.setVisible(False)
            self._llm_layout.addWidget(field, 0, column)
        self._update_llm_placeholders()
        self._sync_llm_field_visibility()

    def _sync_llm_field_metrics(self) -> None:
        """Reserve enough row height for styled fields at high DPI."""
        if not hasattr(self, "_llm_provider"):
            return
        fields = [field for _label, field in self._llm_rows()]
        height = max(
            34,
            round(34 * self._ui_scale),
            *(field.sizeHint().height() for field in fields),
        )
        for field in fields:
            field.setMinimumHeight(height)
            field.setMaximumHeight(height)

        tight_line = self.width() < 1600
        narrow_line = self._llm_layout_compact or self.width() < 1900
        width_scale = min(self._ui_scale, 1.12)
        if tight_line:
            endpoint_width = 202
            model_width = 258
            api_width = 235
        elif narrow_line:
            endpoint_width = round(218 * width_scale)
            model_width = round(278 * width_scale)
            api_width = round(252 * width_scale)
        else:
            endpoint_width = round(252 * width_scale)
            model_width = round(336 * width_scale)
            api_width = round(300 * width_scale)

        fixed_widths = {
            self._llm_endpoint: endpoint_width,
            self._llm_model: model_width,
            self._llm_api_key: api_width,
        }
        for field, width in fixed_widths.items():
            field.setMinimumWidth(width)
            field.setMaximumWidth(width)
            field.setSizePolicy(
                QSizePolicy.Policy.Fixed,
                QSizePolicy.Policy.Fixed,
            )
        self._llm_layout.setHorizontalSpacing(max(6, round(8 * self._ui_scale)))
        self._llm_layout.setVerticalSpacing(0)

    def _sync_llm_provider_width(self) -> None:
        """Keep the provider selector readable without stretching like a text field."""
        if not hasattr(self, "_llm_provider"):
            return
        self._llm_provider.setMinimumWidth(220)
        self._llm_provider.setMaximumWidth(230)
        self._llm_provider.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )

    def _sync_llm_field_visibility(self) -> None:
        """Show provider-specific LLM fields without reviving hidden compact labels."""
        if not hasattr(self, "_llm_provider"):
            return
        provider = self._llm_provider.currentData()
        is_local = provider == "local"
        visible_by_field = {
            self._llm_provider: True,
            self._llm_endpoint: is_local,
            self._llm_model: True,
            self._llm_api_key: not is_local,
        }
        for label, field in self._llm_rows():
            visible = visible_by_field.get(field, True)
            field.setVisible(visible)
            label.setVisible(False)

    def _update_llm_placeholders(self) -> None:
        """Keep compact LLM rows identifiable when labels are hidden."""
        if not hasattr(self, "_llm_provider"):
            return
        for label, field in self._llm_rows():
            hint = label.text().rstrip(":")
            field.setToolTip(hint)
            if isinstance(field, QLineEdit) and field is not self._llm_api_key:
                field.setPlaceholderText(hint)

    def _current_speaker_mode(self) -> str:
        """Return the internal speaker attribution mode."""
        mode = self._speaker_mode.currentData()
        return str(mode or "heuristic")

    def _current_stress_mode(self) -> str:
        """Return the selected TTS stress rendering mode."""
        mode = self._stress_mode.currentData()
        return str(mode or "double_vowel")

    def _populate_speaker_mode_combo(self, selected_mode: str) -> None:
        """Populate speaker attribution choices with localized labels."""
        self._speaker_mode.blockSignals(True)
        self._speaker_mode.clear()
        self._speaker_mode.addItem(
            t("voice.speaker_mode_heuristic"),
            "heuristic",
        )
        self._speaker_mode.addItem(t("voice.speaker_mode_llm"), "llm")
        self._speaker_mode.addItem(
            t("voice.speaker_mode_manual"),
            "manual",
        )
        idx = self._speaker_mode.findData(selected_mode)
        self._speaker_mode.setCurrentIndex(idx if idx >= 0 else 0)
        self._speaker_mode.blockSignals(False)
        apply_combo_content_width(self._speaker_mode)

    def _populate_stress_mode_combo(self, selected_mode: str) -> None:
        """Populate stress rendering choices with localized labels."""
        self._stress_mode.blockSignals(True)
        self._stress_mode.clear()
        self._stress_mode.addItem(
            t("voice.stress_mode_double"),
            "double_vowel",
        )
        self._stress_mode.addItem(t("voice.stress_mode_acute"), "keep_acute")
        self._stress_mode.addItem(t("voice.stress_mode_plain"), "plain")
        idx = self._stress_mode.findData(selected_mode)
        self._stress_mode.setCurrentIndex(idx if idx >= 0 else 0)
        self._stress_mode.blockSignals(False)
        apply_combo_content_width(self._stress_mode)

    def _update_speaker_mode_hint(self) -> None:
        """Show inline hint for currently selected speaker mode."""
        mode = self._current_speaker_mode()
        hints = {
            "heuristic": t("voice.speaker_mode_hint_inline_heuristic"),
            "llm": t("voice.speaker_mode_hint_inline_llm"),
            "manual": t("voice.speaker_mode_hint_inline_manual"),
        }
        self._speaker_mode_hint.setText(hints.get(mode, ""))

    # ── Event handlers ──

    def _on_speaker_mode_changed(self, _idx: int) -> None:
        """Show/hide LLM config when speaker mode changes."""
        mode = self._current_speaker_mode()
        ultra_dense = self.height() < 430
        self._llm_panel.setVisible(mode == "llm" and not ultra_dense)
        self._update_speaker_mode_hint()
        self._refresh_loaded_layout()

    def _on_llm_provider_changed(self, _idx: int) -> None:
        """Toggle endpoint vs API key fields based on provider."""
        provider = self._llm_provider.currentData()
        is_local = provider == "local"
        self._sync_llm_field_visibility()
        if not is_local:
            self._llm_endpoint.setText("https://api.openai.com/v1")
            self._llm_model.setText("gpt-4o-mini")
        else:
            self._llm_endpoint.setText(configured_ollama_endpoint())
            self._llm_model.setText(PRIMARY_QWEN3_MODEL)
        self._refresh_loaded_layout()

    def set_book(self, book: object, output_dir: Path) -> None:
        """Set the book object from normalization page."""
        self._book = book
        self._output_dir = output_dir
        metadata = getattr(book, "metadata", None)
        extra = getattr(metadata, "extra", {}) if metadata is not None else {}
        if isinstance(extra, dict) and extra.get("llm_processing_enabled"):
            idx = self._speaker_mode.findData("llm")
            if idx >= 0:
                self._speaker_mode.setCurrentIndex(idx)
            candidates = extra.get("llm_model_candidates")
            if isinstance(candidates, list) and candidates:
                self._llm_model.setText(str(candidates[0]))
        self._btn_detect.setEnabled(True)

    def load_segments_manifest(self, manifest_path: Path) -> None:
        """Load an existing segment manifest from the Roles step."""
        self._manifest_path = manifest_path
        self._voice_table.load_manifest(self._manifest_path)
        self._btn_save.setEnabled(True)
        self._btn_build.setEnabled(True)
        segments = self._voice_table.get_active_segments()
        self._update_stats(segments)
        self._manifest_label.setText(
            t("voice.manifest_path", path=str(self._manifest_path)),
        )
        self._manifest_label.setVisible(True)
        self._progress.set_status(t("voice.segments_ready", n=len(segments)))
        self._refresh_loaded_layout()

    # ── Detection ──

    def _run_detection(self) -> None:
        if not self._book or not self._output_dir:
            return

        self._btn_detect.setEnabled(False)
        self._progress.set_status(t("voice.detecting"))

        llm_endpoint = self._llm_endpoint.text().strip()
        llm_model = self._llm_model.text().strip()
        llm_api_key = self._llm_api_key.text().strip()

        self._worker = ExportSegmentsWorker(
            book=self._book,
            output_dir=self._output_dir,
            speaker_mode=self._current_speaker_mode(),
            llm_endpoint=llm_endpoint,
            llm_model=llm_model,
            llm_api_key=llm_api_key,
            stress_mode=self._current_stress_mode(),
        )
        self._worker.progress.connect(self._progress.set_status)
        self._worker.finished.connect(self._on_detection_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_detection_done(self, manifest_path: str) -> None:
        self._worker = None
        self._manifest_path = Path(manifest_path)
        self._voice_table.load_manifest(self._manifest_path)
        self._btn_detect.setEnabled(True)
        self._btn_save.setEnabled(True)
        self._btn_build.setEnabled(True)

        segments = self._voice_table.get_active_segments()
        self._update_stats(segments)
        self._manifest_label.setText(
            t("voice.manifest_path", path=str(self._manifest_path)),
        )
        self._manifest_label.setVisible(True)
        self._progress.set_status(
            t("voice.segments_ready", n=len(segments)),
        )
        self._refresh_loaded_layout()

    def _update_stats(self, segments: list) -> None:
        """Update the stats label with segment distribution."""
        speech = sum(
            1 for s in segments
            if s.get("is_dialogue") or s.get("role") in ("male", "female")
        )
        narr = len(segments) - speech
        self._stats_label.setText(
            t(
                "voice.stats_segments",
                total=len(segments),
                speech=speech,
                narr=narr,
            ),
        )

    def _on_error(self, msg: str) -> None:
        self._worker = None
        self._btn_detect.setEnabled(True)
        self._progress.set_status(f"Error: {msg}")

    # ── Build TTS chunks from segments ──

    def _build_tts_chunks(self) -> None:
        """Group user-assigned segments into TTS-ready chunks."""
        segments = self._voice_table.get_active_segments()
        if not segments:
            return

        if not self._output_dir:
            self._output_dir = Path(".")

        metadata = getattr(self._book, "metadata", None)
        language = normalize_book_language(getattr(metadata, "language", "ru"))
        self._set_action_status(t("voice.building_chunks", n=len(segments)))
        self._progress.set_busy(t("voice.building_chunks", n=len(segments)))
        self._set_chunk_actions_enabled(False)
        self._build_worker = BuildTtsChunksWorker(
            segments=_copy_segments_for_worker(segments),
            output_dir=self._output_dir,
            book_title=self._output_dir.name,
            language=language,
            max_chunk_chars=self._chunk_size.value(),
            parent=self,
        )
        self._build_worker.finished.connect(self._on_chunks_built)
        self._build_worker.error.connect(self._on_background_action_error)
        self._build_worker.finished.connect(lambda *_args: self._clear_build_worker())
        self._build_worker.error.connect(lambda _msg: self._clear_build_worker())
        self._build_worker.start()

    def _on_chunks_built(self, chunks_path: str, chunk_count: int) -> None:
        self._progress.set_status(t("voice.chunks_done", n=chunk_count))
        self._set_action_status(t("voice.chunks_saved", n=chunk_count, path=chunks_path))
        self._manifest_label.setText(t("voice.manifest_path", path=chunks_path))
        self._manifest_label.setVisible(True)
        self.chunks_built.emit(chunks_path)
        self._set_chunk_actions_enabled(True)
        self._refresh_loaded_layout()

    def _clear_build_worker(self) -> None:
        self._build_worker = None
        self._set_chunk_actions_enabled(True)
        self._refresh_loaded_layout()

    # ── Load / Save ──

    def _load_manifest(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("voice.load_manifest"),
            "",
            "JSON (*.json);;All Files (*)",
        )
        if path:
            self._manifest_path = Path(path)
            self._voice_table.load_manifest(self._manifest_path)
            self._btn_save.setEnabled(True)
            self._btn_build.setEnabled(True)
            self._manifest_label.setText(
                t("voice.manifest_path", path=str(self._manifest_path)),
            )
            self._manifest_label.setVisible(True)
            self._refresh_loaded_layout()

    def _save_manifest(self) -> None:
        if not self._manifest_path:
            path, _ = QFileDialog.getSaveFileName(
                self,
                t("voice.save_manifest"),
                "segments_manifest.json",
                "JSON (*.json);;All Files (*)",
            )
            if path:
                self._manifest_path = Path(path)
            else:
                return
        self._set_action_status(t("voice.saving", path=str(self._manifest_path)))
        self._progress.set_busy(t("voice.saving", path=str(self._manifest_path)))
        self._set_chunk_actions_enabled(False)
        self._save_worker = SaveVoiceManifestWorker(
            path=self._manifest_path,
            segments=_copy_segments_for_worker(self._voice_table.get_segments()),
            manifest_is_v2=self._voice_table._manifest_is_v2,
            manifest_meta=dict(self._voice_table._manifest_meta),
            parent=self,
        )
        self._save_worker.finished.connect(self._on_manifest_saved)
        self._save_worker.error.connect(self._on_background_action_error)
        self._save_worker.finished.connect(lambda _path: self._clear_save_worker())
        self._save_worker.error.connect(lambda _msg: self._clear_save_worker())
        self._save_worker.start()

    def _on_manifest_saved(self, path: str) -> None:
        self._progress.set_status(t("voice.saved", path=path))
        self._set_action_status(t("voice.saved", path=path))
        self._manifest_label.setText(t("voice.manifest_path", path=path))
        self._manifest_label.setVisible(True)
        self._set_chunk_actions_enabled(True)
        self._refresh_loaded_layout()

    def _clear_save_worker(self) -> None:
        self._save_worker = None
        self._set_chunk_actions_enabled(True)
        self._refresh_loaded_layout()

    def _on_background_action_error(self, msg: str) -> None:
        self._progress.set_status(t("voice.action_error", msg=msg))
        self._set_action_status(t("voice.action_error", msg=msg), error=True)
        self._set_chunk_actions_enabled(True)

    def _set_chunk_actions_enabled(self, enabled: bool) -> None:
        has_segments = bool(self._voice_table.get_segments())
        self._btn_save.setEnabled(enabled and has_segments)
        self._btn_build.setEnabled(enabled and bool(self._voice_table.get_active_segments()))
        self._btn_load.setEnabled(enabled)
        self._btn_detect.setEnabled(enabled and self._book is not None)

    def _set_action_status(self, text: str, *, error: bool = False) -> None:
        self._action_status.setText(text)
        color = "rgba(185,28,28,0.95)" if error else "rgba(15,118,110,0.92)"
        self._action_status.setStyleSheet(
            f"color: {color}; font-size: 11px; font-weight: 700; padding: 0 2px;",
        )
        self._sync_action_status_visibility()

    def _sync_action_status_visibility(self) -> None:
        self._action_status.setVisible(bool(self._action_status.text()))

    def get_manifest_path(self) -> Path | None:
        """Return path to the current manifest file."""
        return self._manifest_path

    def _refresh_loaded_layout(self) -> None:
        """Recompute compact/dense layout after manifest-dependent widgets appear."""
        self._sync_compact_mode()
        self._sync_settings_panel_height()
        self.updateGeometry()


def _copy_segments_for_worker(segments: list[dict]) -> list[dict]:
    """Return a thread-owned shallow copy of segment dictionaries."""
    return [dict(segment) for segment in segments]
