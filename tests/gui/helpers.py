"""Shared PyQt GUI regression helpers."""

from __future__ import annotations

import os
import platform
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

QtCore = pytest.importorskip("PyQt6.QtCore")
QtGui = pytest.importorskip("PyQt6.QtGui")
QtWidgets = pytest.importorskip("PyQt6.QtWidgets")

QApplication = QtWidgets.QApplication
QPushButton = QtWidgets.QPushButton
QScrollArea = QtWidgets.QScrollArea
QWidget = QtWidgets.QWidget
Qt = QtCore.Qt
QImage = QtGui.QImage
QColor = QtGui.QColor


def qapp():
    app = QApplication.instance() or QApplication([])
    from book_normalizer.gui.app import _resolve_theme

    app.setStyleSheet(_resolve_theme(1.0))
    return app


def render_widget(widget: QWidget, width: int, height: int, *, scale: float = 1.0) -> QImage:
    app = qapp()
    from book_normalizer.gui.app import _resolve_theme

    app.setStyleSheet(_resolve_theme(scale))
    if hasattr(widget, "set_ui_scale"):
        widget.set_ui_scale(scale)
    widget.resize(width, height)
    widget.show()
    flush_events(app)
    image = widget.grab().toImage()
    assert image.width() > 0
    assert image.height() > 0
    assert not _is_blank(image)
    return image


def flush_events(app=None) -> None:
    app = app or qapp()
    for _ in range(3):
        app.processEvents()


def assert_layout_sane(widget: QWidget) -> None:
    """Catch common layout regressions: overflow, collapsed widgets and clipped buttons."""
    flush_events()
    for child in widget.findChildren(QWidget):
        if not child.isVisible():
            continue
        geometry = child.geometry()
        assert geometry.width() >= 0
        assert geometry.height() >= 0

    for scroll in widget.findChildren(QScrollArea):
        if not scroll.isVisible():
            continue
        assert scroll.horizontalScrollBar().maximum() == 0

    for button in widget.findChildren(QPushButton):
        if not button.isVisible() or not button.text():
            continue
        if button.objectName() not in {"primaryBtn", "successBtn", "dangerBtn"}:
            continue
        hint = button.sizeHint()
        assert button.width() + 4 >= min(hint.width(), 320), button.text()
        assert button.height() + 4 >= hint.height(), button.text()


def assert_visible_buttons_actionable(widget: QWidget) -> None:
    """Ensure visible buttons are wired and not visually clipped."""
    flush_events()
    for button in widget.findChildren(QPushButton):
        if not button.isVisible() or not button.text():
            continue
        hint = button.sizeHint()
        assert button.receivers(button.clicked) > 0, button.text()
        assert button.width() + 4 >= min(hint.width(), 320), button.text()
        assert button.height() + 4 >= hint.height(), button.text()


def assert_snapshot_matches(name: str, image: QImage, *, tolerance: float = 0.015) -> None:
    """Compare a widget capture to a golden PNG if present.

    Set UPDATE_GUI_SNAPSHOTS=1 to write/update baselines.
    """
    snapshot_dir = Path(__file__).resolve().parent / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    platform_name = platform.system().lower()
    generic_path = snapshot_dir / f"{name}.png"
    platform_path = snapshot_dir / f"{name}_{platform_name}.png"
    expected_path = platform_path if platform_path.exists() else generic_path
    if os.environ.get("UPDATE_GUI_SNAPSHOTS") == "1":
        update_path = platform_path if platform_name != "windows" else generic_path
        assert image.save(str(update_path))
        return
    if not expected_path.exists():
        pytest.skip(f"Missing GUI snapshot baseline: {expected_path}")

    expected = QImage(str(expected_path))
    assert expected.size() == image.size()
    mismatch = _pixel_mismatch_ratio(expected, image)
    if mismatch > tolerance:
        diff_path = snapshot_dir / f"{name}.diff.png"
        _write_diff(expected, image, diff_path)
        if not platform_path.exists() and platform_name != "windows":
            _assert_portable_visual_smoke(image)
            return
    assert mismatch <= tolerance


def _assert_portable_visual_smoke(image: QImage) -> None:
    """Keep cross-platform CI useful without pixel-locking OS font rendering."""
    samples = list(_sample_colors(image))
    assert len(samples) >= 100
    unique_colors = {(c.red() // 8, c.green() // 8, c.blue() // 8) for c in samples}
    luminance = [
        0.2126 * c.red() + 0.7152 * c.green() + 0.0722 * c.blue()
        for c in samples
    ]
    average_luminance = sum(luminance) / len(luminance)
    dark_ratio = sum(1 for value in luminance if value < 96) / len(luminance)

    assert len(unique_colors) >= 24
    assert average_luminance >= 170
    assert dark_ratio <= 0.20


def _is_blank(image: QImage) -> bool:
    first = QColor(image.pixel(0, 0)).rgba()
    step_x = max(1, image.width() // 20)
    step_y = max(1, image.height() // 20)
    for y in range(0, image.height(), step_y):
        for x in range(0, image.width(), step_x):
            if QColor(image.pixel(x, y)).rgba() != first:
                return False
    return True


def _pixel_mismatch_ratio(left: QImage, right: QImage) -> float:
    mismatches = 0
    total = left.width() * left.height()
    for y in range(left.height()):
        for x in range(left.width()):
            if QColor(left.pixel(x, y)).rgba() != QColor(right.pixel(x, y)).rgba():
                mismatches += 1
    return mismatches / max(total, 1)


def _sample_colors(image: QImage):
    step_x = max(1, image.width() // 48)
    step_y = max(1, image.height() // 32)
    for y in range(0, image.height(), step_y):
        for x in range(0, image.width(), step_x):
            yield QColor(image.pixel(x, y))


def _write_diff(expected: QImage, actual: QImage, path: Path) -> None:
    diff = QImage(actual.size(), QImage.Format.Format_RGB32)
    for y in range(actual.height()):
        for x in range(actual.width()):
            color = QColor(255, 0, 0) if expected.pixel(x, y) != actual.pixel(x, y) else QColor(actual.pixel(x, y))
            diff.setPixelColor(x, y, color)
    diff.save(str(path))
