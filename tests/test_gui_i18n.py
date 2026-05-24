from __future__ import annotations

import os
import platform
import re
import unicodedata

import pytest

from book_normalizer.gui.app import _resolve_theme
from book_normalizer.gui.i18n import SUPPORTED_LANGUAGES, TRANSLATIONS, set_language, t
from book_normalizer.gui.main_window import MainWindow
from tests.gui.helpers import assert_layout_sane, flush_events, qapp

_FORMAT_FIELD_RE = re.compile(r"(?<!\{)\{([^{}]+)\}(?!\})")
_MOJIBAKE_MARKERS = (
    "РЈ",
    "Рџ",
    "РЎ",
    "Рќ",
    "Рћ",
    "Рљ",
    "Рґ",
    "СЃ",
    "вЂ",
    "К»",
    "Кј",
    "Тљ",
)


def _has_regional_indicator_or_symbol(text: str) -> bool:
    return any(
        "\U0001f1e6" <= char <= "\U0001f1ff"
        or unicodedata.category(char) == "So"
        for char in text
    )


def _format_fields(text: str) -> set[str]:
    return set(_FORMAT_FIELD_RE.findall(text))


def test_all_gui_translations_cover_every_supported_language() -> None:
    supported = {code for code, _label in SUPPORTED_LANGUAGES}

    for key, entry in TRANSLATIONS.items():
        assert supported <= set(entry), key
        en_fields = _format_fields(entry["en"])
        for lang in supported:
            text = entry[lang]
            if key != "app.subtitle":
                assert text.strip(), f"{key}:{lang}"
            assert _format_fields(text) == en_fields, f"{key}:{lang}"
            assert "??" not in text, f"{key}:{lang}"
            assert "wsl" not in text.lower(), f"{key}:{lang}"
            assert not any(marker in text for marker in _MOJIBAKE_MARKERS), f"{key}:{lang}"


def test_main_window_switches_every_supported_gui_language(qtbot) -> None:
    app = qapp()
    window = MainWindow()
    qtbot.addWidget(window)
    window.resize(1180, 760)
    window.show()
    flush_events(app)

    combo = window._lang_combo
    assert combo.count() == len(SUPPORTED_LANGUAGES)
    assert not hasattr(window, "_subtitle")

    for index, (code, _label) in enumerate(SUPPORTED_LANGUAGES):
        combo.setCurrentIndex(index)
        flush_events(app)
        assert combo.currentData() == code
        assert window.windowTitle() == t("app.title")
        assert window._title.text() == t("app.title")
        assert window._tabs.tabText(0) == t("tab.normalize")
        assert window._tabs.tabText(1) == t("tab.roles")
        assert window._tabs.tabText(2) == t("tab.chunks")
        assert window._tabs.tabText(3) == t("tab.voices")
        assert window._tabs.tabText(4) == t("tab.assemble")
        for tab_index in range(window._tabs.count()):
            window._tabs.setCurrentIndex(tab_index)
            flush_events(app)
        assert_layout_sane(window)

    set_language("ru")


def test_language_selector_uses_text_codes_not_flag_emoji(qtbot) -> None:
    app = qapp()
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    flush_events(app)

    combo = window._lang_combo
    expected_codes = [code.upper() for code, _label in SUPPORTED_LANGUAGES]
    assert combo.count() == len(expected_codes)
    for index, code in enumerate(expected_codes):
        text = combo.itemText(index)
        assert text.startswith(code)
        assert not _has_regional_indicator_or_symbol(text), text

    window.close()
    window.deleteLater()


def test_tesseract_psm_help_is_readable_in_every_supported_language() -> None:
    expectations = {
        "en": ("normal book page", "reading order may need review", "do not use for full pages"),
        "ru": ("обычная страница книги", "порядок чтения надо проверить", "не использовать для полной страницы"),
        "zh": ("普通书页", "阅读顺序可能需要复查", "不要用于整页"),
        "kk": ("кітаптың қалыпты беті", "оқу ретін тексеріңіз", "толық бетке қолданбаңыз"),
        "uz": ("oddiy kitob sahifasi", "o'qish tartibini tekshiring", "to'liq sahifa uchun ishlatmang"),
    }
    vague_fragments = {
        "single column",
        "sparse text",
        "один столбец",
        "редкий текст",
        "разреженный текст",
        "单列",
        "稀疏",
        "үздіксіз мәтін бағаны",
        "uzluksiz matn ustuni",
    }

    for code, _label in SUPPORTED_LANGUAGES:
        set_language(code)
        options = [t(f"norm.ocr_psm_{value}") for value in (3, 4, 6, 11, 13)]
        help_text = t("norm.ocr_psm_tip").lower()
        combined = "\n".join(options + [help_text]).lower()
        assert len(options) == 5
        assert all(option.strip() for option in options)
        assert all("??" not in option for option in options)
        assert "??" not in help_text
        assert "\ufffd" not in help_text
        assert not any(fragment.lower() in combined for fragment in vague_fragments)
        for fragment in expectations[code]:
            assert fragment in help_text

    set_language("ru")


