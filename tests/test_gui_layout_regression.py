"""Frontend regression tests for PyQt layout stability."""

from __future__ import annotations

import pytest

from tests.gui.helpers import assert_layout_sane, assert_snapshot_matches, qapp, render_widget

MainWindow = pytest.importorskip("book_normalizer.gui.main_window").MainWindow


@pytest.mark.parametrize("size", [(760, 520), (1180, 760), (1440, 900)])
@pytest.mark.parametrize("scale", [0.8, 1.0, 1.25, 1.45])
def test_main_window_layout_does_not_overflow(size: tuple[int, int], scale: float) -> None:
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


@pytest.mark.gui_snapshot
def test_main_window_snapshot_matches_baseline() -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    image = render_widget(window, 1180, 760, scale=1.0)
    assert_snapshot_matches("main_window_1180x760", image)
    window.close()
    window.deleteLater()

