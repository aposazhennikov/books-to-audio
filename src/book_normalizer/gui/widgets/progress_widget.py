"""Progress indicator widget with ETA display."""

from __future__ import annotations

import time

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from book_normalizer.gui.i18n import get_language, t

_ELAPSED_LABELS = {
    "en": "Elapsed",
    "ru": "Прошло",
    "zh": "已用",
    "kk": "Өтті",
    "uz": "O'tdi",
}

_ETA_LABELS = {
    "en": "ETA",
    "ru": "Осталось",
    "zh": "预计剩余",
    "kk": "Қалды",
    "uz": "Qoldi",
}


def _localized_label(labels: dict[str, str]) -> str:
    return labels.get(get_language(), labels["en"])


def _remaining_chunks_text(count: int) -> str:
    lang = get_language()
    if lang == "ru":
        return f"осталось {count}"
    if lang == "zh":
        return f"剩余 {count}"
    if lang == "kk":
        return f"{count} қалды"
    if lang == "uz":
        return f"{count} qoldi"
    return f"{count} left"


def _format_duration(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    if total_seconds < 60:
        return t("time.seconds_short", sec=total_seconds)
    minutes, sec = divmod(total_seconds, 60)
    if minutes < 60:
        return f"{minutes}m {sec:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


class ProgressWidget(QWidget):
    """Combined progress bar with status text and ETA."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._status_kind = "ready"
        self._last_progress: tuple[int, int, str] = (0, 100, "")
        self._started_at: float | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._refresh_time_label)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(4)

        self._status = QLabel(t("progress.ready"))
        self._status.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._status.setWordWrap(True)
        self._status.setStyleSheet(
            "font-weight: 600; font-size: 12px;"
            "color: rgba(51,65,85,0.72);",
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
        self._eta.setMinimumWidth(240)
        self._eta.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._eta.setStyleSheet(
            "font-weight: 600; font-size: 12px;"
            "color: rgba(2,132,199,0.92);",
        )
        bar_layout.addWidget(self._eta)
        self._bar_row.setVisible(False)
        layout.addWidget(self._bar_row)

    def set_status(self, text: str) -> None:
        """Update the status text and hide progress bar."""
        self._status_kind = "custom"
        self._stop_timing()
        self._status.setText(text)
        self._bar_row.setVisible(False)

    def set_progress(self, current: int, total: int, eta: str = "") -> None:
        """Update progress bar and ETA."""
        self._status_kind = "progress"
        self._last_progress = (current, total, eta)
        self._ensure_timing_started()
        self._bar_row.setVisible(True)
        self._bar.setMaximum(total)
        self._bar.setValue(current)
        self._apply_progress_text()

    def set_busy(self, text: str) -> None:
        """Show indeterminate progress (spinner) with text."""
        self._status_kind = "busy"
        self._ensure_timing_started()
        self._status.setText(text)
        self._bar_row.setVisible(True)
        self._bar.setMaximum(0)
        self._bar.setValue(0)
        self._apply_time_text()

    def reset(self) -> None:
        """Reset to initial state."""
        self._status_kind = "ready"
        self._last_progress = (0, 100, "")
        self._stop_timing()
        self._bar.setValue(0)
        self._bar.setMaximum(100)
        self._bar_row.setVisible(False)
        self._status.setText(t("progress.ready"))
        self._eta.setText("")

    def retranslate(self) -> None:
        """Refresh neutral/progress text after the app language changes."""
        if self._status_kind == "ready":
            self._status.setText(t("progress.ready"))
        elif self._status_kind == "progress":
            self._apply_progress_text()
        elif not self._bar_row.isHidden():
            self._apply_time_text()

    def _apply_progress_text(self) -> None:
        """Render progress status using the active language."""
        current, total, eta = self._last_progress
        pct = (current / total * 100) if total > 0 else 0
        remaining = total - current
        status = f"{current}/{total} ({pct:.0f}%)"
        if remaining > 0:
            status += f" - {_remaining_chunks_text(remaining)}"
        self._status.setText(status)
        self._apply_time_text()

    def _ensure_timing_started(self) -> None:
        if self._started_at is None:
            self._started_at = time.monotonic()
        if not self._timer.isActive():
            self._timer.start()

    def _stop_timing(self) -> None:
        self._timer.stop()
        self._started_at = None
        self._eta.setText("")

    def _refresh_time_label(self) -> None:
        if not self._bar_row.isHidden() and self._started_at is not None:
            self._apply_time_text()

    def _apply_time_text(self) -> None:
        """Render elapsed time and ETA using the active language."""
        if self._started_at is None:
            self._eta.setText("")
            return
        elapsed = _format_duration(time.monotonic() - self._started_at)
        parts = [f"{_localized_label(_ELAPSED_LABELS)}: {elapsed}"]
        if self._status_kind == "progress":
            _current, _total, eta = self._last_progress
            if eta:
                parts.append(f"{_localized_label(_ETA_LABELS)}: {eta}")
        self._eta.setText(" | ".join(parts))
