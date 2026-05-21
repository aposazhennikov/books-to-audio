from __future__ import annotations

import re

from book_normalizer.gui.i18n import SUPPORTED_LANGUAGES, TRANSLATIONS, set_language, t
from book_normalizer.gui.main_window import MainWindow
from tests.gui.helpers import assert_layout_sane, flush_events, qapp

_FORMAT_FIELD_RE = re.compile(r"(?<!\{)\{([^{}]+)\}(?!\})")


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
        assert window._tabs.tabText(1) == t("tab.voices")
        assert window._tabs.tabText(2) == t("tab.synthesize")
        assert window._tabs.tabText(3) == t("tab.assemble")
        for tab_index in range(window._tabs.count()):
            window._tabs.setCurrentIndex(tab_index)
            flush_events(app)
        assert_layout_sane(window)

    set_language("ru")
