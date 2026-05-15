"""Tests for abbreviation expansion."""

import pytest

from book_normalizer.normalization.abbreviations import expand_abbreviations

# ── Multi-word abbreviations ─────────────────────────────────────────

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
        ("в т. ч. налоги", "в том числе налоги"),
        ("т. о. результат", "таким образом результат"),
        ("до н. э.", "до нашей эры"),
        ("в 100 г. н. э.", "в 100 года нашей эры"),
    ],
)
def test_multi_word_abbreviations(input_text: str, expected: str) -> None:
    """Multi-word abbreviations are expanded correctly."""
    assert expand_abbreviations(input_text) == expected


def test_compound_abbreviation() -> None:
    """Combined 'и т.д. и т.п.' is expanded as a whole."""
    result = expand_abbreviations("и т. д. и т. п.")
    assert result == "и так далее и тому подобное"


# ── Year / century abbreviations ─────────────────────────────────────

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


def test_century_range_abbreviation() -> None:
    """'вв.' after a Roman numeral range is expanded to 'веков'."""
    assert expand_abbreviations("XIX—XX вв.") == "XIX–XX веков"


# ── Number-adjacent abbreviations ────────────────────────────────────

@pytest.mark.parametrize(
    "input_text, expected_word",
    [
        ("45 млн экземпляров", "миллионов"),
        ("45 млн. рублей", "миллионов"),
        ("10 млрд рублей", "миллиардов"),
        ("10 млрд. долларов", "миллиардов"),
        ("5 тыс. метров", "тысяч"),
        ("100 руб.", "рублей"),
        ("50 коп.", "копеек"),
        ("10 долл.", "долларов"),
        ("200 экз.", "экземпляров"),
    ],
)
def test_number_adjacent(input_text: str, expected_word: str) -> None:
    """Number-adjacent abbreviations are expanded."""
    result = expand_abbreviations(input_text)
    assert expected_word in result


# ── Measurement units ────────────────────────────────────────────────

@pytest.mark.parametrize(
    "input_text, expected_word",
    [
        ("10 км от города", "километров"),
        ("5 кг муки", "килограммов"),
        ("3 мм толщиной", "миллиметров"),
        ("20 см длиной", "сантиметров"),
        ("100 га земли", "гектаров"),
    ],
)
def test_measurement_units(input_text: str, expected_word: str) -> None:
    """Measurement units are expanded."""
    result = expand_abbreviations(input_text)
    assert expected_word in result


# ── Simple standalone abbreviations ──────────────────────────────────

def test_simple_abbreviations() -> None:
    """Simple standalone abbreviations are expanded."""
    assert "другие" in expand_abbreviations("и др.")
    assert "прочее" in expand_abbreviations("и пр.")
    assert "смотри" in expand_abbreviations("см.")
    assert "например" in expand_abbreviations("напр.")


@pytest.mark.parametrize(
    "input_text, expected_word",
    [
        ("проф. Иванов", "профессор"),
        ("акад. Петров", "академик"),
        ("доц. Сидоров", "доцент"),
        ("канд. наук", "кандидат"),
        ("им. Ленина", "имени"),
        ("гр. Кузнецов", "гражданин"),
        ("зав. кафедрой", "заведующий"),
        ("зам. директора", "заместитель"),
    ],
)
def test_title_abbreviations(input_text: str, expected_word: str) -> None:
    """Title / position abbreviations are expanded."""
    result = expand_abbreviations(input_text)
    assert expected_word in result


@pytest.mark.parametrize(
    "input_text, expected_word",
    [
        ("обл. Московская", "область"),
        ("ул. Ленина", "улица"),
        ("пер. Тихий", "переулок"),
        ("пл. Победы", "площадь"),
        ("бул. Гоголя", "бульвар"),
        ("д. 15", "дом"),
        ("корп. 2", "корпус"),
    ],
)
def test_address_abbreviations(input_text: str, expected_word: str) -> None:
    """Address abbreviations are expanded."""
    result = expand_abbreviations(input_text)
    assert expected_word in result


@pytest.mark.parametrize(
    "input_text, expected_word",
    [
        ("изд. 2017", "издание"),
        ("ред. Петрова", "редакция"),
        ("рис. 5", "рисунок"),
        ("табл. 3", "таблица"),
        ("гл. 7", "глава"),
        ("ст. 128", "статья"),
        ("с. 45", "страница"),
        ("сб. трудов", "сборник"),
        ("вып. 12", "выпуск"),
    ],
)
def test_publication_abbreviations(input_text: str, expected_word: str) -> None:
    """Publication / editorial abbreviations are expanded."""
    result = expand_abbreviations(input_text)
    assert expected_word in result


@pytest.mark.parametrize(
    "input_text, expected_word",
    [
        ("15 мин.", "минут"),
        ("30 сек.", "секунд"),
        ("г. Москва", "город"),
        ("р. Волга", "река"),
        ("оз. Байкал", "озеро"),
        ("о. Сахалин", "остров"),
        ("п. Листвянка", "посёлок"),
        ("тел. 123-45-67", "телефон"),
    ],
)
def test_misc_abbreviations(input_text: str, expected_word: str) -> None:
    """Miscellaneous abbreviations are expanded."""
    result = expand_abbreviations(input_text)
    assert expected_word in result


# ── Safety checks ────────────────────────────────────────────────────

def test_no_false_positives_on_plain_text() -> None:
    """Plain text without abbreviations is unchanged."""
    text = "Он пошёл домой и лёг спать."
    assert expand_abbreviations(text) == text


def test_mln_not_expanded_without_number() -> None:
    """'млн' without a preceding number is not expanded."""
    text = "Слово млн в тексте"
    assert "миллионов" not in expand_abbreviations(text)
