from __future__ import annotations

from book_normalizer.gui.ui_scaler import MAX_UI_SCALE, MIN_UI_SCALE, clamp_scale, scale_stylesheet


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
