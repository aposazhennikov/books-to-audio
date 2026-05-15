"""Entry point for the PyQt6 GUI application."""

from __future__ import annotations

import sys

from book_normalizer.gui.ui_scaler import UiScaler, scale_stylesheet

THEME = """
/* Global */
* {
    font-family: "Segoe UI", "Inter", "Helvetica Neue", sans-serif;
    font-size: 13px;
}

QMainWindow {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #0c1118, stop:0.55 #111827, stop:1 #171321
    );
}

QWidget#centralWidget {
    background: transparent;
}

QLabel {
    color: rgba(226, 232, 240, 0.90);
}

QFrame#sampleVoicePanel,
QFrame#clonePanel {
    background: rgba(18, 24, 36, 0.94);
    border: 1px solid rgba(148, 163, 184, 0.15);
    border-radius: 14px;
}

QTabWidget::pane {
    background: rgba(18, 24, 36, 0.92);
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 14px;
    padding: 12px;
}

QTabWidget#synthesisModeTabs::pane,
QTabWidget#voiceTopTabs::pane {
    background: transparent;
    border: none;
    padding: 8px 0 0 0;
}

QTabBar {
    background: transparent;
}

QTabBar::tab {
    padding: 10px 22px;
    margin-right: 6px;
    font-size: 13px;
    font-weight: 600;
    color: rgba(226, 232, 240, 0.62);
    background: rgba(15, 23, 42, 0.64);
    border: 1px solid rgba(148, 163, 184, 0.12);
    border-bottom: none;
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
}

QTabWidget#synthesisModeTabs QTabBar::tab,
QTabWidget#voiceTopTabs QTabBar::tab {
    padding: 8px 18px;
    border-radius: 10px;
    border: 1px solid rgba(148, 163, 184, 0.14);
    margin-right: 8px;
}

QTabBar::tab:selected {
    color: #f8fafc;
    background: rgba(30, 41, 59, 0.92);
    border-bottom: 2px solid #8b5cf6;
}

QTabWidget#synthesisModeTabs QTabBar::tab:selected,
QTabWidget#voiceTopTabs QTabBar::tab:selected {
    border: 1px solid rgba(139, 92, 246, 0.42);
    background: rgba(139, 92, 246, 0.18);
}

QTabBar::tab:hover:!selected {
    color: rgba(248, 250, 252, 0.9);
    background: rgba(30, 41, 59, 0.82);
}

QPushButton {
    padding: 8px 18px;
    border: 1px solid rgba(148, 163, 184, 0.20);
    border-radius: 9px;
    background: rgba(30, 41, 59, 0.86);
    color: #e5e7eb;
    font-weight: 600;
    font-size: 12px;
}

QPushButton:hover {
    background: rgba(51, 65, 85, 0.92);
    border-color: rgba(139, 92, 246, 0.52);
    color: #f8fafc;
}

QPushButton:pressed {
    background: rgba(139, 92, 246, 0.24);
}

QPushButton:disabled {
    background: rgba(15, 23, 42, 0.58);
    color: rgba(226, 232, 240, 0.32);
    border-color: rgba(148, 163, 184, 0.08);
}

QPushButton#primaryBtn {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #7c3aed, stop:1 #06b6d4
    );
    color: #ffffff;
    font-size: 14px;
    font-weight: 700;
    border: none;
    padding: 10px 22px;
    min-height: 20px;
}

QPushButton#primaryBtn:hover {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #8b5cf6, stop:1 #22d3ee
    );
}

QPushButton#primaryBtn:disabled {
    background: rgba(124, 58, 237, 0.24);
    color: rgba(255, 255, 255, 0.36);
}

QPushButton#dangerBtn {
    background: rgba(239, 68, 68, 0.16);
    border: 1px solid rgba(248, 113, 113, 0.34);
    color: #fca5a5;
    font-size: 14px;
    font-weight: 700;
    min-height: 20px;
}

QPushButton#dangerBtn:hover {
    background: rgba(239, 68, 68, 0.30);
    color: #ffffff;
}

QPushButton#dangerBtn:disabled {
    background: rgba(239, 68, 68, 0.08);
    color: rgba(252, 165, 165, 0.32);
    border-color: rgba(248, 113, 113, 0.12);
}

QPushButton#successBtn {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #10b981, stop:1 #06b6d4
    );
    color: #ffffff;
    font-size: 14px;
    font-weight: 700;
    border: none;
    min-height: 20px;
}

QPushButton#successBtn:hover {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #34d399, stop:1 #22d3ee
    );
}

QPushButton#successBtn:disabled {
    background: rgba(16, 185, 129, 0.20);
    color: rgba(255, 255, 255, 0.36);
}

QToolButton {
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 8px;
    background: rgba(30, 41, 59, 0.72);
    color: rgba(226, 232, 240, 0.84);
    padding: 4px 8px;
    font-weight: 700;
}

QToolButton:hover {
    background: rgba(51, 65, 85, 0.90);
    border-color: rgba(139, 92, 246, 0.46);
    color: #ffffff;
}

QToolButton[helpButton="true"] {
    min-width: 20px;
    max-width: 22px;
    min-height: 20px;
    max-height: 22px;
    border-radius: 11px;
    padding: 0;
    color: #c4b5fd;
    background: rgba(139, 92, 246, 0.12);
    border: 1px solid rgba(196, 181, 253, 0.34);
}

QToolButton[helpButton="true"]:hover {
    color: #ffffff;
    background: rgba(139, 92, 246, 0.30);
    border-color: rgba(34, 211, 238, 0.55);
}

QToolButton[secondaryToggle="true"] {
    background: rgba(15, 23, 42, 0.72);
    border: 1px solid rgba(148, 163, 184, 0.14);
    border-radius: 10px;
    color: rgba(226, 232, 240, 0.82);
    padding: 7px 12px;
    text-align: left;
}

QToolButton[secondaryToggle="true"]:checked {
    background: rgba(139, 92, 246, 0.14);
    border-color: rgba(139, 92, 246, 0.36);
    color: #f8fafc;
}

QComboBox,
QSpinBox,
QDoubleSpinBox,
QLineEdit {
    padding: 6px 12px;
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 9px;
    background: rgba(15, 23, 42, 0.74);
    color: #e5e7eb;
    selection-background-color: #7c3aed;
}

QComboBox:hover,
QSpinBox:hover,
QDoubleSpinBox:hover,
QLineEdit:hover {
    border-color: rgba(139, 92, 246, 0.48);
}

QComboBox:focus,
QSpinBox:focus,
QDoubleSpinBox:focus,
QLineEdit:focus {
    border-color: #8b5cf6;
    background: rgba(15, 23, 42, 0.92);
}

QComboBox::drop-down {
    border: none;
    width: 28px;
    subcontrol-origin: padding;
    subcontrol-position: center right;
}

QComboBox::down-arrow {
    image: url({{CHEVRON_DOWN}});
    width: 12px;
    height: 8px;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background: #111827;
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 8px;
    color: #e5e7eb;
    selection-background-color: rgba(139, 92, 246, 0.40);
    padding: 4px;
}

QSpinBox::up-button,
QDoubleSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 20px;
    border: none;
}

QSpinBox::down-button,
QDoubleSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 20px;
    border: none;
}

QSpinBox::up-arrow,
QDoubleSpinBox::up-arrow {
    image: url({{CHEVRON_UP}});
    width: 10px;
    height: 6px;
}

QSpinBox::down-arrow,
QDoubleSpinBox::down-arrow {
    image: url({{CHEVRON_DOWN}});
    width: 10px;
    height: 6px;
}

QTextEdit,
QPlainTextEdit {
    background: rgba(9, 14, 24, 0.86);
    border: 1px solid rgba(148, 163, 184, 0.14);
    border-radius: 10px;
    color: #d1d5db;
    font-family: "Cascadia Code", "Fira Code", "Consolas", monospace;
    font-size: 12px;
    selection-background-color: rgba(139, 92, 246, 0.35);
    padding: 8px;
}

QTableWidget {
    background: rgba(15, 23, 42, 0.64);
    alternate-background-color: rgba(30, 41, 59, 0.54);
    gridline-color: rgba(148, 163, 184, 0.08);
    border: 1px solid rgba(148, 163, 184, 0.14);
    border-radius: 10px;
    color: #e5e7eb;
    selection-background-color: rgba(139, 92, 246, 0.30);
}

QHeaderView::section {
    background: rgba(30, 41, 59, 0.88);
    color: rgba(226, 232, 240, 0.78);
    font-weight: 700;
    font-size: 12px;
    border: none;
    border-bottom: 1px solid rgba(148, 163, 184, 0.12);
    padding: 8px 12px;
}

QProgressBar {
    border: none;
    border-radius: 6px;
    background: rgba(15, 23, 42, 0.82);
    text-align: center;
    color: rgba(226, 232, 240, 0.72);
    font-weight: 600;
    min-height: 14px;
    max-height: 14px;
}

QProgressBar::chunk {
    border-radius: 6px;
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #8b5cf6, stop:1 #22d3ee
    );
}

QScrollBar:vertical {
    width: 8px;
    background: transparent;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: rgba(148, 163, 184, 0.26);
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(203, 213, 225, 0.42);
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
    height: 0;
}

QScrollBar:horizontal {
    height: 8px;
    background: transparent;
}

QScrollBar::handle:horizontal {
    background: rgba(148, 163, 184, 0.26);
    border-radius: 4px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background: rgba(203, 213, 225, 0.42);
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: transparent;
    width: 0;
}

QScrollArea {
    background: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background: transparent;
}

QGroupBox {
    background: transparent;
    border: 1px solid rgba(148, 163, 184, 0.12);
    border-radius: 10px;
    margin-top: 12px;
    padding-top: 6px;
    font-weight: 700;
    color: rgba(226, 232, 240, 0.66);
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 12px;
    color: rgba(196, 181, 253, 0.9);
}

QSplitter::handle {
    background: rgba(148, 163, 184, 0.10);
    width: 1px;
    margin: 8px 2px;
    border-radius: 1px;
}

QStatusBar {
    background: rgba(8, 13, 22, 0.72);
    color: rgba(226, 232, 240, 0.66);
    border-top: 1px solid rgba(148, 163, 184, 0.12);
    font-size: 12px;
    padding: 4px 8px;
}

QToolTip {
    background: #f8fafc;
    border: 1px solid rgba(139, 92, 246, 0.35);
    border-radius: 8px;
    color: #111827;
    padding: 8px 10px;
    font-size: 12px;
}

QFormLayout QLabel {
    font-weight: 600;
    font-size: 12px;
}
"""


def _resolve_theme(scale: float = 1.0) -> str:
    """Replace asset placeholders in THEME with absolute paths."""
    from pathlib import Path

    assets = Path(__file__).resolve().parent / "assets"
    replacements = {
        "{{CHEVRON_DOWN}}": assets / "chevron_down.svg",
        "{{CHEVRON_UP}}": assets / "chevron_up.svg",
    }
    resolved = THEME
    for placeholder, path in replacements.items():
        resolved = resolved.replace(
            placeholder,
            str(path).replace("\\", "/"),
        )
    return scale_stylesheet(resolved, scale)


def main() -> None:
    """Launch the Books-to-Audio GUI application."""
    from PyQt6.QtWidgets import QApplication

    from book_normalizer.gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Books to Audio")
    app.setOrganizationName("books-to-audio")

    window = MainWindow()
    scaler = UiScaler(app, _resolve_theme)
    app._ui_scaler = scaler  # Keep the event filter alive for the app lifetime.
    scaler.install()

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
