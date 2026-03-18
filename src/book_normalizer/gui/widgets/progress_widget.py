"""Progress indicator widget with ETA display."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from book_normalizer.gui.i18n import t


class ProgressWidget(QWidget):
    """Combined progress bar with status text and ETA."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(4)

        self._status = QLabel(t("progress.ready"))
        self._status.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._status.setWordWrap(True)
        self._status.setStyleSheet(
            "font-weight: 600; font-size: 12px;"
            "color: rgba(255,255,255,0.7);",
        )
        layout.addWidget(self._status)

        self._bar_row = QWidget()
        bar_layout = QHBoxLayout(self._bar_row)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(8)
        self._bar = QProgressBar()
        self._bar.setMinimum(0)
        self._bar.setMaximum(100)
        self._bar.setValue(0)
        bar_layout.addWidget(self._bar, stretch=1)

        self._eta = QLabel("")
        self._eta.setMinimumWidth(140)
        self._eta.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._eta.setStyleSheet(
            "font-weight: 600; font-size: 12px;"
            "color: rgba(124,92,252,0.9);",
        )
        bar_layout.addWidget(self._eta)
        self._bar_row.setVisible(False)
        layout.addWidget(self._bar_row)

    def set_status(self, text: str) -> None:
        """Update the status text and hide progress bar."""
        self._status.setText(text)
        self._bar_row.setVisible(False)

    def set_progress(self, current: int, total: int, eta: str = "") -> None:
        """Update progress bar and ETA."""
        self._bar_row.setVisible(True)
        self._bar.setMaximum(total)
        self._bar.setValue(current)
        pct = (current / total * 100) if total > 0 else 0
        remaining = total - current
        status = f"{current}/{total} ({pct:.0f}%)"
        if remaining > 0:
            status += f" • {t('progress.remaining_chunks', n=remaining)}"
        self._status.setText(status)
        if eta:
            self._eta.setText(t("progress.eta", eta=eta))
        else:
            self._eta.setText("")

    def set_busy(self, text: str) -> None:
        """Show indeterminate progress (spinner) with text."""
        self._status.setText(text)
        self._bar_row.setVisible(True)
        self._bar.setMaximum(0)
        self._bar.setValue(0)
        self._eta.setText("")

    def reset(self) -> None:
        """Reset to initial state."""
        self._bar.setValue(0)
        self._bar.setMaximum(100)
        self._bar_row.setVisible(False)
        self._status.setText(t("progress.ready"))
        self._eta.setText("")
