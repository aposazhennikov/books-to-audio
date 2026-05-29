"""Frontend regression tests for PyQt layout stability."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from book_normalizer.gui.i18n import set_language
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


@pytest.fixture(autouse=True)
def _clean_qt_widgets_between_layout_tests() -> None:
    app = QtWidgets.QApplication.instance()
    if app is not None:
        _dispose_top_level_widgets(app)
    yield
    app = QtWidgets.QApplication.instance()
    if app is not None:
        _dispose_top_level_widgets(app)


def _dispose_top_level_widgets(app: QtWidgets.QApplication) -> None:
    for widget in list(app.topLevelWidgets()):
        widget.close()
        widget.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    for _ in range(3):
        app.processEvents()


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


def test_main_window_renders_light_non_purple_theme() -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    image = render_widget(window, 1180, 760, scale=1.0)

    samples = [
        gui_helpers.QColor(image.pixel(x, y))
        for y in range(0, image.height(), max(1, image.height() // 50))
        for x in range(0, image.width(), max(1, image.width() // 70))
    ]
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

    assert average_luminance >= 210
    assert dark_ratio <= 0.08
    assert purple_ratio <= 0.02

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


def test_fullscreen_only_mode_locks_window_to_available_screen() -> None:
    app = qapp()
    window = MainWindow()
    window.enable_fullscreen_only()
    gui_helpers.flush_events(app)

    available = app.primaryScreen().availableGeometry().size()
    assert window.isMaximized()
    assert window.minimumSize() == available
    assert window.maximumSize() == available

    window.showNormal()
    gui_helpers.flush_events(app)
    assert window.isMaximized()
    assert window.minimumSize() == available
    assert window.maximumSize() == available

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


def test_roles_endpoint_field_has_room_for_native_ollama_url() -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    window._tabs.setCurrentIndex(1)
    render_widget(window, 1180, 760, scale=1.0)

    field = window._roles_page._llm_endpoint
    required = field.fontMetrics().horizontalAdvance("http://localhost:11434") + 32

    assert field.width() >= required
    assert field.text() == "http://localhost:11434"

    window.close()
    window.deleteLater()


@pytest.mark.parametrize(
    ("language", "expected_text"),
    [
        ("ru", "Откр."),
        ("en", "Open"),
        ("zh", "打开"),
        ("kk", "Ашу"),
        ("uz", "Och"),
    ],
)
def test_zoomed_synthesis_manifest_action_does_not_clip(
    language: str,
    expected_text: str,
) -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    try:
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
    finally:
        window.close()
        window.deleteLater()
        set_language("ru")


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
    tab_buttons = (
        (
            0,
            (
                table._btn_segment_split,
                table._btn_segment_merge,
                table._btn_segment_delete_empty,
                table._btn_segment_delete,
                table._btn_segment_restore,
            ),
        ),
        (
            1,
            (
                table._btn_full_refresh,
                table._btn_full_apply,
            ),
        ),
    )
    for tab_index, buttons in tab_buttons:
        table._editor_tabs.setCurrentIndex(tab_index)
        render_widget(window, 1180, 760, scale=1.0)
        for button in buttons:
            assert button.height() >= button.sizeHint().height(), button.text()
            parent = button.parentWidget()
            assert parent is not None
            assert button.geometry().bottom() <= parent.rect().bottom()
            bottom_in_window = button.mapTo(window, button.rect().bottomLeft()).y()
            assert bottom_in_window <= window.rect().bottom()

    window.close()
    window.deleteLater()


def test_chunk_table_fixed_headers_have_readable_width() -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    window._tabs.setCurrentIndex(2)
    render_widget(window, 1180, 760, scale=1.0)

    table = window._voices_page._voice_table._table
    header = table.horizontalHeader()
    metrics = header.fontMetrics()
    for column in (0, 1, 2, 7, 8):
        label = table.horizontalHeaderItem(column).text()
        assert metrics.horizontalAdvance(label) + 28 <= header.sectionSize(column), (
            column,
            label,
            header.sectionSize(column),
        )

    window.close()
    window.deleteLater()


def test_chunk_primary_action_is_not_stretched_across_toolbar() -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    window._tabs.setCurrentIndex(2)
    render_widget(window, 1180, 760, scale=1.0)

    page = window._voices_page
    detect_rect = _rect_in_window(window, page._btn_detect)
    load_rect = _rect_in_window(window, page._btn_load)

    assert page._btn_detect.width() <= 380
    assert load_rect.left() - detect_rect.right() >= 40
    assert page._chunk_size.isHidden()

    window.close()
    window.deleteLater()


def test_assembly_pause_fields_stay_centered_at_high_scale() -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    window._tabs.setCurrentIndex(4)
    render_widget(window, 2048, 715, scale=1.45)

    page = window._assembly_page
    for spin in (page._pause_same, page._pause_change):
        assert spin.lineEdit().minimumHeight() == 0
        spin_rect = _rect_in_window(window, spin)
        line_rect = _rect_in_window(window, spin.lineEdit())
        assert abs(spin_rect.center().y() - line_rect.center().y()) <= 1

    window.close()
    window.deleteLater()


def test_synthesis_advanced_numeric_fields_stay_centered_at_high_scale() -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    window._tabs.setCurrentIndex(3)
    window._synthesis_page._mode_tabs.setCurrentIndex(2)
    render_widget(window, 2048, 715, scale=1.45)

    model_combo = window._synthesis_page._asr_model_combo
    model_line = model_combo.lineEdit()
    assert model_line is not None
    assert model_line.minimumHeight() == 0
    combo_rect = _rect_in_window(window, model_combo)
    model_line_rect = _rect_in_window(window, model_line)
    assert abs(combo_rect.center().y() - model_line_rect.center().y()) <= 1

    for spin in (
        window._synthesis_page._batch_size,
        window._synthesis_page._chunk_timeout,
        window._synthesis_page._asr_timeout_spin,
    ):
        assert spin.lineEdit().minimumHeight() == 0
        spin_rect = _rect_in_window(window, spin)
        line_rect = _rect_in_window(window, spin.lineEdit())
        assert abs(spin_rect.center().y() - line_rect.center().y()) <= 1

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


def test_dropdowns_use_content_width_instead_of_full_rows() -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    try:
        window._tabs.setCurrentIndex(3)
        render_widget(window, 2048, 715, scale=1.0)

        checked = [
            window._normalize_page._book_language,
            window._normalize_page._ocr_mode,
            window._voices_page._speaker_mode,
            window._synthesis_page._output_format_combo,
            window._synthesis_page._chapter_combo,
            window._synthesis_page._asr_model_combo,
            window._synthesis_page._asr_device_combo,
            window._synthesis_page._test_source_combo,
            window._synthesis_page._test_voice_combo,
        ]

        for combo in checked:
            longest = max(
                [len(combo.itemText(index)) for index in range(combo.count())] or [1],
            )
            assert combo.minimumContentsLength() == longest
            assert combo.minimumWidth() == combo.maximumWidth()
            assert combo.sizePolicy().horizontalPolicy() == QtWidgets.QSizePolicy.Policy.Fixed

        assert window._synthesis_page._output_format_combo.maximumWidth() < 140
        assert window._synthesis_page._asr_device_combo.maximumWidth() < 140
        assert window._synthesis_page._asr_model_combo.maximumWidth() < 170
        assert window._normalize_page._book_language.maximumWidth() < 220
        assert 170 <= window._voices_page._llm_provider.minimumWidth() <= 230
        assert window._voices_page._llm_provider.maximumWidth() <= 230
    finally:
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
            page._btn_detect,
            page._btn_load,
            page._btn_save,
            page._btn_build,
            page._voice_table,
        ],
    )
    assert page._stress_mode.isHidden()
    assert page._chunk_size.isHidden()
    assert page._progress.isHidden()
    assert page._top_tabs.geometry().bottom() <= page._voice_table.geometry().top()
    assert page._voice_table._editor_tabs.isHidden()
    assert page._voice_table._chapter_nav_panel.isHidden()
    assert page._voice_table._preset_toolbar_panel.isHidden()
    assert page._voice_table._quick_apply_panel.isHidden()
    assert page._voice_table._table.horizontalScrollBar().maximum() == 0
    assert (
        page._voice_table._table.verticalScrollBarPolicy()
        == QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
    )

    window.close()
    window.deleteLater()


@pytest.mark.parametrize(
    ("size", "scale", "expect_ultra_dense"),
    [
        ((2048, 715), 1.45, False),
        ((760, 520), 1.45, True),
    ],
)
def test_loaded_chunk_page_does_not_overlap_in_height_constrained_viewports(
    size: tuple[int, int],
    scale: float,
    expect_ultra_dense: bool,
) -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    window._tabs.setCurrentIndex(2)
    _populate_loaded_chunk_page(window)
    render_widget(window, size[0], size[1], scale=scale)

    page = window._voices_page
    assert page._compact_mode is True
    assert page._voice_table._dense_mode is True
    assert page._voice_table._ultra_dense_mode is expect_ultra_dense
    assert page._progress.isHidden()
    assert page._voice_table._editor_tabs.isHidden()

    if expect_ultra_dense:
        assert page._voice_table._preset_toolbar_panel.isHidden()
        assert page._voice_table._quick_apply_panel.isHidden()
        assert page._stats_label.isHidden()
    else:
        assert page._voice_table._preset_toolbar_panel.isVisible()
        assert page._voice_table._quick_apply_panel.isVisible()
        assert page._stats_label.isHidden()
        assert page._voice_table._compact_mode is True

    siblings = [page._top_tabs, page._voice_table]
    if page._stats_label.isVisible():
        siblings.append(page._stats_label)
    for upper, lower in zip(siblings, siblings[1:]):
        assert upper.geometry().bottom() <= lower.geometry().top(), (
            upper.objectName() or upper.__class__.__name__,
            lower.objectName() or lower.__class__.__name__,
            upper.geometry().getRect(),
            lower.geometry().getRect(),
        )

    top_tabs_rect = _rect_in_window(window, page._top_tabs)
    for button in (page._btn_detect, page._btn_load, page._btn_save, page._btn_build):
        button_rect = _rect_in_window(window, button)
        assert button_rect.bottom() <= top_tabs_rect.bottom()
        assert button_rect.right() <= top_tabs_rect.right()

    table_panel_rect = _rect_in_window(window, page._voice_table)
    for child in (
        page._voice_table._chapter_nav_panel,
        page._voice_table._preset_toolbar_panel,
        page._voice_table._quick_apply_panel,
        page._voice_table._table,
        page._voice_table._editor_tabs,
    ):
        if not child.isVisible():
            continue
        child_rect = _rect_in_window(window, child)
        assert child_rect.bottom() <= table_panel_rect.bottom(), (
            child.objectName() or child.__class__.__name__,
            child_rect.getRect(),
            table_panel_rect.getRect(),
        )
        assert child_rect.right() <= table_panel_rect.right()

    assert page._voice_table._table.horizontalScrollBar().maximum() == 0

    window.close()
    window.deleteLater()


def test_loaded_llm_chunk_page_keeps_settings_controls_inside_panel() -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    window._tabs.setCurrentIndex(2)
    _populate_loaded_chunk_page(window, speaker_mode="llm")
    render_widget(window, 2048, 1228, scale=1.0)

    page = window._voices_page
    top_tabs_rect = _rect_in_window(window, page._top_tabs)
    table_rect = _rect_in_window(window, page._voice_table)
    assert top_tabs_rect.bottom() <= table_rect.top()

    for child in (
        page._speaker_mode,
        page._stress_mode,
        page._llm_panel,
        page._action_panel,
        page._progress,
        page._manifest_label,
    ):
        if not child.isVisible():
            continue
        child_rect = _rect_in_window(window, child)
        assert child_rect.top() >= top_tabs_rect.top(), (
            child.objectName() or child.__class__.__name__,
            child_rect.getRect(),
            top_tabs_rect.getRect(),
        )
        assert child_rect.bottom() <= top_tabs_rect.bottom(), (
            child.objectName() or child.__class__.__name__,
            child_rect.getRect(),
            top_tabs_rect.getRect(),
        )

    assert page._llm_panel.isVisible()
    assert page._top_tabs.height() >= 170
    nav_rect = _rect_in_window(window, page._voice_table._chapter_nav_panel)
    action_rect = _rect_in_window(window, page._action_panel)
    assert nav_rect.top() - action_rect.bottom() <= 32
    assert _rect_in_window(window, page._btn_load).left() - _rect_in_window(
        window,
        page._btn_detect,
    ).right() <= 12

    window.close()
    window.deleteLater()


def test_loaded_llm_chunk_page_keeps_full_layout_at_high_dpi_fullscreen_width() -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    window._tabs.setCurrentIndex(2)
    _populate_loaded_chunk_page(window, speaker_mode="llm")
    render_widget(window, 1366, 1100, scale=1.45)

    page = window._voices_page
    assert page._compact_mode is False
    assert page._llm_layout_compact is False
    assert page._voice_table._compact_mode is True
    assert page._speaker_mode_label.isVisible()
    assert page._stress_mode_label.isVisible()
    assert page._stress_mode.isVisible()
    assert page._llm_provider.width() >= 170
    _assert_no_visual_overlap(
        window,
        [page._llm_provider, page._llm_endpoint, page._llm_model],
    )

    window.close()
    window.deleteLater()


@pytest.mark.parametrize(
    ("size", "scale"),
    [
        ((2048, 1228), 1.0),
        ((1984, 1536), 1.0),
        ((1636, 1536), 1.45),
        ((2048, 873), 1.0),
    ],
)
def test_loaded_llm_chunk_page_keeps_fields_separated_and_editor_accessible(
    size: tuple[int, int],
    scale: float,
) -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    window._tabs.setCurrentIndex(2)
    _populate_loaded_chunk_page(window, speaker_mode="llm")
    render_widget(window, size[0], size[1], scale=scale)

    page = window._voices_page
    table = page._voice_table
    top_tabs_rect = _rect_in_window(window, page._top_tabs)
    table_panel_rect = _rect_in_window(window, table)

    assert page._llm_panel.isVisible()
    _assert_no_visual_overlap(
        window,
        [page._llm_provider, page._llm_endpoint, page._llm_model],
    )
    for field in (page._llm_provider, page._llm_endpoint, page._llm_model):
        field_rect = _rect_in_window(window, field)
        assert field_rect.top() >= top_tabs_rect.top()
        assert field_rect.bottom() <= top_tabs_rect.bottom()

    assert table._editor_tabs.isVisible()
    assert table._segment_editor.isVisible()
    assert table._segment_editor.height() >= 44
    editor_tabs_rect = _rect_in_window(window, table._editor_tabs)
    segment_editor_rect = _rect_in_window(window, table._segment_editor)
    assert top_tabs_rect.bottom() <= table_panel_rect.top()
    assert editor_tabs_rect.bottom() <= table_panel_rect.bottom()
    assert segment_editor_rect.bottom() <= editor_tabs_rect.bottom()

    window.close()
    window.deleteLater()


def test_loaded_llm_chunk_page_ultra_dense_has_no_overlapping_llm_controls() -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    window._tabs.setCurrentIndex(2)
    _populate_loaded_chunk_page(window, speaker_mode="llm")
    render_widget(window, 760, 520, scale=1.45)

    page = window._voices_page
    assert page._voice_table._ultra_dense_mode is True
    assert page._llm_panel.isHidden()
    _assert_no_visual_overlap(
        window,
        [
            page._speaker_mode,
            page._action_panel,
            page._voice_table,
        ],
    )

    window.close()
    window.deleteLater()


def test_loaded_llm_chunk_page_keeps_editor_and_scroll_controls_usable() -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    window._tabs.setCurrentIndex(2)
    _populate_loaded_chunk_page(window, speaker_mode="llm")
    render_widget(window, 2048, 873, scale=1.0)

    page = window._voices_page
    assert page._progress.isHidden()
    assert page._manifest_label.isHidden()
    assert page._voice_table._editor_tabs.isVisible()
    assert page._voice_table._btn_prev_segment.isVisible()
    assert page._voice_table._btn_next_segment.isVisible()
    assert page._voice_table._table.verticalScrollBar().maximum() > 0
    assert page._voice_table._table.verticalScrollBar().isVisible()
    assert (
        page._voice_table._segment_editor.verticalScrollBarPolicy()
        == QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
    )
    toolbar_rect = _rect_in_window(window, page._voice_table._preset_toolbar_panel)
    quick_rect = _rect_in_window(window, page._voice_table._quick_apply_panel)
    preset_button_rect = _rect_in_window(window, page._voice_table._btn_all_narrator)
    quick_combo_rect = _rect_in_window(window, page._voice_table._quick_combo)
    assert quick_rect.top() >= toolbar_rect.top()
    assert quick_rect.bottom() <= toolbar_rect.bottom()
    assert abs(preset_button_rect.center().y() - quick_combo_rect.center().y()) <= 2

    top_tabs_rect = _rect_in_window(window, page._top_tabs)
    table_panel_rect = _rect_in_window(window, page._voice_table)
    editor_tabs_rect = _rect_in_window(window, page._voice_table._editor_tabs)
    segment_editor_rect = _rect_in_window(window, page._voice_table._segment_editor)

    assert top_tabs_rect.bottom() <= table_panel_rect.top()
    assert editor_tabs_rect.bottom() <= table_panel_rect.bottom()
    assert segment_editor_rect.bottom() <= editor_tabs_rect.bottom()
    assert page._voice_table._table.horizontalScrollBar().maximum() == 0

    window.close()
    window.deleteLater()


def test_language_switch_does_not_rebuild_loaded_chunk_table(monkeypatch) -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    window._tabs.setCurrentIndex(2)
    segments = [
        {
            "segment_index": index,
            "chapter_index": index // 50,
            "role": "male" if index % 5 == 0 else "narrator",
            "speaker": "Диктор" if index % 5 else "Персонаж",
            "is_dialogue": index % 5 == 0,
            "voice_id": "male_confident" if index % 5 == 0 else "narrator_calm",
            "intonation": "calm",
            "text": f"Сегмент {index}.",
        }
        for index in range(1500)
    ]
    table = window._voices_page._voice_table
    table.set_segments(segments)
    render_widget(window, 1180, 760, scale=1.0)

    rebuilds = 0
    original_populate = table._populate_table

    def counted_populate() -> None:
        nonlocal rebuilds
        rebuilds += 1
        original_populate()

    monkeypatch.setattr(table, "_populate_table", counted_populate)
    live_voice_controls_before = sum(
        1
        for row in range(table._table.rowCount())
        if table._table.cellWidget(row, 5) is not None
    )

    target_code = "en" if window._lang_combo.currentData() != "en" else "ru"
    target = window._lang_combo.findData(target_code)
    assert target >= 0
    window._lang_combo.setCurrentIndex(target)
    render_widget(window, 1180, 760, scale=1.0)

    live_voice_controls_after = sum(
        1
        for row in range(table._table.rowCount())
        if table._table.cellWidget(row, 5) is not None
    )
    assert rebuilds == 0
    assert table._table.rowCount() == len(segments)
    assert 0 < live_voice_controls_after < len(segments) // 2
    assert live_voice_controls_after <= live_voice_controls_before + 8

    window.close()
    window.deleteLater()


def test_zoomed_chunk_actions_keep_breathing_room() -> None:
    app = qapp()
    _ = app
    window = MainWindow()
    window._tabs.setCurrentIndex(2)
    render_widget(window, 760, 520, scale=1.45)

    page = window._voices_page
    field_bottom = _rect_in_window(window, page._speaker_mode).bottom()
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
def test_main_window_snapshot_matches_baseline(tmp_path: Path) -> None:
    image_path = tmp_path / "main_window_1180x760.png"
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    env["BOOKS_TO_AUDIO_SNAPSHOT_OUT"] = str(image_path)
    code = """
