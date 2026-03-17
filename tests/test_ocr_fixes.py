"""Tests for OCR artifact fixes."""

import pytest

from book_normalizer.normalization.ocr_fixes import fix_mixed_script


@pytest.mark.parametrize(
    "input_text, expected",
    [
        ("Ha девице", "На девице"),
        ("HO еще", "НО еще"),
        ("сказал OH", "сказал ОН"),
        ("TO по рюмочке", "ТО по рюмочке"),
    ],
)
def test_mixed_script_fixed(input_text: str, expected: str) -> None:
    """Mixed-script words are fixed by replacing Latin with Cyrillic."""
    assert fix_mixed_script(input_text) == expected


def test_pure_latin_preserved() -> None:
    """Purely Latin words (English, French) are not touched."""
    text = "pour être outchitel"
    assert fix_mixed_script(text) == text


def test_pure_cyrillic_preserved() -> None:
    """Purely Cyrillic text is not modified."""
    text = "Обычный русский текст без артефактов."
    assert fix_mixed_script(text) == text


def test_mixed_in_context() -> None:
    """Mixed-script fix works within a full sentence."""
    result = fix_mixed_script("Он вышел Ha улицу и сказал: «Hет!»")
    assert "На" in result
    assert "Нет" in result
