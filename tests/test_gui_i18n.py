from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from book_normalizer.gui.app import _resolve_theme
from book_normalizer.gui.i18n import SUPPORTED_LANGUAGES, TRANSLATIONS, set_language, t
from book_normalizer.gui.main_window import MainWindow
from book_normalizer.gui.pages.normalize_page import NormalizePage
from book_normalizer.gui.pages.roles_page import RolesPage
from book_normalizer.gui.widgets.voice_table import VoiceTableWidget
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


def test_progress_widgets_retranslate_ready_state(qtbot) -> None:
    app = qapp()
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    flush_events(app)

    for code, _label in SUPPORTED_LANGUAGES:
        index = window._lang_combo.findData(code)
        assert index >= 0
        window._lang_combo.setCurrentIndex(index)
        flush_events(app)
        ready = t("progress.ready")
        for page in (
            window._normalize_page,
            window._roles_page,
            window._voices_page,
            window._synthesis_page,
            window._assembly_page,
        ):
            assert page._progress._status.text() == ready

    set_language("ru")


def test_cached_restore_statuses_retranslate_after_language_switch(qtbot) -> None:
    app = qapp()
    normalize_page = NormalizePage()
    roles_page = RolesPage()
    qtbot.addWidget(normalize_page)
    qtbot.addWidget(roles_page)

    set_language("ru")
    normalize_page._cache_restored_chapters = 1
    normalize_page._progress.set_status(t("norm.cache_restored", n=1))
    roles_page._cache_restored_roles = 90
    roles_page._progress.set_status(t("roles.cache_restored", n=90))
    normalize_page.retranslate()
    assert normalize_page._help_buttons["norm.llm_tip"].toolTip() == t("norm.llm_tip")

    set_language("zh")
    normalize_page.retranslate()
    roles_page.retranslate()
    flush_events(app)

    assert normalize_page._progress._status.text() == t("norm.cache_restored", n=1)
    assert roles_page._progress._status.text() == t("roles.cache_restored", n=90)
    assert "Восстановлено" not in normalize_page._progress._status.text()
    assert "Роли восстановлены" not in roles_page._progress._status.text()
    assert normalize_page._help_buttons["norm.llm_tip"].toolTip() == t("norm.llm_tip")

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


def test_workflow_status_copy_matches_five_step_product_flow() -> None:
    expected_fragments = {
        "ru": {
            "status.norm_done": "извлеките роли",
            "status.roles_done": "проверьте чанки",
            "status.voices_done": "вкладку «Голоса»",
            "voice.chunks_done": "вкладку «Голоса»",
        },
        "en": {
            "status.norm_done": "Extract roles next",
            "status.roles_done": "Review chunks next",
            "status.voices_done": "Go to Voices tab",
            "voice.chunks_done": "Go to the Voices tab",
        },
        "zh": {
            "status.norm_done": "提取角色",
            "status.roles_done": "检查分块",
            "status.voices_done": "声音",
            "voice.chunks_done": "声音",
        },
        "kk": {
            "status.norm_done": "рөлдерді",
            "status.roles_done": "чанктарды",
            "status.voices_done": "Дауыстар",
            "voice.chunks_done": "Дауыстар",
        },
        "uz": {
            "status.norm_done": "rollarni",
            "status.roles_done": "bo‘laklarni",
            "status.voices_done": "Ovozlar",
            "voice.chunks_done": "Ovozlar",
        },
    }
    stale_fragments = (
        "Synthesize tab",
        "синтез",
        "综合",
        "Синтездеу",
        "Sintezlash",
        "Voice assignment ready",
        "Дауыстық тапсырма дайын",
        "Ovozli topshiriq tayyor",
    )

    for code, fragments in expected_fragments.items():
        set_language(code)
        for key, fragment in fragments.items():
            text = t(key, n=3)
            assert fragment in text, f"{key}:{code}"
            assert not any(stale in text for stale in stale_fragments), f"{key}:{code}:{text}"

    set_language("ru")


