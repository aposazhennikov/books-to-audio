"""Entry point for the PyQt6 GUI application."""

from __future__ import annotations

import sys


def main() -> None:
    """Launch the Books-to-Audio GUI application."""
    from PyQt6.QtWidgets import QApplication

    from book_normalizer.gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Books to Audio")
    app.setOrganizationName("books-to-audio")

    app.setStyleSheet("""
        QMainWindow {
            background-color: #f5f6fa;
        }
        QPushButton {
            padding: 6px 16px;
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            background-color: #ecf0f1;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: #dfe6e9;
        }
        QPushButton:pressed {
            background-color: #b2bec3;
        }
        QPushButton:disabled {
            background-color: #dfe6e9;
            color: #95a5a6;
        }
        QComboBox, QSpinBox {
            padding: 4px 8px;
            border: 1px solid #bdc3c7;
            border-radius: 3px;
            background: white;
        }
        QTableWidget {
            gridline-color: #dfe6e9;
            border: 1px solid #bdc3c7;
            alternate-background-color: #f8f9fa;
        }
        QProgressBar {
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            text-align: center;
            background-color: #ecf0f1;
        }
        QProgressBar::chunk {
            background-color: #3498db;
            border-radius: 3px;
        }
        QPlainTextEdit {
            border: 1px solid #bdc3c7;
            border-radius: 3px;
            background: white;
            font-family: Consolas, monospace;
            font-size: 12px;
        }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