def test_voice_chunk_table_labels_are_polished_for_supported_languages() -> None:
    expected = {
        "ru": {
            "voice.play_audio": "Слушать",
            "voice.col_chapter": "Гл.",
            "voice.col_audio": "Аудио",
            "voice.type_narrator": "Автор",
        },
        "zh": {
            "voice.play_audio": "播放",
            "voice.col_chapter": "章",
            "voice.col_audio": "音频",
            "voice.type_narrator": "旁白",
        },
        "kk": {
            "voice.play_audio": "Тыңдау",
            "voice.col_chapter": "Тар.",
            "voice.col_audio": "Дыбыс",
            "voice.type_narrator": "Автор",
        },
        "uz": {
            "voice.play_audio": "Eshitish",
            "voice.col_chapter": "Bob",
            "voice.col_audio": "Ovoz",
            "voice.type_narrator": "Hikoya",
        },
    }

    for code, labels in expected.items():
        set_language(code)
        for key, value in labels.items():
            assert t(key) == value
        assert "LLM Model" not in t("voice.llm_model")
        assert "演讲" not in t("voice.stats_segments")
        assert "Баяндауыш" not in t("voice.stats_segments")

    set_language("ru")


def test_synthesis_mode_tabs_are_localized_for_supported_languages(qtbot) -> None:
    expected = {
        "ru": ["Свой голос", "Готовые голоса", "Дополнительно"],
        "en": ["Custom Voice", "Built-in Speakers", "Advanced"],
        "zh": ["自定义声音", "内置声音", "高级"],
        "kk": ["Өз дауысы", "Дайын дауыстар", "Қосымша"],
        "uz": ["O'z ovozi", "Tayyor ovozlar", "Qo'shimcha"],
    }
    english_leaks = ("custom voice", "built-in speakers", "advanced")

    app = qapp()
    window = MainWindow()
    qtbot.addWidget(window)
    window.resize(760, 520)
    window.show()
    flush_events(app)

    combo = window._lang_combo
    window._tabs.setCurrentIndex(3)
    for code, labels in expected.items():
        index = combo.findData(code)
        assert index >= 0
        combo.setCurrentIndex(index)
        flush_events(app)
        page = window._synthesis_page
        assert [page._mode_tabs.tabText(i) for i in range(3)] == labels
        if code != "en":
            combined = " ".join(labels).lower()
            assert not any(leak in combined for leak in english_leaks)

    set_language("ru")


def test_theme_has_multilingual_font_fallbacks() -> None:
    theme = _resolve_theme()

    for font_name in (
        "Segoe UI",
        "Microsoft YaHei",
        "PingFang SC",
        "Noto Sans CJK",
        "WenQuanYi Zen Hei",
        "Noto Sans",
    ):
        assert font_name in theme


def test_ci_linux_has_installed_cjk_font_for_chinese_gui() -> None:
    if os.environ.get("CI") != "true" or platform.system() != "Linux":
        pytest.skip("CJK font availability is enforced on Linux CI.")

    qt_gui = pytest.importorskip("PyQt6.QtGui")
    families = set(qt_gui.QFontDatabase.families())

    assert any(
        any(token in family for token in ("Noto Sans CJK", "WenQuanYi", "Source Han"))
        for family in families
    )


def test_theme_keeps_disabled_primary_buttons_readable() -> None:
    theme = _resolve_theme()
    block = theme.split("QPushButton#primaryBtn:disabled", maxsplit=1)[1].split(
        "}",
        maxsplit=1,
    )[0]

    assert "rgba(30, 41, 59, 0.52)" in block
    assert "rgba(255, 255, 255, 0.36)" not in block
