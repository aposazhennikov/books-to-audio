"""Internationalization (i18n) support for GUI."""

# ruff: noqa: E501

from __future__ import annotations

from typing import Any

from book_normalizer.gui.i18n_catalog import (
    TRANSLATIONS,
    TranslationMergeReport,
    enrich_translation_catalog,
)

_LANG: str = "ru"
TRANSLATION_RUNTIME_REPORTS: list[TranslationMergeReport] = []

_FALLBACK_TRANSLATIONS: dict[str, dict[str, str]] = {
    "norm.web_upload_selected": {
        "en": "Uploaded book selected: {name}",
        "ru": "Загруженная книга выбрана: {name}",
        "zh": "已选择上传的图书：{name}",
        "kk": "Жүктелген кітап таңдалды: {name}",
        "uz": "Yuklangan kitob tanlandi: {name}",
    },
}

SUPPORTED_LANGUAGES: tuple[tuple[str, str], ...] = (
    ("ru", "RU  Русский"),
    ("en", "EN  English"),
    ("zh", "ZH  中文"),
    ("kk", "KK  Қазақша"),
    ("uz", "UZ  Oʻzbekcha"),
)


def set_language(lang: str) -> None:
    """Set current UI language."""
    global _LANG  # noqa: PLW0603
    supported = {code for code, _label in SUPPORTED_LANGUAGES}
    _LANG = lang if lang in supported else "en"


def get_language() -> str:
    """Return current UI language code."""
    return _LANG


_VOICE_PRESET_LOCALES: dict[str, dict[str, tuple[str, str]]] = {
    "narrator_calm": {
        "zh": ("旁白 — 平静", "平静稳定的旁白。吐字清晰，节奏从容。"),
        "kk": ("Диктор — Сабырлы", "Сабырлы, тұрақты диктор. Айқын дикция, байыпты қарқын."),
        "uz": ("Hikoyachi — Vazmin", "Vazmin, barqaror hikoyachi. Aniq talaffuz, me'yorli sur'at."),
    },
    "narrator_energetic": {
        "zh": ("旁白 — 充满活力", "有张力的旁白。自信、富有表现力的朗读。"),
        "kk": ("Диктор — Қуатты", "Ширақ диктор. Сенімді, әсерлі оқу."),
        "uz": ("Hikoyachi — Jo'shqin", "Jo'shqin hikoyachi. Ishonchli, ifodali o'qish."),
    },
    "narrator_wise": {
        "zh": ("旁白 — 睿智", "沉稳睿智的旁白。低沉音色，节奏不急不缓。"),
        "kk": ("Диктор — Дана", "Тәжірибелі, дана диктор. Терең тембр, асықпай оқу."),
        "uz": ("Hikoyachi — Dono", "Tajribali, dono hikoyachi. Chuqur tembr, shoshilmagan sur'at."),
    },
    "male_young": {
        "zh": ("男声 — 年轻", "年轻、有活力的男声。自然且带情绪的语调。"),
        "kk": ("Ер дауыс — Жас", "Жас, серпінді ер дауыс. Табиғи әрі эмоциялық интонация."),
        "uz": ("Erkak ovozi — Yosh", "Yosh, serg'ayrat erkak ovozi. Tabiiy, hissiy intonatsiya."),
    },
    "male_confident": {
        "zh": ("男声 — 自信", "自信的中年男声。清晰、果断。"),
        "kk": ("Ер дауыс — Сенімді", "Орта жастағы сенімді ер дауыс. Айқын, шешімді."),
        "uz": ("Erkak ovozi — Ishonchli", "O'rta yoshdagi ishonchli erkak ovozi. Aniq, qat'iy."),
    },
    "male_deep": {
        "zh": ("男声 — 低沉", "低沉的男中音。庄重、有分量的表达。"),
        "kk": ("Ер дауыс — Терең", "Терең баритон. Салмақты, беделді сөйлеу."),
        "uz": ("Erkak ovozi — Chuqur", "Chuqur bariton. Salobatli, vazmin nutq."),
    },
    "male_lively": {
        "zh": ("男声 — 活泼", "活泼开朗的男声。带幽默感，轻松有魅力。"),
        "kk": ("Ер дауыс — Ширақ", "Көңілді, ширақ ер дауыс. Әзіл мен жеңілдік бар."),
        "uz": ("Erkak ovozi — Tetik", "Tetik, quvnoq erkak ovozi. Hazil va yengillik bilan."),
    },
    "male_regional": {
        "zh": ("男声 — 富有表现力", "有性格的男声。表达鲜明，有个人魅力。"),
        "kk": ("Ер дауыс — Әсерлі", "Мінезі бар әсерлі ер дауыс. Харизмалы сөйлеу."),
        "uz": ("Erkak ovozi — Ifodali", "Xarakterli ifodali erkak ovozi. Jozibali nutq."),
    },
    "female_warm": {
        "zh": ("女声 — 温暖", "温暖柔和的女声。温柔、关怀的语调。"),
        "kk": ("Әйел дауыс — Жылы", "Жылы, жұмсақ әйел дауыс. Нәзік, қамқор интонация."),
        "uz": ("Ayol ovozi — Iliq", "Iliq, yumshoq ayol ovozi. Mehribon, g'amxo'r intonatsiya."),
    },
    "female_bright": {
        "zh": ("女声 — 明亮", "明亮清晰的女声。富有表现力，充满能量。"),
        "kk": ("Әйел дауыс — Жарқын", "Жарқын, анық әйел дауыс. Әсерлі, қуатты."),
        "uz": ("Ayol ovozi — Yorqin", "Yorqin, tiniq ayol ovozi. Ifodali, serg'ayrat."),
    },
    "female_playful": {
        "zh": ("女声 — 俏皮", "俏皮的女声。轻快，像带着微笑说话。"),
        "kk": ("Әйел дауыс — Ойнақы", "Ойнақы әйел дауыс. Жеңіл, күлімдеген үн."),
        "uz": ("Ayol ovozi — O'ynoqi", "O'ynoqi ayol ovozi. Yengil, tabassumli nutq."),
    },
    "female_gentle": {
        "zh": ("女声 — 轻柔", "轻柔、旋律感强的女声。柔和、安抚的表达。"),
        "kk": ("Әйел дауыс — Нәзік", "Нәзік, әуезді әйел дауыс. Жұмсақ, тыныштандыратын сөйлеу."),
        "uz": ("Ayol ovozi — Muloyim", "Muloyim, ohangdor ayol ovozi. Yumshoq, tinchlantiruvchi nutq."),
    },
}


_VOICE_CATEGORY_LABELS: dict[str, dict[str, str]] = {
    "narrator": {
        "en": "Narrators",
        "ru": "Дикторы",
        "zh": "旁白声音",
        "kk": "Дикторлар",
        "uz": "Hikoyachilar",
    },
    "male": {
        "en": "Male voices",
        "ru": "Мужские голоса",
        "zh": "男声",
        "kk": "Ер дауыстар",
        "uz": "Erkak ovozlari",
    },
    "female": {
        "en": "Female voices",
        "ru": "Женские голоса",
        "zh": "女声",
        "kk": "Әйел дауыстар",
        "uz": "Ayol ovozlari",
    },
    "custom": {
        "en": "Custom voices",
        "ru": "\u041a\u0430\u0441\u0442\u043e\u043c\u043d\u044b\u0435 \u0433\u043e\u043b\u043e\u0441\u0430",
        "zh": "Custom voices",
        "kk": "Custom voices",
        "uz": "Custom voices",
    },
}


def voice_category_label(category: str) -> str:
    """Return a localized voice category label."""
    labels = _VOICE_CATEGORY_LABELS.get(category, {})
    return labels.get(_LANG, labels.get("en", category))


def voice_preset_label(preset: object) -> str:
    """Return a localized voice preset label."""
    if _LANG == "ru":
        return str(getattr(preset, "label_ru"))
    if _LANG == "en":
        return str(getattr(preset, "label_en"))
    preset_id = str(getattr(preset, "id"))
    return _VOICE_PRESET_LOCALES.get(preset_id, {}).get(
        _LANG,
        (str(getattr(preset, "label_en")), ""),
    )[0]


def voice_preset_description(preset: object) -> str:
    """Return a localized voice preset description."""
    if _LANG == "ru":
        return str(getattr(preset, "description_ru"))
    if _LANG == "en":
        return str(getattr(preset, "description_en"))
    preset_id = str(getattr(preset, "id"))
    return _VOICE_PRESET_LOCALES.get(preset_id, {}).get(
        _LANG,
        ("", str(getattr(preset, "description_en"))),
    )[1]


def t(key: str, **kwargs: Any) -> str:
    """Translate key to current language, with optional format kwargs."""
    entry = TRANSLATIONS.get(key) or _FALLBACK_TRANSLATIONS.get(key)
    if not entry:
        return key
    text = entry.get(_LANG, entry.get("en", key))
    if kwargs:
        text = text.format(**kwargs)
    return text


