"""Frontend regression tests for PyQt layout stability."""

from __future__ import annotations

import pytest

from tests.gui.helpers import assert_layout_sane, assert_snapshot_matches, qapp, render_widget

MainWindow = pytest.importorskip("book_normalizer.gui.main_window").MainWindow
QtWidgets = pytest.importorskip("PyQt6.QtWidgets")


@pytest.mark.parametrize(
    ("size", "scale"),
    [
        ((760, 520), 0.8),
        ((760, 520), 1.45),
        ((1180, 760), 1.0),
        ((1180, 760), 1.25),
        ((1440, 900), 1.0),
        ((2048, 715), 1.45),
    ],
)
def test_main_window_layout_does_not_overflow(
    size: tuple[int, int],
    scale: float,
) -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    render_widget(window, size[0], size[1], scale=scale)
    assert_layout_sane(window)
    window.close()
    window.deleteLater()


def test_main_window_tabs_survive_basic_navigation() -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    render_widget(window, 1180, 760, scale=1.0)

    for index in range(window._tabs.count()):
        window._tabs.setCurrentIndex(index)
        render_widget(window, 1180, 760, scale=1.0)
        assert_layout_sane(window)

    window.close()
    window.deleteLater()


@pytest.mark.parametrize("size", [(760, 520), (2048, 715)])
def test_zoom_does_not_force_window_larger_than_viewport(size: tuple[int, int]) -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    render_widget(window, size[0], size[1], scale=1.45)

    assert window.width() <= size[0]
    assert window.height() <= size[1]

    window.close()
    window.deleteLater()


def test_zoomed_voice_controls_keep_enough_text_height() -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    window._tabs.setCurrentIndex(1)
    render_widget(window, 2048, 715, scale=1.45)

    controls = []
    for klass in (
        QtWidgets.QComboBox,
        QtWidgets.QSpinBox,
        QtWidgets.QLineEdit,
        QtWidgets.QPushButton,
        QtWidgets.QToolButton,
    ):
        controls.extend(window.findChildren(klass))

    for control in controls:
        if not control.isVisible():
            continue
        assert control.height() >= control.fontMetrics().height() + 6

    window.close()
    window.deleteLater()


@pytest.mark.parametrize("size", [(760, 520), (2048, 715)])
def test_zoomed_voice_settings_do_not_overlap_assignment_table(
    size: tuple[int, int],
) -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    window._tabs.setCurrentIndex(1)
    render_widget(window, size[0], size[1], scale=1.45)

    settings = window._voices_page._top_tabs.geometry()
    table = window._voices_page._voice_table.geometry()

    assert settings.y() + settings.height() <= table.y()

    window.close()
    window.deleteLater()


def test_voice_settings_panel_has_no_visible_scrollbar() -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    window._tabs.setCurrentIndex(1)
    render_widget(window, 1180, 760, scale=1.0)

    assert window.findChild(QtWidgets.QScrollArea, "voiceSettingsScroll") is None
    for scroll in window.findChildren(QtWidgets.QScrollArea):
        if not scroll.isVisible():
            continue
        assert scroll.objectName() != "voiceSettingsScroll"
        assert scroll.horizontalScrollBar().maximum() == 0

    window.close()
    window.deleteLater()


@pytest.mark.gui_snapshot
def test_main_window_snapshot_matches_baseline() -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    image = render_widget(window, 1180, 760, scale=1.0)
    assert_snapshot_matches("main_window_1180x760", image)
    window.close()
    window.deleteLater()

