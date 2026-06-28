"""Tests for OCR artifact fixes."""

import pytest

from book_normalizer.normalization.ocr_fixes import (
    fix_mixed_script,
    fix_ocr_artifacts,
    fix_russian_particle_hyphens,
)
from book_normalizer.normalization.pipeline import NormalizationPipeline


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


def test_russian_particle_hyphens_restored() -> None:
    text = "Он умолял вывести их из пустыни хоть куданибудь."
    assert fix_russian_particle_hyphens(text) == (
        "Он умолял вывести их из пустыни хоть куда-нибудь."
    )


def test_russian_particle_hyphen_fix_handles_common_pronouns() -> None:
    text = "ктото, чтолибо, гденибудь, какойто, откудато"
    assert fix_russian_particle_hyphens(text) == (
        "кто-то, что-либо, где-нибудь, какой-то, откуда-то"
    )


def test_russian_particle_hyphen_fix_handles_personal_pronouns() -> None:
    text = "А мыто, идиоты, эксцентриситет высчитывали."
    assert fix_russian_particle_hyphens(text) == (
        "А мы-то, идиоты, эксцентриситет высчитывали."
    )


def test_russian_particle_hyphen_fix_does_not_touch_ordinary_words() -> None:
    text = "Это зато работает без лишних правок."
    assert fix_russian_particle_hyphens(text) == text


def test_ocr_artifacts_restore_russian_particle_hyphens() -> None:
    text = "Он умолял вывести их из пустыни хоть куданибудь."
    assert fix_ocr_artifacts(text) == (
        "Он умолял вывести их из пустыни хоть куда-нибудь."
    )


def test_ocr_artifacts_restore_dropped_initial_letter_in_priem() -> None:
    text = "рием шел ни шатко, ни валко."
    assert fix_ocr_artifacts(text) == "Прием шел ни шатко, ни валко."


def test_pipeline_restores_dropped_initial_letter_in_priem() -> None:
    text = "рием шел ни шатко, ни валко."
    assert NormalizationPipeline.for_language("ru").normalize_text(text) == (
        "Приём шёл ни шатко, ни валко."
    )


def test_ocr_artifacts_restore_obvious_missing_prepositions() -> None:
    text = (
        "с одной планет Зенов. "
        "искать кристаллы оставленной кланом планете. "
        "Пилигримы записывали них информацию."
    )
    assert fix_ocr_artifacts(text) == (
        "с одной из планет Зенов. "
        "искать кристаллы на оставленной кланом планете. "
        "Пилигримы записывали в них информацию."
    )


def test_ocr_artifacts_remove_spurious_period_after_single_letter() -> None:
    text = "Все гораздо хуже. К. Земле идёт Имперский флот."
    assert fix_ocr_artifacts(text) == "Все гораздо хуже. К Земле идёт Имперский флот."


def test_ocr_artifacts_restore_dropped_initial_from_nearby_name() -> None:
    text = "ергей понимал, что спит. Сергей вспомнил сон."
    assert fix_ocr_artifacts(text) == "Сергей понимал, что спит. Сергей вспомнил сон."


def test_ocr_artifacts_restore_dropped_initial_without_name_hardcode() -> None:
    text = "лександр вошёл в комнату. Александр кивнул."
    assert fix_ocr_artifacts(text) == "Александр вошёл в комнату. Александр кивнул."


def test_ocr_artifacts_do_not_restore_dropped_initial_without_context() -> None:
    text = "ергей понимал, что спит."
    assert fix_ocr_artifacts(text) == text


def test_ocr_artifacts_split_glued_function_word_with_pronoun_tail() -> None:
    text = "Ты уверен, что тут вокругнечему ломаться?"
    assert fix_ocr_artifacts(text) == "Ты уверен, что тут вокруг нечему ломаться?"


def test_ocr_artifacts_split_past_plural_verb_from_u_preposition() -> None:
    text = "Искры падалиу их ног и быстро гасли."
    assert fix_ocr_artifacts(text) == "Искры падали у их ног и быстро гасли."


def test_ocr_artifacts_do_not_split_ordinary_words_ending_with_u_sound() -> None:
    text = "Я не понимаю, почему их не предупредили."
    assert fix_ocr_artifacts(text) == text


def test_ocr_artifacts_restores_obvious_chernaya_kniga_direction() -> None:
    text = "они должны бежать не от «Черной Книги», а ней."
    assert fix_ocr_artifacts(text) == "они должны бежать не от «Черной Книги», а за ней."


def test_ocr_artifacts_preserve_short_russian_author_tag_tail() -> None:
    text = (
        "\u2014 \u041d\u0435\u043f\u0440\u0430\u0432\u0438\u043b\u044c\u043d\u0430\u044f "
        "\u043a\u043e\u043c\u0431\u0438\u043d\u0430\u0446\u0438\u044f "
        "\u043c\u0430\u0441\u0435\u043b, \u2014 \u0441\u0443\u0445\u043e "
        "\u0441\u043e\u043e\u0431\u0449\u0438\u043b \u043e\u043d."
    )
    assert fix_ocr_artifacts(text) == text


def test_ocr_artifacts_still_remove_short_latin_trailing_junk() -> None:
    text = "\u0420\u0443\u0441\u0441\u043a\u0438\u0439 \u0442\u0435\u043a\u0441\u0442 xy"
    assert fix_ocr_artifacts(text) == "\u0420\u0443\u0441\u0441\u043a\u0438\u0439 \u0442\u0435\u043a\u0441\u0442"


def test_pipeline_restores_particle_hyphen_after_line_hyphen_repair() -> None:
    text = "А мы-\nто, идиоты, эксцентриситет высчитывали."
    assert NormalizationPipeline.for_language("ru").normalize_text(text) == (
        "А мы-то, идиоты, эксцентриситет высчитывали."
    )
