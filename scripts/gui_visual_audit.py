#!/usr/bin/env python3
"""Render GUI screenshots and fail on obvious visual regressions."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from PyQt6 import QtCore, QtGui, QtWidgets  # noqa: E402

from book_normalizer.gui.app import _resolve_theme  # noqa: E402
from book_normalizer.gui.i18n import set_language  # noqa: E402
from book_normalizer.gui.main_window import MainWindow  # noqa: E402
from book_normalizer.gui.ui_scaler import BASE_FONT_SIZE, make_app_font  # noqa: E402

DEFAULT_SIZES = ((760, 520), (1180, 760), (2048, 715))
DEFAULT_SCALES = (1.0, 1.45)


@dataclass(frozen=True)
class AuditCase:
    """One rendered GUI state."""

    tab: int
    width: int
    height: int
    scale: float
    screenshot: str
    average_luminance: float
    dark_ratio: float
    purple_ratio: float
    visible_scrollbars: list[str]
    issues: list[str]


def main() -> int:
    parser = argparse.ArgumentParser(description="Render GUI screenshots and audit visual invariants.")
    parser.add_argument("--out-dir", default="output/gui_visual_audit", help="Folder for PNGs and summary JSON.")
    parser.add_argument("--language", default="ru", help="GUI language code to render. Default: ru.")
    parser.add_argument("--sizes", nargs="*", default=[_format_size(size) for size in DEFAULT_SIZES])
    parser.add_argument("--scales", nargs="*", type=float, default=list(DEFAULT_SCALES))
    parser.add_argument(
        "--tabs",
        nargs="*",
        default=["all"],
        help="Tab indexes to render, or all. Default: all.",
    )
    args = parser.parse_args()

    sizes = [_parse_size(value) for value in args.sizes]
    tabs = _parse_tabs(args.tabs)
    cases = run_visual_audit(
        out_dir=Path(args.out_dir),
        language=args.language,
        sizes=sizes,
        scales=tuple(args.scales),
        tabs=tabs,
    )
    failed = [case for case in cases if case.issues]
    print(f"GUI visual audit wrote {len(cases)} screenshots to {Path(args.out_dir).resolve()}")
    if failed:
        print("Visual issues:")
        for case in failed:
            print(f"- tab={case.tab} size={case.width}x{case.height} scale={case.scale}: {'; '.join(case.issues)}")
        return 1
    print("GUI visual audit passed.")
    return 0


def run_visual_audit(
    *,
    out_dir: Path,
    language: str = "ru",
    sizes: tuple[tuple[int, int], ...] = DEFAULT_SIZES,
    scales: tuple[float, ...] = DEFAULT_SCALES,
    tabs: tuple[int, ...] | None = None,
) -> list[AuditCase]:
    """Render requested tab/size/scale combinations and write audit summary."""

    out_dir.mkdir(parents=True, exist_ok=True)
    app = _qapp()
    set_language(language)
    window = MainWindow()
    tab_indexes = tabs if tabs is not None else tuple(range(window._tabs.count()))
    cases: list[AuditCase] = []

    try:
        for width, height in sizes:
            for scale in scales:
                _apply_scale(app, window, scale)
                window.resize(width, height)
                window.show()
                _flush_events(app)
                for tab in tab_indexes:
                    window._tabs.setCurrentIndex(tab)
                    _flush_events(app)
                    image = window.grab().toImage()
                    screenshot = out_dir / f"tab{tab}_{width}x{height}_scale{scale:g}.png"
                    if not image.save(str(screenshot)):
                        raise RuntimeError(f"Could not save screenshot: {screenshot}")
                    cases.append(_audit_case(window, image, tab, width, height, scale, screenshot))
    finally:
        window.close()
        window.deleteLater()
        _flush_events(app)

    summary_path = out_dir / "summary.json"
    summary_path.write_text(
        json.dumps([asdict(case) for case in cases], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return cases


def _audit_case(
    window: MainWindow,
    image: QtGui.QImage,
    tab: int,
    width: int,
    height: int,
    scale: float,
    screenshot: Path,
) -> AuditCase:
    average_luminance, dark_ratio, purple_ratio = _theme_metrics(image)
    visible_scrollbars = _visible_scrollbars(window)
    issues: list[str] = []
    if average_luminance < 210:
        issues.append(f"theme too dark: average_luminance={average_luminance:.1f}")
    if dark_ratio > 0.08:
        issues.append(f"too many dark pixels: dark_ratio={dark_ratio:.3f}")
    if purple_ratio > 0.02:
        issues.append(f"purple theme leakage: purple_ratio={purple_ratio:.3f}")
    if visible_scrollbars:
        issues.append(f"visible scrollbars: {', '.join(visible_scrollbars)}")
    if tab == 0:
        issues.extend(_normalize_page_issues(window))
    if tab == 2:
        issues.extend(_chunk_page_issues(window))

    return AuditCase(
        tab=tab,
        width=width,
        height=height,
        scale=scale,
        screenshot=str(screenshot),
        average_luminance=round(average_luminance, 2),
        dark_ratio=round(dark_ratio, 4),
        purple_ratio=round(purple_ratio, 4),
        visible_scrollbars=visible_scrollbars,
        issues=issues,
    )


def _normalize_page_issues(window: MainWindow) -> list[str]:
    page = window._normalize_page
    issues: list[str] = []
    if page._norm_text.isReadOnly():
        issues.append("normalized text editor is read-only")
    if page.findChildren(QtWidgets.QSplitter):
        issues.append("normalization page still uses a splitter handle")
    issues.extend(_spinbox_alignment_issues(page._ocr_dpi, "ocr_dpi"))
    return issues


def _chunk_page_issues(window: MainWindow) -> list[str]:
    page = window._voices_page
    issues = _spinbox_alignment_issues(page._chunk_size, "chunk_size")
    if page._chunk_size.width() > 160:
        issues.append(f"chunk size field too wide: {page._chunk_size.width()}")
    return issues


def _spinbox_alignment_issues(spinbox: QtWidgets.QSpinBox, name: str) -> list[str]:
    issues: list[str] = []
    alignment = spinbox.alignment()
    line_alignment = spinbox.lineEdit().alignment()
    if not (alignment & QtCore.Qt.AlignmentFlag.AlignHCenter):
        issues.append(f"{name} text is not horizontally centered")
    if not (alignment & QtCore.Qt.AlignmentFlag.AlignVCenter):
        issues.append(f"{name} text is not vertically centered")
    if not (line_alignment & QtCore.Qt.AlignmentFlag.AlignHCenter):
        issues.append(f"{name} line edit is not horizontally centered")
    if not (line_alignment & QtCore.Qt.AlignmentFlag.AlignVCenter):
        issues.append(f"{name} line edit is not vertically centered")
    if spinbox.buttonSymbols() != QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons:
        issues.append(f"{name} still shows spinner buttons")
    return issues


def _visible_scrollbars(root: QtWidgets.QWidget) -> list[str]:
    scrollbars: list[str] = []
    for scrollbar in root.findChildren(QtWidgets.QScrollBar):
        if not scrollbar.isVisible():
            continue
        maximum = scrollbar.maximum()
        if maximum <= 0:
            continue
        owner = scrollbar.parentWidget()
        if owner is None:
            owner_label = "unknown"
        else:
            owner_label = owner.objectName() or owner.__class__.__name__
        orientation = "vertical" if scrollbar.orientation() == QtCore.Qt.Orientation.Vertical else "horizontal"
        scrollbars.append(f"{owner_label}:{orientation}:{maximum}")
    return scrollbars


def _theme_metrics(image: QtGui.QImage) -> tuple[float, float, float]:
    samples = list(_sample_colors(image))
    luminance = [
        0.2126 * color.red() + 0.7152 * color.green() + 0.0722 * color.blue()
        for color in samples
    ]
    average_luminance = sum(luminance) / len(luminance)
    dark_ratio = sum(1 for value in luminance if value < 96) / len(luminance)
    purple_ratio = sum(
        1
        for color in samples
        if color.blue() > color.red() + 20
        and color.red() > color.green() + 10
        and color.blue() > 130
    ) / len(samples)
    return average_luminance, dark_ratio, purple_ratio


def _sample_colors(image: QtGui.QImage) -> list[QtGui.QColor]:
    step_x = max(1, image.width() // 70)
    step_y = max(1, image.height() // 50)
    return [
        QtGui.QColor(image.pixel(x, y))
        for y in range(0, image.height(), step_y)
        for x in range(0, image.width(), step_x)
    ]


def _qapp() -> QtWidgets.QApplication:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setFont(make_app_font(BASE_FONT_SIZE))
    app.setStyleSheet(_resolve_theme(1.0))
    return app


def _apply_scale(app: QtWidgets.QApplication, window: MainWindow, scale: float) -> None:
    app.setFont(make_app_font(max(10, round(BASE_FONT_SIZE * scale))))
    app.setStyleSheet(_resolve_theme(scale))
    window.set_ui_scale(scale)


def _flush_events(app: QtWidgets.QApplication) -> None:
    for _ in range(4):
        app.processEvents()


def _parse_size(value: str) -> tuple[int, int]:
    try:
        width_text, height_text = value.lower().split("x", maxsplit=1)
        width = int(width_text)
        height = int(height_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid size '{value}', expected WIDTHxHEIGHT") from exc
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("Size values must be positive")
    return width, height


def _format_size(size: tuple[int, int]) -> str:
    return f"{size[0]}x{size[1]}"


def _parse_tabs(values: list[str]) -> tuple[int, ...] | None:
    if not values or values == ["all"]:
        return None
    tabs = tuple(int(value) for value in values)
    if any(tab < 0 for tab in tabs):
        raise argparse.ArgumentTypeError("Tab indexes must be zero or positive")
    return tabs


if __name__ == "__main__":
    raise SystemExit(main())
