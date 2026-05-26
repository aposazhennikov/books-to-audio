"""Shared styles for modal dialogs."""

from __future__ import annotations

READABLE_MESSAGE_BOX_STYLE = """
QMessageBox {
    background-color: #f8fafc;
}

QMessageBox QLabel {
    color: #0f172a;
    font-weight: 500;
    line-height: 1.35;
}

QMessageBox QPushButton {
    min-width: 132px;
    min-height: 32px;
    padding: 8px 16px;
    border-radius: 8px;
    border: 1px solid rgba(91, 115, 142, 0.28);
    background: #ffffff;
    color: #0f172a;
    font-weight: 700;
}

QMessageBox QPushButton:hover {
    background: #e0f2fe;
    border-color: rgba(14, 165, 233, 0.52);
}
"""


def apply_readable_message_box_style(box: object) -> None:
    """Force readable message-box colors across OS light/dark themes."""
    set_style_sheet = getattr(box, "setStyleSheet", None)
    if callable(set_style_sheet):
        set_style_sheet(READABLE_MESSAGE_BOX_STYLE)
