"""Small reusable help buttons for dense GUI forms."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QToolButton, QToolTip, QWidget

_HELP_TEXT_PROPERTY = "_books_to_audio_help_text"


def help_button(text: str = "") -> QToolButton:
    """Return a compact ? button that works on hover and click."""
    btn = QToolButton()
    btn.setText("?")
    btn.setProperty("helpButton", True)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setMinimumSize(20, 20)
    btn.setMaximumSize(24, 24)
    btn.setToolTipDuration(12000)
    set_help_text(btn, text)
    btn.clicked.connect(lambda _checked=False, b=btn: show_help(b))
    return btn


def set_help_text(button: QToolButton, text: str) -> None:
    """Update text used by tooltip, status tip, and click-to-show help."""
    button.setProperty(_HELP_TEXT_PROPERTY, text)
    button.setToolTip(text)
    button.setStatusTip(text)


def label_with_help(label: QLabel, text: str = "") -> tuple[QWidget, QToolButton]:
    """Wrap a label and a help button into a compact form-label widget."""
    wrap = QWidget()
    row = QHBoxLayout(wrap)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(6)
    row.addWidget(label)
    button = help_button(text)
    row.addWidget(button)
    row.addStretch()
    return wrap, button


def show_help(button: QToolButton) -> None:
    """Show the current help text immediately next to the button."""
    text = str(button.property(_HELP_TEXT_PROPERTY) or button.toolTip() or "")
    if text:
        QToolTip.showText(button.mapToGlobal(button.rect().bottomLeft()), text, button)