import os
from pathlib import Path

from book_normalizer.gui.i18n import set_language
from book_normalizer.gui.main_window import MainWindow
from tests.gui.helpers import qapp, render_widget

app = qapp()
set_language("ru")
window = MainWindow()
image = render_widget(window, 1180, 760, scale=1.0)
assert image.save(os.environ["BOOKS_TO_AUDIO_SNAPSHOT_OUT"])
window.close()
window.deleteLater()
app.processEvents()
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        timeout=45,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    image = gui_helpers.QImage(str(image_path))
    assert not image.isNull()
    assert_snapshot_matches("main_window_1180x760", image)


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


def _populate_loaded_chunk_page(window: MainWindow, *, speaker_mode: str = "heuristic") -> None:
    page = window._voices_page
    mode_index = page._speaker_mode.findData(speaker_mode)
    assert mode_index >= 0
    page._speaker_mode.setCurrentIndex(mode_index)
    segments = [
        {
            "segment_index": index,
            "chapter_index": index // 8,
            "role": "male" if index % 5 == 1 else "female" if index % 7 == 2 else "narrator",
            "speaker": "Диктор" if index % 5 != 1 and index % 7 != 2 else "Персонаж",
            "is_dialogue": index % 5 == 1 or index % 7 == 2,
            "voice_id": (
                "male_confident"
                if index % 5 == 1
                else "female_warm"
                if index % 7 == 2
                else "narrator_calm"
            ),
            "intonation": "calm",
            "text": "Длинный текст превью сегмента для проверки загруженного состояния таблицы.",
        }
        for index in range(32)
    ]
    page._voice_table.set_segments(segments)
    page._btn_save.setEnabled(True)
    page._btn_build.setEnabled(True)
    page._progress.set_status(
        "Собрано 799 TTS-чанков. Перейдите на вкладку Голоса для следующего шага.",
    )
    page._manifest_label.setText(
        "Манифест: C:\\Users\\LENOVO\\Desktop\\OwnProjects\\books-to-audio\\output\\"
        "Ожидаемый_Писец__электронная_книга_pdf\\chunks_manifest_v2.json",
    )
    page._manifest_label.setVisible(True)
    page._refresh_loaded_layout()


def _rect_in_window(
    root: QtWidgets.QWidget,
    widget: QtWidgets.QWidget,
) -> QtCore.QRect:
    top_left = widget.mapTo(root, widget.rect().topLeft())
    return QtCore.QRect(top_left, widget.size()).adjusted(0, 0, -1, -1)
