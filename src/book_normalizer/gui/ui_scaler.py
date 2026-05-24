"""Application-wide UI scaling helpers."""

from __future__ import annotations

import re
from collections.abc import Callable

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QLineEdit,
    QPushButton,
    QToolButton,
    QWidget,
)

MIN_UI_SCALE = 0.8
MAX_UI_SCALE = 1.45
SCALE_STEP = 0.05
BASE_FONT_SIZE = 13
MULTILINGUAL_FONT_FAMILIES = (
    "Segoe UI",
    "Microsoft YaHei UI",
    "Microsoft YaHei",
    "PingFang SC",
    "Hiragino Sans GB",
    "Noto Sans CJK SC",
    "Noto Sans CJK",
    "WenQuanYi Zen Hei",
    "Noto Sans",
    "Inter",
    "Helvetica Neue",
)

_FONT_SIZE_RE = re.compile(r"(font-size\s*:\s*)(\d+(?:\.\d+)?)(px)", re.IGNORECASE)
_BASE_STYLESHEET_PROPERTY = "_books_to_audio_base_stylesheet"
_BASE_MIN_HEIGHT_PROPERTY = "_books_to_audio_base_minimum_height"
_BASE_MIN_WIDTH_PROPERTY = "_books_to_audio_base_minimum_width"
_BASE_MAX_WIDTH_PROPERTY = "_books_to_audio_base_maximum_width"
_BASE_MAX_HEIGHT_PROPERTY = "_books_to_audio_base_maximum_height"
_QT_UNBOUNDED_SIZE = 16_000_000


def clamp_scale(scale: float) -> float:
    """Clamp scale to the supported UI zoom range."""

    return max(MIN_UI_SCALE, min(MAX_UI_SCALE, round(scale, 2)))


def scale_stylesheet(stylesheet: str, scale: float) -> str:
    """Scale px font-size declarations without mutating the original stylesheet."""

    scale = clamp_scale(scale)

    def repl(match: re.Match[str]) -> str:
        base_size = float(match.group(2))
        size = max(9, round(base_size * scale))
        return f"{match.group(1)}{size}{match.group(3)}"

    return _FONT_SIZE_RE.sub(repl, stylesheet)


def make_app_font(
    point_size: int,
    weight: QFont.Weight | None = None,
) -> QFont:
    """Create the application font with multilingual fallback families."""
    font = QFont()
    if hasattr(font, "setFamilies"):
        font.setFamilies(list(MULTILINGUAL_FONT_FAMILIES))
    else:  # pragma: no cover - Qt 6 exposes setFamilies
        font.setFamily(MULTILINGUAL_FONT_FAMILIES[0])
    font.setPointSize(point_size)
    if weight is not None:
        font.setWeight(weight)
    return font


def apply_widget_scale_metrics(root: QWidget, scale: float) -> None:
    """Scale fixed widget metrics that Qt stylesheets cannot infer from fonts."""

    scale = clamp_scale(scale)
    for widget in [root, *root.findChildren(QWidget)]:
        if isinstance(widget, (QComboBox, QAbstractSpinBox, QLineEdit)):
            _set_scaled_minimum_height(widget, scale, fallback=32, padding=14)
            if isinstance(widget, QAbstractSpinBox):
                widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
                try:
                    line_edit = widget.lineEdit()
                except RuntimeError:
                    line_edit = None
                if line_edit is not None:
                    line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if isinstance(widget, QComboBox) and widget.minimumContentsLength() <= 0:
                widget.setMinimumContentsLength(14)
                widget.setSizeAdjustPolicy(
                    QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon,
                )
            continue

        if isinstance(widget, QPushButton):
            fallback = 38 if widget.objectName() in {"primaryBtn", "successBtn", "dangerBtn"} else 32
            _set_scaled_minimum_height(widget, scale, fallback=fallback, padding=16)
            continue

        if isinstance(widget, QToolButton):
            _set_scaled_minimum_height(widget, scale, fallback=28, padding=10)
            if widget.property("helpButton"):
                _set_scaled_minimum_width(widget, scale, fallback=20)
                _set_scaled_maximum_width(widget, scale)
                _set_scaled_maximum_height(widget, scale)
            continue


