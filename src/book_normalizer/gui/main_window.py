"""Main application window with tabbed interface."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from book_normalizer.gui.i18n import set_language, t
from book_normalizer.gui.pages.assembly_page import AssemblyPage
from book_normalizer.gui.pages.normalize_page import NormalizePage
from book_normalizer.gui.pages.synthesis_page import SynthesisPage
from book_normalizer.gui.pages.voices_page import VoicesPage


class MainWindow(QMainWindow):
    """Main application window for Books-to-Audio pipeline."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Books to Audio")
        self._ui_scale = 1.0
        self.setMinimumSize(760, 520)
        self.resize(1180, 760)
        icon_path = Path(__file__).resolve().parent / "assets" / "icon.svg"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self._output_dir: Path | None = None
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
        self._title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self._title.setStyleSheet("color: #f8fafc;")
        header_row.addWidget(self._title)

        header_row.addStretch()

        # Language switcher.
        self._lang_label = QLabel()
        self._lang_label.setStyleSheet(
            "color: rgba(226,232,240,0.62); font-size: 12px; font-weight: 600;"
        )
        header_row.addWidget(self._lang_label)

        self._lang_combo = QComboBox()
        self._lang_combo.addItem("\U0001f1f7\U0001f1fa  \u0420\u0443\u0441\u0441\u043a\u0438\u0439", "ru")
        self._lang_combo.addItem("\U0001f1ec\U0001f1e7  English", "en")
        self._lang_combo.setMinimumWidth(136)
        self._lang_combo.setMaximumWidth(210)
        self._lang_combo.setStyleSheet(
            "QComboBox { font-size: 13px; font-weight: 600; }"
        )
        self._lang_combo.currentIndexChanged.connect(self._on_language_changed)
        header_row.addWidget(self._lang_combo)

        layout.addLayout(header_row)

        # Subtitle.
        self._subtitle = QLabel()
        self._subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle.setStyleSheet(
            "color: rgba(226,232,240,0.48); font-size: 13px; margin-bottom: 4px;"
        )
        layout.addWidget(self._subtitle)

        # ── Tabs ──
        self._tabs = QTabWidget()
        self._normalize_page = NormalizePage()
        self._voices_page = VoicesPage()
        self._synthesis_page = SynthesisPage()
        self._assembly_page = AssemblyPage()

        self._tabs.addTab(self._normalize_page, "")
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
        self.setMinimumSize(max(700, round(760 * scale)), max(480, round(520 * scale)))
        self._title.setFont(
            QFont("Segoe UI", max(16, round(22 * scale)), QFont.Weight.Bold)
        )
        self._lang_combo.setMinimumWidth(max(124, round(136 * scale)))
        self._lang_combo.setMaximumWidth(max(170, round(210 * scale)))

    def _connect_signals(self) -> None:
        """Wire up page transitions."""
        original_finished = self._normalize_page._on_finished

        def patched_finished(book):
            original_finished(book)
            self._on_normalization_done(book)

        self._normalize_page._on_finished = patched_finished

        self._voices_page.chunks_built.connect(self._on_chunks_built)

    def _on_language_changed(self, _index: int) -> None:
        """Handle language combo change."""
        lang = self._lang_combo.currentData()
        set_language(lang)
        self._retranslate()
        self._normalize_page.retranslate()
        self._voices_page.retranslate()
        self._synthesis_page.retranslate()
        self._assembly_page.retranslate()

    def _retranslate(self) -> None:
        """Update all translatable strings in the main window."""
        self._title.setText(t("app.title"))
        self._subtitle.setText(t("app.subtitle"))
        self._lang_label.setText(t("app.lang_label"))
        self._statusbar.showMessage(t("app.ready"))

        self._tabs.setTabText(0, t("tab.normalize"))
        self._tabs.setTabText(1, t("tab.voices"))
        self._tabs.setTabText(2, t("tab.synthesize"))
        self._tabs.setTabText(3, t("tab.assemble"))

    def _on_normalization_done(self, book: object) -> None:
        """Called when normalization completes."""
        path_text = self._normalize_page._path_label.text()
        no_file = t("norm.no_file")
        if path_text and path_text != no_file:
            from book_normalizer.cli import _build_output_dir
            self._output_dir = _build_output_dir(Path(path_text), Path("output")).resolve()
            self._output_dir.mkdir(parents=True, exist_ok=True)

            self._voices_page.set_book(book, self._output_dir)
            self._statusbar.showMessage(
                t("status.norm_done", n=len(book.chapters))
            )
            self._tabs.setCurrentIndex(1)

    def _on_chunks_built(self, chunks_path: str) -> None:
        """Called when TTS chunks are built from segments."""
        mp = Path(chunks_path)
        out_dir = self._output_dir or mp.parent
        self._synthesis_page.set_manifest(mp, out_dir)
        audio_dir = out_dir / "audio_chunks"
        if mp.name.endswith("_v2.json") or mp.name == "chunks_manifest_v2.json":
            self._assembly_page.set_manifest(mp, out_dir)
        else:
            self._assembly_page.set_audio_dir(audio_dir, out_dir)
        self._statusbar.showMessage(t("status.voices_done"))
