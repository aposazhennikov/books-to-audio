"""Tests for abbreviation expansion."""

import pytest

from book_normalizer.normalization.abbreviations import expand_abbreviations


@pytest.mark.parametrize(
    "input_text, expected",
    [
        ("и т. д.", "и так далее"),
        ("и т. п.", "и тому подобное"),
        ("т. е. вот так", "то есть вот так"),
        ("т. н. герой", "так называемый герой"),
        ("т. к. он ушёл", "так как он ушёл"),
        ("и т.д.", "и так далее"),
        ("и т.п.", "и тому подобное"),
    ],
)
def test_multi_word_abbreviations(input_text: str, expected: str) -> None:
    """Multi-word abbreviations are expanded correctly."""
    assert expand_abbreviations(input_text) == expected


def test_year_abbreviation() -> None:
    """'г.' after a 4-digit year is expanded to 'года'."""
    assert expand_abbreviations("в 1812 г.") == "в 1812 года"
    assert expand_abbreviations("в 1917г.") == "в 1917 года"


def test_year_range_abbreviation() -> None:
    """'гг.' after a year range is expanded to 'годов'."""
    assert expand_abbreviations("1941—1945 гг.") == "1941–1945 годов"


def test_century_abbreviation() -> None:
    """'в.' after a Roman numeral is expanded to 'века'."""
    assert expand_abbreviations("XVIII в.") == "XVIII века"
    assert expand_abbreviations("XIX в.") == "XIX века"


def test_simple_abbreviations() -> None:
    """Simple standalone abbreviations are expanded."""
    assert "другие" in expand_abbreviations("и др.")
    assert "прочее" in expand_abbreviations("и пр.")
    assert "смотри" in expand_abbreviations("см.")
    assert "например" in expand_abbreviations("напр.")


def test_no_false_positives_on_plain_text() -> None:
    """Plain text without abbreviations is unchanged."""
    text = "Он пошёл домой и лёг спать."
    assert expand_abbreviations(text) == text


def test_compound_abbreviation() -> None:
    """Combined 'и т.д. и т.п.' is expanded as a whole."""
    result = expand_abbreviations("и т. д. и т. п.")
    assert result == "и так далее и тому подобное"
