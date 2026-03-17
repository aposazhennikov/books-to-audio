"""Main application window with tabbed interface."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QLabel,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from book_normalizer.gui.pages.assembly_page import AssemblyPage
from book_normalizer.gui.pages.normalize_page import NormalizePage
from book_normalizer.gui.pages.synthesis_page import SynthesisPage
from book_normalizer.gui.pages.voices_page import VoicesPage


class MainWindow(QMainWindow):
    """Main application window for Books-to-Audio pipeline."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Books to Audio — Audiobook Generator")
        self.setMinimumSize(1100, 750)
        self._output_dir: Path | None = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)

        # Header.
        header = QLabel("Books to Audio")
        header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: #2c3e50; margin: 4px 0;")
        layout.addWidget(header)

        subtitle = QLabel("Audiobook generation pipeline: Normalize → Voices → Synthesize → Assemble")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #7f8c8d; margin-bottom: 8px;")
        layout.addWidget(subtitle)

        # Tabs.
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #bdc3c7; border-radius: 4px; }
            QTabBar::tab {
                padding: 8px 24px;
                font-size: 13px;
                min-width: 120px;
            }
            QTabBar::tab:selected {
                font-weight: bold;
                background: #ecf0f1;
            }
        """)

        self._normalize_page = NormalizePage()
        self._voices_page = VoicesPage()
        self._synthesis_page = SynthesisPage()
        self._assembly_page = AssemblyPage()

        self._tabs.addTab(self._normalize_page, "1. Normalize")
        self._tabs.addTab(self._voices_page, "2. Voices")
        self._tabs.addTab(self._synthesis_page, "3. Synthesize")
        self._tabs.addTab(self._assembly_page, "4. Assemble")

        layout.addWidget(self._tabs, stretch=1)

        # Status bar.
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage("Ready. Load a book file to begin.")

    def _connect_signals(self) -> None:
        """Wire up page transitions."""
        # After normalization completes, pass book to voices page.
        self._normalize_page._worker_finished = self._on_normalization_done

        original_finished = self._normalize_page._on_finished

        def patched_finished(book):
            original_finished(book)
            self._on_normalization_done(book)

        self._normalize_page._on_finished = patched_finished

        # After voice detection, pass manifest to synthesis page.
        original_voice_done = self._voices_page._on_detection_done

        def patched_voice_done(manifest_path):
            original_voice_done(manifest_path)
            self._on_voices_done(manifest_path)

        self._voices_page._on_detection_done = patched_voice_done

    def _on_normalization_done(self, book: object) -> None:
        """Called when normalization completes."""
        # Determine output directory.
        path_text = self._normalize_page._path_label.text()
        if path_text and path_text != "No file selected":
            from book_normalizer.cli import _build_output_dir
            self._output_dir = _build_output_dir(Path(path_text), Path("output")).resolve()
            self._output_dir.mkdir(parents=True, exist_ok=True)

            self._voices_page.set_book(book, self._output_dir)
            self._statusbar.showMessage(
                f"Normalization complete. {len(book.chapters)} chapters. Go to Voices tab."
            )
            self._tabs.setCurrentIndex(1)

    def _on_voices_done(self, manifest_path: str) -> None:
        """Called when voice detection/chunking completes."""
        mp = Path(manifest_path)
        if self._output_dir:
            self._synthesis_page.set_manifest(mp, self._output_dir)
            audio_dir = self._output_dir / "audio_chunks"
            self._assembly_page.set_audio_dir(audio_dir, self._output_dir)
            self._statusbar.showMessage("Voice assignment ready. Go to Synthesize tab.")
