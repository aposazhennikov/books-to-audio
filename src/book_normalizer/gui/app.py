"""Entry point for the PyQt6 GUI application."""

from __future__ import annotations

import sys


THEME = """
/* ── Global ── */
* {
    font-family: "Segoe UI", "Inter", "Helvetica Neue", sans-serif;
    font-size: 13px;
}

QMainWindow {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #0f0c29, stop:0.5 #302b63, stop:1 #24243e
    );
}

QWidget#centralWidget {
    background: transparent;
}

/* ── Cards / Panels ── */
QTabWidget::pane {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 12px;
    padding: 12px;
}

QTabBar {
    background: transparent;
}
QTabBar::tab {
    padding: 10px 28px;
    margin-right: 4px;
    font-size: 13px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.55);
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-bottom: none;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}
QTabBar::tab:selected {
    color: #fff;
    background: rgba(255, 255, 255, 0.10);
    border-bottom: 2px solid #7c5cfc;
}
QTabBar::tab:hover:!selected {
    color: rgba(255, 255, 255, 0.8);
    background: rgba(255, 255, 255, 0.07);
}

/* ── Labels ── */
QLabel {
    color: rgba(255, 255, 255, 0.85);
}

/* ── Buttons ── */
QPushButton {
    padding: 8px 20px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.08);
    color: #e0e0e0;
    font-weight: 600;
    font-size: 12px;
}
QPushButton:hover {
    background: rgba(255, 255, 255, 0.14);
    border-color: rgba(124, 92, 252, 0.4);
    color: #fff;
}
QPushButton:pressed {
    background: rgba(124, 92, 252, 0.25);
}
QPushButton:disabled {
    background: rgba(255, 255, 255, 0.03);
    color: rgba(255, 255, 255, 0.25);
    border-color: rgba(255, 255, 255, 0.04);
}

QPushButton#primaryBtn {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #7c5cfc, stop:1 #b44dff
    );
    color: #fff;
    font-size: 14px;
    font-weight: 700;
    border: none;
    padding: 10px 24px;
    min-height: 20px;
}
QPushButton#primaryBtn:hover {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #8b6ffc, stop:1 #c060ff
    );
}
QPushButton#primaryBtn:disabled {
    background: rgba(124, 92, 252, 0.25);
    color: rgba(255, 255, 255, 0.35);
}

QPushButton#dangerBtn {
    background: rgba(231, 76, 60, 0.2);
    border: 1px solid rgba(231, 76, 60, 0.35);
    color: #e74c3c;
    font-size: 14px;
    font-weight: 700;
    min-height: 20px;
}
QPushButton#dangerBtn:hover {
    background: rgba(231, 76, 60, 0.35);
    color: #fff;
}
QPushButton#dangerBtn:disabled {
    background: rgba(231, 76, 60, 0.08);
    color: rgba(231, 76, 60, 0.3);
    border-color: rgba(231, 76, 60, 0.12);
}

QPushButton#successBtn {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #00b894, stop:1 #00cec9
    );
    color: #fff;
    font-size: 14px;
    font-weight: 700;
    border: none;
    min-height: 20px;
}
QPushButton#successBtn:hover {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #00d9a6, stop:1 #00e0db
    );
}
QPushButton#successBtn:disabled {
    background: rgba(0, 184, 148, 0.2);
    color: rgba(255, 255, 255, 0.35);
}

/* ── Inputs ── */
QComboBox, QSpinBox, QLineEdit {
    padding: 6px 12px;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.06);
    color: #e0e0e0;
    selection-background-color: #7c5cfc;
}
QComboBox:hover, QSpinBox:hover, QLineEdit:hover {
    border-color: rgba(124, 92, 252, 0.4);
}
QComboBox:focus, QSpinBox:focus, QLineEdit:focus {
    border-color: #7c5cfc;
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
    background: #2a2750;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 6px;
    color: #e0e0e0;
    selection-background-color: rgba(124, 92, 252, 0.4);
    padding: 4px;
}

QSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 20px;
    border: none;
}
QSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 20px;
    border: none;
}
QSpinBox::up-arrow {
    image: url({{CHEVRON_UP}});
    width: 10px;
    height: 6px;
}
QSpinBox::down-arrow {
    image: url({{CHEVRON_DOWN}});
    width: 10px;
    height: 6px;
}

/* ── Table ── */
QTableWidget {
    background: rgba(255, 255, 255, 0.04);
    alternate-background-color: rgba(255, 255, 255, 0.02);
    gridline-color: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    color: #e0e0e0;
    selection-background-color: rgba(124, 92, 252, 0.3);
}
QHeaderView::section {
    background: rgba(255, 255, 255, 0.06);
    color: rgba(255, 255, 255, 0.7);
    font-weight: 700;
    font-size: 12px;
    border: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding: 8px 12px;
}

/* ── Progress Bar ── */
QProgressBar {
    border: none;
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.06);
    text-align: center;
    color: rgba(255, 255, 255, 0.7);
    font-weight: 600;
    min-height: 14px;
    max-height: 14px;
}
QProgressBar::chunk {
    border-radius: 6px;
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #7c5cfc, stop:1 #b44dff
    );
}

/* ── Text Areas ── */
QPlainTextEdit {
    background: rgba(0, 0, 0, 0.25);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    color: #d4d4d4;
    font-family: "Cascadia Code", "Fira Code", "Consolas", monospace;
    font-size: 12px;
    selection-background-color: rgba(124, 92, 252, 0.35);
    padding: 8px;
}

/* ── Scrollbars ── */
QScrollBar:vertical {
    width: 8px;
    background: transparent;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 0.15);
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(255, 255, 255, 0.25);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
    height: 0;
}
QScrollBar:horizontal {
    height: 8px;
    background: transparent;
}
QScrollBar::handle:horizontal {
    background: rgba(255, 255, 255, 0.15);
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: rgba(255, 255, 255, 0.25);
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: transparent;
    width: 0;
}

/* ── Scroll Area ── */
QScrollArea {
    background: transparent;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background: transparent;
}

/* ── Group Box ── */
QGroupBox {
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 6px;
    font-weight: 700;
    color: rgba(255, 255, 255, 0.6);
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 12px;
    color: rgba(124, 92, 252, 0.8);
}

/* ── Splitter ── */
QSplitter::handle {
    background: rgba(255, 255, 255, 0.08);
    width: 2px;
    margin: 4px 8px;
    border-radius: 1px;
}

/* ── Status bar ── */
QStatusBar {
    background: rgba(0, 0, 0, 0.2);
    color: rgba(255, 255, 255, 0.6);
    border-top: 1px solid rgba(255, 255, 255, 0.06);
    font-size: 12px;
    padding: 4px 8px;
}

/* ── Tooltips ── */
QToolTip {
    background: #2a2750;
    border: 1px solid rgba(124, 92, 252, 0.3);
    border-radius: 6px;
    color: #e0e0e0;
    padding: 6px 10px;
    font-size: 12px;
}

/* ── Form labels ── */
QFormLayout QLabel {
    font-weight: 600;
    font-size: 12px;
}
"""


def _resolve_theme() -> str:
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
    return resolved


def main() -> None:
    """Launch the Books-to-Audio GUI application."""
    from PyQt6.QtWidgets import QApplication

    from book_normalizer.gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Books to Audio")
    app.setOrganizationName("books-to-audio")
    app.setStyleSheet(_resolve_theme())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
