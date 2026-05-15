"""Application-wide UI scaling helpers."""

from __future__ import annotations

import re
from collections.abc import Callable

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtWidgets import QApplication, QWidget

MIN_UI_SCALE = 0.8
MAX_UI_SCALE = 1.45
SCALE_STEP = 0.05
BASE_FONT_SIZE = 13

_FONT_SIZE_RE = re.compile(r"(font-size\s*:\s*)(\d+(?:\.\d+)?)(px)", re.IGNORECASE)
_BASE_STYLESHEET_PROPERTY = "_books_to_audio_base_stylesheet"


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


class UiScaler(QObject):
    """Global zoom controller for keyboard, trackpad and wheel gestures."""

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
        self._wheel_accumulator = 0
        self._pinch_accumulator = 0.0
        self._gesture_accumulator = 0.0
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

        if event.type() == QEvent.Type.Wheel and self._handle_wheel_event(event):
            return True

        if event.type() == QEvent.Type.NativeGesture and self._handle_native_gesture(event):
            return True

        if event.type() == QEvent.Type.Gesture and self._handle_gesture_event(event):
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
        self._app.setFont(QFont("Segoe UI", max(10, round(BASE_FONT_SIZE * new_scale))))
        self._app.setStyleSheet(self._theme_factory(new_scale))

        for widget in self._app.topLevelWidgets():
            self._enable_pinch_gesture(widget)
            self._scale_widget_styles(widget, new_scale)
            if hasattr(widget, "set_ui_scale"):
                widget.set_ui_scale(new_scale)

        if resize_windows:
            self._resize_windows(old_scale, new_scale)
        self._applied_once = True

    def _handle_key_event(self, event: QEvent) -> bool:
        modifiers = event.modifiers()
        if not modifiers & Qt.KeyboardModifier.ControlModifier:
            return False

        key = event.key()
        if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.zoom_in()
        elif key in (Qt.Key.Key_Minus, Qt.Key.Key_Underscore):
            self.zoom_out()
        elif key == Qt.Key.Key_0:
            self.reset()
        else:
            return False

        event.accept()
        return True

    def _handle_wheel_event(self, event: QEvent) -> bool:
        modifiers = event.modifiers()
        if not modifiers & Qt.KeyboardModifier.ControlModifier:
            return False

        self._wheel_accumulator += event.angleDelta().y()
        if abs(self._wheel_accumulator) >= 120:
            direction = 1 if self._wheel_accumulator > 0 else -1
            self.apply_scale(self._scale + direction * SCALE_STEP)
            self._wheel_accumulator = 0

        event.accept()
        return True

    def _handle_native_gesture(self, event: QEvent) -> bool:
        if event.gestureType() != Qt.NativeGestureType.ZoomNativeGesture:
            return False

        self._pinch_accumulator += event.value()
        if abs(self._pinch_accumulator) >= 0.18:
            direction = 1 if self._pinch_accumulator > 0 else -1
            self.apply_scale(self._scale + direction * SCALE_STEP)
            self._pinch_accumulator = 0.0

        event.accept()
        return True

    def _handle_gesture_event(self, event: QEvent) -> bool:
        gesture = event.gesture(Qt.GestureType.PinchGesture)
        if gesture is None:
            return False

        factor = gesture.scaleFactor()
        if not factor:
            return False

        self._gesture_accumulator += factor - 1.0
        if abs(self._gesture_accumulator) >= 0.12:
            direction = 1 if self._gesture_accumulator > 0 else -1
            self.apply_scale(self._scale + direction * SCALE_STEP)
            self._gesture_accumulator = 0.0

        event.accept()
        return True

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
            width = round(widget.width() * ratio)
            height = round(widget.height() * ratio)
            width = max(minimum.width(), min(width, round(available.width() * 0.96)))
            height = max(minimum.height(), min(height, round(available.height() * 0.92)))
            widget.resize(width, height)