def test_voice_chunk_table_labels_are_polished_for_supported_languages() -> None:
    expected = {
        "ru": {
            "voice.play_audio": "Слушать",
            "voice.load_manifest": "Загрузить",
            "voice.save_manifest": "Сохранить",
            "voice.editor_split": "Разделить",
            "synth.chunk_editor_split": "Разделить",
            "synth.load_manifest": "Загрузить",
            "voice.col_chapter": "Гл.",
            "voice.col_audio": "Аудио",
            "voice.type_narrator": "Автор",
        },
        "zh": {
            "voice.play_audio": "播放",
            "voice.load_manifest": "加载",
            "voice.save_manifest": "保存",
            "voice.editor_split": "分割",
            "synth.chunk_editor_split": "分割",
            "synth.load_manifest": "加载",
            "voice.col_chapter": "章",
            "voice.col_audio": "音频",
            "voice.type_narrator": "旁白",
        },
        "kk": {
            "voice.play_audio": "Тыңдау",
            "voice.load_manifest": "Жүктеу",
            "voice.save_manifest": "Сақтау",
            "voice.editor_split": "Бөлу",
            "synth.chunk_editor_split": "Бөлу",
            "synth.load_manifest": "Жүктеу",
            "voice.col_chapter": "Тар.",
            "voice.col_audio": "Дыбыс",
            "voice.type_narrator": "Автор",
        },
        "uz": {
            "voice.play_audio": "Eshitish",
            "voice.load_manifest": "Yuklash",
            "voice.save_manifest": "Saqlash",
            "voice.editor_split": "Bo'lish",
            "synth.chunk_editor_split": "Bo'lish",
            "synth.load_manifest": "Yuklash",
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


def test_reported_localization_hotspots_are_translated_for_non_english_languages() -> None:
    expected = {
        "zh": {
            "voice.prev_segment": "上一个",
            "voice.next_segment": "下一个",
            "synth.asr_title": "ASR 质量门",
            "synth.asr_filter": "分块筛选：",
            "synth.asr_filter_bad": "失败/警告",
            "norm.ocr_mode_auto": "自动",
            "synth.quality_no_manifest": "尚未加载清单。",
        },
        "kk": {
            "voice.prev_segment": "Алдыңғы",
            "voice.next_segment": "Келесі",
            "synth.asr_title": "ASR сапа тексеруі",
            "synth.asr_filter": "Чанк сүзгісі:",
            "synth.asr_filter_bad": "қате/ескерту",
            "norm.ocr_mode_auto": "Авто",
            "synth.quality_no_manifest": "Манифест жүктелмеген.",
        },
        "uz": {
            "voice.prev_segment": "Oldingi",
            "voice.next_segment": "Keyingi",
            "synth.asr_title": "ASR sifat tekshiruvi",
            "synth.asr_filter": "Bo'lak filtri:",
            "synth.asr_filter_bad": "xato/ogoh",
            "norm.ocr_mode_auto": "Avto",
            "synth.quality_no_manifest": "Manifest yuklanmagan.",
        },
    }
    english_starts = {
        "synth.asr_timeout_help": "Maximum time",
        "synth.asr_device_help": "auto lets",
        "voice.prev_segment_tip": "Select the previous",
        "voice.next_segment_tip": "Select the next",
    }

    for code, labels in expected.items():
        set_language(code)
        for key, value in labels.items():
            assert t(key) == value, f"{key}:{code}"
        for key, english_start in english_starts.items():
            assert not t(key).startswith(english_start), f"{key}:{code}"

    set_language("ru")


def test_roles_page_localizes_generic_inventory_rows(qtbot) -> None:
    app = qapp()
    page = RolesPage()
    qtbot.addWidget(page)
    inventory = {
        "total_direct_speech": 3,
        "total_segments": 4,
        "roles": [
            {
                "display_name": "Male character",
                "description": "Direct-speech character inferred from local dialogue context.",
                "direct_speech_count": 3,
                "segment_count": 4,
                "emotions": [
                    {"emotion": "calm", "count": 2},
                    {"emotion": "tense", "count": 1},
                ],
            }
        ],
    }
    expected = {
        "zh": ("男性角色", "本地对话", "平静: 2", "紧张: 1"),
        "kk": ("Ер кейіпкер", "Жергілікті", "Тыныш: 2", "Шиеленісті: 1"),
        "uz": ("Erkak personaj", "Lokal dialog", "Tinch: 2", "Tarang: 1"),
    }

    set_language("ru")
    page._populate_table(inventory)
    for code, (role, description_part, calm, tense) in expected.items():
        set_language(code)
        page.retranslate()
        flush_events(app)
        assert page._table.item(0, 0).text() == role
        assert description_part in page._table.item(0, 1).text()
        emotion_text = page._table.item(0, 3).text()
        assert calm in emotion_text
        assert tense in emotion_text

    set_language("ru")


def test_voice_table_retranslate_refreshes_loaded_rows_and_controls(qtbot) -> None:
    app = qapp()
    table = VoiceTableWidget()
    qtbot.addWidget(table)
    table.set_segments(
        [
            {
                "segment_index": 0,
                "chapter_index": 0,
                "role": "narrator",
                "voice_id": "narrator_calm",
                "intonation": "calm",
                "text": "Line",
                "is_dialogue": False,
            }
        ]
    )
    table._ensure_row_widgets(0)

    set_language("ru")
    table.retranslate()
    flush_events(app)
    assert table._chapter_filter.itemText(0) == "Все главы"
    assert table._table.item(0, 1).text() == "Автор"
    assert table._table.cellWidget(0, 6).currentText() == "Спокойная"

    set_language("zh")
    table.retranslate()
    table._ensure_row_widgets(0)
    flush_events(app)
    assert table._chapter_filter.itemText(0) == "所有章节"
    assert table._btn_prev_segment.text() == "上一个"
    assert table._btn_next_segment.text() == "下一个"
    assert table._table.item(0, 1).text() == "旁白"
    assert table._table.cellWidget(0, 6).currentText() == "平静"

    set_language("ru")


def test_synthesis_asr_and_quality_panels_are_localized(qtbot) -> None:
    app = qapp()
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    flush_events(app)
    window._tabs.setCurrentIndex(3)
    window._synthesis_page._mode_tabs.setCurrentIndex(2)
    expected = {
        "zh": ("ASR 质量门", "全部", "失败/警告", "自动", "质量面板", "尚未加载清单。"),
        "kk": (
            "ASR сапа тексеруі",
            "барлығы",
            "қате/ескерту",
            "Авто",
            "Сапа панелі",
            "Манифест жүктелмеген.",
        ),
        "uz": (
            "ASR sifat tekshiruvi",
            "barchasi",
            "xato/ogoh",
            "Avto",
            "Sifat paneli",
            "Manifest yuklanmagan.",
        ),
    }

    for code, labels in expected.items():
        lang_index = window._lang_combo.findData(code)
        assert lang_index >= 0
        window._lang_combo.setCurrentIndex(lang_index)
        flush_events(app)
        page = window._synthesis_page
        assert page._asr_title.text() == labels[0]
        assert page._asr_filter_combo.itemText(0) == labels[1]
        assert page._asr_filter_combo.itemText(1) == labels[2]
        assert page._asr_device_combo.itemText(0) == labels[3]
        assert page._quality_title.text() == labels[4]
        assert page._quality_summary_label.text() == labels[5]
        assert page._btn_quality_run.text() != "Run full QA"

    set_language("ru")


def test_synthesis_static_statuses_retranslate_after_language_switch(qtbot) -> None:
    app = qapp()
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    flush_events(app)

    combo = window._lang_combo
    combo.setCurrentIndex(combo.findData("ru"))
    flush_events(app)
    page = window._synthesis_page
    page._sample_status.setText(
        "Sample voice необязателен; если включен, prompt extraction выполнится перед чанками.",
    )
    page._asr_status.setText(t("synth.asr_idle"))

    combo.setCurrentIndex(combo.findData("zh"))
    flush_events(app)

    assert page._sample_status.text() == t("synth.sample_idle")
    assert page._asr_status.text() == t("synth.asr_idle")
    assert "Sample voice" not in page._sample_status.text()
    assert "ASR QA только" not in page._asr_status.text()

    set_language("ru")


def test_chunk_segment_source_copy_replaces_old_dialogue_attribution_terms() -> None:
    expected = {
        "ru": {
            "voice.speaker_mode": "Источник сегментов:",
            "voice.speaker_mode_heuristic": "Правила: быстрое разбиение",
            "voice.speaker_mode_llm": "LLM: роли и сцены",
            "voice.speaker_mode_manual": "Ручной манифест",
            "voice.detect": "Пересобрать сегменты",
            "voice.detecting": "Собираем умные сегменты…",
            "voice.attributing": "Размечаем роли (LLM)…",
            "voice.segments_ready": "сегментов готово",
        },
        "en": {
            "voice.speaker_mode": "Segment source:",
            "voice.speaker_mode_heuristic": "Rules: quick split",
            "voice.speaker_mode_llm": "LLM: roles and scenes",
            "voice.speaker_mode_manual": "Manual manifest",
            "voice.detect": "Rebuild segments",
            "voice.detecting": "Building smart segments…",
            "voice.attributing": "Assigning roles (LLM)…",
            "voice.segments_ready": "segments ready",
        },
        "zh": {
            "voice.speaker_mode": "分段来源：",
            "voice.speaker_mode_heuristic": "规则：快速分段",
            "voice.speaker_mode_llm": "LLM：角色与场景",
            "voice.speaker_mode_manual": "手动清单",
            "voice.detect": "重新生成分段",
            "voice.detecting": "正在生成智能分段…",
            "voice.attributing": "正在标注角色 (LLM)…",
            "voice.segments_ready": "分段已就绪",
        },
        "kk": {
            "voice.speaker_mode": "Сегмент көзі:",
            "voice.speaker_mode_heuristic": "Ереже: жылдам бөлу",
            "voice.speaker_mode_llm": "LLM: рөлдер мен көріністер",
            "voice.speaker_mode_manual": "Қолмен манифест",
            "voice.detect": "Сегменттерді қайта құру",
            "voice.detecting": "Ақылды сегменттер жиналуда…",
            "voice.attributing": "Рөлдер белгіленуде (LLM)…",
            "voice.segments_ready": "сегмент дайын",
        },
        "uz": {
            "voice.speaker_mode": "Segment manbasi:",
            "voice.speaker_mode_heuristic": "Qoidalar: tez bo'lish",
            "voice.speaker_mode_llm": "LLM: rollar va sahnalar",
            "voice.speaker_mode_manual": "Qo'lda manifest",
            "voice.detect": "Segmentlarni qayta qurish",
            "voice.detecting": "Aqlli segmentlar yig'ilmoqda…",
            "voice.attributing": "Rollar belgilanmoqda (LLM)…",
            "voice.segments_ready": "segment tayyor",
        },
    }
    stale_fragments = (
        "Dialogue Attribution",
        "Разметка реплик",
        "Speaker attribution",
        "Атрибуция дикторов",
        "male/female",
        "муж./жен.",
        "对话归属",
        "男性/女性",
        "Диалог атрибуты",
        "Dialog atributi",
    )

    for code, labels in expected.items():
        set_language(code)
        for key, value in labels.items():
            text = t(key, n=3, mode="LLM")
            assert value in text, f"{key}:{code}:{text}"
        combined = "\n".join(
            t(key, n=3, mode="LLM")
            for key in (
                "voice.speaker_mode",
                "voice.speaker_mode_hint",
                "voice.detecting",
                "voice.attributing",
                "voice.segments_ready",
            )
        )
        assert not any(fragment in combined for fragment in stale_fragments), (
            code,
            combined,
        )

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


def test_synthesis_sample_panel_labels_are_localized(qtbot) -> None:
    expected = {
        "ru": ("Образец голоса", "Новый образец на всю книгу", "Аудио образца:", "Слушать", "Текст образца:"),
        "en": ("CustomVoice Sample", "New sample for whole book", "Sample audio:", "Play", "Sample text:"),
        "zh": ("声音样本", "整本书使用新样本", "样本音频：", "播放", "样本文本："),
        "kk": ("Дауыс үлгісі", "Бүкіл кітапқа жаңа үлгі", "Үлгі аудио:", "Тыңдау", "Үлгі мәтіні:"),
        "uz": ("Ovoz namunasi", "Butun kitob uchun yangi namuna", "Namuna audiosi:", "Eshitish", "Namuna matni:"),
    }

    app = qapp()
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    flush_events(app)

    combo = window._lang_combo
    window._tabs.setCurrentIndex(3)
    page = window._synthesis_page
    for code, labels in expected.items():
        index = combo.findData(code)
        assert index >= 0
        combo.setCurrentIndex(index)
        flush_events(app)
        assert (
            page._sample_title.text(),
            page._custom_strategy_combo.itemText(0),
            page._sample_audio_label.text(),
            page._btn_sample_play.text(),
            page._sample_transcript_label.text(),
        ) == labels

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


def test_linux_ci_installs_cjk_font_package_for_chinese_gui() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "fonts-noto-cjk" in workflow


def test_theme_keeps_disabled_primary_buttons_readable() -> None:
    theme = _resolve_theme()
    block = theme.split("QPushButton#primaryBtn:disabled", maxsplit=1)[1].split(
        "}",
        maxsplit=1,
    )[0]

    assert "rgba(30, 41, 59, 0.52)" in block
    assert "rgba(255, 255, 255, 0.36)" not in block
