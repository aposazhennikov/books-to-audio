"""Tests for number expansion."""

import pytest

from book_normalizer.normalization.numbers import expand_numbers


@pytest.mark.parametrize(
    "input_text, expected_word",
    [
        ("ему 17 лет", "семнадцать"),
        ("было 5 человек", "пять"),
        ("через 100 лет", "сто"),
    ],
)
def test_cardinal_numbers(input_text: str, expected_word: str) -> None:
    """Standalone cardinal numbers are expanded to words."""
    result = expand_numbers(input_text)
    assert expected_word in result


def test_ordinal_number() -> None:
    """Ordinal numbers with suffix are expanded."""
    result = expand_numbers("17-й полк")
    assert "семнадцатый" in result


def test_no_expansion_for_zero() -> None:
    """Zero is not expanded (edge case)."""
    assert expand_numbers("0") == "0"


def test_plain_text_unchanged() -> None:
    """Text without numbers passes through unchanged."""
    text = "Он пошёл домой и лёг спать."
    assert expand_numbers(text) == text


def test_number_in_middle_of_sentence() -> None:
    """Number surrounded by text is expanded."""
    result = expand_numbers("у него было 3 собаки")
    assert "три" in result
