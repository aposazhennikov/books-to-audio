from __future__ import annotations

from book_normalizer.gui.ui_scaler import (
    MAX_UI_SCALE,
    MIN_UI_SCALE,
    MULTILINGUAL_FONT_FAMILIES,
    SCALE_STEP,
    UiScaler,
    apply_widget_scale_metrics,
    clamp_scale,
    make_app_font,
    scale_stylesheet,
)


class _PointerEvent:
    def __init__(
        self,
        event_type,
        *,
        modifiers=None,
        gesture_type=None,
        pinch_gesture=None,
        value=0.0,
    ) -> None:
        from PyQt6.QtCore import Qt

        self._event_type = event_type
        self._modifiers = modifiers or Qt.KeyboardModifier.NoModifier
        self._gesture_type = gesture_type
        self._pinch_gesture = pinch_gesture
        self._value = value
        self.accepted = False

    def type(self):
        return self._event_type

    def modifiers(self):
        return self._modifiers

    def gestureType(self):  # noqa: N802
        return self._gesture_type

    def value(self):
        return self._value

    def gesture(self, gesture_type):
        from PyQt6.QtCore import Qt

        if gesture_type == Qt.GestureType.PinchGesture:
            return self._pinch_gesture
        return None

    def accept(self) -> None:
        self.accepted = True


class _PinchGesture:
    def __init__(self, scale_factor: float) -> None:
        self._scale_factor = scale_factor

    def scaleFactor(self):  # noqa: N802
        return self._scale_factor


def _scaler():
    from book_normalizer.gui.app import _resolve_theme
    from tests.gui.helpers import qapp

    return UiScaler(qapp(), _resolve_theme)


def test_clamp_scale_limits_zoom_range() -> None:
    assert clamp_scale(0.1) == MIN_UI_SCALE
    assert clamp_scale(10.0) == MAX_UI_SCALE
    assert clamp_scale(1.23) == 1.23


def test_scale_stylesheet_scales_font_size_px_only() -> None:
    stylesheet = "QLabel { font-size: 20px; padding: 12px; }"

    scaled = scale_stylesheet(stylesheet, 1.25)

    assert "font-size: 25px" in scaled
    assert "padding: 12px" in scaled


def test_scale_stylesheet_keeps_tiny_fonts_readable() -> None:
    assert "font-size: 9px" in scale_stylesheet("font-size: 4px;", 0.8)


def test_make_app_font_carries_multilingual_fallbacks() -> None:
    font = make_app_font(13)

    families = font.families() if hasattr(font, "families") else [font.family()]
    assert families[: len(MULTILINGUAL_FONT_FAMILIES)] == list(
        MULTILINGUAL_FONT_FAMILIES,
    )
    assert font.pointSize() == 13


def test_apply_widget_scale_metrics_centers_numeric_fields() -> None:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QSpinBox, QVBoxLayout, QWidget

    root = QWidget()
    layout = QVBoxLayout(root)
    spin = QSpinBox()
    spin.setValue(600)
    layout.addWidget(spin)

    apply_widget_scale_metrics(root, 1.45)

    assert spin.alignment() & Qt.AlignmentFlag.AlignHCenter
    assert spin.alignment() & Qt.AlignmentFlag.AlignVCenter
    line_edit = spin.lineEdit()
    assert line_edit is not None
    assert line_edit.alignment() & Qt.AlignmentFlag.AlignHCenter
    assert line_edit.alignment() & Qt.AlignmentFlag.AlignVCenter


def test_gui_test_harness_uses_runtime_multilingual_font() -> None:
    from tests.gui.helpers import qapp

    app = qapp()
    families = app.font().families() if hasattr(app.font(), "families") else [app.font().family()]

    assert families[: len(MULTILINGUAL_FONT_FAMILIES)] == list(
        MULTILINGUAL_FONT_FAMILIES,
    )


def test_ctrl_wheel_changes_ui_scale() -> None:
    from PyQt6.QtCore import QPoint, QPointF, Qt
    from PyQt6.QtGui import QWheelEvent
    from PyQt6.QtWidgets import QWidget

    scaler = _scaler()
    target = QWidget()
    event = QWheelEvent(
        QPointF(10, 10),
        QPointF(10, 10),
        QPoint(0, 0),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.ControlModifier,
        Qt.ScrollPhase.ScrollUpdate,
        False,
    )

    assert scaler.eventFilter(target, event) is True
    assert scaler.scale == 1.0 + SCALE_STEP
    assert event.isAccepted() is True


def test_plain_wheel_is_left_for_scroll_widgets() -> None:
    from PyQt6.QtCore import QEvent

    scaler = _scaler()
    event = _PointerEvent(QEvent.Type.Wheel)

    assert scaler._is_pointer_zoom_event(event) is False
    assert scaler.scale == 1.0
    assert event.accepted is False


def test_native_zoom_gesture_changes_ui_scale() -> None:
    from PyQt6.QtCore import QEvent, Qt
    from PyQt6.QtWidgets import QWidget

    scaler = _scaler()
    target = QWidget()
    event = _PointerEvent(
        QEvent.Type.NativeGesture,
        gesture_type=Qt.NativeGestureType.ZoomNativeGesture,
        value=0.08,
    )

    assert scaler.eventFilter(target, event) is True
    assert scaler.scale == 1.08
    assert event.accepted is True


def test_non_zoom_native_gesture_is_ignored_by_scaler() -> None:
    from PyQt6.QtCore import QEvent, Qt

    scaler = _scaler()
    event = _PointerEvent(
        QEvent.Type.NativeGesture,
        gesture_type=Qt.NativeGestureType.PanNativeGesture,
    )

    assert scaler._is_pointer_zoom_event(event) is False
    assert scaler.scale == 1.0
    assert event.accepted is False


def test_pinch_gesture_changes_ui_scale() -> None:
    from PyQt6.QtCore import QEvent
    from PyQt6.QtWidgets import QWidget

    scaler = _scaler()
    target = QWidget()
    event = _PointerEvent(QEvent.Type.Gesture, pinch_gesture=_PinchGesture(1.1))

    assert scaler.eventFilter(target, event) is True
    assert scaler.scale == 1.1
    assert event.accepted is True


def test_keyboard_shortcuts_still_control_intentional_ui_zoom() -> None:
    from PyQt6.QtCore import QEvent, Qt
    from PyQt6.QtGui import QKeyEvent
    from PyQt6.QtWidgets import QWidget

    scaler = _scaler()
    target = QWidget()

    zoom_in = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Plus,
        Qt.KeyboardModifier.ControlModifier,
    )
    assert scaler.eventFilter(target, zoom_in) is True
    assert scaler.scale == 1.0 + SCALE_STEP

    zoom_out = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Minus,
        Qt.KeyboardModifier.ControlModifier,
    )
    assert scaler.eventFilter(target, zoom_out) is True
    assert scaler.scale == 1.0

    scaler.zoom_in()
    reset = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_0,
        Qt.KeyboardModifier.ControlModifier,
    )
    assert scaler.eventFilter(target, reset) is True
    assert scaler.scale == 1.0
