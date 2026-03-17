"""Progress indicator widget with ETA display."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget


class ProgressWidget(QWidget):
    """Combined progress bar with status text and ETA."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._status = QLabel("Ready")
        self._status.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._status)

        bar_row = QHBoxLayout()
        self._bar = QProgressBar()
        self._bar.setMinimum(0)
        self._bar.setMaximum(100)
        self._bar.setValue(0)
        bar_row.addWidget(self._bar, stretch=1)

        self._eta = QLabel("")
        self._eta.setMinimumWidth(120)
        self._eta.setAlignment(Qt.AlignmentFlag.AlignRight)
        bar_row.addWidget(self._eta)
        layout.addLayout(bar_row)

    def set_status(self, text: str) -> None:
        """Update the status text."""
        self._status.setText(text)

    def set_progress(self, current: int, total: int, eta: str = "") -> None:
        """Update progress bar and ETA."""
        self._bar.setMaximum(total)
        self._bar.setValue(current)
        pct = (current / total * 100) if total > 0 else 0
        self._status.setText(f"{current}/{total} ({pct:.0f}%)")
        if eta:
            self._eta.setText(f"ETA: {eta}")
        else:
            self._eta.setText("")

    def reset(self) -> None:
        """Reset to initial state."""
        self._bar.setValue(0)
        self._bar.setMaximum(100)
        self._status.setText("Ready")
        self._eta.setText("")