def _remember_int_property(widget: QWidget, property_name: str, current: int, fallback: int) -> int:
    stored = widget.property(property_name)
    if stored is None:
        value = current if current > 0 and current < _QT_UNBOUNDED_SIZE else fallback
        widget.setProperty(property_name, value)
        return value
    try:
        return int(stored)
    except (TypeError, ValueError):
        return fallback


def _set_scaled_minimum_height(
    widget: QWidget,
    scale: float,
    *,
    fallback: int,
    padding: int,
) -> None:
    base = _remember_int_property(
        widget,
        _BASE_MIN_HEIGHT_PROPERTY,
        widget.minimumHeight(),
        fallback,
    )
    font_safe_height = widget.fontMetrics().height() + round(padding * scale)
    widget.setMinimumHeight(max(round(base * scale), font_safe_height))


def _set_scaled_minimum_width(widget: QWidget, scale: float, *, fallback: int) -> None:
    base = _remember_int_property(
        widget,
        _BASE_MIN_WIDTH_PROPERTY,
        widget.minimumWidth(),
        fallback,
    )
    widget.setMinimumWidth(max(1, round(base * scale)))


def _set_scaled_maximum_width(widget: QWidget, scale: float) -> None:
    base = _remember_int_property(
        widget,
        _BASE_MAX_WIDTH_PROPERTY,
        widget.maximumWidth(),
        0,
    )
    if base > 0:
        widget.setMaximumWidth(max(1, round(base * scale)))


def _set_scaled_maximum_height(widget: QWidget, scale: float) -> None:
    base = _remember_int_property(
        widget,
        _BASE_MAX_HEIGHT_PROPERTY,
        widget.maximumHeight(),
        0,
    )
    if base > 0:
        widget.setMaximumHeight(max(1, round(base * scale)))


