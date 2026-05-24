"""Frontend regression tests for PyQt layout stability."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.gui import helpers as gui_helpers
from tests.gui.helpers import (
    assert_layout_sane,
    assert_snapshot_matches,
    assert_visible_buttons_actionable,
    qapp,
    render_widget,
)

MainWindow = pytest.importorskip("book_normalizer.gui.main_window").MainWindow
QtCore = pytest.importorskip("PyQt6.QtCore")
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


@pytest.mark.parametrize(
    ("size", "scale"),
    [
        ((760, 520), 1.45),
        ((1180, 760), 1.0),
        ((2048, 715), 1.45),
    ],
)
def test_visible_buttons_are_connected_and_fit(
    size: tuple[int, int],
    scale: float,
) -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    render_widget(window, size[0], size[1], scale=scale)
    assert not window._tabs.tabBar().usesScrollButtons()

    for index in range(window._tabs.count()):
        window._tabs.setCurrentIndex(index)
        render_widget(window, size[0], size[1], scale=scale)
        assert_visible_buttons_actionable(window)

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


def test_zoomed_roles_table_headers_do_not_clip() -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    window._tabs.setCurrentIndex(1)
    render_widget(window, 760, 520, scale=1.45)

    table = window._roles_page._table
    header = table.horizontalHeader()
    visible_labels = [
        table.horizontalHeaderItem(column).text()
        for column in range(table.columnCount())
    ]

    assert visible_labels == ["Роль", "Опис.", "Речь", "Эмоции", "Сегм."]
    for column, label in enumerate(visible_labels):
        assert header.fontMetrics().horizontalAdvance(label) + 14 <= header.sectionSize(column)

    window.close()
    window.deleteLater()


def test_zoomed_roles_model_field_stays_readable_in_compact_layout() -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    window._tabs.setCurrentIndex(1)
    render_widget(window, 760, 520, scale=1.45)

    page = window._roles_page
    endpoint_rect = _rect_in_window(window, page._llm_endpoint)
    model_rect = _rect_in_window(window, page._llm_model)
    button_rect = _rect_in_window(window, page._btn_extract)

    assert page._compact_mode is True
    assert model_rect.width() >= 300
    assert model_rect.top() == endpoint_rect.top()
    assert button_rect.top() - model_rect.bottom() >= 8
    assert button_rect.left() <= endpoint_rect.left()
    assert button_rect.right() >= model_rect.right()

    window.close()
    window.deleteLater()


@pytest.mark.parametrize(
    ("language", "expected_text"),
    [
        ("ru", "Открыть"),
        ("en", "Open"),
        ("zh", "打开"),
        ("kk", "Ашу"),
        ("uz", "Ochish"),
    ],
)
def test_zoomed_synthesis_manifest_action_does_not_clip(
    language: str,
    expected_text: str,
) -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    lang_index = window._lang_combo.findData(language)
    assert lang_index >= 0
    window._lang_combo.setCurrentIndex(lang_index)
    window._tabs.setCurrentIndex(3)
    render_widget(window, 760, 520, scale=1.45)

    page = window._synthesis_page
    button = page._btn_load
    text_width = button.fontMetrics().horizontalAdvance(button.text())

    assert button.text() == expected_text
    assert text_width + 60 <= button.width()
    assert _rect_in_window(window, button).right() <= window.rect().right()

    window.close()
    window.deleteLater()


def test_voice_settings_panel_has_no_visible_scrollbar() -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    window._tabs.setCurrentIndex(1)
    window._voices_page._top_tabs.setCurrentIndex(1)
    render_widget(window, 1180, 760, scale=1.0)

    assert window.findChild(QtWidgets.QScrollArea, "voiceSettingsScroll") is None
    for scroll in window.findChildren(QtWidgets.QScrollArea):
        if not scroll.isVisible():
            continue
        assert scroll.objectName() != "voiceSettingsScroll"
        assert scroll.verticalScrollBarPolicy() == QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        assert scroll.horizontalScrollBarPolicy() == QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        assert not scroll.verticalScrollBar().isVisible()
        assert not scroll.horizontalScrollBar().isVisible()
        assert scroll.horizontalScrollBar().maximum() == 0

    window.close()
    window.deleteLater()


def test_chunk_editor_action_buttons_are_not_clipped() -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    window._tabs.setCurrentIndex(2)
    window._voices_page._voice_table.set_segments(
        [
            {
                "segment_index": 0,
                "chapter_index": 0,
                "role": "narrator",
                "voice_id": "narrator_calm",
                "intonation": "calm",
                "text": "A short editable segment.",
            },
        ]
    )
    render_widget(window, 1180, 760, scale=1.0)

    table = window._voices_page._voice_table
    assert table._editor_tabs.isVisible()
    for button in (
        table._btn_segment_split,
        table._btn_segment_merge,
        table._btn_segment_delete_empty,
        table._btn_segment_delete,
        table._btn_segment_restore,
    ):
        parent = button.parentWidget()
        assert parent is not None
        assert button.geometry().bottom() <= parent.rect().bottom()
        bottom_in_window = button.mapTo(window, button.rect().bottomLeft()).y()
        assert bottom_in_window <= window.rect().bottom()

    window.close()
    window.deleteLater()


def test_synthesis_page_actions_are_visible_without_settings_scrollbar() -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    window._tabs.setCurrentIndex(3)
    render_widget(window, 1180, 760, scale=1.0)

    page = window._synthesis_page
    for scroll in page.findChildren(QtWidgets.QScrollArea):
        if not scroll.isVisible():
            continue
        assert scroll.verticalScrollBarPolicy() == QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        assert scroll.horizontalScrollBarPolicy() == QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    for editor in page.findChildren(QtWidgets.QPlainTextEdit):
        if not editor.isVisible():
            continue
        assert editor.verticalScrollBarPolicy() == QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        assert editor.horizontalScrollBarPolicy() == QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff

    for button in (page._btn_test, page._btn_play_test, page._btn_start, page._btn_stop):
        assert button.isVisible()
        bottom_in_window = button.mapTo(window, button.rect().bottomLeft()).y()
        assert bottom_in_window <= window.rect().bottom()

    window.close()
    window.deleteLater()


def test_zoomed_normalization_controls_do_not_overlap() -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    window._tabs.setCurrentIndex(0)
    render_widget(window, 760, 520, scale=1.45)

    page = window._normalize_page
    _assert_no_visual_overlap(
        window,
        [
            page._book_language,
            page._llm_normalize,
            page._btn_run,
            page._progress,
            page._raw_text,
            page._norm_text,
        ],
    )
    assert page._book_language_label_wrap.isHidden()
    assert page._llm_normalize_label_wrap.isHidden()

    window.close()
    window.deleteLater()


def test_zoomed_chunk_markup_controls_do_not_overlap() -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    window._tabs.setCurrentIndex(2)
    render_widget(window, 760, 520, scale=1.45)

    page = window._voices_page
    _assert_no_visual_overlap(
        window,
        [
            page._speaker_mode,
            page._chunk_size,
            page._btn_detect,
            page._btn_load,
            page._btn_save,
            page._btn_build,
            page._voice_table,
        ],
    )
    assert page._stress_mode.isHidden()
    assert page._progress.isHidden()
    assert page._top_tabs.geometry().bottom() <= page._voice_table.geometry().top()
    assert page._voice_table._editor_tabs.isHidden()
    assert page._voice_table._chapter_nav_panel.isHidden()
    assert page._voice_table._preset_toolbar_panel.isHidden()
    assert page._voice_table._quick_apply_panel.isHidden()
    assert page._voice_table._table.horizontalScrollBar().maximum() == 0

    window.close()
    window.deleteLater()


def test_zoomed_chunk_actions_keep_breathing_room() -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    window._tabs.setCurrentIndex(2)
    render_widget(window, 760, 520, scale=1.45)

    page = window._voices_page
    field_bottom = max(
        _rect_in_window(window, page._speaker_mode).bottom(),
        _rect_in_window(window, page._chunk_size).bottom(),
    )
    action_top = min(
        _rect_in_window(window, button).top()
        for button in (
            page._btn_detect,
            page._btn_load,
            page._btn_save,
            page._btn_build,
        )
    )

    assert action_top - field_bottom >= 12

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


def test_main_window_snapshot_uses_portable_smoke_on_non_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = qapp()
    _ = app
    expected_path = (
        Path(__file__).resolve().parent
        / "gui"
        / "snapshots"
        / "main_window_1180x760.png"
    )
    expected = gui_helpers.QImage(str(expected_path))
    assert not expected.isNull()

    image = gui_helpers.QImage(expected.size(), gui_helpers.QImage.Format.Format_RGB32)
    for y in range(image.height()):
        for x in range(image.width()):
            image.setPixelColor(
                x,
                y,
                gui_helpers.QColor(
                    180 + ((x * 7 + y * 3) % 76),
                    180 + ((x * 5 + y * 11) % 76),
                    180 + ((x * 13 + y * 17) % 76),
                ),
            )

    diff_path = expected_path.with_name("main_window_1180x760.diff.png")
    diff_path.unlink(missing_ok=True)
    monkeypatch.setattr(gui_helpers.platform, "system", lambda: "Darwin")

    assert_snapshot_matches("main_window_1180x760", image)
    assert not diff_path.exists()


def test_main_window_snapshot_uses_portable_smoke_on_ci_without_platform_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_path = (
        Path(__file__).resolve().parent
        / "gui"
        / "snapshots"
        / "main_window_1180x760.png"
    )
    expected = gui_helpers.QImage(str(expected_path))
    assert not expected.isNull()

    image = gui_helpers.QImage(expected.size(), gui_helpers.QImage.Format.Format_RGB32)
    for y in range(image.height()):
        for x in range(image.width()):
            image.setPixelColor(
                x,
                y,
                gui_helpers.QColor(
                    190 + ((x * 7 + y * 3) % 60),
                    190 + ((x * 5 + y * 11) % 60),
                    190 + ((x * 13 + y * 17) % 60),
                ),
            )

    diff_path = expected_path.with_name("main_window_1180x760.diff.png")
    diff_path.unlink(missing_ok=True)
    monkeypatch.setenv("CI", "true")
    monkeypatch.setattr(gui_helpers.platform, "system", lambda: "Windows")

    assert_snapshot_matches("main_window_1180x760", image)
    assert not diff_path.exists()


def _assert_no_visual_overlap(root: QtWidgets.QWidget, widgets: list[QtWidgets.QWidget]) -> None:
    rects = []
    for widget in widgets:
        if not widget.isVisible():
            continue
        top_left = widget.mapTo(root, widget.rect().topLeft())
        rect = QtCore.QRect(top_left, widget.size()).adjusted(0, 0, -1, -1)
        rects.append((widget, rect))

    for index, (left_widget, left_rect) in enumerate(rects):
        for right_widget, right_rect in rects[index + 1:]:
            assert not left_rect.intersects(right_rect), (
                left_widget.objectName() or left_widget.__class__.__name__,
                right_widget.objectName() or right_widget.__class__.__name__,
                left_rect.getRect(),
                right_rect.getRect(),
            )


def _rect_in_window(
    root: QtWidgets.QWidget,
    widget: QtWidgets.QWidget,
) -> QtCore.QRect:
    top_left = widget.mapTo(root, widget.rect().topLeft())
    return QtCore.QRect(top_left, widget.size()).adjusted(0, 0, -1, -1)

