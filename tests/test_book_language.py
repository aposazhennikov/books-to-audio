from __future__ import annotations

from book_normalizer.languages import (
    SUPPORTED_LANGUAGE_CODES,
    normalize_book_language,
    qwen_tts_language,
    readable_word_ratio,
    target_script_char_count,
    target_script_ratio,
    tesseract_language,
    text_unreadable,
)


def test_supported_book_languages_match_product_scope() -> None:
    assert SUPPORTED_LANGUAGE_CODES == ("ru", "en", "zh", "kk", "uz")


def test_language_aliases_and_runtime_names() -> None:
    assert normalize_book_language("rus") == "ru"
    assert normalize_book_language("en-US") == "en"
    assert normalize_book_language("kz") == "kk"
    assert normalize_book_language("uzb") == "uz"
    assert normalize_book_language("unknown") == "ru"

    assert tesseract_language("zh") == "chi_sim"
    assert qwen_tts_language("kk") == "Kazakh"


def test_language_script_quality_uses_selected_language() -> None:
    english = "This is a clean English paragraph with enough words."
    chinese = "\u8fd9\u662f\u4e00\u6bb5\u53ef\u8bfb\u7684\u4e2d\u6587\u6587\u672c\u3002"

    assert target_script_ratio(english, "en") == 1.0
    assert target_script_char_count(chinese, "zh") >= 8
    assert readable_word_ratio(english, "en") > 0.7
    assert text_unreadable(english, "ru") is True
    assert text_unreadable(english, "en") is False