def _install_extra_translations() -> None:
    """Install optional locale catalogs and fail fast if they drift."""
    from book_normalizer.gui.i18n_extra import EXTRA_TRANSLATIONS

    base_keys = set(TRANSLATIONS)
    for lang, catalog in EXTRA_TRANSLATIONS.items():
        extra = set(catalog) - base_keys
        if extra:
            raise RuntimeError(
                f"Locale '{lang}' is out of sync: extra={sorted(extra)}"
            )
        updates = {key: {lang: text} for key, text in catalog.items()}
        TRANSLATION_RUNTIME_REPORTS.append(
            enrich_translation_catalog(
                TRANSLATIONS,
                updates,
                source=f"i18n_extra.{lang}",
                allow_overrides={(key, lang) for key in updates},
            )
        )

    polished = {
        "app.title": {
            "zh": "书籍转音频",
            "kk": "Кітаптарды аудиоға",
            "uz": "Kitoblarni audioga",
        },
        "app.subtitle": {"en": "", "ru": "", "zh": "", "kk": "", "uz": ""},
        "app.lang_label": {"zh": "语言：", "kk": "Тіл:", "uz": "Til:"},
        "tab.voices": {"zh": "4. 合成", "kk": "4. Синтез", "uz": "4. Sintez"},
        "tab.voices_short": {"zh": "4. TTS", "kk": "4. TTS", "uz": "4. TTS"},
        "tab.synthesize": {"zh": "4. 合成", "kk": "4. Синтез", "uz": "4. Sintez"},
        "tab.synthesize_short": {"zh": "4. TTS", "kk": "4. TTS", "uz": "4. TTS"},
        "tab.assemble": {"zh": "5. 章节", "kk": "5. Тараулар", "uz": "5. Boblar"},
        "tab.assemble_short": {"zh": "5. 章节", "kk": "5. Тарау", "uz": "5. Bob"},
        "synth.mode_custom_voice": {
            "ru": "Свой голос",
            "zh": "自定义声音",
            "kk": "Өз дауысы",
            "uz": "O'z ovozi",
        },
        "synth.mode_preset_speakers": {
            "ru": "Из шага 3",
            "zh": "来自第 3 步",
            "kk": "3-қадамнан",
            "uz": "3-bosqichdan",
        },
        "synth.mode_advanced": {
            "ru": "Дополнительно",
            "zh": "高级",
            "kk": "Қосымша",
            "uz": "Qo'shimcha",
        },
        "voice.generate_previews": {
            "zh": "生成预览",
            "kk": "Алдын ала тыңдауды жасау",
            "uz": "Oldindan tinglashlarni yaratish",
        },
        "voice.generating_previews": {
            "zh": "正在本机生成预览（可能需要几分钟）…",
            "kk": "Алдын ала тыңдаулар жергілікті жасалуда (бірнеше минут алуы мүмкін)…",
            "uz": "Oldindan tinglashlar lokal yaratilmoqda (bir necha daqiqa olishi mumkin)…",
        },
        "norm.raw_placeholder": {
            "zh": "原始文本",
            "kk": "Файлдағы түпнұсқа мәтін",
            "uz": "Fayldagi asl matn",
        },
        "norm.norm_placeholder": {
            "zh": "规范化后",
            "kk": "Нормалдаудан кейін",
            "uz": "Normallashtirishdan keyin",
        },
        "norm.ocr_psm_hint": {
            "zh": "选择最接近页面渲染结果的版式。",
            "kk": "Рендерленген бетке ең жақын орналасуды таңдаңыз.",
            "uz": "Render qilingan sahifaga eng yaqin tuzilmani tanlang.",
        },
        "norm.ocr_psm": {
            "zh": "OCR 页面版式 (PSM)：",
            "kk": "OCR бет құрылымы (PSM):",
            "uz": "OCR sahifa tuzilmasi (PSM):",
        },
        "norm.ocr_psm_3": {
            "zh": "3 - 自动整页：书页版式不确定",
            "kk": "3 - Авто толық бет: кітап орналасуы белгісіз",
            "uz": "3 - Avto to'liq sahifa: kitob tuzilmasi noma'lum",
        },
        "norm.ocr_psm_4": {
            "zh": "4 - 普通书页：稳定阅读顺序",
            "kk": "4 - Кітаптың қалыпты беті: тұрақты оқу реті",
            "uz": "4 - Oddiy kitob sahifasi: barqaror o'qish tartibi",
        },
        "norm.ocr_psm_6": {
            "zh": "6 - 裁剪正文：一个选中的文本块",
            "kk": "6 - Қиылған негізгі мәтін: бір таңдалған блок",
            "uz": "6 - Kesilgan asosiy matn: bitta tanlangan blok",
        },
        "norm.ocr_psm_11": {
            "zh": "11 - 零散片段：题注/印章/边注",
            "kk": "11 - Шашыраған фрагменттер: жазу, мөр, шеткі белгі",
            "uz": "11 - Tarqoq bo'laklar: izoh, muhr, chet yozuv",
        },
        "norm.ocr_psm_13": {
            "zh": "13 - 标题或单行：不是整页",
            "kk": "13 - Тақырып не бір жол: толық бет емес",
            "uz": "13 - Sarlavha yoki bir qator: to'liq sahifa emas",
        },
        "norm.ocr_psm_tip": {
            "zh": (
                "Tesseract 页面分割模式 (PSM)：\n"
                "3 自动整页 = 书页结构不确定、混排、多个正文块或含插图时使用。\n"
                "4 普通书页 = 完整扫描书页，正文能按稳定顺序从上到下阅读；多数书先试它。\n"
                "6 裁剪正文 = 图片已经是一个选中的矩形正文块，没有页眉、页脚或边注。\n"
                "11 零散片段 = 题注、印章、边注、表单或分散文字；阅读顺序可能需要复查。\n"
                "13 标题或单行 = 只有一条短横向标题/页眉/文字；不要用于整页。"
            ),
            "kk": (
                "Tesseract бет сегментациясы (PSM):\n"
                "3 авто толық бет = кітап бетінің құрылымы белгісіз, аралас, бірнеше мәтін блогы немесе сурет бар.\n"
                "4 кітаптың қалыпты беті = толық скан, негізгі мәтін жоғарыдан төмен тұрақты ретпен оқылады; көбіне алдымен осыны таңдаңыз.\n"
                "6 қиылған негізгі мәтін = сурет бір таңдалған тікбұрышты мәтін блогына дейін қиылған, өріс/колонтитул жоқ.\n"
                "11 шашыраған фрагменттер = жазулар, мөрлер, шеткі белгілер, формалар немесе бөлек мәтіндер; оқу ретін тексеріңіз.\n"
                "13 тақырып не бір жол = бір қысқа көлденең тақырып/жол ғана; толық бетке қолданбаңыз."
            ),
            "uz": (
                "Tesseract sahifa segmentatsiyasi (PSM):\n"
                "3 avto to'liq sahifa = kitob sahifasi tuzilmasi noma'lum, aralash, bir nechta matn bloki yoki rasm bor.\n"
                "4 oddiy kitob sahifasi = to'liq skan, asosiy matn yuqoridan pastga barqaror tartibda o'qiladi; ko'p kitoblarda avval shuni sinang.\n"
                "6 kesilgan asosiy matn = rasm bitta tanlangan to'rtburchak matn blokigacha kesilgan, chet yozuv yoki kolontitul yo'q.\n"
                "11 tarqoq bo'laklar = izohlar, muhrlar, chet yozuvlar, blanklar yoki tarqoq matn; o'qish tartibini tekshiring.\n"
                "13 sarlavha yoki bir qator = faqat qisqa gorizontal sarlavha/qator; to'liq sahifa uchun ishlatmang."
            ),
        },
        "norm.ocr_unavailable_native": {
            "zh": "Tesseract 未安装；正在使用 PDF 内置文本提取。请运行：{hint}",
            "kk": "Tesseract орнатылмаған; PDF ішіндегі мәтінді шығарып көремін. Іске қосыңыз: {hint}",
            "uz": "Tesseract o'rnatilmagan; PDF ichidagi matn olinmoqda. Ishga tushiring: {hint}",
        },
        "norm.err_tesseract_missing_force": {
            "zh": "Tesseract 未安装。请运行：{hint}。或把 OCR 模式切换为 auto/off。",
            "kk": "Tesseract орнатылмаған. Іске қосыңыз: {hint}. Немесе OCR режимін auto/off етіңіз.",
            "uz": "Tesseract o'rnatilmagan. Ishga tushiring: {hint}. Yoki OCR rejimini auto/off qiling.",
        },
        "norm.err_tesseract_missing_scanned": {
            "zh": "PDF 文本层缺失或不可读，并且未安装 Tesseract。请运行：{hint}。然后重新运行规范化。",
            "kk": "PDF мәтін қабаты жоқ немесе оқылмайды, ал Tesseract орнатылмаған. Іске қосыңыз: {hint}. Содан кейін нормалдауды қайта іске қосыңыз.",
            "uz": "PDF matn qatlami yo'q yoki o'qilmaydi, Tesseract esa o'rnatilmagan. Ishga tushiring: {hint}. Keyin normallashtirishni qayta boshlang.",
        },
        "norm.llm_review_required": {
            "zh": "LLM 保留了 {rejected} 个段落未修改。Review report：{path}",
            "kk": "LLM {rejected} абзацты өзгертпей қалдырды. Review report: {path}",
            "uz": "LLM {rejected} paragrafni o'zgartirmay qoldirdi. Review report: {path}",
        },
        "synth.sage_help": {
            "zh": "SageAttention 是本机 TTS Python 环境中的可选加速内核。仅在已安装并在 GPU 上测试后启用。",
            "kk": "SageAttention — жергілікті TTS Python ортасына арналған қосымша жылдам attention ядросы. Тек орнатылып, GPU-да тексерілген болса қосыңыз.",
            "uz": "SageAttention lokal TTS Python muhiti uchun ixtiyoriy tezroq attention yadrosi. Faqat GPU qurilmangizda o‘rnatilgan va sinovdan o‘tgan bo‘lsa yoqing.",
        },
        "synth.sage_hint": {
            "zh": "SageAttention 用量化 attention 内核替换 SDPA。\n需要在本机 TTS Python 环境中安装 SageAttention；推荐 GitHub v2：\n  pip install git+https://github.com/thu-ml/SageAttention.git\n如果启用但不可用，合成会以明确错误停止。",
            "kk": "SageAttention SDPA-ны квантталған attention ядроларымен ауыстырады.\nЖергілікті TTS Python ортасында SageAttention қажет; GitHub v2 ұсынылады:\n  pip install git+https://github.com/thu-ml/SageAttention.git\nҚосылып, бірақ қолжетімсіз болса, синтез анық қатемен тоқтайды.",
            "uz": "SageAttention SDPA o‘rniga kvantlangan attention yadrolarini ishlatadi.\nLokal TTS Python muhitida SageAttention kerak; GitHub v2 tavsiya etiladi:\n  pip install git+https://github.com/thu-ml/SageAttention.git\nYoqilgan, lekin mavjud bo‘lmasa, sintez aniq xato bilan to‘xtaydi.",
        },
        "tab.normalize": {"zh": "1. 规范化", "kk": "1. Нормалдау"},
        "tab.normalize_short": {"zh": "1. 规范", "kk": "1. Норм."},
        "norm.book_language": {
            "zh": "书籍语言：",
            "kk": "Кітап тілі:",
            "uz": "Kitob tili:",
        },
        "norm.book_language_tip": {
            "zh": "控制 OCR 语言、语言安全的规范化、分块元数据以及 Qwen/ComfyUI 合成语言。",
            "kk": "OCR тілін, тілге қауіпсіз нормалдауды, чанк метадеректерін және Qwen/ComfyUI синтез тілін басқарады.",
            "uz": "OCR tili, tilga xavfsiz normallashtirish, chunk metadata va Qwen/ComfyUI sintez tilini boshqaradi.",
        },
        "book_language.ru": {"zh": "俄语", "kk": "Орысша", "uz": "Ruscha"},
        "book_language.en": {"zh": "英语", "kk": "Ағылшынша", "uz": "Inglizcha"},
        "book_language.zh": {"zh": "中文", "kk": "Қытайша", "uz": "Xitoycha"},
        "book_language.kk": {"zh": "哈萨克语", "kk": "Қазақша", "uz": "Qozoqcha"},
        "book_language.uz": {"zh": "乌兹别克语", "kk": "Өзбекше", "uz": "Oʻzbekcha"},
        "voice.col_chapter": {"zh": "章", "kk": "Тар.", "uz": "Bob"},
        "voice.col_chunk": {"zh": "分块", "kk": "Чанк", "uz": "Boʻlak"},
        "voice.col_audio": {"zh": "音频", "kk": "Дыбыс", "uz": "Ovoz"},
        "voice.col_retry": {"zh": "重试", "kk": "Қайталау", "uz": "Qayta"},
        "voice.load_manifest": {"zh": "加载", "kk": "Жүктеу", "uz": "Yuklash"},
        "voice.load_manifest_tip": {
            "zh": "加载已保存的分段清单。",
            "kk": "Сақталған сегмент манифесін жүктеу.",
            "uz": "Saqlangan segment manifestini yuklash.",
        },
        "voice.save_manifest": {"zh": "保存", "kk": "Сақтау", "uz": "Saqlash"},
        "voice.save_manifest_tip": {
            "zh": "保存当前分段和声音分配。",
            "kk": "Қазіргі сегменттер мен дауыс тағайындауларын сақтау.",
            "uz": "Joriy segmentlar va ovoz biriktirishlarini saqlash.",
        },
        "voice.play_audio": {
            "ru": "Слушать",
            "zh": "播放",
            "kk": "Тыңдау",
            "uz": "Eshitish",
        },
        "voice.editor_split": {"zh": "分割", "kk": "Бөлу", "uz": "Bo'lish"},
        "voice.editor_split_tip": {
            "zh": "在光标位置分割选中的分段。",
            "kk": "Таңдалған сегментті курсор тұрған жерден бөлу.",
            "uz": "Tanlangan segmentni kursor turgan joydan bo'lish.",
        },
        "synth.chunk_editor_split": {
            "zh": "\u5206\u5272",
            "kk": "\u0411\u04e9\u043b\u0443",
            "uz": "Bo'lish",
        },
        "synth.load_manifest": {
            "zh": "\u52a0\u8f7d",
            "kk": "\u0416\u04af\u043a\u0442\u0435\u0443",
            "uz": "Yuklash",
        },
        "synth.sample_enable": {
            "ru": "Использовать образец голоса для этой книги",
            "zh": "为本书使用声音样本",
            "kk": "Осы кітап үшін дауыс үлгісін қолдану",
            "uz": "Bu kitob uchun ovoz namunasidan foydalanish",
        },
        "synth.sample_title": {
            "ru": "Образец голоса",
            "zh": "声音样本",
            "kk": "Дауыс үлгісі",
            "uz": "Ovoz namunasi",
        },
        "synth.strategy_sample_all": {
            "ru": "Новый образец на всю книгу",
            "zh": "整本书使用新样本",
            "kk": "Бүкіл кітапқа жаңа үлгі",
            "uz": "Butun kitob uchun yangi namuna",
        },
        "synth.sample_audio": {
            "ru": "Аудио образца:",
            "zh": "样本音频：",
            "kk": "Үлгі аудио:",
            "uz": "Namuna audiosi:",
        },
        "synth.sample_play": {
            "ru": "Слушать",
            "zh": "播放",
            "kk": "Тыңдау",
            "uz": "Eshitish",
        },
        "synth.sample_pause": {
            "ru": "Пауза",
            "zh": "暂停",
            "kk": "Пауза",
            "uz": "Pauza",
        },
        "synth.sample_transcript": {
            "ru": "Текст образца:",
            "zh": "样本文本：",
            "kk": "Үлгі мәтіні:",
            "uz": "Namuna matni:",
        },
        "synth.sample_ready": {
            "ru": "Аудио образца загружено. Перед синтезом введите точный текст.",
            "zh": "样本音频已加载。合成前请输入准确文本。",
            "kk": "Үлгі аудио жүктелді. Синтез алдында нақты мәтінді енгізіңіз.",
            "uz": "Namuna audiosi yuklandi. Sintezdan oldin aniq matnni kiriting.",
        },
        "synth.sample_missing": {
            "ru": "Выберите аудио образца и введите точный текст.",
            "zh": "请选择样本音频并输入准确文本。",
            "kk": "Үлгі аудионы таңдап, нақты мәтінді енгізіңіз.",
            "uz": "Namuna audiosini tanlang va aniq matnni kiriting.",
        },
        "synth.sample_preview_help": {
            "ru": "Прослушайте выбранный образец, чтобы проверить голос и текст.",
            "zh": "播放所选样本，检查声音和文本是否正确。",
            "kk": "Дауыс пен мәтін дұрыс екенін тексеру үшін үлгіні тыңдаңыз.",
            "uz": "Ovoz va matn to'g'riligini tekshirish uchun tanlangan namunani tinglang.",
        },
        "synth.sample_transcript_help": {
            "ru": "Точный текст, произнесенный в аудио образца. Чем точнее совпадение, тем лучше голосовой промпт.",
            "zh": "样本音频中实际说出的准确文本。越接近，声音提示越好。",
            "kk": "Үлгі аудиода айтылған нақты мәтін. Сәйкестік неғұрлым дәл болса, дауыс промпты соғұрлым жақсы.",
            "uz": "Namuna audiosida aytilgan aniq matn. Qanchalik mos bo'lsa, ovoz prompti shunchalik yaxshi bo'ladi.",
        },
        "voice.speaker_mode": {
            "zh": "分段来源：",
            "kk": "Сегмент көзі:",
            "uz": "Segment manbasi:",
        },
        "voice.speaker_mode_heuristic": {
            "zh": "规则：快速分段",
            "kk": "Ереже: жылдам бөлу",
            "uz": "Qoidalar: tez bo'lish",
        },
        "voice.speaker_mode_llm": {
            "zh": "LLM：角色与场景",
            "kk": "LLM: рөлдер мен көріністер",
            "uz": "LLM: rollar va sahnalar",
        },
        "voice.speaker_mode_manual": {
            "zh": "手动清单",
            "kk": "Қолмен манифест",
            "uz": "Qo'lda manifest",
        },
        "voice.speaker_mode_hint": {
            "zh": (
                "规则：快速分段 - 根据标点和引号在本机生成草稿。无需网络。\n"
                "LLM：角色与场景 - 本地模型保留文本、划分场景并标注角色。\n"
                "手动清单 - 加载或创建分段，然后在表格中编辑文本、角色和声音。"
            ),
            "kk": (
                "Ереже: жылдам бөлу - тыныс белгілері мен тырнақша бойынша жергілікті жоба жасайды. Желі қажет емес.\n"
                "LLM: рөлдер мен көріністер - жергілікті модель мәтінді сақтап, көріністерге бөліп, рөлдерді белгілейді.\n"
                "Қолмен манифест - сегменттерді жүктеп не жасаңыз, кейін мәтінді, рөлдерді және дауыстарды кестеде түзетіңіз."
            ),
            "uz": (
                "Qoidalar: tez bo'lish - tinish belgilari va qo'shtirnoqlar asosida lokal qoralama yaratadi. Tarmoq kerak emas.\n"
                "LLM: rollar va sahnalar - lokal model matnni saqlab, sahnalarga bo'ladi va rollarni belgilaydi.\n"
                "Qo'lda manifest - segmentlarni yuklang yoki yarating, keyin jadvalda matn, rollar va ovozlarni tahrirlang."
            ),
        },
        "voice.detect": {
            "zh": "重新生成分段",
            "kk": "Сегменттерді қайта құру",
            "uz": "Segmentlarni qayta qurish",
        },
        "voice.detecting": {
            "zh": "正在生成智能分段…",
            "kk": "Ақылды сегменттер жиналуда…",
            "uz": "Aqlli segmentlar yig'ilmoqda…",
        },
        "voice.detecting_dialogue": {
            "zh": "正在读取对话边界…",
            "kk": "Диалог шекаралары оқылуда…",
            "uz": "Dialog chegaralari o'qilmoqda…",
        },
        "voice.attributing": {
            "zh": "正在标注角色 ({mode})…",
            "kk": "Рөлдер белгіленуде ({mode})…",
            "uz": "Rollar belgilanmoqda ({mode})…",
        },
        "voice.segments_ready": {
            "zh": "✔ {n} 个分段已就绪。请检查角色和文本，然后点击“构建 TTS 分块”。",
            "kk": "✔ {n} сегмент дайын. Рөлдер мен мәтінді тексеріп, «TTS чанктарын құру» түймесін басыңыз.",
            "uz": "✔ {n} segment tayyor. Rollar va matnni tekshirib, “TTS bo‘laklarini qurish” tugmasini bosing.",
        },
        "voice.mark_retry": {"zh": "重试", "kk": "Қайталау", "uz": "Qayta"},
        "voice.type_narrator": {"zh": "旁白", "kk": "Автор", "uz": "Hikoya"},
        "voice.chunks_done": {
            "en": "✔ Built {n} TTS chunks! Go to Synthesis to render audio.",
            "ru": "✔ Собрано {n} TTS-чанков! Перейдите на «Синтез», чтобы собрать аудио.",
            "zh": "✔ 已生成 {n} 个 TTS 分块。下一步进入“合成”生成音频。",
            "kk": "✔ {n} TTS чанкі дайын. Аудио жасау үшін «Синтезге» өтіңіз.",
            "uz": "✔ {n} TTS bo‘lagi tayyor. Audio yaratish uchun “Sintez”ga o‘ting.",
        },
        "voice.manifest_path": {
            "zh": "清单：{path}",
            "kk": "Манифест: {path}",
            "uz": "Manifest: {path}",
        },
        "voice.llm_model": {
            "zh": "LLM 模型：",
            "kk": "LLM моделі:",
            "uz": "LLM modeli:",
        },
        "voice.stats_segments": {
            "zh": "{total} 段 | 对话: {speech} | 旁白: {narr}",
            "kk": "{total} сегмент | Сөз: {speech} | Автор: {narr}",
            "uz": "{total} segment | Nutq: {speech} | Hikoya: {narr}",
        },
        "status.norm_done": {
            "en": "Normalization complete. {n} chapters. Extract roles next.",
            "ru": "Нормализация завершена. {n} глав. Дальше извлеките роли.",
            "zh": "规范化完成：{n} 章。下一步提取角色。",
            "kk": "Нормалдау аяқталды: {n} тарау. Енді рөлдерді алыңыз.",
            "uz": "Normallashtirish tugadi: {n} bob. Keyin rollarni ajrating.",
        },
        "status.roles_done": {
            "en": "Roles and smart segments are ready. Review chunks next.",
            "ru": "Роли и умные сегменты готовы. Дальше проверьте чанки.",
            "zh": "角色和智能片段已就绪。下一步检查分块。",
            "kk": "Рөлдер мен ақылды сегменттер дайын. Енді чанктарды тексеріңіз.",
            "uz": "Rollar va aqlli segmentlar tayyor. Keyin bo‘laklarni tekshiring.",
        },
        "status.voices_done": {
            "en": "Chunks are ready. Go to Synthesis.",
            "ru": "Чанки готовы. Перейдите на «Синтез».",
            "zh": "分块已就绪。进入“合成”。",
            "kk": "Чанктар дайын. «Синтезге» өтіңіз.",
            "uz": "Bo‘laklar tayyor. “Sintez”ga o‘ting.",
        },
        "synth.chunks_word": {"zh": "分块"},
    }
    TRANSLATION_RUNTIME_REPORTS.append(
        enrich_translation_catalog(
            TRANSLATIONS,
            polished,
            source="i18n.polished",
            allow_overrides={
                (key, locale)
                for key, values in polished.items()
                for locale in values
            },
        )
    )

    compact_runtime_updates = {
            "voice.select_all": {
                "en": "☑ All",
                "ru": "☑ Все",
                "zh": "☑ 全选",
                "kk": "☑ Барлығы",
                "uz": "☑ Hammasi",
            },
            "voice.select_none": {
                "en": "☐ None",
                "ru": "☐ Ничего",
                "zh": "☐ 全不选",
                "kk": "☐ Ешқайсысы",
                "uz": "☐ Hech biri",
            },
            "voice.compact_narrator": {
                "en": "Narr.",
                "ru": "Диктор",
                "zh": "旁白",
                "kk": "Диктор",
                "uz": "Hikoya",
            },
            "voice.compact_male": {
                "en": "Male",
                "ru": "Муж.",
                "zh": "男声",
                "kk": "Ер",
                "uz": "Erkak",
            },
            "voice.compact_female": {
                "en": "Female",
                "ru": "Жен.",
                "zh": "女声",
                "kk": "Әйел",
                "uz": "Ayol",
            },
            "voice.compact_auto": {
                "en": "Auto",
                "ru": "Авто",
                "zh": "自动",
                "kk": "Авто",
                "uz": "Avto",
            },
            "voice.compact_all": {
                "en": "All",
                "ru": "Все",
                "zh": "全部",
                "kk": "Бәрі",
                "uz": "Barchasi",
            },
            "voice.compact_dialogue": {
                "en": "Speech",
                "ru": "Речь",
                "zh": "对白",
                "kk": "Сөз",
                "uz": "Nutq",
            },
            "voice.compact_author": {
                "en": "Narr.",
                "ru": "Автор",
                "zh": "旁白",
                "kk": "Автор",
                "uz": "Muallif",
            },
            "voice.compact_detect": {
                "en": "Detect",
                "ru": "\u0421\u0435\u0433\u043c.",
                "zh": "检测",
                "kk": "Белгілеу",
                "uz": "Aniqlash",
            },
            "voice.compact_load_manifest": {
                "en": "Load",
                "ru": "\u041e\u0442\u043a\u0440.",
                "zh": "加载",
                "kk": "Жүктеу",
                "uz": "Yuklash",
            },
            "voice.compact_save_manifest": {
                "en": "Save",
                "ru": "\u0421\u043e\u0445\u0440.",
                "zh": "保存",
                "kk": "Сақтау",
                "uz": "Saqlash",
            },
            "voice.compact_build_chunks": {
                "en": "TTS",
                "ru": "TTS",
                "zh": "构建",
                "kk": "Жинау",
                "uz": "Yig'ish",
            },
            "voice.compact_split": {
                "en": "Split",
                "ru": "\u0420\u0435\u0437.",
                "zh": "分割",
                "kk": "Бөлу",
                "uz": "Bo'lish",
            },
            "voice.compact_merge": {
                "en": "Merge",
                "ru": "\u0421\u043a\u043b.",
                "zh": "合并",
                "kk": "Біріктіру",
                "uz": "Birlashtirish",
            },
            "voice.compact_empty": {
                "en": "Empty",
                "ru": "\u041f\u0443\u0441\u0442.",
                "zh": "空白",
                "kk": "Бос",
                "uz": "Bo'sh",
            },
            "voice.compact_delete": {
                "en": "Delete",
                "ru": "\u0423\u0434\u0430\u043b",
                "zh": "删除",
                "kk": "Өшіру",
                "uz": "O'chirish",
            },
            "voice.compact_restore": {
                "en": "Restore",
                "ru": "Назад",
                "zh": "恢复",
                "kk": "Қайтару",
                "uz": "Tiklash",
            },
            "synth.compact_test_start": {
                "en": "Test",
                "ru": "Тест",
                "zh": "测试",
                "kk": "Тест",
                "uz": "Sinov",
            },
            "synth.compact_test_play": {
                "en": "Play",
                "ru": "Слушать",
                "zh": "播放",
                "kk": "Тыңдау",
                "uz": "Eshitish",
            },
            "synth.compact_start": {
                "en": "Start",
                "ru": "Пуск",
                "zh": "开始",
                "kk": "Бастау",
                "uz": "Boshlash",
            },
            "voice.speaker_label": {
                "en": "speaker: {speaker}",
                "ru": "спикер: {speaker}",
                "zh": "说话人：{speaker}",
                "kk": "спикер: {speaker}",
                "uz": "spiker: {speaker}",
            },
            "voice.none_selected": {
                "en": "Nothing selected! Check the voices to generate.",
                "ru": "Ничего не выбрано! Отметьте голоса галочками.",
                "zh": "没有选择声音！请勾选要生成的声音。",
                "kk": "Ештеңе таңдалмаған! Жасалатын дауыстарды белгілеңіз.",
                "uz": "Hech narsa tanlanmagan! Yaratiladigan ovozlarni belgilang.",
            },
            "voice.generating": {
                "en": "Generating…",
                "ru": "Генерация…",
                "zh": "正在生成…",
                "kk": "Жасалуда…",
                "uz": "Yaratilmoqda…",
            },
            "voice.model_loaded_generating": {
                "en": "Model loaded. Generating...",
                "ru": "Модель загружена. Генерация...",
                "zh": "模型已加载。正在生成...",
                "kk": "Модель жүктелді. Жасалуда...",
                "uz": "Model yuklandi. Yaratilmoqda...",
            },
            "voice.process_exit_code": {
                "en": "Process exited with code {code}",
                "ru": "Процесс завершился с кодом {code}",
                "zh": "进程已退出，代码 {code}",
                "kk": "Процесс {code} кодымен аяқталды",
                "uz": "Jarayon {code} kodi bilan tugadi",
            },
            "voice.timeout_generation": {
                "en": "Timeout: generation took too long",
                "ru": "Таймаут: генерация заняла слишком много времени",
                "zh": "超时：生成耗时过长",
                "kk": "Таймаут: жасау тым ұзаққа созылды",
                "uz": "Vaqt tugadi: yaratish juda uzoq davom etdi",
            },
            "voice.script_not_found": {
                "en": "Script not found: {path}",
                "ru": "Скрипт не найден: {path}",
                "zh": "未找到脚本：{path}",
                "kk": "Скрипт табылмады: {path}",
                "uz": "Skript topilmadi: {path}",
            },
            "synth.select_reference_audio": {
                "en": "Select Reference Audio",
                "ru": "Выбрать аудио-образец",
                "zh": "选择参考音频",
                "kk": "Эталон аудионы таңдау",
                "uz": "Namuna audioni tanlash",
            },
            "synth.clone_remove_voice": {
                "en": "Remove voice",
                "ru": "Удалить голос",
                "zh": "移除声音",
                "kk": "Дауысты жою",
                "uz": "Ovozni olib tashlash",
            },
            "voice.error": {
                "en": "Error: {msg}",
                "ru": "Ошибка: {msg}",
                "zh": "错误：{msg}",
                "kk": "Қате: {msg}",
                "uz": "Xato: {msg}",
            },
            "voice.model_loading_attn_hint": {
                "en": "Model loading... (attn: {impl} — install flash-attn for 1.5–2x speedup)",
                "ru": "Модель загружается... (attn: {impl} — установите flash-attn для ускорения в 1.5–2 раза)",
                "zh": "模型正在加载...（attn：{impl} — 安装 flash-attn 可提速 1.5–2 倍）",
                "kk": "Модель жүктелуде... (attn: {impl} — 1.5–2 есе жылдамдату үшін flash-attn орнатыңыз)",
                "uz": "Model yuklanmoqda... (attn: {impl} — 1.5–2 marta tezlashtirish uchun flash-attn o'rnating)",
            },
            "time.seconds_short": {
                "en": "{sec}s",
                "ru": "{sec} сек",
                "zh": "{sec} 秒",
                "kk": "{sec} с",
                "uz": "{sec} s",
            },
        }
    TRANSLATION_RUNTIME_REPORTS.append(
        enrich_translation_catalog(
            TRANSLATIONS,
            compact_runtime_updates,
            source="i18n.compact_runtime_updates",
            allow_overrides={
                (key, locale)
                for key, values in compact_runtime_updates.items()
                for locale in values
            },
        )
    )

    asr_runtime_base_updates = {
            "synth.asr_title": {
                "en": "ASR quality gate",
                "ru": "ASR-проверка качества",
            },
            "synth.asr_enable": {
                "en": "After synthesis:",
                "ru": "После синтеза:",
            },
            "synth.asr_enable_check": {
                "en": "Run ASR QA before assembly",
                "ru": "Запустить ASR QA перед сборкой",
            },
            "synth.asr_model": {
                "en": "ASR model:",
                "ru": "ASR модель:",
            },
            "synth.asr_device": {
                "en": "ASR device:",
                "ru": "ASR устройство:",
            },
            "synth.asr_timeout": {
                "en": "ASR timeout:",
                "ru": "ASR таймаут:",
            },
            "synth.asr_filter": {
                "en": "Chunk filter:",
                "ru": "Фильтр чанков:",
            },
            "synth.asr_run_now": {
                "en": "Run ASR QA now",
                "ru": "Запустить ASR QA",
            },
            "synth.compact_asr_run_now": {
                "en": "ASR QA",
                "ru": "ASR QA",
            },
            "synth.asr_open_report": {
                "en": "Open report",
                "ru": "Открыть отчет",
            },
            "synth.asr_open_diff": {
                "en": "Open diff",
                "ru": "Открыть diff",
            },
            "synth.asr_select_issue": {
                "en": "Select issue",
                "ru": "Выбрать проблему",
            },
            "synth.asr_idle": {
                "en": "ASR QA is report-first: it annotates the manifest and keeps audio unchanged.",
                "ru": "ASR QA только пишет отчет и аннотации; аудио не меняется.",
            },
            "synth.asr_running": {
                "en": "Running ASR QA...",
                "ru": "ASR QA выполняется...",
            },
            "synth.asr_done": {
                "en": "ASR QA {status}: failed={failed}, warnings={warning}, errors={error}. Report: {path}",
                "ru": "ASR QA {status}: ошибок={failed}, предупреждений={warning}, сбоев={error}. Отчет: {path}",
            },
            "synth.asr_error": {
                "en": "ASR QA error: {msg}",
                "ru": "Ошибка ASR QA: {msg}",
            },
            "synth.asr_selected_issue": {
                "en": "Selected the first ASR warning/failed chunk for manual retry.",
                "ru": "Выбран первый чанк с предупреждением/ошибкой ASR для ручного повтора.",
            },
            "synth.asr_no_issues": {
                "en": "No ASR warning or failed chunks found.",
                "ru": "ASR чанков с предупреждениями или ошибками не найдено.",
            },
            "synth.asr_overview_help": {
                "en": (
                    "ASR means automatic speech recognition. Here it is used as a local quality gate: "
                    "the app listens to each synthesized chunk with faster-whisper, turns the audio back "
                    "into text, then compares that transcript with the expected chunk text. It checks "
                    "missing words, extra words, repeated text, WER, CER, language, low confidence, empty "
                    "transcripts, timeouts, and ASR errors. It does not judge acting, emotion, accent, "
                    "speaker artistry, or voice similarity, and it does not resynthesize automatically."
                ),
                "ru": (
                    "ASR - это автоматическое распознавание речи. Здесь это локальная проверка качества: "
                    "приложение прослушивает каждый синтезированный чанк через faster-whisper, превращает "
                    "аудио обратно в текст и сравнивает распознанный текст с ожидаемым текстом чанка. "
                    "Проверяются пропущенные слова, лишние слова, повторы, WER, CER, язык, низкая "
                    "уверенность, пустой transcript, timeout и ошибки ASR. Это не оценка актерской игры, "
                    "эмоций, акцента, художественности, похожести голоса и не автоматический пересинтез."
                ),
            },
            "synth.asr_enable_help": {
                "en": (
                    "When enabled, ASR QA runs after TTS synthesis and before chapter assembly. It writes "
                    "a full JSON report and compact manifest annotations. The generated audio stays in "
                    "place, so failed chunks are left for manual review or retry."
                ),
                "ru": (
                    "Если включено, ASR QA запускается после TTS-синтеза и до сборки глав. Она пишет "
                    "полный JSON-отчет и компактные аннотации в manifest. Готовое аудио не меняется: "
                    "проблемные чанки остаются для ручной проверки или повтора."
                ),
            },
            "synth.asr_model_help": {
                "en": (
                    "Choose the faster-whisper model. tiny/base are fastest and least accurate, useful for "
                    "quick smoke checks. small is the recommended default for normal QA. medium is slower "
                    "but usually catches more mistakes. large-v3 is the most accurate listed option and is "
                    "best for final QA, but it needs much more VRAM/RAM and time. For Chinese and other "
                    "languages without spaces, prefer CER-heavy judgment because WER/match ratio are less stable."
                ),
                "ru": (
                    "Выберите модель faster-whisper. tiny/base самые быстрые и менее точные, подходят для "
                    "быстрой проверки. small - рекомендуемый вариант по умолчанию. medium медленнее, но "
                    "обычно лучше ловит ошибки. large-v3 самая точная из списка и лучше для финальной QA, "
                    "но требует намного больше VRAM/RAM и времени. Для китайского и языков без пробелов "
                    "лучше сильнее смотреть на CER, потому что WER/match ratio менее стабильны."
                ),
            },
            "synth.asr_device_help": {
                "en": (
                    "auto lets faster-whisper choose the best available device and is safest for most users. "
                    "cpu works everywhere and avoids GPU setup problems, but is slower, especially with "
                    "medium or large-v3. cuda uses an NVIDIA GPU and is best for long books or large models "
                    "when CUDA drivers and enough VRAM are installed. If CUDA fails, switch back to auto or cpu."
                ),
                "ru": (
                    "auto позволяет faster-whisper выбрать лучшее доступное устройство и обычно безопаснее "
                    "для большинства пользователей. cpu работает почти везде и не требует настройки GPU, "
                    "но медленнее, особенно с medium или large-v3. cuda использует NVIDIA GPU и лучше для "
                    "длинных книг или больших моделей, если установлены CUDA-драйверы и хватает VRAM. "
                    "Если cuda падает, вернитесь на auto или cpu."
                ),
            },
            "synth.asr_timeout_help": {
                "en": (
                    "Maximum time for recognizing one chunk. Keep it around 180 seconds for normal chunks. "
                    "Increase it for very long chunks, CPU mode, or large-v3. If a chunk times out, the book "
                    "continues and that chunk is marked with a timeout issue in the report."
                ),
                "ru": (
                    "Максимальное время распознавания одного чанка. Для обычных чанков оставьте около "
                    "180 секунд. Увеличивайте для очень длинных чанков, CPU-режима или large-v3. Если "
                    "чанк превысит timeout, книга продолжит проверяться, а этот чанк получит issue timeout."
                ),
            },
            "synth.asr_filter_help": {
                "en": (
                    "Filters the chunk selector after an ASR report is written. failed/warning shows chunks "
                    "that need attention. failed means hard metric or language/empty transcript problems. "
                    "warning means suspicious but not necessarily broken, such as low confidence or partial "
                    "word mismatch. passed shows chunks with no ASR issues."
                ),
                "ru": (
                    "Фильтрует список чанков после записи ASR-отчета. failed/warning показывает то, что "
                    "нужно проверить. failed - серьезные проблемы по метрикам, языку или пустому transcript. "
                    "warning - подозрительно, но не обязательно сломано: например, низкая уверенность или "
                    "частичное несовпадение слов. passed показывает чанки без ASR-проблем."
                ),
            },
            "synth.asr_run_help": {
                "en": (
                    "Run ASR QA immediately for the loaded manifest. This first keeps the existing WAV checks, "
                    "then runs faster-whisper only for active chunks that have audio files."
                ),
                "ru": (
                    "Запускает ASR QA сразу для загруженного manifest. Сначала выполняются существующие "
                    "WAV-проверки, затем faster-whisper запускается только для активных чанков с аудио."
                ),
            },
            "synth.asr_report_help": {
                "en": (
                    "Opens the full JSON report: expected text, ASR transcript, normalized text, metrics, "
                    "missing and extra word spans, issue summary, backend, model, language, and timings."
                ),
                "ru": (
                    "Открывает полный JSON-отчет: ожидаемый текст, ASR transcript, нормализованный текст, "
                    "метрики, пропущенные и лишние spans слов, summary issues, backend, модель, язык и время."
                ),
            },
            "synth.asr_diff_help": {
                "en": (
                    "Opens a readable text diff for chunks with ASR warnings or failures. Use it to decide "
                    "whether to manually retry, edit text, or ignore a harmless ASR mismatch."
                ),
                "ru": (
                    "Открывает читаемый text diff для чанков с ASR warning/failure. По нему удобно решить, "
                    "нужен ли ручной повтор, правка текста или можно игнорировать безвредное несовпадение ASR."
                ),
            },
            "synth.asr_select_issue_help": {
                "en": (
                    "Jumps to the first failed, warning, or error chunk from the ASR annotations so you can "
                    "listen, inspect the text, and choose a manual retry."
                ),
                "ru": (
                    "Переходит к первому chunk с failed, warning или error из ASR-аннотаций, чтобы можно "
                    "было прослушать, проверить текст и выбрать ручной повтор."
                ),
            },
        }
    TRANSLATION_RUNTIME_REPORTS.append(
        enrich_translation_catalog(
            TRANSLATIONS,
            asr_runtime_base_updates,
            source="i18n.asr_runtime_base_updates",
            allow_overrides={
                (key, locale)
                for key, values in asr_runtime_base_updates.items()
                for locale in values
            },
        )
    )

    localized_runtime_updates = {
        "norm.ocr_mode_auto": {
            "en": "Auto",
            "ru": "Авто",
            "zh": "自动",
            "kk": "Авто",
            "uz": "Avto",
        },
        "norm.ocr_mode_off": {
            "en": "Off",
            "ru": "Выкл.",
            "zh": "关闭",
            "kk": "Өшіру",
            "uz": "O'chirilgan",
        },
        "norm.ocr_mode_force": {
            "en": "Force OCR",
            "ru": "Всегда OCR",
            "zh": "强制 OCR",
            "kk": "OCR мәжбүрлі",
            "uz": "OCR majburiy",
        },
        "norm.ocr_mode_compare": {
            "en": "Compare",
            "ru": "Сравнить",
            "zh": "对比",
            "kk": "Салыстыру",
            "uz": "Solishtirish",
        },
        "voice.prev_segment": {
            "zh": "上一个",
            "kk": "Алдыңғы",
            "uz": "Oldingi",
        },
        "voice.prev_segment_tip": {
            "zh": "选择上一个可见片段。",
            "kk": "Алдыңғы көрінетін сегментті таңдаңыз.",
            "uz": "Oldingi ko'rinadigan segmentni tanlang.",
        },
        "voice.next_segment": {
            "zh": "下一个",
            "kk": "Келесі",
            "uz": "Keyingi",
        },
        "voice.next_segment_tip": {
            "zh": "选择下一个可见片段。",
            "kk": "Келесі көрінетін сегментті таңдаңыз.",
            "uz": "Keyingi ko'rinadigan segmentni tanlang.",
        },
        "inton.neutral": {"zh": "中性", "kk": "Бейтарап", "uz": "Neytral"},
        "inton.calm": {"zh": "平静", "kk": "Тыныш", "uz": "Tinch"},
        "inton.excited": {"zh": "激动", "kk": "Толқыған", "uz": "Hayajonli"},
        "inton.joyful": {"zh": "欢快", "kk": "Қуанышты", "uz": "Quvonchli"},
        "inton.sad": {"zh": "悲伤", "kk": "Мұңды", "uz": "G'amgin"},
        "inton.angry": {"zh": "愤怒", "kk": "Ашулы", "uz": "Jahldor"},
        "inton.whisper": {"zh": "耳语", "kk": "Сыбыр", "uz": "Shivir"},
        "inton.tense": {
            "en": "Tense",
            "ru": "Напряженная",
            "zh": "紧张",
            "kk": "Шиеленісті",
            "uz": "Tarang",
        },
        "inton.cheerful": {
            "en": "Cheerful",
            "ru": "Веселая",
            "zh": "愉快",
            "kk": "Көңілді",
            "uz": "Quvnoq",
        },
        "inton.curious": {
            "en": "Curious",
            "ru": "Любопытная",
            "zh": "好奇",
            "kk": "Қызыққан",
            "uz": "Qiziquvchan",
        },
        "inton.question": {
            "en": "Question",
            "ru": "Вопрос",
            "zh": "疑问",
            "kk": "Сұрақ",
            "uz": "Savol",
        },
        "inton.surprised": {
            "en": "Surprised",
            "ru": "Удивленная",
            "zh": "惊讶",
            "kk": "Таңғалған",
            "uz": "Hayron",
        },
        "inton.statement": {
            "en": "Statement",
            "ru": "Утверждение",
            "zh": "陈述",
            "kk": "Баяндау",
            "uz": "Bayon",
        },
        "inton.confused": {
            "en": "Confused",
            "ru": "Растерянная",
            "zh": "困惑",
            "kk": "Абыржыған",
            "uz": "Chalkash",
        },
        "inton.fearful": {
            "en": "Fearful",
            "ru": "Испуганная",
            "zh": "害怕",
            "kk": "Қорыққан",
            "uz": "Qo'rqqan",
        },
        "inton.urgent": {
            "en": "Urgent",
            "ru": "Срочная",
            "zh": "急促",
            "kk": "Шұғыл",
            "uz": "Shoshilinch",
        },
        "inton.gentle": {
            "en": "Gentle",
            "ru": "Мягкая",
            "zh": "温柔",
            "kk": "Нәзік",
            "uz": "Muloyim",
        },
        "inton.warm": {
            "en": "Warm",
            "ru": "Теплая",
            "zh": "温暖",
            "kk": "Жылы",
            "uz": "Iliq",
        },
        "inton.anxious": {
            "en": "Anxious",
            "ru": "Тревожная",
            "zh": "焦虑",
            "kk": "Мазасыз",
            "uz": "Bezovta",
        },
        "inton.serious": {
            "en": "Serious",
            "ru": "Серьезная",
            "zh": "严肃",
            "kk": "Байсалды",
            "uz": "Jiddiy",
        },
        "inton.playful": {
            "en": "Playful",
            "ru": "Игривый",
            "zh": "俏皮",
            "kk": "Ойнақы",
            "uz": "O'ynoqi",
        },
        "roles.desc_direct_speech": {
            "en": "Direct-speech role detected in the book.",
            "ru": "Роль прямой речи найдена в книге.",
            "zh": "在书中检测到的直接对话角色。",
            "kk": "Кітаптан табылған тікелей сөз рөлі.",
            "uz": "Kitobda aniqlangan bevosita nutq roli.",
        },
        "roles.desc_direct_speech_inferred": {
            "en": "Direct-speech character inferred from local dialogue context.",
            "ru": "Персонаж прямой речи определен по локальному контексту диалога.",
            "zh": "根据本地对话上下文推断的角色。",
            "kk": "Жергілікті диалог контекстінен анықталған кейіпкер.",
            "uz": "Lokal dialog kontekstidan aniqlangan personaj.",
        },
        "roles.desc_narrator": {
            "en": "Narrator and authorial prose.",
            "ru": "Диктор и авторская проза.",
            "zh": "旁白和作者叙述。",
            "kk": "Диктор және авторлық баяндау.",
            "uz": "Hikoyachi va muallif matni.",
        },
        "roles.desc_system": {
            "en": "System narration block: {name}.",
            "ru": "Системный блок повествования: {name}.",
            "zh": "系统叙述块：{name}。",
            "kk": "Жүйелік баяндау блогы: {name}.",
            "uz": "Tizimli hikoya bloki: {name}.",
        },
        "synth.quality_title": {
            "en": "Quality dashboard",
            "ru": "Панель качества",
            "zh": "质量面板",
            "kk": "Сапа панелі",
            "uz": "Sifat paneli",
        },
        "synth.quality_no_manifest": {
            "en": "No manifest loaded.",
            "ru": "Манифест не загружен.",
            "zh": "尚未加载清单。",
            "kk": "Манифест жүктелмеген.",
            "uz": "Manifest yuklanmagan.",
        },
        "synth.quality_col_chapter": {"en": "Chapter", "ru": "Глава", "zh": "章节", "kk": "Тарау", "uz": "Bob"},
        "synth.quality_col_status": {"en": "Status", "ru": "Статус", "zh": "状态", "kk": "Күй", "uz": "Holat"},
        "synth.quality_col_passed": {"en": "Passed", "ru": "ОК", "zh": "通过", "kk": "Өтті", "uz": "O'tdi"},
        "synth.quality_col_warning": {"en": "Warn", "ru": "Пред.", "zh": "警告", "kk": "Ескерту", "uz": "Ogoh"},
        "synth.quality_col_failed": {"en": "Failed", "ru": "Ошибка", "zh": "失败", "kk": "Қате", "uz": "Xato"},
        "synth.quality_col_unchecked": {"en": "Unchecked", "ru": "Не пров.", "zh": "未检查", "kk": "Тексерілмеген", "uz": "Tekshirilmagan"},
        "synth.quality_status_green": {"en": "green", "ru": "зеленый", "zh": "正常", "kk": "жасыл", "uz": "yashil"},
        "synth.quality_status_yellow": {"en": "yellow", "ru": "желтый", "zh": "注意", "kk": "сары", "uz": "sariq"},
        "synth.quality_status_red": {"en": "red", "ru": "красный", "zh": "错误", "kk": "қызыл", "uz": "qizil"},
        "synth.quality_summary": {
            "en": "Quality: {passed} passed, {warning} warning, {failed} failed, {unchecked} unchecked.",
            "ru": "Качество: пройдено {passed}, предупреждений {warning}, ошибок {failed}, не проверено {unchecked}.",
            "zh": "质量：通过 {passed}，警告 {warning}，失败 {failed}，未检查 {unchecked}。",
            "kk": "Сапа: өтті {passed}, ескерту {warning}, қате {failed}, тексерілмеген {unchecked}.",
            "uz": "Sifat: o'tdi {passed}, ogoh {warning}, xato {failed}, tekshirilmagan {unchecked}.",
        },
        "synth.quality_run_full": {"en": "Run full QA", "ru": "Полная QA", "zh": "运行完整 QA", "kk": "Толық QA", "uz": "To'liq QA"},
        "synth.quality_resynth": {"en": "Resynthesize failed/warning", "ru": "Пересинтез ошибок", "zh": "重合成失败/警告", "kk": "Қате/ескертуді қайта синтездеу", "uz": "Xato/ogohni qayta sintez"},
        "synth.quality_open_issue": {"en": "Open issue", "ru": "Открыть проблему", "zh": "打开问题", "kk": "Мәселені ашу", "uz": "Muammoni ochish"},
        "synth.quality_open_report": {"en": "Open report", "ru": "Открыть отчет", "zh": "打开报告", "kk": "Есепті ашу", "uz": "Hisobotni ochish"},
        "synth.quality_master": {"en": "Master passed chapters", "ru": "Мастеринг пройденных глав", "zh": "母版处理通过的章节", "kk": "Өткен тарауларды мастерингтеу", "uz": "O'tgan boblarni mastering"},
        "synth.quality_resynthesizing": {"en": "Resynthesizing failed/warning chunks...", "ru": "Пересинтезируем чанки с ошибками/предупреждениями...", "zh": "正在重合成失败/警告分块...", "kk": "Қате/ескерту чанктары қайта синтезделуде...", "uz": "Xato/ogoh bo'laklar qayta sintezlanmoqda..."},
        "synth.quality_master_done": {"en": "Mastered {n} file(s): {path}", "ru": "Мастеринг завершен: {n} файл(ов), {path}", "zh": "母版处理完成：{n} 个文件，{path}", "kk": "Мастеринг аяқталды: {n} файл, {path}", "uz": "Mastering tugadi: {n} fayl, {path}"},
        "synth.quality_master_report": {"en": "Mastering report: {path}", "ru": "Отчет мастеринга: {path}", "zh": "母版处理报告：{path}", "kk": "Мастеринг есебі: {path}", "uz": "Mastering hisoboti: {path}"},
        "synth.asr_title": {"zh": "ASR 质量门", "kk": "ASR сапа тексеруі", "uz": "ASR sifat tekshiruvi"},
        "synth.asr_enable": {"zh": "合成后：", "kk": "Синтезден кейін:", "uz": "Sintezdan keyin:"},
        "synth.asr_enable_check": {"zh": "组装前运行 ASR QA", "kk": "Жинау алдында ASR QA іске қосу", "uz": "Yig'ishdan oldin ASR QA ishga tushirish"},
        "synth.asr_model": {"zh": "ASR 模型：", "kk": "ASR моделі:", "uz": "ASR modeli:"},
        "synth.asr_device": {"zh": "ASR 设备：", "kk": "ASR құрылғысы:", "uz": "ASR qurilmasi:"},
        "synth.asr_device_auto": {"en": "Auto", "ru": "Авто", "zh": "自动", "kk": "Авто", "uz": "Avto"},
        "synth.asr_device_cpu": {"en": "CPU", "ru": "CPU", "zh": "CPU", "kk": "CPU", "uz": "CPU"},
        "synth.asr_device_cuda": {"en": "CUDA", "ru": "CUDA", "zh": "CUDA", "kk": "CUDA", "uz": "CUDA"},
        "synth.asr_timeout": {"zh": "ASR 超时：", "kk": "ASR таймауты:", "uz": "ASR vaqti:"},
        "synth.asr_filter": {"zh": "分块筛选：", "kk": "Чанк сүзгісі:", "uz": "Bo'lak filtri:"},
        "synth.asr_filter_all": {"en": "all", "ru": "все", "zh": "全部", "kk": "барлығы", "uz": "barchasi"},
        "synth.asr_filter_bad": {"en": "failed/warning", "ru": "ошибка/пред.", "zh": "失败/警告", "kk": "қате/ескерту", "uz": "xato/ogoh"},
        "synth.asr_filter_failed": {"en": "failed", "ru": "ошибка", "zh": "失败", "kk": "қате", "uz": "xato"},
        "synth.asr_filter_warning": {"en": "warning", "ru": "предупреждение", "zh": "警告", "kk": "ескерту", "uz": "ogoh"},
        "synth.asr_filter_passed": {"en": "passed", "ru": "пройдено", "zh": "通过", "kk": "өтті", "uz": "o'tdi"},
        "synth.asr_run_now": {"zh": "立即运行 ASR QA", "kk": "ASR QA қазір іске қосу", "uz": "ASR QA ni hozir ishga tushirish"},
        "synth.asr_open_report": {"zh": "打开报告", "kk": "Есепті ашу", "uz": "Hisobotni ochish"},
        "synth.asr_open_diff": {"zh": "打开差异", "kk": "Diff ашу", "uz": "Diff ochish"},
        "synth.asr_select_issue": {"zh": "选择问题", "kk": "Мәселені таңдау", "uz": "Muammoni tanlash"},
        "synth.asr_idle": {"zh": "ASR QA 只写入报告和标注；音频不会改变。", "kk": "ASR QA тек есеп пен белгі жазады; аудио өзгермейді.", "uz": "ASR QA faqat hisobot va belgi yozadi; audio o'zgarmaydi."},
        "synth.asr_running": {"zh": "正在运行 ASR QA...", "kk": "ASR QA орындалуда...", "uz": "ASR QA bajarilmoqda..."},
        "synth.asr_done": {
            "zh": "ASR QA {status}：失败={failed}，警告={warning}，错误={error}。报告：{path}",
            "kk": "ASR QA {status}: қате={failed}, ескерту={warning}, сбой={error}. Есеп: {path}",
            "uz": "ASR QA {status}: xato={failed}, ogoh={warning}, nosozlik={error}. Hisobot: {path}",
        },
        "synth.asr_error": {"zh": "ASR QA 错误：{msg}", "kk": "ASR QA қатесі: {msg}", "uz": "ASR QA xatosi: {msg}"},
        "synth.asr_selected_issue": {"zh": "已选择第一个带 ASR 警告/失败的分块以便手动重试。", "kk": "Қолмен қайталау үшін алғашқы ASR ескерту/қате чанкі таңдалды.", "uz": "Qo'lda qayta urinish uchun birinchi ASR ogoh/xato bo'lagi tanlandi."},
        "synth.asr_no_issues": {"zh": "未找到 ASR 警告或失败分块。", "kk": "ASR ескертуі немесе қатесі бар чанк табылмады.", "uz": "ASR ogoh yoki xato bo'laklari topilmadi."},
        "synth.asr_overview_help": {
            "zh": "ASR 是自动语音识别。这里它作为本地质量门：应用用 faster-whisper 听每个合成分块，把音频转回文本，再与预期文本比较。它检查漏词、多词、重复、WER、CER、语言、低置信度、空转写、超时和 ASR 错误。它不评估表演、情绪、口音、音色艺术性或声音相似度，也不会自动重合成。",
            "kk": "ASR - автоматты сөйлеуді тану. Мұнда ол жергілікті сапа тексеруі ретінде қолданылады: қолданба әр синтезделген чанкті faster-whisper арқылы тыңдап, аудионы мәтінге айналдырады да, күтілген мәтінмен салыстырады. Жоғалған сөздер, артық сөздер, қайталау, WER, CER, тіл, төмен сенімділік, бос транскрипт, таймаут және ASR қателері тексеріледі. Ол актерлік орындауды, эмоцияны, акцентті, дауыс ұқсастығын бағаламайды және автоматты қайта синтездемейді.",
            "uz": "ASR - avtomatik nutqni tanish. Bu yerda u lokal sifat tekshiruvi sifatida ishlaydi: ilova har bir sintez qilingan bo'lakni faster-whisper bilan tinglaydi, audioni matnga qaytaradi va kutilgan matn bilan solishtiradi. Tushib qolgan so'zlar, ortiqcha so'zlar, takrorlar, WER, CER, til, past ishonch, bo'sh transkript, timeout va ASR xatolarini tekshiradi. U ijro, emotsiya, aksent, ovoz o'xshashligini baholamaydi va avtomatik qayta sintez qilmaydi.",
        },
        "synth.asr_enable_help": {
            "zh": "启用后，ASR QA 会在 TTS 合成后、章节组装前运行。它写入完整 JSON 报告和紧凑清单标注。生成的音频保持不变，失败分块留给手动检查或重试。",
            "kk": "Қосылса, ASR QA TTS синтезінен кейін және тарауларды жинауға дейін іске қосылады. Ол толық JSON есебін және манифестке қысқа белгілерді жазады. Дайын аудио өзгермейді, қате чанктер қолмен тексеруге немесе қайталауға қалады.",
            "uz": "Yoqilsa, ASR QA TTS sintezidan keyin va boblarni yig'ishdan oldin ishlaydi. U to'liq JSON hisobot va manifestga qisqa belgilar yozadi. Yaratilgan audio o'zgarmaydi, xato bo'laklar qo'lda tekshirish yoki qayta urinish uchun qoladi.",
        },
        "synth.asr_model_help": {
            "zh": "选择 faster-whisper 模型。tiny/base 最快但精度较低，适合快速冒烟检查。small 是普通 QA 的推荐默认值。medium 更慢但通常能发现更多问题。large-v3 是列表中最准确的选项，适合最终 QA，但需要更多 VRAM/RAM 和时间。中文等无空格语言建议更多参考 CER，因为 WER/匹配率不够稳定。",
            "kk": "faster-whisper моделін таңдаңыз. tiny/base ең жылдам, бірақ дәлдігі төмен, жылдам тексеруге ыңғайлы. small - қалыпты QA үшін ұсынылатын әдепкі мән. medium баяулау, бірақ көбіне көбірек қате табады. large-v3 тізімдегі ең дәл нұсқа және финалдық QA үшін жақсы, бірақ көбірек VRAM/RAM және уақыт қажет. Қытай тілі сияқты бос орынсыз тілдерде CER-ге көбірек сүйеніңіз.",
            "uz": "faster-whisper modelini tanlang. tiny/base eng tez, lekin aniqligi past, tez smoke tekshiruvlar uchun qulay. small odatiy QA uchun tavsiya etilgan standart. medium sekinroq, lekin ko'proq xato topadi. large-v3 ro'yxatdagi eng aniq variant va final QA uchun yaxshi, ammo ko'proq VRAM/RAM va vaqt talab qiladi. Xitoycha kabi bo'shliqsiz tillarda CER ga ko'proq qarang.",
        },
        "synth.asr_device_help": {
            "zh": "auto 让 faster-whisper 选择最佳可用设备，通常最安全。cpu 到处可用并避免 GPU 配置问题，但速度较慢，尤其是 medium 或 large-v3。cuda 使用 NVIDIA GPU，适合长书或大模型，前提是已安装 CUDA 驱动且 VRAM 足够。如果 CUDA 失败，请切回 auto 或 cpu。",
            "kk": "auto faster-whisper-ге ең жақсы қолжетімді құрылғыны таңдауға мүмкіндік береді және көбіне қауіпсіз. cpu барлық жерде жұмыс істейді және GPU баптауын қажет етпейді, бірақ medium немесе large-v3 кезінде баяу. cuda NVIDIA GPU қолданады, ұзын кітаптар мен үлкен модельдерге жақсы, егер CUDA драйверлері және жеткілікті VRAM бар болса. CUDA істемесе, auto немесе cpu режиміне қайтыңыз.",
            "uz": "auto faster-whisper ga eng yaxshi mavjud qurilmani tanlashga imkon beradi va ko'pchilik uchun xavfsiz. cpu hamma joyda ishlaydi va GPU sozlash muammolarini chetlab o'tadi, lekin sekinroq, ayniqsa medium yoki large-v3 bilan. cuda NVIDIA GPU ishlatadi va uzun kitoblar yoki katta modellar uchun yaxshi, agar CUDA drayverlari va yetarli VRAM bo'lsa. CUDA ishlamasa, auto yoki cpu ga qayting.",
        },
        "synth.asr_timeout_help": {
            "zh": "识别一个分块的最长时间。普通分块保持在约 180 秒。超长分块、CPU 模式或 large-v3 可适当增加。如果分块超时，整本书会继续处理，该分块会在报告中标记为 timeout 问题。",
            "kk": "Бір чанкті тануға берілетін ең ұзақ уақыт. Қалыпты чанктер үшін шамамен 180 секунд қалдырыңыз. Өте ұзын чанктер, CPU режимі немесе large-v3 үшін көбейтіңіз. Чанк таймаутқа түссе, кітап тексерілуін жалғастырады, ал ол чанк есепте timeout мәселесі болып белгіленеді.",
            "uz": "Bitta bo'lakni tanish uchun maksimal vaqt. Oddiy bo'laklar uchun taxminan 180 soniya qoldiring. Juda uzun bo'laklar, CPU rejimi yoki large-v3 uchun oshiring. Bo'lak timeout bo'lsa, kitob davom etadi va hisobotda timeout muammosi sifatida belgilanadi.",
        },
        "synth.asr_filter_help": {
            "zh": "ASR 报告写入后筛选分块选择器。失败/警告会显示需要关注的分块。失败表示硬指标、语言或空转写问题。警告表示可疑但不一定损坏，例如低置信度或部分词不匹配。通过表示没有 ASR 问题的分块。",
            "kk": "ASR есебі жазылғаннан кейін чанк таңдағышын сүзеді. Қате/ескерту назар керек чанктерді көрсетеді. Қате - метрика, тіл немесе бос транскрипт мәселесі. Ескерту - күмәнді, бірақ міндетті түрде бұзылған емес, мысалы төмен сенімділік немесе сөздердің жартылай сәйкес келмеуі. Өтті - ASR мәселесі жоқ чанктер.",
            "uz": "ASR hisoboti yozilgandan keyin bo'lak tanlagichni filtrlaydi. xato/ogoh e'tibor kerak bo'laklarni ko'rsatadi. xato - metrika, til yoki bo'sh transkript muammosi. ogoh - shubhali, lekin shart emas buzilgan: masalan, past ishonch yoki qisman so'z mos kelmasligi. o'tdi - ASR muammosiz bo'laklar.",
        },
        "synth.asr_run_help": {
            "zh": "立即对已加载清单运行 ASR QA。它会先保留现有 WAV 检查，然后只对有音频文件的活动分块运行 faster-whisper。",
            "kk": "Жүктелген манифест үшін ASR QA-ны бірден іске қосады. Алдымен бар WAV тексерулерін сақтайды, содан кейін аудио файлы бар белсенді чанктерге ғана faster-whisper жүргізеді.",
            "uz": "Yuklangan manifest uchun ASR QA ni darhol ishga tushiradi. Avval mavjud WAV tekshiruvlarini saqlaydi, keyin audio fayli bor faol bo'laklar uchun faster-whisper ishlatadi.",
        },
        "synth.asr_report_help": {
            "zh": "打开完整 JSON 报告：预期文本、ASR 转写、规范化文本、指标、漏词和多词范围、问题摘要、后端、模型、语言和耗时。",
            "kk": "Толық JSON есебін ашады: күтілген мәтін, ASR транскрипті, нормаланған мәтін, метрикалар, жоғалған/артық сөз аралықтары, мәселе жиыны, backend, модель, тіл және уақыт.",
            "uz": "To'liq JSON hisobotni ochadi: kutilgan matn, ASR transkript, normallashgan matn, metrikalar, tushgan va ortiqcha so'z oraliqlari, muammo xulosasi, backend, model, til va vaqtlar.",
        },
        "synth.asr_diff_help": {
            "zh": "打开带 ASR 警告或失败分块的可读文本差异。可用来决定是否手动重试、编辑文本或忽略无害的 ASR 不匹配。",
            "kk": "ASR ескертуі немесе қатесі бар чанктер үшін оқылатын мәтін diff ашады. Қолмен қайталау, мәтінді түзету немесе зиянсыз ASR сәйкессіздігін елемеу керегін шешуге көмектеседі.",
            "uz": "ASR ogoh yoki xato bo'laklari uchun o'qiladigan matn diffini ochadi. Qo'lda qayta urinish, matnni tuzatish yoki zararsiz ASR nomosligini e'tiborsiz qoldirishni tanlashga yordam beradi.",
        },
        "synth.asr_select_issue_help": {
            "zh": "跳到 ASR 标注中的第一个失败、警告或错误分块，方便你试听、检查文本并选择手动重试。",
            "kk": "ASR белгілеріндегі алғашқы failed, warning немесе error чанкке өтеді, сонда тыңдап, мәтінді тексеріп, қолмен қайталауды таңдай аласыз.",
            "uz": "ASR belgilaridagi birinchi failed, warning yoki error bo'lakka o'tadi, shunda tinglash, matnni tekshirish va qo'lda qayta urinish mumkin.",
        },
    }
    TRANSLATION_RUNTIME_REPORTS.append(
        enrich_translation_catalog(
            TRANSLATIONS,
            localized_runtime_updates,
            source="i18n.localized_runtime_updates",
            allow_overrides={
                (key, locale)
                for key, values in localized_runtime_updates.items()
                for locale in values
            },
        )
    )

    for key, entry in TRANSLATIONS.items():
        if key.startswith("synth.asr_") or key == "synth.compact_asr_run_now":
            fallback_updates = {
                key: {
                    code: entry["en"]
                    for code in ("zh", "kk", "uz")
                    if code not in entry
                }
            }
            if fallback_updates[key]:
                TRANSLATION_RUNTIME_REPORTS.append(
                    enrich_translation_catalog(
                        TRANSLATIONS,
                        fallback_updates,
                        source="i18n.asr_fallbacks",
                    )
                )


_install_extra_translations()