class UiScaler(QObject):
    """Global zoom controller for keyboard shortcuts and touchpad gestures."""

    def __init__(
        self,
        app: QApplication,
        theme_factory: Callable[[float], str],
        *,
        initial_scale: float = 1.0,
    ) -> None:
        super().__init__(app)
        self._app = app
        self._theme_factory = theme_factory
        self._scale = clamp_scale(initial_scale)
        self._applied_once = False

    @property
    def scale(self) -> float:
        return self._scale

    def install(self) -> None:
        self._app.installEventFilter(self)
        for widget in self._app.topLevelWidgets():
            self._enable_pinch_gesture(widget)
        self.apply_scale(self._scale, resize_windows=False)

    def eventFilter(self, obj: QObject | None, event: QEvent | None) -> bool:  # noqa: N802
        if event is None:
            return super().eventFilter(obj, event)

        if event.type() == QEvent.Type.KeyPress and self._handle_key_event(event):
            return True

        if self._handle_pointer_zoom_event(event):
            return True

        return super().eventFilter(obj, event)

    def zoom_in(self) -> None:
        self.apply_scale(self._scale + SCALE_STEP)

    def zoom_out(self) -> None:
        self.apply_scale(self._scale - SCALE_STEP)

    def reset(self) -> None:
        self.apply_scale(1.0)

    def apply_scale(self, scale: float, *, resize_windows: bool = True) -> None:
        new_scale = clamp_scale(scale)
        if new_scale == self._scale and self._applied_once:
            return

        old_scale = self._scale
        self._scale = new_scale
        self._app.setFont(make_app_font(max(10, round(BASE_FONT_SIZE * new_scale))))
        self._app.setStyleSheet(self._theme_factory(new_scale))

        for widget in self._app.topLevelWidgets():
            self._enable_pinch_gesture(widget)
            self._scale_widget_styles(widget, new_scale)
            if hasattr(widget, "set_ui_scale"):
                widget.set_ui_scale(new_scale)
            if isinstance(widget, QWidget):
                apply_widget_scale_metrics(widget, new_scale)

        if resize_windows:
            self._resize_windows(old_scale, new_scale)
        self._applied_once = True

    def _handle_key_event(self, event: QEvent) -> bool:
        modifiers = event.modifiers()
        if not modifiers & Qt.KeyboardModifier.ControlModifier:
            return False

        key = event.key()
        text = event.text() if hasattr(event, "text") else ""
        if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal) or text in {"+", "="}:
            self.zoom_in()
        elif key in (Qt.Key.Key_Minus, Qt.Key.Key_Underscore) or text in {"-", "_"}:
            self.zoom_out()
        elif key == Qt.Key.Key_0 or text == "0":
            self.reset()
        else:
            return False

        event.accept()
        return True

    def _handle_pointer_zoom_event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Wheel:
            if not event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                return False

            steps = self._wheel_zoom_steps(event)
            if steps:
                self.apply_scale(self._scale + (SCALE_STEP * steps))
            event.accept()
            return True

        if event.type() == QEvent.Type.NativeGesture:
            if event.gestureType() != Qt.NativeGestureType.ZoomNativeGesture:
                return False

            value = float(event.value()) if hasattr(event, "value") else 0.0
            if value:
                self.apply_scale(self._scale + value)
            event.accept()
            return True

        if event.type() == QEvent.Type.Gesture:
            gesture = event.gesture(Qt.GestureType.PinchGesture)
            if gesture is None:
                return False

            scale_factor = (
                float(gesture.scaleFactor())
                if hasattr(gesture, "scaleFactor")
                else 1.0
            )
            if scale_factor > 0 and scale_factor != 1.0:
                self.apply_scale(self._scale * scale_factor)
            event.accept()
            return True

        return False

    def _is_pointer_zoom_event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Wheel:
            return bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)

        if event.type() == QEvent.Type.NativeGesture:
            return event.gestureType() == Qt.NativeGestureType.ZoomNativeGesture

        if event.type() == QEvent.Type.Gesture:
            return event.gesture(Qt.GestureType.PinchGesture) is not None

        return False

    @staticmethod
    def _wheel_zoom_steps(event: QEvent) -> float:
        angle_delta = event.angleDelta() if hasattr(event, "angleDelta") else None
        if angle_delta is not None and angle_delta.y():
            return angle_delta.y() / 120

        pixel_delta = event.pixelDelta() if hasattr(event, "pixelDelta") else None
        if pixel_delta is not None and pixel_delta.y():
            return pixel_delta.y() / 120

        return 0.0

    def _scale_widget_styles(self, root: QWidget, scale: float) -> None:
        widgets = [root, *root.findChildren(QWidget)]
        for widget in widgets:
            stylesheet = widget.styleSheet()
            if not stylesheet:
                continue

            base_stylesheet = widget.property(_BASE_STYLESHEET_PROPERTY)
            if not base_stylesheet:
                base_stylesheet = stylesheet
                widget.setProperty(_BASE_STYLESHEET_PROPERTY, base_stylesheet)

            widget.setStyleSheet(scale_stylesheet(str(base_stylesheet), scale))

    @staticmethod
    def _enable_pinch_gesture(widget: QWidget) -> None:
        widget.grabGesture(Qt.GestureType.PinchGesture)

    def _resize_windows(self, old_scale: float, new_scale: float) -> None:
        if old_scale <= 0:
            return

        ratio = new_scale / old_scale
        for widget in self._app.topLevelWidgets():
            if not widget.isVisible() or widget.isMaximized() or widget.isFullScreen():
                continue

            screen = widget.screen() or QGuiApplication.primaryScreen()
            available = screen.availableGeometry() if screen else widget.geometry()
            minimum = widget.minimumSize()
            max_width = max(320, round(available.width() * 0.96))
            max_height = max(320, round(available.height() * 0.92))
            min_width = min(minimum.width(), max_width)
            min_height = min(minimum.height(), max_height)
            width = round(widget.width() * ratio)
            height = round(widget.height() * ratio)
            width = max(min_width, min(width, max_width))
            height = max(min_height, min(height, max_height))
            widget.resize(width, height)
