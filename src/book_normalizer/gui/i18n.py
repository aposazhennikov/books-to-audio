"""Internationalization (i18n) support for GUI."""

# ruff: noqa: E501

from __future__ import annotations

from typing import Any

_LANG: str = "ru"

SUPPORTED_LANGUAGES: tuple[tuple[str, str], ...] = (
    ("ru", "RU  Русский"),
    ("en", "EN  English"),
    ("zh", "ZH  中文"),
    ("kk", "KK  Қазақша"),
    ("uz", "UZ  Oʻzbekcha"),
)

TRANSLATIONS: dict[str, dict[str, str]] = {
    # ── App-level ──
    "app.title": {"en": "Books to Audio", "ru": "Книги в Аудио"},
    "app.subtitle": {
        "en": "Normalize \u2192 Voices \u2192 Synthesize \u2192 Assemble",
        "ru": "\u041d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f \u2192 \u0413\u043e\u043b\u043e\u0441\u0430 \u2192 \u0421\u0438\u043d\u0442\u0435\u0437 \u2192 \u0421\u0431\u043e\u0440\u043a\u0430",
    },
    "app.ready": {
        "en": "Ready. Load a book file to begin.",
        "ru": "\u0413\u043e\u0442\u043e\u0432\u043e. \u0417\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u0435 \u043a\u043d\u0438\u0433\u0443 \u0434\u043b\u044f \u043d\u0430\u0447\u0430\u043b\u0430.",
    },
    "app.lang_label": {"en": "Language:", "ru": "\u042f\u0437\u044b\u043a:"},
    "auto.button": {
        "en": "Build audiobook automatically",
        "ru": "\u0421\u043e\u0431\u0440\u0430\u0442\u044c \u0430\u0443\u0434\u0438\u043e\u043a\u043d\u0438\u0433\u0443 \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438",
        "zh": "\u81ea\u52a8\u751f\u6210\u6709\u58f0\u4e66",
        "kk": "\u0410\u0443\u0434\u0438\u043e\u043a\u0456\u0442\u0430\u043f\u0442\u044b \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0442\u044b \u0436\u0438\u043d\u0430\u0443",
        "uz": "Audiokitobni avtomatik yig'ish",
    },
    "auto.button_short": {
        "en": "Auto build",
        "ru": "\u0410\u0432\u0442\u043e\u0441\u0431\u043e\u0440\u043a\u0430",
        "zh": "\u81ea\u52a8\u751f\u6210",
        "kk": "\u0410\u0432\u0442\u043e\u0436\u0438\u043d\u0430\u0443",
        "uz": "Avtoyig'ish",
    },
    "auto.button_tiny": {
        "en": "Auto",
        "ru": "\u0410\u0432\u0442\u043e",
        "zh": "\u81ea\u52a8",
        "kk": "\u0410\u0432\u0442\u043e",
        "uz": "Avto",
    },
    "auto.tooltip": {
        "en": "Runs normalization, role extraction, chunking, TTS, and assembly with quality-first settings.",
        "ru": "\u0417\u0430\u043f\u0443\u0441\u043a\u0430\u0435\u0442 \u043d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044e, \u0438\u0437\u0432\u043b\u0435\u0447\u0435\u043d\u0438\u0435 \u0440\u043e\u043b\u0435\u0439, \u0447\u0430\u043d\u043a\u0438, \u043e\u0437\u0432\u0443\u0447\u043a\u0443 \u0438 \u0441\u043a\u043b\u0435\u0439\u043a\u0443 \u0441 \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430\u043c\u0438 \u043d\u0430 \u043a\u0430\u0447\u0435\u0441\u0442\u0432\u043e.",
        "zh": "\u4ee5\u8d28\u91cf\u4f18\u5148\u8bbe\u7f6e\u4f9d\u6b21\u8fd0\u884c\u89c4\u8303\u5316\u3001\u89d2\u8272\u63d0\u53d6\u3001\u5206\u5757\u3001TTS \u548c\u5408\u6210\u3002",
        "kk": "\u0421\u0430\u043f\u0430\u0493\u0430 \u0431\u0430\u0441\u044b\u043c\u0434\u044b\u049b \u0431\u0435\u0440\u0435\u0442\u0456\u043d \u0431\u0430\u043f\u0442\u0430\u0443\u043b\u0430\u0440\u043c\u0435\u043d \u043d\u043e\u0440\u043c\u0430\u043b\u0434\u0430\u0443, \u0440\u04e9\u043b\u0434\u0435\u0440, \u0447\u0430\u043d\u043a\u0442\u0430\u0440, TTS \u0436\u04d9\u043d\u0435 \u0436\u0438\u043d\u0430\u0443 \u049b\u0430\u0434\u0430\u043c\u0434\u0430\u0440\u044b\u043d \u0456\u0441\u043a\u0435 \u049b\u043e\u0441\u0430\u0434\u044b.",
        "uz": "Sifatga ustuvor sozlamalar bilan normalizatsiya, rollar, bo'laklar, TTS va yig'ishni ishga tushiradi.",
    },
    "auto.need_file": {
        "en": "Select a book first, then start automatic audiobook build.",
        "ru": "\u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u0432\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043a\u043d\u0438\u0433\u0443, \u0437\u0430\u0442\u0435\u043c \u0437\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u0435 \u0430\u0432\u0442\u043e\u0441\u0431\u043e\u0440\u043a\u0443.",
        "zh": "\u8bf7\u5148\u9009\u62e9\u4e66\u7a3f\uff0c\u7136\u540e\u542f\u52a8\u81ea\u52a8\u751f\u6210\u3002",
        "kk": "\u0410\u043b\u0434\u044b\u043c\u0435\u043d \u043a\u0456\u0442\u0430\u043f\u0442\u044b \u0442\u0430\u04a3\u0434\u0430\u04a3\u044b\u0437, \u0441\u043e\u0434\u0430\u043d \u043a\u0435\u0439\u0456\u043d \u0430\u0432\u0442\u043e\u0436\u0438\u043d\u0430\u0443\u0434\u044b \u0456\u0441\u043a\u0435 \u049b\u043e\u0441\u044b\u04a3\u044b\u0437.",
        "uz": "Avval kitobni tanlang, keyin avtomatik yig'ishni boshlang.",
    },
    "auto.normalizing": {
        "en": "Automatic build started: normalizing with quality-first settings.",
        "ru": "\u0410\u0432\u0442\u043e\u0441\u0431\u043e\u0440\u043a\u0430 \u0437\u0430\u043f\u0443\u0449\u0435\u043d\u0430: \u043d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0443\u0435\u043c \u0441 \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430\u043c\u0438 \u043d\u0430 \u043a\u0430\u0447\u0435\u0441\u0442\u0432\u043e.",
        "zh": "\u81ea\u52a8\u751f\u6210\u5df2\u542f\u52a8\uff1a\u6b63\u4ee5\u8d28\u91cf\u4f18\u5148\u8bbe\u7f6e\u89c4\u8303\u5316\u3002",
        "kk": "\u0410\u0432\u0442\u043e\u0436\u0438\u043d\u0430\u0443 \u0431\u0430\u0441\u0442\u0430\u043b\u0434\u044b: \u0441\u0430\u043f\u0430\u0493\u0430 \u0431\u0430\u0441\u044b\u043c\u0434\u044b\u049b \u0431\u0435\u0440\u0456\u043f \u043d\u043e\u0440\u043c\u0430\u043b\u0434\u0430\u0443.",
        "uz": "Avtoyig'ish boshlandi: sifatga ustuvor sozlamalar bilan normallashtirilmoqda.",
    },
    "auto.roles": {
        "en": "Automatic build: extracting roles and smart segments.",
        "ru": "\u0410\u0432\u0442\u043e\u0441\u0431\u043e\u0440\u043a\u0430: \u0438\u0437\u0432\u043b\u0435\u043a\u0430\u0435\u043c \u0440\u043e\u043b\u0438 \u0438 \u0443\u043c\u043d\u044b\u0435 \u0441\u0435\u0433\u043c\u0435\u043d\u0442\u044b.",
        "zh": "\u81ea\u52a8\u751f\u6210\uff1a\u6b63\u5728\u63d0\u53d6\u89d2\u8272\u548c\u667a\u80fd\u5206\u6bb5\u3002",
        "kk": "\u0410\u0432\u0442\u043e\u0436\u0438\u043d\u0430\u0443: \u0440\u04e9\u043b\u0434\u0435\u0440 \u043c\u0435\u043d \u0430\u049b\u044b\u043b\u0434\u044b \u0441\u0435\u0433\u043c\u0435\u043d\u0442\u0442\u0435\u0440 \u0430\u043b\u044b\u043d\u0443\u0434\u0430.",
        "uz": "Avtoyig'ish: rollar va aqlli segmentlar ajratilmoqda.",
    },
    "auto.chunks": {
        "en": "Automatic build: preparing TTS chunks.",
        "ru": "\u0410\u0432\u0442\u043e\u0441\u0431\u043e\u0440\u043a\u0430: \u0433\u043e\u0442\u043e\u0432\u0438\u043c TTS-\u0447\u0430\u043d\u043a\u0438.",
        "zh": "\u81ea\u52a8\u751f\u6210\uff1a\u6b63\u5728\u51c6\u5907 TTS \u5206\u5757\u3002",
        "kk": "\u0410\u0432\u0442\u043e\u0436\u0438\u043d\u0430\u0443: TTS \u0447\u0430\u043d\u043a\u0442\u0430\u0440\u044b \u0434\u0430\u0439\u044b\u043d\u0434\u0430\u043b\u0443\u0434\u0430.",
        "uz": "Avtoyig'ish: TTS bo'laklari tayyorlanmoqda.",
    },
    "auto.synthesis": {
        "en": "Automatic build: generating audio. This is the long overnight step.",
        "ru": "\u0410\u0432\u0442\u043e\u0441\u0431\u043e\u0440\u043a\u0430: \u043e\u0437\u0432\u0443\u0447\u0438\u0432\u0430\u0435\u043c. \u042d\u0442\u043e \u0434\u043e\u043b\u0433\u0438\u0439 \u043d\u043e\u0447\u043d\u043e\u0439 \u044d\u0442\u0430\u043f.",
        "zh": "\u81ea\u52a8\u751f\u6210\uff1a\u6b63\u5728\u751f\u6210\u97f3\u9891\u3002\u8fd9\u662f\u9002\u5408\u591c\u95f4\u8fd0\u884c\u7684\u957f\u6b65\u9aa4\u3002",
        "kk": "\u0410\u0432\u0442\u043e\u0436\u0438\u043d\u0430\u0443: \u0434\u044b\u0431\u044b\u0441 \u0436\u0430\u0441\u0430\u043b\u0443\u0434\u0430. \u0411\u04b1\u043b \u0442\u04af\u043d\u0433\u0456 \u04b1\u0437\u0430\u049b \u049b\u0430\u0434\u0430\u043c.",
        "uz": "Avtoyig'ish: audio yaratilmoqda. Bu tun bo'yi davom etadigan uzun bosqich.",
    },
    "auto.assembly": {
        "en": "Automatic build: assembling the final audiobook.",
        "ru": "\u0410\u0432\u0442\u043e\u0441\u0431\u043e\u0440\u043a\u0430: \u0441\u043a\u043b\u0435\u0438\u0432\u0430\u0435\u043c \u0433\u043e\u0442\u043e\u0432\u0443\u044e \u0430\u0443\u0434\u0438\u043e\u043a\u043d\u0438\u0433\u0443.",
        "zh": "\u81ea\u52a8\u751f\u6210\uff1a\u6b63\u5728\u5408\u6210\u6700\u7ec8\u6709\u58f0\u4e66\u3002",
        "kk": "\u0410\u0432\u0442\u043e\u0436\u0438\u043d\u0430\u0443: \u0434\u0430\u0439\u044b\u043d \u0430\u0443\u0434\u0438\u043e\u043a\u0456\u0442\u0430\u043f \u0436\u0438\u043d\u0430\u043b\u0443\u0434\u0430.",
        "uz": "Avtoyig'ish: yakuniy audiokitob yig'ilmoqda.",
    },
    "auto.production": {
        "en": "Automatic build: running production preflight.",
        "ru": "Автосборка: выполняем production preflight.",
        "zh": "Automatic build: running production preflight.",
        "kk": "Automatic build: running production preflight.",
        "uz": "Automatic build: running production preflight.",
    },
    "auto.complete": {
        "en": "Automatic audiobook build complete.",
        "ru": "\u0410\u0432\u0442\u043e\u0441\u0431\u043e\u0440\u043a\u0430 \u0430\u0443\u0434\u0438\u043e\u043a\u043d\u0438\u0433\u0438 \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0430.",
        "zh": "\u6709\u58f0\u4e66\u5df2\u81ea\u52a8\u751f\u6210\u5b8c\u6210\u3002",
        "kk": "\u0410\u0443\u0434\u0438\u043e\u043a\u0456\u0442\u0430\u043f\u0442\u044b \u0430\u0432\u0442\u043e\u0436\u0438\u043d\u0430\u0443 \u0430\u044f\u049b\u0442\u0430\u043b\u0434\u044b.",
        "uz": "Audiokitobni avtomatik yig'ish tugadi.",
    },
    "auto.failed": {
        "en": "Automatic build stopped: {msg}",
        "ru": "\u0410\u0432\u0442\u043e\u0441\u0431\u043e\u0440\u043a\u0430 \u043e\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d\u0430: {msg}",
        "zh": "\u81ea\u52a8\u751f\u6210\u5df2\u505c\u6b62\uff1a{msg}",
        "kk": "\u0410\u0432\u0442\u043e\u0436\u0438\u043d\u0430\u0443 \u0442\u043e\u049b\u0442\u0430\u0434\u044b: {msg}",
        "uz": "Avtoyig'ish to'xtadi: {msg}",
    },

    # ── Tab names ──
    "tab.normalize": {
        "en": "1. Normalize",
        "ru": "1. \u041d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f",
    },
    "tab.normalize_short": {
        "en": "1. Norm.",
        "ru": "1. \u041d\u043e\u0440\u043c.",
    },
    "tab.roles": {
        "en": "2. Roles",
        "ru": "2. \u0420\u043e\u043b\u0438",
        "zh": "2. \u89d2\u8272",
        "kk": "2. \u0420\u04e9\u043b\u0434\u0435\u0440",
        "uz": "2. Rollar",
    },
    "tab.roles_short": {
        "en": "2. Roles",
        "ru": "2. \u0420\u043e\u043b\u0438",
        "zh": "2. \u89d2\u8272",
        "kk": "2. \u0420\u04e9\u043b",
        "uz": "2. Rol",
    },
    "tab.chunks": {
        "en": "3. Chunks",
        "ru": "3. \u0427\u0430\u043d\u043a\u0438",
        "zh": "3. \u5206\u5757",
        "kk": "3. \u0427\u0430\u043d\u043a\u0442\u0430\u0440",
        "uz": "3. Bo\u02bblaklar",
    },
    "tab.chunks_short": {
        "en": "3. Chunks",
        "ru": "3. \u0427\u0430\u043d\u043a\u0438",
        "zh": "3. \u5206\u5757",
        "kk": "3. \u0427\u0430\u043d\u043a",
        "uz": "3. Bo\u02bb.",
    },
    "tab.voices": {
        "en": "4. Voices",
        "ru": "4. \u0413\u043e\u043b\u043e\u0441\u0430",
        "zh": "4. \u58f0\u97f3",
        "kk": "4. \u0414\u0430\u0443\u044b\u0441\u0442\u0430\u0440",
        "uz": "4. Ovozlar",
    },
    "tab.voices_short": {
        "en": "4. Voices",
        "ru": "4. \u0413\u043e\u043b\u043e\u0441\u0430",
        "zh": "4. \u58f0\u97f3",
        "kk": "4. \u0414\u0430\u0443\u044b\u0441",
        "uz": "4. Ovoz",
    },
    "tab.synthesize": {
        "en": "4. Voices",
        "ru": "4. \u0413\u043e\u043b\u043e\u0441\u0430",
    },
    "tab.synthesize_short": {
        "en": "4. Voices",
        "ru": "4. \u0413\u043e\u043b\u043e\u0441\u0430",
    },
    "tab.assemble": {
        "en": "5. Chapters",
        "ru": "5. \u041e\u0444\u043e\u0440\u043c\u043b\u0435\u043d\u0438\u0435",
    },
    "tab.assemble_short": {
        "en": "5. Build",
        "ru": "5. \u0413\u043b\u0430\u0432\u044b",
    },

    # ── Normalize page ──
    "norm.no_file": {
        "en": "No file selected",
        "ru": "\u0424\u0430\u0439\u043b \u043d\u0435 \u0432\u044b\u0431\u0440\u0430\u043d",
    },
    "norm.browse": {"en": "Browse\u2026", "ru": "\u041e\u0431\u0437\u043e\u0440\u2026"},
    "norm.book_language": {
        "en": "Book language:",
        "ru": "\u042f\u0437\u044b\u043a \u043a\u043d\u0438\u0433\u0438:",
    },
    "norm.book_language_tip": {
        "en": "Controls OCR language, language-safe normalization, chunk metadata, and Qwen/ComfyUI synthesis language.",
        "ru": "\u0412\u043b\u0438\u044f\u0435\u0442 \u043d\u0430 \u044f\u0437\u044b\u043a OCR, \u0431\u0435\u0437\u043e\u043f\u0430\u0441\u043d\u0443\u044e \u043d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044e, \u043c\u0435\u0442\u0430\u0434\u0430\u043d\u043d\u044b\u0435 \u0447\u0430\u043d\u043a\u043e\u0432 \u0438 \u044f\u0437\u044b\u043a \u0441\u0438\u043d\u0442\u0435\u0437\u0430 Qwen/ComfyUI.",
    },
    "book_language.ru": {"en": "Russian", "ru": "\u0420\u0443\u0441\u0441\u043a\u0438\u0439"},
    "book_language.en": {"en": "English", "ru": "\u0410\u043d\u0433\u043b\u0438\u0439\u0441\u043a\u0438\u0439"},
    "book_language.zh": {"en": "Chinese", "ru": "\u041a\u0438\u0442\u0430\u0439\u0441\u043a\u0438\u0439"},
    "book_language.kk": {"en": "Kazakh", "ru": "\u041a\u0430\u0437\u0430\u0445\u0441\u043a\u0438\u0439"},
    "book_language.uz": {"en": "Uzbek", "ru": "\u0423\u0437\u0431\u0435\u043a\u0441\u043a\u0438\u0439"},
    "norm.ocr_mode": {"en": "OCR Mode:", "ru": "\u0420\u0435\u0436\u0438\u043c OCR:"},
    "norm.ocr_mode_hint": {
        "en": "auto = OCR if text unreadable | off = no OCR | force = always OCR | compare = both",
        "ru": "auto = OCR \u0435\u0441\u043b\u0438 \u0442\u0435\u043a\u0441\u0442 \u043d\u0435\u0447\u0438\u0442\u0430\u0435\u043c | off = \u0431\u0435\u0437 OCR | force = \u0432\u0441\u0435\u0433\u0434\u0430 OCR | compare = \u043e\u0431\u0430",
    },
    "norm.ocr_mode_tip": {
        "en": (
            "auto \u2014 OCR only if native text is empty or unreadable (Cyrillic < 30%)\n"
            "off \u2014 use only native PDF text extraction, no OCR\n"
            "force \u2014 always run OCR, ignore native text\n"
            "compare \u2014 run both, save comparison report"
        ),
        "ru": (
            "auto \u2014 OCR \u0442\u043e\u043b\u044c\u043a\u043e \u0435\u0441\u043b\u0438 \u0442\u0435\u043a\u0441\u0442 \u043f\u0443\u0441\u0442 \u0438\u043b\u0438 \u043d\u0435\u0447\u0438\u0442\u0430\u0435\u043c (\u043a\u0438\u0440\u0438\u043b\u043b\u0438\u0446\u0430 < 30%)\n"
            "off \u2014 \u0442\u043e\u043b\u044c\u043a\u043e \u0438\u0437\u0432\u043b\u0435\u0447\u0435\u043d\u0438\u0435 \u0442\u0435\u043a\u0441\u0442\u0430 \u0438\u0437 PDF, \u0431\u0435\u0437 OCR\n"
            "force \u2014 \u0432\u0441\u0435\u0433\u0434\u0430 \u0437\u0430\u043f\u0443\u0441\u043a\u0430\u0442\u044c OCR, \u0438\u0433\u043d\u043e\u0440\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0432\u0441\u0442\u0440\u043e\u0435\u043d\u043d\u044b\u0439 \u0442\u0435\u043a\u0441\u0442\n"
            "compare \u2014 \u0437\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u044c \u043e\u0431\u0430 \u0441\u043f\u043e\u0441\u043e\u0431\u0430, \u0441\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u043e\u0442\u0447\u0451\u0442"
        ),
    },
    "norm.ocr_dpi": {"en": "OCR DPI:", "ru": "OCR DPI:"},
    "norm.ocr_dpi_hint": {
        "en": "300 = fast | 400 = recommended | 600 = best quality (slow)",
        "ru": "300 = \u0431\u044b\u0441\u0442\u0440\u043e | 400 = \u0440\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0443\u0435\u0442\u0441\u044f | 600 = \u043b\u0443\u0447\u0448\u0435\u0435 \u043a\u0430\u0447\u0435\u0441\u0442\u0432\u043e (\u043c\u0435\u0434\u043b\u0435\u043d\u043d\u043e)",
    },
    "norm.ocr_dpi_tip": {
        "en": (
            "DPI (dots per inch) for rendering PDF pages to images before OCR.\n"
            "Higher = better quality text recognition, but slower.\n"
            "300 = fast, 400 = good balance (default), 600 = best quality."
        ),
        "ru": (
            "DPI (\u0442\u043e\u0447\u0435\u043a \u043d\u0430 \u0434\u044e\u0439\u043c) \u0434\u043b\u044f \u0440\u0435\u043d\u0434\u0435\u0440\u0430 \u0441\u0442\u0440\u0430\u043d\u0438\u0446 PDF \u043f\u0435\u0440\u0435\u0434 OCR.\n"
            "\u0411\u043e\u043b\u044c\u0448\u0435 = \u043b\u0443\u0447\u0448\u0435 \u043a\u0430\u0447\u0435\u0441\u0442\u0432\u043e, \u043d\u043e \u043c\u0435\u0434\u043b\u0435\u043d\u043d\u0435\u0435.\n"
            "300 = \u0431\u044b\u0441\u0442\u0440\u043e, 400 = \u043e\u043f\u0442\u0438\u043c\u0430\u043b\u044c\u043d\u043e, 600 = \u043c\u0430\u043a\u0441\u0438\u043c\u0430\u043b\u044c\u043d\u043e\u0435 \u043a\u0430\u0447\u0435\u0441\u0442\u0432\u043e."
        ),
    },
    "norm.ocr_psm": {
        "en": "OCR page layout (PSM):",
        "ru": "Разметка страницы OCR (PSM):",
    },
    "norm.ocr_psm_hint": {
        "en": "Choose the layout that best matches the rendered page.",
        "ru": "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0440\u0430\u0437\u043c\u0435\u0442\u043a\u0443, \u043a\u043e\u0442\u043e\u0440\u0430\u044f \u0431\u043b\u0438\u0436\u0435 \u0432\u0441\u0435\u0433\u043e \u043a \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u0435 \u043f\u043e\u0441\u043b\u0435 \u0440\u0435\u043d\u0434\u0435\u0440\u0430.",
    },
    "norm.ocr_psm_3": {
        "en": "3 - Auto full page: unknown book layout",
        "ru": "3 - Авто-страница: если верстка книги непонятна",
    },
    "norm.ocr_psm_4": {
        "en": "4 - Normal book page: continuous reading order",
        "ru": "4 - Обычная страница книги: сплошной порядок чтения",
    },
    "norm.ocr_psm_6": {
        "en": "6 - Cropped body text: one selected text block",
        "ru": "6 - Вырезанный основной текст: один выбранный блок",
    },
    "norm.ocr_psm_11": {
        "en": "11 - Loose fragments: captions, stamps, margin notes",
        "ru": "11 - Разбросанные фрагменты: подписи, штампы, поля",
    },
    "norm.ocr_psm_13": {
        "en": "13 - Title or one line: short strip, not a page",
        "ru": "13 - Заголовок или одна строка: не целая страница",
    },
    "norm.ocr_psm_compact_3": {
        "en": "3 - Auto",
        "ru": "3 - Авто",
        "zh": "3 - 自动",
        "kk": "3 - Авто",
        "uz": "3 - Avto",
    },
    "norm.ocr_psm_compact_4": {
        "en": "4 - Book page",
        "ru": "4 - Страница книги",
        "zh": "4 - 书页",
        "kk": "4 - Кітап беті",
        "uz": "4 - Kitob sahifasi",
    },
    "norm.ocr_psm_compact_6": {
        "en": "6 - Cropped text",
        "ru": "6 - Обрезанный текст",
        "zh": "6 - 裁剪正文",
        "kk": "6 - Қиылған мәтін",
        "uz": "6 - Kesilgan matn",
    },
    "norm.ocr_psm_compact_11": {
        "en": "11 - Fragments",
        "ru": "11 - Фрагменты",
        "zh": "11 - 片段",
        "kk": "11 - Фрагменттер",
        "uz": "11 - Bo'laklar",
    },
    "norm.ocr_psm_compact_13": {
        "en": "13 - One line",
        "ru": "13 - Одна строка",
        "zh": "13 - 单行",
        "kk": "13 - Бір жол",
        "uz": "13 - Bir qator",
    },
    "norm.ocr_psm_summary_3": {
        "en": "Use when page layout is uncertain; review reading order after OCR.",
        "ru": "Для сложной страницы: Tesseract сам ищет порядок, но результат надо проверить.",
        "zh": "页面结构不确定时使用；OCR 后请复核阅读顺序。",
        "kk": "Бет құрылымы белгісіз болса; OCR-дан кейін оқу ретін тексеріңіз.",
        "uz": "Sahifa tuzilmasi noaniq bo'lsa ishlating; OCRdan keyin o'qish tartibini tekshiring.",
    },
    "norm.ocr_psm_summary_4": {
        "en": "Best first choice for a normal full-page book scan.",
        "ru": "Лучший первый выбор для обычного полного скана книжной страницы.",
        "zh": "普通整页书籍扫描的首选。",
        "kk": "Кітаптың қалыпты толық скан беті үшін бірінші таңдау.",
        "uz": "Oddiy to'liq skan qilingan kitob sahifasi uchun birinchi tanlov.",
    },
    "norm.ocr_psm_summary_6": {
        "en": "Use only for a cropped rectangle with one main text block.",
        "ru": "Только для обрезанного прямоугольника с одним основным блоком текста.",
        "zh": "仅用于已裁剪的单个正文矩形区域。",
        "kk": "Бір негізгі мәтін блогы бар қиылған тікбұрыш үшін ғана.",
        "uz": "Faqat bitta asosiy matn bloki bor kesilgan to'rtburchak uchun.",
    },
    "norm.ocr_psm_summary_11": {
        "en": "For notes, stamps, captions, or scattered pieces; not for normal pages.",
        "ru": "Для заметок, штампов, подписей и разбросанных кусков; не для обычной страницы.",
        "zh": "用于笔记、印章、图注或分散片段；不适合普通书页。",
        "kk": "Жазба, мөр, түсіндірме не шашыраған бөліктер үшін; қалыпты бетке емес.",
        "uz": "Izoh, muhr, sarlavha yoki tarqoq bo'laklar uchun; oddiy sahifa uchun emas.",
    },
    "norm.ocr_psm_summary_13": {
        "en": "For a single title/header line; do not use for full pages.",
        "ru": "Для одной строки или заголовка; не используйте для полной страницы.",
        "zh": "用于单行标题或页眉；不要用于整页。",
        "kk": "Бір жол не тақырып үшін; толық бетке қолданбаңыз.",
        "uz": "Bitta sarlavha yoki qator uchun; to'liq sahifaga ishlatmang.",
    },
    "norm.ocr_psm_tip": {
        "en": (
            "Tesseract Page Segmentation Mode (PSM):\n"
            "3 auto full page = use when the book page has unknown layout, several blocks, illustrations, or mixed structure.\n"
            "4 normal book page = use for a full scanned page whose main text can be read from top to bottom in a stable order.\n"
            "6 cropped body text = use only when the image is already a selected rectangle with one main text block.\n"
            "11 loose fragments = use for captions, stamps, margin notes, forms, or scattered text pieces; reading order may need review.\n"
            "13 title or one line = use for one short horizontal title/header/line; do not use for full pages."
        ),
        "ru": (
            "\u0420\u0435\u0436\u0438\u043c \u0441\u0435\u0433\u043c\u0435\u043d\u0442\u0430\u0446\u0438\u0438 \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u044b Tesseract (PSM):\n"
            "3 авто-страница = когда у страницы книги непонятная верстка, несколько блоков, иллюстрации или смешанная структура.\n"
            "4 обычная страница книги = полный скан страницы, где основной текст читается сверху вниз в стабильном порядке.\n"
            "6 вырезанный основной текст = только если изображение уже обрезано до одного прямоугольного блока текста без полей и колонтитулов.\n"
            "11 разбросанные фрагменты = подписи, штампы, заметки на полях, формы или отдельные куски текста; порядок чтения надо проверить.\n"
            "13 заголовок или одна строка = одна короткая горизонтальная строка/шапка; не использовать для полной страницы."
        ),
    },
    "norm.ocr_not_applicable": {
        "en": "OCR settings apply only to PDF files",
        "ru": "\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438 OCR \u043f\u0440\u0438\u043c\u0435\u043d\u0438\u043c\u044b \u0442\u043e\u043b\u044c\u043a\u043e \u043a PDF",
    },
    "norm.ocr_install_hint": {
        "en": "Tesseract is not available in this OS. Install native OCR tools: {cmd}",
        "ru": "Tesseract не найден в этой ОС. Установите OCR нативным установщиком: {cmd}",
        "zh": "当前系统未找到 Tesseract。请用本机安装器安装 OCR 工具：{cmd}",
        "kk": "Бұл ОС-та Tesseract табылмады. OCR құралдарын жергілікті орнатқышпен орнатыңыз: {cmd}",
        "uz": "Bu OSda Tesseract topilmadi. OCR vositalarini mahalliy o‘rnatuvchi bilan o‘rnating: {cmd}",
    },
    "norm.ocr_install_language_hint": {
        "en": "Tesseract is installed, but language data '{lang}' is missing. Install OCR language packs: {cmd}",
        "ru": "Tesseract установлен, но нет языкового пакета '{lang}'. Установите OCR-языки: {cmd}",
        "zh": "已安装 Tesseract，但缺少语言数据 '{lang}'。请安装 OCR 语言包：{cmd}",
        "kk": "Tesseract орнатылған, бірақ '{lang}' тіл деректері жоқ. OCR тіл пакеттерін орнатыңыз: {cmd}",
        "uz": "Tesseract o‘rnatilgan, lekin '{lang}' til maʼlumoti yo‘q. OCR til paketlarini o‘rnating: {cmd}",
    },
    "norm.ocr_install_button": {
        "en": "Install OCR",
        "ru": "Установить OCR",
        "zh": "安装 OCR",
        "kk": "OCR орнату",
        "uz": "OCR o‘rnatish",
    },
    "norm.ocr_install_started": {
        "en": "Started native OCR installer: {cmd}",
        "ru": "Запущен нативный установщик OCR: {cmd}",
        "zh": "已启动本机 OCR 安装器：{cmd}",
        "kk": "Жергілікті OCR орнатқышы іске қосылды: {cmd}",
        "uz": "Mahalliy OCR o‘rnatuvchisi ishga tushdi: {cmd}",
    },
    "norm.ocr_install_failed": {
        "en": "Could not launch installer. Run manually: {cmd}",
        "ru": "Не удалось запустить установщик. Запустите вручную: {cmd}",
        "zh": "无法启动安装器。请手动运行：{cmd}",
        "kk": "Орнатқышты іске қосу мүмкін болмады. Қолмен іске қосыңыз: {cmd}",
        "uz": "O‘rnatuvchini ishga tushirib bo‘lmadi. Qo‘lda ishga tushiring: {cmd}",
    },
    "norm.llm_normalize": {
        "en": "LLM/GPU normalization:",
        "ru": "LLM/GPU \u043d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f:",
    },
    "norm.llm_normalize_check": {
        "en": "Use local model after rules",
        "ru": "\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u044c \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u0443\u044e \u043c\u043e\u0434\u0435\u043b\u044c \u043f\u043e\u0441\u043b\u0435 \u043f\u0440\u0430\u0432\u0438\u043b",
    },
    "norm.llm_normalize_check_compact": {
        "en": "Local LLM",
        "ru": "\u041b\u043e\u043a\u0430\u043b\u044c\u043d\u0430\u044f LLM",
        "zh": "\u672c\u5730 LLM",
        "kk": "\u0416\u0435\u0440\u0433\u0456\u043b\u0456\u043a\u0442\u0456 LLM",
        "uz": "Lokal LLM",
    },
    "norm.llm_endpoint": {
        "en": "LLM endpoint:",
        "ru": "LLM endpoint:",
    },
    "norm.llm_model": {
        "en": "LLM model:",
        "ru": "LLM \u043c\u043e\u0434\u0435\u043b\u044c:",
    },
    "norm.llm_hint": {
        "en": "Uses an OpenAI-compatible local server. GPU usage depends on that server, e.g. Ollama with CUDA.",
        "ru": "\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0435\u0442 OpenAI-compatible \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0439 \u0441\u0435\u0440\u0432\u0435\u0440. GPU \u0437\u0430\u0434\u0435\u0439\u0441\u0442\u0432\u0443\u0435\u0442\u0441\u044f \u0441\u0430\u043c\u0438\u043c \u0441\u0435\u0440\u0432\u0435\u0440\u043e\u043c, \u043d\u0430\u043f\u0440\u0438\u043c\u0435\u0440 Ollama \u0441 CUDA.",
    },
    "norm.llm_tip": {
        "en": (
            "Runs the existing rule-based normalizer first, then asks a local "
            "OpenAI-compatible LLM to conservatively fix punctuation, typos, "
            "and yo letters. The app validates every answer and keeps the "
            "original text if the model changes too much."
        ),
        "ru": (
            "\u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u0438\u0434\u0451\u0442 \u0431\u044b\u0441\u0442\u0440\u0430\u044f \u043d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f \u043f\u0440\u0430\u0432\u0438\u043b\u0430\u043c\u0438, \u0437\u0430\u0442\u0435\u043c "
            "\u043b\u043e\u043a\u0430\u043b\u044c\u043d\u0430\u044f OpenAI-compatible LLM \u0430\u043a\u043a\u0443\u0440\u0430\u0442\u043d\u043e \u0438\u0441\u043f\u0440\u0430\u0432\u043b\u044f\u0435\u0442 "
            "\u043f\u0443\u043d\u043a\u0442\u0443\u0430\u0446\u0438\u044e, \u043e\u043f\u0435\u0447\u0430\u0442\u043a\u0438 \u0438 \u0431\u0443\u043a\u0432\u0443 \u0451. \u041a\u0430\u0436\u0434\u044b\u0439 \u043e\u0442\u0432\u0435\u0442 "
            "\u043f\u0440\u043e\u0432\u0435\u0440\u044f\u0435\u0442\u0441\u044f; \u0435\u0441\u043b\u0438 \u043c\u043e\u0434\u0435\u043b\u044c \u0441\u043b\u0438\u0448\u043a\u043e\u043c \u043c\u0435\u043d\u044f\u0435\u0442 \u0442\u0435\u043a\u0441\u0442, "
            "\u043e\u0441\u0442\u0430\u0451\u0442\u0441\u044f \u0438\u0441\u0445\u043e\u0434\u043d\u044b\u0439 \u0430\u0431\u0437\u0430\u0446."
        ),
    },
    "norm.run": {
        "en": "Run Normalization",
        "ru": "\u0417\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u044c \u043d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044e",
    },
    "norm.starting": {
        "en": "Starting\u2026",
        "ru": "\u0417\u0430\u043f\u0443\u0441\u043a\u2026",
    },
    "norm.cache_dialog_title": {
        "en": "Completed normalization found",
        "ru": "Готовая нормализация найдена",
        "zh": "已找到完成的标准化结果",
        "kk": "Дайын нормализация табылды",
        "uz": "Yakunlangan normalizatsiya topildi",
    },
    "norm.cache_dialog_text": {
        "en": "A cached result exists for “{name}” with the current settings.",
        "ru": "Для «{name}» найден результат с текущими параметрами.",
        "zh": "“{name}”在当前设置下已有缓存结果。",
        "kk": "«{name}» үшін ағымдағы баптаулармен кеш нәтижесі бар.",
        "uz": "“{name}” uchun joriy sozlamalar bilan kesh natijasi bor.",
    },
    "norm.cache_dialog_text_mismatch": {
        "en": "A cached result exists for “{name}”, but its settings differ from the current ones.",
        "ru": "Для «{name}» найден кеш, но его настройки отличаются от текущих.",
        "zh": "“{name}” 有缓存结果，但它的设置与当前设置不同。",
        "kk": "«{name}» үшін кеш нәтижесі бар, бірақ оның баптаулары ағымдағы баптаулардан өзгеше.",
        "uz": "“{name}” uchun kesh natijasi bor, lekin uning sozlamalari joriy sozlamalardan farq qiladi.",
    },
    "norm.cache_dialog_informative": {
        "en": (
            "Restore it to continue immediately with chapters and role extraction. "
            "Choose “Run from scratch” only if you want to read the source, OCR, and LLM steps again."
        ),
        "ru": (
            "Восстановите его из кеша, чтобы сразу продолжить с главами и ролями. "
            "Выберите «Запустить заново», только если хотите повторно прочитать файл, OCR и LLM-шаги."
        ),
        "zh": "从缓存恢复即可立即继续处理章节和角色。只有在想重新读取源文件、OCR 和 LLM 步骤时，才选择“重新运行”。",
        "kk": (
            "Кештен қалпына келтірсеңіз, тараулар мен рөлдерге бірден өтесіз. "
            "Бастапқы файлды, OCR және LLM қадамдарын қайта орындау керек болса ғана «Қайта іске қосу» таңдаңыз."
        ),
        "uz": (
            "Keshdan tiklasangiz, boblar va rollar bilan darhol davom etasiz. "
            "Manba fayl, OCR va LLM bosqichlarini qayta bajarishni istasangizgina “Qayta ishga tushirish”ni tanlang."
        ),
    },
    "norm.cache_dialog_informative_mismatch": {
        "en": (
            "Restoring uses the cached result as it was built before. "
            "Choose “Run from scratch” to apply the current OCR, DPI, PSM, or LLM settings."
        ),
        "ru": (
            "Восстановление возьмет уже собранный результат из кеша. "
            "Выберите «Запустить заново», чтобы применить текущие OCR, DPI, PSM или LLM-настройки."
        ),
        "zh": "恢复会使用之前生成的缓存结果。选择“重新运行”以应用当前 OCR、DPI、PSM 或 LLM 设置。",
        "kk": (
            "Қалпына келтіру бұрын жасалған кеш нәтижесін пайдаланады. "
            "Ағымдағы OCR, DPI, PSM немесе LLM баптауларын қолдану үшін «Қайта іске қосу» таңдаңыз."
        ),
        "uz": (
            "Tiklash avval yaratilgan kesh natijasidan foydalanadi. "
            "Joriy OCR, DPI, PSM yoki LLM sozlamalarini qo'llash uchun “Qayta ishga tushirish”ni tanlang."
        ),
    },
    "norm.cache_restore_button": {
        "en": "Restore from cache",
        "ru": "Восстановить из кеша",
        "zh": "从缓存恢复",
        "kk": "Кештен қалпына келтіру",
        "uz": "Keshdan tiklash",
    },
    "norm.cache_run_fresh_button": {
        "en": "Run from scratch",
        "ru": "Запустить заново",
        "zh": "重新运行",
        "kk": "Қайта іске қосу",
        "uz": "Qayta ishga tushirish",
    },
    "norm.cache_cancel_button": {
        "en": "Cancel",
        "ru": "Отмена",
        "zh": "取消",
        "kk": "Болдырмау",
        "uz": "Bekor qilish",
    },
    "norm.cache_restored": {
        "en": "Restored from cache. Chapters: {n}.",
        "ru": "Восстановлено из кеша. Глав: {n}.",
        "zh": "已从缓存恢复。章节数：{n}。",
        "kk": "Кештен қалпына келтірілді. Тараулар: {n}.",
        "uz": "Keshdan tiklandi. Boblar: {n}.",
    },
    "norm.cache_restore_failed": {
        "en": "Could not restore cached normalization: {msg}",
        "ru": "Не удалось восстановить нормализацию из кеша: {msg}",
        "zh": "无法恢复缓存的标准化结果：{msg}",
        "kk": "Кештегі нормализацияны қалпына келтіру мүмкін болмады: {msg}",
        "uz": "Keshlangan normalizatsiyani tiklab bo'lmadi: {msg}",
    },
    "norm.loading": {
        "en": "Loading book\u2026",
        "ru": "\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u043a\u043d\u0438\u0433\u0438\u2026",
    },
    "norm.pdf_checking": {
        "en": "Checking PDF and OCR settings...",
        "ru": "\u041f\u0440\u043e\u0432\u0435\u0440\u044f\u044e PDF \u0438 OCR-\u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438...",
        "zh": "正在检查 PDF 和 OCR 设置...",
        "kk": "PDF және OCR баптаулары тексерілуде...",
        "uz": "PDF va OCR sozlamalari tekshirilmoqda...",
    },
    "norm.pdf_native_extracting": {
        "en": "Checking the embedded PDF text layer...",
        "ru": "\u041f\u0440\u043e\u0432\u0435\u0440\u044f\u044e \u0432\u0441\u0442\u0440\u043e\u0435\u043d\u043d\u044b\u0439 \u0442\u0435\u043a\u0441\u0442\u043e\u0432\u044b\u0439 \u0441\u043b\u043e\u0439 PDF...",
        "zh": "正在检查 PDF 内置文本层...",
        "kk": "PDF ішіндегі мәтін қабаты тексерілуде...",
        "uz": "PDF ichidagi matn qatlami tekshirilmoqda...",
    },
    "norm.ocr_prepare": {
        "en": "Preparing OCR (DPI={dpi}, PSM={psm})...",
        "ru": "\u0413\u043e\u0442\u043e\u0432\u043b\u044e OCR (DPI={dpi}, PSM={psm})...",
        "zh": "正在准备 OCR (DPI={dpi}, PSM={psm})...",
        "kk": "OCR дайындалуда (DPI={dpi}, PSM={psm})...",
        "uz": "OCR tayyorlanmoqda (DPI={dpi}, PSM={psm})...",
    },
    "norm.ocr_pages_start": {
        "en": "OCR will process {total} page(s) at {dpi} DPI, PSM {psm}. The first page can take a while; ETA appears after it finishes.",
        "ru": "OCR \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442 {total} \u0441\u0442\u0440. \u043f\u0440\u0438 {dpi} DPI, PSM {psm}. \u041f\u0435\u0440\u0432\u0430\u044f \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u0430 \u043c\u043e\u0436\u0435\u0442 \u0438\u0434\u0442\u0438 \u0434\u043e\u043b\u0433\u043e; ETA \u043f\u043e\u044f\u0432\u0438\u0442\u0441\u044f \u043f\u043e\u0441\u043b\u0435 \u043d\u0435\u0451.",
        "zh": "OCR 将处理 {total} 页，{dpi} DPI，PSM {psm}。第一页可能较慢；完成后会显示 ETA。",
        "kk": "OCR {total} бетті {dpi} DPI, PSM {psm} режимінде өңдейді. Бірінші бет ұзақ жүруі мүмкін; ETA содан кейін шығады.",
        "uz": "OCR {total} sahifani {dpi} DPI, PSM {psm} bilan qayta ishlaydi. Birinchi sahifa uzoqroq ketishi mumkin; ETA undan keyin chiqadi.",
    },
    "norm.ocr_page_rendering": {
        "en": "OCR: rendering page {page}/{total} at {dpi} DPI...",
        "ru": "OCR: \u0440\u0435\u043d\u0434\u0435\u0440 \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u044b {page}/{total} \u043f\u0440\u0438 {dpi} DPI...",
        "zh": "OCR：正在渲染第 {page}/{total} 页，{dpi} DPI...",
        "kk": "OCR: {page}/{total} бет {dpi} DPI-да рендерленуде...",
        "uz": "OCR: {page}/{total} sahifa {dpi} DPI da render qilinmoqda...",
    },
    "norm.ocr_page_recognizing": {
        "en": "OCR: recognizing page {page}/{total}, segment {segment}/{segments}...",
        "ru": "OCR: \u0440\u0430\u0441\u043f\u043e\u0437\u043d\u0430\u044e \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u0443 {page}/{total}, \u0441\u0435\u0433\u043c\u0435\u043d\u0442 {segment}/{segments}...",
        "zh": "OCR：正在识别第 {page}/{total} 页，片段 {segment}/{segments}...",
        "kk": "OCR: {page}/{total} бет танылуда, сегмент {segment}/{segments}...",
        "uz": "OCR: {page}/{total} sahifa tanilmoqda, segment {segment}/{segments}...",
    },
    "norm.ocr_page_done": {
        "en": "OCR: {done}/{total} page(s) done - ETA: {eta}",
        "ru": "OCR: \u0433\u043e\u0442\u043e\u0432\u043e {done}/{total} \u0441\u0442\u0440. - \u041e\u0441\u0442\u0430\u043b\u043e\u0441\u044c: {eta}",
        "zh": "OCR：已完成 {done}/{total} 页 - ETA：{eta}",
        "kk": "OCR: {done}/{total} бет дайын - ETA: {eta}",
        "uz": "OCR: {done}/{total} sahifa tayyor - ETA: {eta}",
    },
    "norm.ocr_unavailable_native": {
        "en": "Tesseract is not installed; using native PDF text extraction. Run: {hint}",
        "ru": "Tesseract не установлен; использую встроенное извлечение текста PDF. Запустите: {hint}",
    },
    "norm.err_tesseract_missing_force": {
        "en": "Tesseract is not installed. Run: {hint}. Or switch OCR mode to auto/off.",
        "ru": "Tesseract не установлен. Запустите: {hint}. Или переключите OCR в auto/off.",
    },
    "norm.err_tesseract_missing_scanned": {
        "en": "The PDF text layer is missing or unreadable, and Tesseract is not installed. Run: {hint}. Then run normalization again.",
        "ru": "Текстовый слой PDF отсутствует или нечитаем, а Tesseract не установлен. Запустите: {hint}. Затем запустите нормализацию снова.",
    },
    "norm.err_ocr_failed_unreadable": {
        "en": "The PDF text layer is unreadable, and OCR did not produce readable Russian text. Check the Tesseract Russian language pack or try another DPI/PSM setting.",
        "ru": "\u0422\u0435\u043a\u0441\u0442\u043e\u0432\u044b\u0439 \u0441\u043b\u043e\u0439 PDF \u043d\u0435\u0447\u0438\u0442\u0430\u0435\u043c, \u0438 OCR \u043d\u0435 \u0434\u0430\u043b \u0447\u0438\u0442\u0430\u0435\u043c\u044b\u0439 \u0440\u0443\u0441\u0441\u043a\u0438\u0439 \u0442\u0435\u043a\u0441\u0442. \u041f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 \u0440\u0443\u0441\u0441\u043a\u0438\u0439 \u044f\u0437\u044b\u043a\u043e\u0432\u043e\u0439 \u043f\u0430\u043a\u0435\u0442 Tesseract \u0438\u043b\u0438 \u043f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u0434\u0440\u0443\u0433\u0438\u0435 DPI/PSM.",
    },
    "norm.err_ocr_failed_force": {
        "en": "OCR did not produce readable Russian text. Check the Tesseract Russian language pack or try another DPI/PSM setting.",
        "ru": "OCR \u043d\u0435 \u0434\u0430\u043b \u0447\u0438\u0442\u0430\u0435\u043c\u044b\u0439 \u0440\u0443\u0441\u0441\u043a\u0438\u0439 \u0442\u0435\u043a\u0441\u0442. \u041f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 \u0440\u0443\u0441\u0441\u043a\u0438\u0439 \u044f\u0437\u044b\u043a\u043e\u0432\u043e\u0439 \u043f\u0430\u043a\u0435\u0442 Tesseract \u0438\u043b\u0438 \u043f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u0434\u0440\u0443\u0433\u0438\u0435 DPI/PSM.",
    },
    "norm.normalizing": {
        "en": "Normalizing: {stage} ({cur}/{total}) \u2014 ETA: {eta}",
        "ru": "\u041d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f: {stage} ({cur}/{total}) \u2014 \u041e\u0441\u0442\u0430\u043b\u043e\u0441\u044c: {eta}",
    },
    "norm.norm_paragraphs": {
        "en": "Normalizing: {done}/{total} paragraphs \u2014 ETA: {eta}",
        "ru": "\u041d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f: {done}/{total} \u0430\u0431\u0437\u0430\u0446\u0435\u0432 \u2014 \u041e\u0441\u0442\u0430\u043b\u043e\u0441\u044c: {eta}",
    },
    "norm.llm_start": {
        "en": "LLM normalization: model {model}",
        "ru": "LLM-\u043d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f: \u043c\u043e\u0434\u0435\u043b\u044c {model}",
    },
    "norm.llm_progress": {
        "en": "LLM normalization: {done}/{total} paragraphs, accepted {accepted}, rejected {rejected} \u2014 ETA: {eta}",
        "ru": "LLM-\u043d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f: {done}/{total} \u0430\u0431\u0437\u0430\u0446\u0435\u0432, \u043f\u0440\u0438\u043d\u044f\u0442\u043e {accepted}, \u043e\u0442\u043a\u043b\u043e\u043d\u0435\u043d\u043e {rejected} \u2014 \u041e\u0441\u0442\u0430\u043b\u043e\u0441\u044c: {eta}",
    },
    "norm.llm_done": {
        "en": "LLM normalization complete: accepted {accepted}, rejected {rejected}",
        "ru": "LLM-\u043d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f \u0433\u043e\u0442\u043e\u0432\u0430: \u043f\u0440\u0438\u043d\u044f\u0442\u043e {accepted}, \u043e\u0442\u043a\u043b\u043e\u043d\u0435\u043d\u043e {rejected}",
    },
    "norm.llm_review_required": {
        "en": "LLM left {rejected} paragraph(s) unchanged. Review report: {path}",
        "ru": "LLM \u043e\u0441\u0442\u0430\u0432\u0438\u043b\u0430 {rejected} \u0430\u0431\u0437\u0430\u0446(\u0435\u0432) \u0431\u0435\u0437 \u043f\u0440\u0430\u0432\u043a\u0438. Review-report: {path}",
    },
    "norm.detecting_chapters": {
        "en": "Detecting chapters\u2026",
        "ru": "\u041e\u043f\u0440\u0435\u0434\u0435\u043b\u0435\u043d\u0438\u0435 \u0433\u043b\u0430\u0432\u2026",
    },
    "norm.annotating_stress": {
        "en": "Annotating stress marks\u2026",
        "ru": "\u0420\u0430\u0441\u0441\u0442\u0430\u043d\u043e\u0432\u043a\u0430 \u0443\u0434\u0430\u0440\u0435\u043d\u0438\u0439\u2026",
    },
    "norm.done": {
        "en": "Done: {n} chapters, {time} total",
        "ru": "\u0413\u043e\u0442\u043e\u0432\u043e: {n} \u0433\u043b\u0430\u0432, {time} \u0432\u0441\u0435\u0433\u043e",
    },
    "norm.raw_placeholder": {
        "en": "Original text",
        "ru": "\u041e\u0440\u0438\u0433\u0438\u043d\u0430\u043b \u0438\u0437 \u0444\u0430\u0439\u043b\u0430",
    },
    "norm.norm_placeholder": {
        "en": "After normalization",
        "ru": "\u041f\u043e\u0441\u043b\u0435 \u043d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u0438",
    },
    "norm.apply_manual_edits": {
        "en": "Apply edits",
        "ru": "\u041f\u0440\u0438\u043c\u0435\u043d\u0438\u0442\u044c \u043f\u0440\u0430\u0432\u043a\u0438",
        "zh": "\u5e94\u7528\u7f16\u8f91",
        "kk": "\u04e8\u04a3\u0434\u0435\u0443\u0434\u0456 \u049b\u043e\u043b\u0434\u0430\u043d\u0443",
        "uz": "Tahrirlarni qo\u02bblash",
    },
    "norm.apply_manual_edits_compact": {
        "en": "Apply",
        "ru": "\u041f\u0440\u0438\u043c\u0435\u043d\u0438\u0442\u044c",
        "zh": "\u5e94\u7528",
        "kk": "\u049a\u043e\u043b\u0434\u0430\u043d\u0443",
        "uz": "Qo'llash",
    },
    "norm.apply_manual_edits_tip": {
        "en": "Write the edited normalized text back into the book before role/chunk markup.",
        "ru": "\u0417\u0430\u043f\u0438\u0441\u0430\u0442\u044c \u0440\u0443\u0447\u043d\u044b\u0435 \u043f\u0440\u0430\u0432\u043a\u0438 \u0432 \u043a\u043d\u0438\u0433\u0443 \u043f\u0435\u0440\u0435\u0434 \u0440\u0430\u0437\u043c\u0435\u0442\u043a\u043e\u0439 \u0440\u043e\u043b\u0435\u0439 \u0438 \u0447\u0430\u043d\u043a\u043e\u0432.",
        "zh": "\u5728\u89d2\u8272\u548c\u5206\u5757\u6807\u6ce8\u524d\uff0c\u5c06\u5df2\u7f16\u8f91\u7684\u89c4\u8303\u5316\u6587\u672c\u5199\u56de\u4e66\u7a3f\u3002",
        "kk": "\u0420\u04e9\u043b\u0434\u0435\u0440 \u043c\u0435\u043d \u0447\u0430\u043d\u043a\u0442\u0430\u0440\u0434\u044b \u0431\u0435\u043b\u0433\u0456\u043b\u0435\u0443\u0434\u0435\u043d \u0431\u04b1\u0440\u044b\u043d \u04e9\u04a3\u0434\u0435\u043b\u0433\u0435\u043d \u043c\u04d9\u0442\u0456\u043d\u0434\u0456 \u043a\u0456\u0442\u0430\u043f\u049b\u0430 \u049b\u0430\u0439\u0442\u0430 \u0436\u0430\u0437\u0443.",
        "uz": "Rol va bo\u02bbak belgilashdan oldin tahrirlangan normallashtirilgan matnni kitobga yozish.",
    },
    "norm.manual_edit_applied": {
        "en": "Applied manual edits to {n} paragraph(s).",
        "ru": "\u0420\u0443\u0447\u043d\u044b\u0435 \u043f\u0440\u0430\u0432\u043a\u0438 \u043f\u0440\u0438\u043c\u0435\u043d\u0435\u043d\u044b \u043a {n} \u0430\u0431\u0437\u0430\u0446(\u0430\u043c).",
        "zh": "\u5df2\u5c06\u624b\u52a8\u7f16\u8f91\u5e94\u7528\u5230 {n} \u4e2a\u6bb5\u843d\u3002",
        "kk": "\u049a\u043e\u043b\u043c\u0435\u043d \u04e9\u04a3\u0434\u0435\u0443 {n} \u0430\u0431\u0437\u0430\u0446\u049b\u0430 \u049b\u043e\u043b\u0434\u0430\u043d\u044b\u043b\u0434\u044b.",
        "uz": "Qo\u02bblanma tahrirlar {n} paragrafga qo\u02bbllandi.",
    },
    "norm.manual_edit_mismatch": {
        "en": "Cannot apply edits: {edited} edited blocks for {paragraphs} book paragraph(s). Keep blank-line paragraph boundaries.",
        "ru": "\u041d\u0435 \u043c\u043e\u0433\u0443 \u043f\u0440\u0438\u043c\u0435\u043d\u0438\u0442\u044c \u043f\u0440\u0430\u0432\u043a\u0438: {edited} \u0431\u043b\u043e\u043a(\u0430) \u043d\u0430 {paragraphs} \u0430\u0431\u0437\u0430\u0446(\u0435\u0432) \u043a\u043d\u0438\u0433\u0438. \u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u0435 \u0433\u0440\u0430\u043d\u0438\u0446\u044b \u0430\u0431\u0437\u0430\u0446\u0435\u0432 \u043f\u0443\u0441\u0442\u044b\u043c\u0438 \u0441\u0442\u0440\u043e\u043a\u0430\u043c\u0438.",
        "zh": "\u65e0\u6cd5\u5e94\u7528\u7f16\u8f91\uff1a{edited} \u4e2a\u7f16\u8f91\u5757\u5bf9\u5e94 {paragraphs} \u4e2a\u4e66\u7a3f\u6bb5\u843d\u3002\u8bf7\u4fdd\u7559\u7a7a\u884c\u6bb5\u843d\u8fb9\u754c\u3002",
        "kk": "\u04e8\u04a3\u0434\u0435\u0443\u0434\u0456 \u049b\u043e\u043b\u0434\u0430\u043d\u0443 \u043c\u04af\u043c\u043a\u0456\u043d \u0435\u043c\u0435\u0441: {paragraphs} \u0430\u0431\u0437\u0430\u0446 \u04af\u0448\u0456\u043d {edited} \u04e9\u04a3\u0434\u0435\u043b\u0433\u0435\u043d \u0431\u043b\u043e\u043a. \u0410\u0431\u0437\u0430\u0446 \u0448\u0435\u043a\u0430\u0440\u0430\u043b\u0430\u0440\u044b\u043d \u0431\u043e\u0441 \u0436\u043e\u043b\u0434\u0430\u0440\u043c\u0435\u043d \u0441\u0430\u049b\u0442\u0430\u04a3\u044b\u0437.",
        "uz": "Tahrirlarni qo\u02bblab bo\u02bblmadi: {paragraphs} kitob paragrafi uchun {edited} tahrirlangan blok. Paragraf chegaralarini bo\u02bbsh qatorlar bilan saqlang.",
    },
    "norm.select_file": {
        "en": "Select Book File",
        "ru": "\u0412\u044b\u0431\u0440\u0430\u0442\u044c \u0444\u0430\u0439\u043b \u043a\u043d\u0438\u0433\u0438",
    },

    # ── Roles page ──
    "roles.llm_endpoint": {
        "en": "Local LLM endpoint",
        "ru": "\u0410\u0434\u0440\u0435\u0441 \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0439 LLM",
        "zh": "\u672c\u5730 LLM \u7aef\u70b9",
        "kk": "\u0416\u0435\u0440\u0433\u0456\u043b\u0456\u043a\u0442\u0456 LLM endpoint",
        "uz": "Lokal LLM endpoint",
    },
    "roles.llm_model": {
        "en": "Model profile",
        "ru": "\u041f\u0440\u043e\u0444\u0438\u043b\u044c \u043c\u043e\u0434\u0435\u043b\u0438",
        "zh": "\u6a21\u578b\u914d\u7f6e",
        "kk": "\u041c\u043e\u0434\u0435\u043b\u044c \u043f\u0440\u043e\u0444\u0438\u043b\u0456",
        "uz": "Model profili",
    },
    "roles.extract": {
        "en": "Extract roles and chunks",
        "ru": "\u0418\u0437\u0432\u043b\u0435\u0447\u044c \u0440\u043e\u043b\u0438 \u0438 \u0447\u0430\u043d\u043a\u0438",
        "zh": "\u63d0\u53d6\u89d2\u8272\u548c\u5206\u5757",
        "kk": "\u0420\u04e9\u043b\u0434\u0435\u0440 \u043c\u0435\u043d \u0447\u0430\u043d\u043a\u0442\u0430\u0440\u0434\u044b \u0430\u043b\u0443",
        "uz": "Rollar va bo\u02bblaklarni ajratish",
    },
    "roles.empty": {
        "en": "Normalize a book, then extract roles for audiobook casting.",
        "ru": "\u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u043d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0443\u0439\u0442\u0435 \u043a\u043d\u0438\u0433\u0443, \u0437\u0430\u0442\u0435\u043c \u0438\u0437\u0432\u043b\u0435\u043a\u0438\u0442\u0435 \u0440\u043e\u043b\u0438 \u0434\u043b\u044f \u0430\u0443\u0434\u0438\u043e\u0441\u043f\u0435\u043a\u0442\u0430\u043a\u043b\u044f.",
        "zh": "\u5148\u89c4\u8303\u5316\u4e66\u7a3f\uff0c\u518d\u4e3a\u6709\u58f0\u5267\u63d0\u53d6\u89d2\u8272\u3002",
        "kk": "\u0410\u043b\u0434\u044b\u043c\u0435\u043d \u043a\u0456\u0442\u0430\u043f\u0442\u044b \u043d\u043e\u0440\u043c\u0430\u043b\u0434\u0430\u04a3\u044b\u0437, \u0441\u043e\u0434\u0430\u043d \u043a\u0435\u0439\u0456\u043d \u0430\u0443\u0434\u0438\u043e\u049b\u043e\u0439\u044b\u043b\u044b\u043c \u04af\u0448\u0456\u043d \u0440\u04e9\u043b\u0434\u0435\u0440\u0434\u0456 \u0430\u043b\u044b\u04a3\u044b\u0437.",
        "uz": "Avval kitobni normallashtiring, keyin audiospektakl uchun rollarni ajrating.",
    },
    "roles.ready": {
        "en": "Book is ready. Local LLM will build character roles and segment manifest.",
        "ru": "\u041a\u043d\u0438\u0433\u0430 \u0433\u043e\u0442\u043e\u0432\u0430. \u041b\u043e\u043a\u0430\u043b\u044c\u043d\u0430\u044f LLM \u0441\u043e\u0431\u0435\u0440\u0451\u0442 \u0440\u043e\u043b\u0438 \u0438 segment manifest.",
        "zh": "\u4e66\u7a3f\u5df2\u5c31\u7eea\u3002\u672c\u5730 LLM \u5c06\u6784\u5efa\u89d2\u8272\u548c\u7247\u6bb5\u6e05\u5355\u3002",
        "kk": "\u041a\u0456\u0442\u0430\u043f \u0434\u0430\u0439\u044b\u043d. \u0416\u0435\u0440\u0433\u0456\u043b\u0456\u043a\u0442\u0456 LLM \u0440\u04e9\u043b\u0434\u0435\u0440 \u043c\u0435\u043d segment manifest \u049b\u04b1\u0440\u0430\u0434\u044b.",
        "uz": "Kitob tayyor. Lokal LLM rollar va segment manifestini yaratadi.",
    },
    "roles.extracting": {
        "en": "Extracting roles and smart segments with local LLM...",
        "ru": "\u0418\u0437\u0432\u043b\u0435\u043a\u0430\u0435\u043c \u0440\u043e\u043b\u0438 \u0438 \u0443\u043c\u043d\u044b\u0435 \u0441\u0435\u0433\u043c\u0435\u043d\u0442\u044b \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0439 LLM...",
        "zh": "\u6b63\u5728\u7528\u672c\u5730 LLM \u63d0\u53d6\u89d2\u8272\u548c\u667a\u80fd\u7247\u6bb5...",
        "kk": "\u0416\u0435\u0440\u0433\u0456\u043b\u0456\u043a\u0442\u0456 LLM \u0430\u0440\u049b\u044b\u043b\u044b \u0440\u04e9\u043b\u0434\u0435\u0440 \u043c\u0435\u043d \u0430\u049b\u044b\u043b\u0434\u044b \u0441\u0435\u0433\u043c\u0435\u043d\u0442\u0442\u0435\u0440 \u0430\u043b\u044b\u043d\u044b\u043f \u0436\u0430\u0442\u044b\u0440...",
        "uz": "Lokal LLM bilan rollar va aqlli segmentlar ajratilmoqda...",
    },
    "roles.cache_dialog_title": {
        "en": "Completed role extraction found",
        "ru": "\u0413\u043e\u0442\u043e\u0432\u044b\u0435 \u0440\u043e\u043b\u0438 \u043d\u0430\u0439\u0434\u0435\u043d\u044b",
        "zh": "\u5df2\u627e\u5230\u5b8c\u6210\u7684\u89d2\u8272\u63d0\u53d6",
        "kk": "\u0414\u0430\u0439\u044b\u043d \u0440\u04e9\u043b\u0434\u0435\u0440 \u0442\u0430\u0431\u044b\u043b\u0434\u044b",
        "uz": "Yakunlangan rollar topildi",
    },
    "roles.cache_dialog_text": {
        "en": "Cached roles and chunks already exist for this book and the current settings.",
        "ru": "\u0414\u043b\u044f \u044d\u0442\u043e\u0439 \u043a\u043d\u0438\u0433\u0438 \u0438 \u0442\u0435\u043a\u0443\u0449\u0438\u0445 \u043d\u0430\u0441\u0442\u0440\u043e\u0435\u043a \u0443\u0436\u0435 \u0435\u0441\u0442\u044c \u0438\u0437\u0432\u043b\u0435\u0447\u0451\u043d\u043d\u044b\u0435 \u0440\u043e\u043b\u0438 \u0438 \u0447\u0430\u043d\u043a\u0438.",
        "zh": "\u5f53\u524d\u4e66\u7a3f\u548c\u8bbe\u7f6e\u5df2\u6709\u7f13\u5b58\u7684\u89d2\u8272\u4e0e\u5206\u5757\u3002",
        "kk": "\u041e\u0441\u044b \u043a\u0456\u0442\u0430\u043f \u043f\u0435\u043d \u0430\u0493\u044b\u043c\u0434\u0430\u0493\u044b \u0431\u0430\u043f\u0442\u0430\u0443\u043b\u0430\u0440 \u04af\u0448\u0456\u043d \u0430\u043b\u044b\u043d\u0493\u0430\u043d \u0440\u04e9\u043b\u0434\u0435\u0440 \u043c\u0435\u043d \u0447\u0430\u043d\u043a\u0442\u0430\u0440 \u043a\u0435\u0448\u0442\u0435 \u0431\u0430\u0440.",
        "uz": "Bu kitob va joriy sozlamalar uchun rollar va bo'laklar keshda bor.",
    },
    "roles.cache_dialog_informative": {
        "en": (
            "Restore them from cache to continue immediately with chunk review. "
            "Choose \"Extract again\" only if you want to rerun LLM role markup."
        ),
        "ru": (
            "\u0412\u043e\u0441\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u0435 \u0438\u0445 \u0438\u0437 \u043a\u0435\u0448\u0430, \u0447\u0442\u043e\u0431\u044b \u0441\u0440\u0430\u0437\u0443 \u043f\u0435\u0440\u0435\u0439\u0442\u0438 \u043a \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0435 \u0447\u0430\u043d\u043a\u043e\u0432. "
            "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \"\u0418\u0437\u0432\u043b\u0435\u0447\u044c \u0437\u0430\u043d\u043e\u0432\u043e\", \u0442\u043e\u043b\u044c\u043a\u043e \u0435\u0441\u043b\u0438 \u0445\u043e\u0442\u0438\u0442\u0435 \u043f\u043e\u0432\u0442\u043e\u0440\u043d\u043e \u043f\u0440\u043e\u0433\u043d\u0430\u0442\u044c LLM-\u0440\u0430\u0437\u043c\u0435\u0442\u043a\u0443 \u0440\u043e\u043b\u0435\u0439."
        ),
        "zh": "\u4ece\u7f13\u5b58\u6062\u590d\u5373\u53ef\u7acb\u5373\u8fdb\u5165\u5206\u5757\u68c0\u67e5\u3002\u53ea\u6709\u60f3\u91cd\u65b0\u8fd0\u884c LLM \u89d2\u8272\u6807\u6ce8\u65f6\uff0c\u624d\u9009\u62e9\u201c\u91cd\u65b0\u63d0\u53d6\u201d\u3002",
        "kk": (
            "\u041a\u0435\u0448\u0442\u0435\u043d \u049b\u0430\u043b\u043f\u044b\u043d\u0430 \u043a\u0435\u043b\u0442\u0456\u0440\u0441\u0435\u04a3\u0456\u0437, \u0447\u0430\u043d\u043a\u0442\u0430\u0440\u0434\u044b \u0442\u0435\u043a\u0441\u0435\u0440\u0443\u0433\u0435 \u0431\u0456\u0440\u0434\u0435\u043d \u04e9\u0442\u0435\u0441\u0456\u0437. "
            "LLM \u0430\u0440\u049b\u044b\u043b\u044b \u0440\u04e9\u043b\u0434\u0435\u0440\u0434\u0456 \u049b\u0430\u0439\u0442\u0430 \u0431\u0435\u043b\u0433\u0456\u043b\u0435\u0443 \u049b\u0430\u0436\u0435\u0442 \u0431\u043e\u043b\u0441\u0430 \u0493\u0430\u043d\u0430 \"\u049a\u0430\u0439\u0442\u0430 \u0430\u043b\u0443\" \u0442\u0430\u04a3\u0434\u0430\u04a3\u044b\u0437."
        ),
        "uz": (
            "Keshdan tiklasangiz, bo'laklarni tekshirishga darhol o'tasiz. "
            "LLM orqali rollarni qayta belgilash kerak bo'lsagina \"Qayta ajratish\"ni tanlang."
        ),
    },
    "roles.cache_restore_button": {
        "en": "Restore roles",
        "ru": "\u0412\u043e\u0441\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u044c \u0440\u043e\u043b\u0438",
        "zh": "\u6062\u590d\u89d2\u8272",
        "kk": "\u0420\u04e9\u043b\u0434\u0435\u0440\u0434\u0456 \u049b\u0430\u043b\u043f\u044b\u043d\u0430 \u043a\u0435\u043b\u0442\u0456\u0440\u0443",
        "uz": "Rollarni tiklash",
    },
    "roles.cache_run_fresh_button": {
        "en": "Extract again",
        "ru": "\u0418\u0437\u0432\u043b\u0435\u0447\u044c \u0437\u0430\u043d\u043e\u0432\u043e",
        "zh": "\u91cd\u65b0\u63d0\u53d6",
        "kk": "\u049a\u0430\u0439\u0442\u0430 \u0430\u043b\u0443",
        "uz": "Qayta ajratish",
    },
    "roles.cache_cancel_button": {
        "en": "Cancel",
        "ru": "\u041e\u0442\u043c\u0435\u043d\u0430",
        "zh": "\u53d6\u6d88",
        "kk": "\u0411\u043e\u043b\u0434\u044b\u0440\u043c\u0430\u0443",
        "uz": "Bekor qilish",
    },
    "roles.cache_restored": {
        "en": "Restored roles from cache. Roles: {n}.",
        "ru": "\u0420\u043e\u043b\u0438 \u0432\u043e\u0441\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d\u044b \u0438\u0437 \u043a\u0435\u0448\u0430. \u0420\u043e\u043b\u0435\u0439: {n}.",
        "zh": "\u5df2\u4ece\u7f13\u5b58\u6062\u590d\u89d2\u8272\u3002\u89d2\u8272\u6570\uff1a{n}\u3002",
        "kk": "\u0420\u04e9\u043b\u0434\u0435\u0440 \u043a\u0435\u0448\u0442\u0435\u043d \u049b\u0430\u043b\u043f\u044b\u043d\u0430 \u043a\u0435\u043b\u0442\u0456\u0440\u0456\u043b\u0434\u0456. \u0420\u04e9\u043b\u0434\u0435\u0440: {n}.",
        "uz": "Rollar keshdan tiklandi. Rollar: {n}.",
    },
    "roles.cache_restore_failed": {
        "en": "Could not restore cached roles: {msg}",
        "ru": "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0432\u043e\u0441\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u044c \u0440\u043e\u043b\u0438 \u0438\u0437 \u043a\u0435\u0448\u0430: {msg}",
        "zh": "\u65e0\u6cd5\u6062\u590d\u7f13\u5b58\u89d2\u8272\uff1a{msg}",
        "kk": "\u041a\u0435\u0448\u0442\u0435\u0433\u0456 \u0440\u04e9\u043b\u0434\u0435\u0440\u0434\u0456 \u049b\u0430\u043b\u043f\u044b\u043d\u0430 \u043a\u0435\u043b\u0442\u0456\u0440\u0443 \u043c\u04af\u043c\u043a\u0456\u043d \u0431\u043e\u043b\u043c\u0430\u0434\u044b: {msg}",
        "uz": "Keshlangan rollarni tiklab bo'lmadi: {msg}",
    },
    "roles.done": {
        "en": "Role inventory ready: {n} role(s).",
        "ru": "\u0421\u043f\u0438\u0441\u043e\u043a \u0440\u043e\u043b\u0435\u0439 \u0433\u043e\u0442\u043e\u0432: {n}.",
        "zh": "\u89d2\u8272\u6e05\u5355\u5df2\u5c31\u7eea\uff1a{n} \u4e2a\u89d2\u8272\u3002",
        "kk": "\u0420\u04e9\u043b\u0434\u0435\u0440 \u0442\u0456\u0437\u0456\u043c\u0456 \u0434\u0430\u0439\u044b\u043d: {n}.",
        "uz": "Rollar ro\u02bbyxati tayyor: {n}.",
    },
    "roles.done_with_review": {
        "en": "Role inventory ready: {n} role(s). Some windows used safe source fallback; review report: {path}",
        "ru": "\u0421\u043f\u0438\u0441\u043e\u043a \u0440\u043e\u043b\u0435\u0439 \u0433\u043e\u0442\u043e\u0432: {n}. \u041d\u0435\u043a\u043e\u0442\u043e\u0440\u044b\u0435 \u043e\u043a\u043d\u0430 \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u044b \u0438\u0441\u0445\u043e\u0434\u043d\u044b\u043c \u0442\u0435\u043a\u0441\u0442\u043e\u043c; \u043e\u0442\u0447\u0451\u0442: {path}",
        "zh": "\u89d2\u8272\u6e05\u5355\u5df2\u5c31\u7eea\uff1a{n} \u4e2a\u89d2\u8272\u3002\u90e8\u5206\u7a97\u53e3\u4f7f\u7528\u5b89\u5168\u539f\u6587\u56de\u9000\uff1b\u62a5\u544a\uff1a{path}",
        "kk": "\u0420\u04e9\u043b\u0434\u0435\u0440 \u0442\u0456\u0437\u0456\u043c\u0456 \u0434\u0430\u0439\u044b\u043d: {n}. \u041a\u0435\u0439\u0431\u0456\u0440 \u0442\u0435\u0440\u0435\u0437\u0435\u043b\u0435\u0440 \u0431\u0430\u0441\u0442\u0430\u043f\u049b\u044b \u043c\u04d9\u0442\u0456\u043d\u043c\u0435\u043d \u0441\u0430\u049b\u0442\u0430\u043b\u0434\u044b; \u0435\u0441\u0435\u043f: {path}",
        "uz": "Rollar ro\u02bbyxati tayyor: {n}. Ayrim oynalar asl matn bilan saqlandi; hisobot: {path}",
    },
    "roles.summary": {
        "en": "{roles} role(s), {speech} direct-speech segment(s), {segments} total segment(s).",
        "ru": "{roles} \u0440\u043e\u043b\u0435\u0439, {speech} \u0441\u0435\u0433\u043c\u0435\u043d\u0442\u043e\u0432 \u043f\u0440\u044f\u043c\u043e\u0439 \u0440\u0435\u0447\u0438, {segments} \u0441\u0435\u0433\u043c\u0435\u043d\u0442\u043e\u0432 \u0432\u0441\u0435\u0433\u043e.",
        "zh": "{roles} \u4e2a\u89d2\u8272\uff0c{speech} \u4e2a\u76f4\u63a5\u8bed\u97f3\u7247\u6bb5\uff0c\u5171 {segments} \u4e2a\u7247\u6bb5\u3002",
        "kk": "{roles} \u0440\u04e9\u043b, {speech} \u0442\u0456\u043a\u0435\u043b\u0435\u0439 \u0441\u04e9\u0437 \u0441\u0435\u0433\u043c\u0435\u043d\u0442\u0456, \u0431\u0430\u0440\u043b\u044b\u0493\u044b {segments} \u0441\u0435\u0433\u043c\u0435\u043d\u0442.",
        "uz": "{roles} rol, {speech} to\u02bbg\u02bbridan-to\u02bbg\u02bbri nutq segmenti, jami {segments} segment.",
    },
    "roles.error": {
        "en": "Role extraction failed: {msg}",
        "ru": "\u0418\u0437\u0432\u043b\u0435\u0447\u0435\u043d\u0438\u0435 \u0440\u043e\u043b\u0435\u0439 \u043d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c: {msg}",
        "zh": "\u89d2\u8272\u63d0\u53d6\u5931\u8d25\uff1a{msg}",
        "kk": "\u0420\u04e9\u043b\u0434\u0435\u0440\u0434\u0456 \u0430\u043b\u0443 \u0441\u04d9\u0442\u0441\u0456\u0437: {msg}",
        "uz": "Rollarni ajratib bo\u02bblmadi: {msg}",
    },
    "roles.col_role": {
        "en": "Role",
        "ru": "\u0420\u043e\u043b\u044c",
        "zh": "\u89d2\u8272",
        "kk": "\u0420\u04e9\u043b",
        "uz": "Rol",
    },
    "roles.col_description": {
        "en": "Description",
        "ru": "\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435",
        "zh": "\u63cf\u8ff0",
        "kk": "\u0421\u0438\u043f\u0430\u0442\u0442\u0430\u043c\u0430",
        "uz": "Tavsif",
    },
    "roles.col_description_short": {
        "en": "Desc.",
        "ru": "Опис.",
        "zh": "描述",
        "kk": "Сип.",
        "uz": "Tavs.",
    },
    "roles.col_speech": {
        "en": "Direct speech",
        "ru": "\u041f\u0440\u044f\u043c\u0430\u044f \u0440\u0435\u0447\u044c",
        "zh": "\u76f4\u63a5\u5bf9\u8bdd",
        "kk": "\u0422\u0456\u043a\u0435\u043b\u0435\u0439 \u0441\u04e9\u0437",
        "uz": "Bevosita nutq",
    },
    "roles.col_speech_short": {
        "en": "Speech",
        "ru": "Речь",
        "zh": "台词",
        "kk": "Сөз",
        "uz": "Nutq",
    },
    "roles.col_emotions": {
        "en": "Emotion spectrum",
        "ru": "\u042d\u043c\u043e\u0446\u0438\u0438",
        "zh": "\u60c5\u7eea\u9891\u8c31",
        "kk": "\u042d\u043c\u043e\u0446\u0438\u044f\u043b\u0430\u0440",
        "uz": "Hissiyotlar",
    },
    "roles.col_emotions_short": {
        "en": "Emotions",
        "ru": "Эмоции",
        "zh": "情绪",
        "kk": "Эмоц.",
        "uz": "Hiss.",
    },
    "roles.col_segments": {
        "en": "Segments",
        "ru": "\u0421\u0435\u0433\u043c\u0435\u043d\u0442\u044b",
        "zh": "\u7247\u6bb5",
        "kk": "\u0421\u0435\u0433\u043c\u0435\u043d\u0442\u0442\u0435\u0440",
        "uz": "Segmentlar",
    },
    "roles.col_segments_short": {
        "en": "Seg.",
        "ru": "Сегм.",
        "zh": "片段",
        "kk": "Сегм.",
        "uz": "Seg.",
    },

    # ── Voices page ──
    "voice.speaker_mode": {
        "en": "Segment source:",
        "ru": "\u0418\u0441\u0442\u043e\u0447\u043d\u0438\u043a \u0441\u0435\u0433\u043c\u0435\u043d\u0442\u043e\u0432:",
    },
    "voice.speaker_mode_heuristic": {
        "en": "Rules: quick split",
        "ru": "\u041f\u0440\u0430\u0432\u0438\u043b\u0430: \u0431\u044b\u0441\u0442\u0440\u043e\u0435 \u0440\u0430\u0437\u0431\u0438\u0435\u043d\u0438\u0435",
    },
    "voice.speaker_mode_llm": {
        "en": "LLM: roles and scenes",
        "ru": "LLM: \u0440\u043e\u043b\u0438 \u0438 \u0441\u0446\u0435\u043d\u044b",
    },
    "voice.speaker_mode_manual": {
        "en": "Manual manifest",
        "ru": "\u0420\u0443\u0447\u043d\u043e\u0439 \u043c\u0430\u043d\u0438\u0444\u0435\u0441\u0442",
    },
    "voice.speaker_mode_hint": {
        "en": (
            "Rules: quick split - builds a local draft from punctuation and "
            "dialogue marks. No network.\n"
            "LLM: roles and scenes - asks the local model to preserve text, "
            "split scenes, and label roles.\n"
            "Manual manifest - load or create segments, then edit text, roles, "
            "and voices in the table."
        ),
        "ru": (
            "\u041f\u0440\u0430\u0432\u0438\u043b\u0430: \u0431\u044b\u0441\u0442\u0440\u043e\u0435 \u0440\u0430\u0437\u0431\u0438\u0435\u043d\u0438\u0435 - \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0439 \u0447\u0435\u0440\u043d\u043e\u0432\u0438\u043a \u043f\u043e \u043f\u0443\u043d\u043a\u0442\u0443\u0430\u0446\u0438\u0438 "
            "\u0438 \u043a\u0430\u0432\u044b\u0447\u043a\u0430\u043c. \u0411\u0435\u0437 \u0441\u0435\u0442\u0438.\n"
            "LLM: \u0440\u043e\u043b\u0438 \u0438 \u0441\u0446\u0435\u043d\u044b - \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u0430\u044f \u043c\u043e\u0434\u0435\u043b\u044c \u0441\u043e\u0445\u0440\u0430\u043d\u044f\u0435\u0442 \u0442\u0435\u043a\u0441\u0442, "
            "\u0434\u0435\u043b\u0438\u0442 \u043d\u0430 \u0441\u0446\u0435\u043d\u044b \u0438 \u0440\u0430\u0437\u043c\u0435\u0447\u0430\u0435\u0442 \u0440\u043e\u043b\u0438.\n"
            "\u0420\u0443\u0447\u043d\u043e\u0439 \u043c\u0430\u043d\u0438\u0444\u0435\u0441\u0442 - \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u0435 \u0438\u043b\u0438 \u0441\u043e\u0437\u0434\u0430\u0439\u0442\u0435 \u0441\u0435\u0433\u043c\u0435\u043d\u0442\u044b, "
            "\u0437\u0430\u0442\u0435\u043c \u043f\u0440\u0430\u0432\u044c\u0442\u0435 \u0442\u0435\u043a\u0441\u0442, \u0440\u043e\u043b\u0438 \u0438 \u0433\u043e\u043b\u043e\u0441\u0430 \u0432 \u0442\u0430\u0431\u043b\u0438\u0446\u0435."
        ),
    },
    "voice.speaker_mode_hint_inline_heuristic": {
        "en": "Fast local draft from punctuation and dialogue marks.",
        "ru": "\u0411\u044b\u0441\u0442\u0440\u044b\u0439 \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0439 \u0447\u0435\u0440\u043d\u043e\u0432\u0438\u043a \u043f\u043e \u043f\u0443\u043d\u043a\u0442\u0443\u0430\u0446\u0438\u0438 \u0438 \u043a\u0430\u0432\u044b\u0447\u043a\u0430\u043c.",
        "zh": "\u57fa\u4e8e\u6807\u70b9\u548c\u5bf9\u8bdd\u7b26\u53f7\u7684\u672c\u673a\u5feb\u901f\u8349\u7a3f\u3002",
        "kk": "\u0422\u044b\u043d\u044b\u0441 \u0431\u0435\u043b\u0433\u0456\u043b\u0435\u0440\u0456 \u043c\u0435\u043d \u0442\u044b\u0440\u043d\u0430\u049b\u0448\u0430\u0493\u0430 \u0441\u04af\u0439\u0435\u043d\u0433\u0435\u043d \u0436\u044b\u043b\u0434\u0430\u043c \u0436\u0435\u0440\u0433\u0456\u043b\u0456\u043a\u0442\u0456 \u043d\u04b1\u0441\u049b\u0430.",
        "uz": "Tinish belgilari va qo'shtirnoqlardan tez lokal qoralama.",
    },
    "voice.speaker_mode_hint_inline_llm": {
        "en": "Local LLM preserves text, splits scenes, and labels roles.",
        "ru": "\u041b\u043e\u043a\u0430\u043b\u044c\u043d\u0430\u044f LLM \u0441\u043e\u0445\u0440\u0430\u043d\u044f\u0435\u0442 \u0442\u0435\u043a\u0441\u0442, \u0441\u0446\u0435\u043d\u044b \u0438 \u0440\u043e\u043b\u0438.",
        "zh": "\u672c\u673a LLM \u4fdd\u7559\u6587\u672c\uff0c\u5212\u5206\u573a\u666f\u5e76\u6807\u6ce8\u89d2\u8272\u3002",
        "kk": "\u0416\u0435\u0440\u0433\u0456\u043b\u0456\u043a\u0442\u0456 LLM \u043c\u04d9\u0442\u0456\u043d\u0434\u0456, \u043a\u04e9\u0440\u0456\u043d\u0456\u0441\u0442\u0456 \u0436\u04d9\u043d\u0435 \u0440\u04e9\u043b\u0434\u0435\u0440\u0434\u0456 \u0441\u0430\u049b\u0442\u0430\u0439\u0434\u044b.",
        "uz": "Lokal LLM matnni saqlaydi, sahnalar va rollarni belgilaydi.",
    },
    "voice.speaker_mode_hint_inline_manual": {
        "en": "Load or create segments, then edit text, roles, and voices.",
        "ru": "\u0417\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u0435 \u0438\u043b\u0438 \u0441\u043e\u0437\u0434\u0430\u0439\u0442\u0435 \u0441\u0435\u0433\u043c\u0435\u043d\u0442\u044b, \u0437\u0430\u0442\u0435\u043c \u043f\u0440\u0430\u0432\u044c\u0442\u0435 \u0440\u043e\u043b\u0438.",
        "zh": "\u52a0\u8f7d\u6216\u521b\u5efa\u5206\u6bb5\uff0c\u7136\u540e\u7f16\u8f91\u6587\u672c\u3001\u89d2\u8272\u548c\u58f0\u97f3\u3002",
        "kk": "\u0421\u0435\u0433\u043c\u0435\u043d\u0442\u0442\u0435\u0440\u0434\u0456 \u0436\u04af\u043a\u0442\u0435\u043f \u043d\u0435 \u0436\u0430\u0441\u0430\u043f, \u043c\u04d9\u0442\u0456\u043d \u043c\u0435\u043d \u0440\u04e9\u043b\u0434\u0435\u0440\u0434\u0456 \u0442\u04af\u0437\u0435\u0442\u0456\u04a3\u0456\u0437.",
        "uz": "Segmentlarni yuklang yoki yarating, keyin matn va rollarni tahrirlang.",
    },
    "voice.max_chunk": {
        "en": "Max Chunk Chars:",
        "ru": "Макс. символов в чанке:",
    },
    "voice.max_chunk_hint": {
        "en": (
            "Soft chunk size limit. Splitting prefers sentence and clause "
            "boundaries and never cuts inside a word."
        ),
        "ru": (
            "Мягкий лимит размера чанка. Разбиение старается идти по "
            "предложениям и фразам и не режет слова."
        ),
    },
    "voice.stress_mode": {
        "en": "TTS Stress Hints:",
        "ru": "\u0423\u0434\u0430\u0440\u0435\u043d\u0438\u044f \u0434\u043b\u044f TTS:",
    },
    "voice.stress_mode_double": {
        "en": "Double stressed vowel",
        "ru": "\u0423\u0434\u0432\u0430\u0438\u0432\u0430\u0442\u044c \u0443\u0434\u0430\u0440\u043d\u0443\u044e \u0433\u043b\u0430\u0441\u043d\u0443\u044e",
    },
    "voice.stress_mode_acute": {
        "en": "Keep acute mark",
        "ru": "\u041e\u0441\u0442\u0430\u0432\u0438\u0442\u044c U+0301",
    },
    "voice.stress_mode_plain": {
        "en": "No stress hints",
        "ru": "\u0411\u0435\u0437 \u043f\u043e\u0434\u0441\u043a\u0430\u0437\u043e\u043a",
    },
    "voice.stress_mode_hint": {
        "en": (
            "How stress marks are rendered in TTS manifests. Double-vowel "
            "mode turns zamo\u0301k into zamook-like hints while keeping source "
            "text unchanged."
        ),
        "ru": (
            "\u041a\u0430\u043a \u0443\u0434\u0430\u0440\u0435\u043d\u0438\u044f \u043f\u043e\u043f\u0430\u0434\u0430\u044e\u0442 \u0432 TTS-\u043c\u0430\u043d\u0438\u0444\u0435\u0441\u0442. "
            "\u0420\u0435\u0436\u0438\u043c \u0443\u0434\u0432\u043e\u0435\u043d\u0438\u044f \u0434\u0435\u043b\u0430\u0435\u0442 \u0437\u0430\u0301\u043c\u043e\u043a -> \u0437\u0430\u0430\u043c\u043e\u043a "
            "\u0438 \u0437\u0430\u043c\u043e\u0301\u043a -> \u0437\u0430\u043c\u043e\u043e\u043a, \u043d\u0435 \u043c\u0435\u043d\u044f\u044f \u0442\u0435\u043a\u0441\u0442 \u043a\u043d\u0438\u0433\u0438."
        ),
    },
    "voice.detect": {
        "en": "Rebuild segments",
        "ru": "Пересобрать сегменты",
    },
    "voice.build_chunks": {
        "en": "Build TTS Chunks",
        "ru": "Собрать чанки для TTS",
    },
    "voice.load_manifest": {
        "en": "Load",
        "ru": "Загрузить",
    },
    "voice.load_manifest_tip": {
        "en": "Load a saved segment manifest.",
        "ru": "Загрузить сохранённый манифест сегментов.",
    },
    "voice.save_manifest": {
        "en": "Save",
        "ru": "Сохранить",
    },
    "voice.save_manifest_tip": {
        "en": "Save current segment and voice assignments.",
        "ru": "Сохранить текущие сегменты и назначения голосов.",
    },
    "voice.all_narrator": {
        "en": "All \u2192 Narrator",
        "ru": "Все \u2192 Диктор",
    },
    "voice.all_male": {
        "en": "All \u2192 Male Confident",
        "ru": "Все \u2192 Муж. уверенный",
    },
    "voice.all_female": {
        "en": "All \u2192 Female Warm",
        "ru": "Все \u2192 Жен. тёплый",
    },
    "voice.auto_detect": {
        "en": "Auto-detect",
        "ru": "Авто-определить",
    },
    "voice.apply_all": {
        "en": "\u2192 All",
        "ru": "\u2192 Все",
    },
    "voice.apply_dialogue": {
        "en": "\u2192 Dialogue only",
        "ru": "\u2192 Только речь",
    },
    "voice.apply_narrator": {
        "en": "\u2192 Narrator only",
        "ru": "\u2192 Только автор",
    },
    "voice.save": {"en": "Save", "ru": "Сохранить"},
    "voice.col_num": {"en": "#", "ru": "#"},
    "voice.col_type": {"en": "Type", "ru": "Тип"},
    "voice.col_chapter": {"en": "Ch.", "ru": "Гл."},
    "voice.col_chunk": {"en": "Chunk", "ru": "Чанк"},
    "voice.col_text": {
        "en": "Text Preview",
        "ru": "Превью текста",
    },
    "voice.col_role": {
        "en": "Role",
        "ru": "Роль",
        "zh": "角色",
        "kk": "Рөл",
        "uz": "Rol",
    },
    "voice.col_role_tip": {
        "en": "Character or system role for this chunk. You can type a corrected character name.",
        "ru": "Персонаж или системная роль чанка. Можно вписать исправленное имя.",
        "zh": "此分块的人物或系统角色。可以输入更正后的人物名。",
        "kk": "Чанктың кейіпкері не жүйелік рөлі. Түзетілген атын жазуға болады.",
        "uz": "Bu bo‘lakdagi personaj yoki tizimli rol. Tuzatilgan personaj nomini yozish mumkin.",
    },
    "voice.role_narrator": {
        "en": "Narrator",
        "ru": "Диктор",
        "zh": "旁白",
        "kk": "Диктор",
        "uz": "Hikoyachi",
    },
    "voice.role_male": {
        "en": "Male character",
        "ru": "Мужской персонаж",
        "zh": "男性角色",
        "kk": "Ер кейіпкер",
        "uz": "Erkak personaj",
    },
    "voice.role_female": {
        "en": "Female character",
        "ru": "Женский персонаж",
        "zh": "女性角色",
        "kk": "Әйел кейіпкер",
        "uz": "Ayol personaj",
    },
    "voice.role_unknown": {
        "en": "Unknown speaker",
        "ru": "Неизвестный говорящий",
        "zh": "未知说话人",
        "kk": "Белгісіз сөйлеуші",
        "uz": "Noma'lum so'zlovchi",
    },
    "voice.role_annotation": {
        "en": "Annotation",
        "ru": "Аннотация",
        "zh": "内容简介",
        "kk": "Аннотация",
        "uz": "Annotatsiya",
    },
    "voice.role_preface": {
        "en": "Preface",
        "ru": "Предисловие",
        "zh": "序言",
        "kk": "Алғысөз",
        "uz": "So'zboshi",
    },
    "voice.role_epilogue": {
        "en": "Epilogue",
        "ru": "Эпилог",
        "zh": "后记",
        "kk": "Эпилог",
        "uz": "Epilog",
    },
    "voice.role_chapter_title": {
        "en": "Chapter title",
        "ru": "Название главы",
        "zh": "章节标题",
        "kk": "Тарау аты",
        "uz": "Bob sarlavhasi",
    },
    "voice.col_voice": {"en": "Voice", "ru": "Голос"},
    "voice.col_intonation": {
        "en": "Intonation",
        "ru": "Интонация",
    },
    "voice.col_audio": {"en": "Audio", "ru": "Аудио"},
    "voice.col_retry": {"en": "Retry", "ru": "Повтор"},
    "voice.col_action": {
        "en": "Action",
        "ru": "\u0423\u0434\u0430\u043b\u0438\u0442\u044c",
        "zh": "\u64cd\u4f5c",
        "kk": "\u04d8\u0440\u0435\u043a\u0435\u0442",
        "uz": "Amal",
    },
    "voice.play_audio": {"en": "Play", "ru": "Play"},
    "voice.mark_retry": {"en": "Retry", "ru": "Повтор"},
    "voice.row_delete_tip": {
        "en": "Exclude this chunk from TTS output.",
        "ru": "\u0418\u0441\u043a\u043b\u044e\u0447\u0438\u0442\u044c \u044d\u0442\u043e\u0442 \u0447\u0430\u043d\u043a \u0438\u0437 TTS-\u0441\u0431\u043e\u0440\u043a\u0438.",
        "zh": "\u4ece TTS \u8f93\u51fa\u4e2d\u6392\u9664\u6b64\u5206\u5757\u3002",
        "kk": "\u0411\u04b1\u043b \u0447\u0430\u043d\u043a\u0442\u044b TTS \u0436\u0438\u043d\u0430\u0443\u044b\u043d\u0430\u043d \u0430\u043b\u044b\u043f \u0442\u0430\u0441\u0442\u0430\u0443.",
        "uz": "Bu bo'lakni TTS chiqishidan chiqarish.",
    },
    "voice.row_restore_tip": {
        "en": "Include this chunk in TTS output again.",
        "ru": "\u0421\u043d\u043e\u0432\u0430 \u0432\u043a\u043b\u044e\u0447\u0438\u0442\u044c \u044d\u0442\u043e\u0442 \u0447\u0430\u043d\u043a \u0432 TTS-\u0441\u0431\u043e\u0440\u043a\u0443.",
        "zh": "\u91cd\u65b0\u5c06\u6b64\u5206\u5757\u52a0\u5165 TTS \u8f93\u51fa\u3002",
        "kk": "\u0411\u04b1\u043b \u0447\u0430\u043d\u043a\u0442\u044b TTS \u0436\u0438\u043d\u0430\u0443\u044b\u043d\u0430 \u049b\u0430\u0439\u0442\u0430 \u049b\u043e\u0441\u0443.",
        "uz": "Bu bo'lakni TTS chiqishiga qayta qo'shish.",
    },
    "voice.editor_segment_tab": {
        "en": "Segment Editor",
        "ru": "\u0421\u0435\u0433\u043c\u0435\u043d\u0442",
    },
    "voice.editor_full_tab": {
        "en": "Full Text",
        "ru": "\u0412\u0435\u0441\u044c \u0442\u0435\u043a\u0441\u0442",
    },
    "voice.editor_segment_title": {
        "en": "Selected segment text",
        "ru": "\u0422\u0435\u043a\u0441\u0442 \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u043e\u0433\u043e \u0441\u0435\u0433\u043c\u0435\u043d\u0442\u0430",
    },
    "voice.editor_segment_placeholder": {
        "en": "Select a row and edit the exact text that will be chunked for TTS.",
        "ru": "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0441\u0442\u0440\u043e\u043a\u0443 \u0438 \u043f\u0440\u0430\u0432\u044c\u0442\u0435 \u0442\u043e\u0447\u043d\u044b\u0439 \u0442\u0435\u043a\u0441\u0442 \u0434\u043b\u044f TTS.",
    },
    "voice.editor_split": {
        "en": "Split",
        "ru": "\u0420\u0430\u0437\u0434\u0435\u043b\u0438\u0442\u044c",
    },
    "voice.editor_split_tip": {
        "en": "Split the selected segment at the text cursor.",
        "ru": "\u0420\u0430\u0437\u0434\u0435\u043b\u0438\u0442\u044c \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u044b\u0439 \u0441\u0435\u0433\u043c\u0435\u043d\u0442 \u043f\u043e \u043a\u0443\u0440\u0441\u043e\u0440\u0443.",
    },
    "voice.editor_merge_next": {
        "en": "Merge next",
        "ru": "\u0421\u043a\u043b\u0435\u0438\u0442\u044c \u0441\u043e \u0441\u043b\u0435\u0434.",
    },
    "voice.editor_delete_empty": {
        "en": "Delete if empty",
        "ru": "\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u043f\u0443\u0441\u0442\u043e\u0439",
    },
    "voice.editor_delete": {
        "en": "Delete",
        "ru": "\u0423\u0434\u0430\u043b\u0438\u0442\u044c",
        "zh": "\u5220\u9664",
        "kk": "\u0416\u043e\u044e",
        "uz": "O\u02bbchirish",
    },
    "voice.editor_restore": {
        "en": "Undo delete",
        "ru": "\u0412\u0435\u0440\u043d\u0443\u0442\u044c",
        "zh": "\u64a4\u9500\u5220\u9664",
        "kk": "\u049a\u0430\u0439\u0442\u0430\u0440\u0443",
        "uz": "Qaytarish",
    },
    "voice.editor_full_title": {
        "en": "Whole text before chunking",
        "ru": "\u0412\u0435\u0441\u044c \u0442\u0435\u043a\u0441\u0442 \u043f\u0435\u0440\u0435\u0434 \u0447\u0430\u043d\u043a\u0430\u043c\u0438",
    },
    "voice.editor_full_placeholder": {
        "en": "Segments are separated by blank lines. Apply back when you want to rebuild the segment list from this text.",
        "ru": "\u0421\u0435\u0433\u043c\u0435\u043d\u0442\u044b \u0440\u0430\u0437\u0434\u0435\u043b\u044f\u044e\u0442\u0441\u044f \u043f\u0443\u0441\u0442\u043e\u0439 \u0441\u0442\u0440\u043e\u043a\u043e\u0439. \u041f\u0440\u0438\u043c\u0435\u043d\u0438\u0442\u0435, \u0447\u0442\u043e\u0431\u044b \u043f\u0435\u0440\u0435\u0441\u043e\u0431\u0440\u0430\u0442\u044c \u0441\u0435\u0433\u043c\u0435\u043d\u0442\u044b.",
    },
    "voice.editor_refresh_full": {
        "en": "Refresh from rows",
        "ru": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c \u0438\u0437 \u0441\u0442\u0440\u043e\u043a",
    },
    "voice.editor_apply_full": {
        "en": "Apply to segments",
        "ru": "\u041f\u0440\u0438\u043c\u0435\u043d\u0438\u0442\u044c \u043a \u0441\u0435\u0433\u043c\u0435\u043d\u0442\u0430\u043c",
    },
    "voice.editor_chars": {
        "en": "{chars} chars",
        "ru": "{chars} \u0441\u0438\u043c\u0432.",
    },
    "voice.editor_full_stats": {
        "en": "{segments} blocks, {chars} chars",
        "ru": "{segments} \u0431\u043b\u043e\u043a\u043e\u0432, {chars} \u0441\u0438\u043c\u0432.",
    },
    "voice.type_speech": {"en": "Speech", "ru": "Речь"},
    "voice.type_narrator": {"en": "Narr.", "ru": "Автор"},
    "voice.type_deleted": {
        "en": "Deleted",
        "ru": "\u0423\u0434\u0430\u043b\u0451\u043d",
        "zh": "\u5df2\u5220\u9664",
        "kk": "\u0416\u043e\u0439\u044b\u043b\u0493\u0430\u043d",
        "uz": "O\u02bbchirilgan",
    },
    "voice.chapter_filter": {
        "en": "Chapter:",
        "ru": "\u0413\u043b\u0430\u0432\u0430:",
        "zh": "\u7ae0\u8282\uff1a",
        "kk": "\u0422\u0430\u0440\u0430\u0443:",
        "uz": "Bob:",
    },
    "voice.prev_segment": {
        "en": "Prev",
        "ru": "\u041d\u0430\u0437\u0430\u0434",
        "zh": "Prev",
        "kk": "Prev",
        "uz": "Prev",
    },
    "voice.prev_segment_tip": {
        "en": "Select the previous visible segment.",
        "ru": "\u041f\u0435\u0440\u0435\u0439\u0442\u0438 \u043a \u043f\u0440\u0435\u0434\u044b\u0434\u0443\u0449\u0435\u043c\u0443 \u0432\u0438\u0434\u0438\u043c\u043e\u043c\u0443 \u0441\u0435\u0433\u043c\u0435\u043d\u0442\u0443.",
        "zh": "Select the previous visible segment.",
        "kk": "Select the previous visible segment.",
        "uz": "Select the previous visible segment.",
    },
    "voice.next_segment": {
        "en": "Next",
        "ru": "\u0414\u0430\u043b\u044c\u0448\u0435",
        "zh": "Next",
        "kk": "Next",
        "uz": "Next",
    },
    "voice.next_segment_tip": {
        "en": "Select the next visible segment.",
        "ru": "\u041f\u0435\u0440\u0435\u0439\u0442\u0438 \u043a \u0441\u043b\u0435\u0434\u0443\u044e\u0449\u0435\u043c\u0443 \u0432\u0438\u0434\u0438\u043c\u043e\u043c\u0443 \u0441\u0435\u0433\u043c\u0435\u043d\u0442\u0443.",
        "zh": "Select the next visible segment.",
        "kk": "Select the next visible segment.",
        "uz": "Select the next visible segment.",
    },
    "voice.chapter_all": {
        "en": "All chapters",
        "ru": "\u0412\u0441\u0435 \u0433\u043b\u0430\u0432\u044b",
        "zh": "\u6240\u6709\u7ae0\u8282",
        "kk": "\u0411\u0430\u0440\u043b\u044b\u049b \u0442\u0430\u0440\u0430\u0443",
        "uz": "Barcha boblar",
    },
    "voice.chapter_item": {
        "en": "Chapter {chapter}",
        "ru": "\u0413\u043b\u0430\u0432\u0430 {chapter}",
        "zh": "\u7b2c {chapter} \u7ae0",
        "kk": "{chapter}-\u0442\u0430\u0440\u0430\u0443",
        "uz": "{chapter}-bob",
    },
    "voice.stats_segments": {
        "en": "{total} segments | Speech: {speech} | Narrator: {narr}",
        "ru": "{total} сегментов | Речь: {speech} | Автор: {narr}",
    },
    "voice.stats": {
        "en": "Total: {total} chunks | Narrator: {narrator} "
              "| Male: {male} | Female: {female}",
        "ru": "Всего: {total} чанков | Диктор: {narrator} "
              "| Муж.: {male} | Жен.: {female}",
    },
    "voice.detecting": {
        "en": "Building smart segments\u2026",
        "ru": "Собираем умные сегменты\u2026",
    },
    "voice.detecting_dialogue": {
        "en": "Reading dialogue boundaries\u2026",
        "ru": "Читаем границы диалогов\u2026",
    },
    "voice.attributing": {
        "en": "Assigning roles ({mode})\u2026",
        "ru": "Размечаем роли ({mode})\u2026",
    },
    "voice.extracting_segments": {
        "en": "Extracting segments\u2026",
        "ru": "Извлечение сегментов\u2026",
    },
    "voice.exported_segments": {
        "en": "Exported {n} segments",
        "ru": "Экспортировано {n} сегментов",
    },
    "voice.chunking": {
        "en": "Chunking\u2026",
        "ru": "Разбиение на чанки\u2026",
    },
    "voice.exported_chunks": {
        "en": "Exported {n} chunks",
        "ru": "Экспортировано {n} чанков",
    },
    "voice.building_chunks": {
        "en": "Building TTS chunks from {n} segments\u2026",
        "ru": "Собираем TTS-чанки из {n} сегментов\u2026",
    },
    "voice.segments_ready": {
        "en": "\u2714 {n} segments ready. Review roles and text, then click "
              "'Build TTS Chunks'.",
        "ru": "\u2714 {n} сегментов готово. Проверьте роли и текст, "
              "затем нажмите \u00abСобрать чанки для TTS\u00bb.",
    },
    "voice.chunks_done": {
        "en": "\u2714 Built {n} TTS chunks! "
              "Go to the Voices tab to choose or train voices.",
        "ru": "\u2714 Собрано {n} TTS-чанков! "
              "Перейдите на вкладку \u00abГолоса\u00bb, чтобы выбрать или обучить голоса.",
    },
    "voice.saved": {
        "en": "\u2714 Saved: {path}",
        "ru": "\u2714 Сохранено: {path}",
    },
    "voice.manifest_path": {
        "en": "Manifest: {path}",
        "ru": "Манифест: {path}",
    },
    # ── Intonation labels ──
    "inton.neutral": {"en": "Neutral", "ru": "Нейтральная"},
    "inton.calm": {"en": "Calm", "ru": "Спокойная"},
    "inton.excited": {"en": "Excited", "ru": "Взволнованная"},
    "inton.joyful": {"en": "Joyful", "ru": "Радостная"},
    "inton.sad": {"en": "Sad", "ru": "Грустная"},
    "inton.angry": {"en": "Angry", "ru": "Злая"},
    "inton.whisper": {"en": "Whisper", "ru": "Шёпот"},
    # ── LLM config ──
    "voice.llm_provider": {
        "en": "LLM Provider:",
        "ru": "LLM провайдер:",
    },
    "voice.llm_local": {"en": "Local (Ollama)", "ru": "Локальный (Ollama)"},
    "voice.llm_openai": {"en": "OpenAI (ChatGPT)", "ru": "OpenAI (ChatGPT)"},
    "voice.llm_endpoint": {
        "en": "Endpoint (ip:port):",
        "ru": "Адрес (ip:порт):",
    },
    "voice.llm_model": {"en": "LLM Model:", "ru": "LLM Модель:"},
    "voice.llm_api_key": {
        "en": "OpenAI API Key:",
        "ru": "OpenAI API ключ:",
    },
    "voice.generate_previews": {
        "en": "Generate Previews",
        "ru": "Сгенерировать превью",
    },
    "voice.refresh_previews": {
        "en": "Refresh",
        "ru": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c",
    },
    "voice.no_previews": {
        "en": "No previews generated yet. Click 'Generate' to create samples.",
        "ru": "\u041f\u0440\u0435\u0432\u044c\u044e \u043d\u0435 \u0441\u0433\u0435\u043d\u0435\u0440\u0438\u0440\u043e\u0432\u0430\u043d\u044b. \u041d\u0430\u0436\u043c\u0438\u0442\u0435 \u00ab\u0421\u0433\u0435\u043d\u0435\u0440\u0438\u0440\u043e\u0432\u0430\u0442\u044c\u00bb.",
    },
    "voice.previews_ready": {
        "en": "{count}/{total} voice previews ready",
        "ru": "{count}/{total} \u043f\u0440\u0435\u0432\u044c\u044e \u0433\u043e\u0442\u043e\u0432\u044b",
    },
    "voice.saved_custom_desc": {
        "en": "Reusable CustomVoice saved in the voice library.",
        "ru": "\u0421\u043e\u0445\u0440\u0430\u043d\u0451\u043d\u043d\u044b\u0439 CustomVoice \u0438\u0437 \u0431\u0438\u0431\u043b\u0438\u043e\u0442\u0435\u043a\u0438 \u0433\u043e\u043b\u043e\u0441\u043e\u0432.",
        "zh": "保存在声音库中的可复用 CustomVoice。",
        "kk": "Дауыс кітапханасында сақталған қайта қолданылатын CustomVoice.",
        "uz": "Ovoz kutubxonasida saqlangan qayta ishlatiladigan CustomVoice.",
    },
    "voice.saved_custom_speaker": {
        "en": "saved: {voice}",
        "ru": "\u0441\u043e\u0445\u0440\u0430\u043d\u0451\u043d: {voice}",
        "zh": "已保存：{voice}",
        "kk": "сақталған: {voice}",
        "uz": "saqlandi: {voice}",
    },
    "voice.generating_previews": {
        "en": "Generating previews locally (this takes a few minutes)\u2026",
        "ru": "\u0413\u0435\u043d\u0435\u0440\u0430\u0446\u0438\u044f \u043f\u0440\u0435\u0432\u044c\u044e \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e (\u044d\u0442\u043e \u0437\u0430\u0439\u043c\u0451\u0442 \u043d\u0435\u0441\u043a\u043e\u043b\u044c\u043a\u043e \u043c\u0438\u043d\u0443\u0442)\u2026",
    },
    "voice.preview_panel": {
        "en": "Voice Library",
        "ru": "\u0411\u0438\u0431\u043b\u0438\u043e\u0442\u0435\u043a\u0430 \u0433\u043e\u043b\u043e\u0441\u043e\u0432",
    },
    "voice.settings_panel": {
        "en": "Voice Markup",
        "ru": "\u0420\u0430\u0437\u043c\u0435\u0442\u043a\u0430",
    },
    "chunks.settings_panel": {
        "en": "Chunk Review",
        "ru": "\u0420\u0435\u0432\u044c\u044e \u0447\u0430\u043d\u043a\u043e\u0432",
        "zh": "\u5206\u5757\u5ba1\u6838",
        "kk": "\u0427\u0430\u043d\u043a\u0442\u0430\u0440\u0434\u044b \u0442\u0435\u043a\u0441\u0435\u0440\u0443",
        "uz": "Bo\u02bbaklarni ko\u02bbrib chiqish",
    },
    "chunks.preset_panel": {
        "en": "Voice Presets",
        "ru": "\u041f\u0440\u0435\u0441\u0435\u0442\u044b \u0433\u043e\u043b\u043e\u0441\u043e\u0432",
        "zh": "\u58f0\u97f3\u9884\u8bbe",
        "kk": "\u0414\u0430\u0443\u044b\u0441 \u043f\u0440\u0435\u0441\u0435\u0442\u0442\u0435\u0440\u0456",
        "uz": "Ovoz presetlari",
    },
    "voice.output_dir": {
        "en": "Output folder:",
        "ru": "\u041f\u0430\u043f\u043a\u0430 \u0432\u044b\u0432\u043e\u0434\u0430:",
    },
    "voice.choose_dir": {
        "en": "Browse\u2026",
        "ru": "\u041e\u0431\u0437\u043e\u0440\u2026",
    },
    "voice.preview_phrase": {
        "en": "Preview phrase:",
        "ru": "\u0424\u0440\u0430\u0437\u0430 \u0434\u043b\u044f \u043f\u0440\u0435\u0432\u044c\u044e:",
    },
    "voice.default_phrase": {
        "en": (
            "Sergey sat at the table drinking tea with raspberry jam. "
            "His mood was rather melancholic."
        ),
        "ru": (
            "\u0421\u0435\u0440\u0433\u0435\u0439 \u0441\u0438\u0434\u0435\u043b \u0437\u0430 \u0441\u0442\u043e\u043b\u043e\u043c \u0438 \u043f\u0438\u043b \u0447\u0430\u0439 \u0441 \u043c\u0430\u043b\u0438\u043d\u043e\u0432\u044b\u043c \u0432\u0430\u0440\u0435\u043d\u044c\u0435\u043c. "
            "\u0421\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u0435 \u0431\u044b\u043b\u043e \u0432\u0435\u0441\u044c\u043c\u0430 \u0442\u043e\u0441\u043a\u043b\u0438\u0432\u044b\u043c."
        ),
    },
    "voice.gen_loading": {
        "en": "Loading TTS model\u2026 (1\u20132 min)",
        "ru": "\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 TTS \u043c\u043e\u0434\u0435\u043b\u0438\u2026 (1\u20132 \u043c\u0438\u043d)",
    },
    "voice.gen_progress": {
        "en": "{done}/{total} \u2014 {name} \u2014 ETA: {eta}",
        "ru": "{done}/{total} \u2014 {name} \u2014 \u041e\u0441\u0442\u0430\u043b\u043e\u0441\u044c: {eta}",
    },
    "voice.gen_done": {
        "en": "Done! All {total} previews generated in {elapsed}",
        "ru": "\u0413\u043e\u0442\u043e\u0432\u043e! \u0412\u0441\u0435 {total} \u043f\u0440\u0435\u0432\u044c\u044e \u0441\u0433\u0435\u043d\u0435\u0440\u0438\u0440\u043e\u0432\u0430\u043d\u044b \u0437\u0430 {elapsed}",
    },

    # ── Synthesis page ──
    "synth.no_manifest": {
        "en": "No manifest loaded",
        "ru": "\u041c\u0430\u043d\u0438\u0444\u0435\u0441\u0442 \u043d\u0435 \u0437\u0430\u0433\u0440\u0443\u0436\u0435\u043d",
    },
    "synth.load_manifest": {
        "en": "Load",
        "ru": "\u0417\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c",
        "zh": "\u52a0\u8f7d",
        "kk": "\u0416\u04af\u043a\u0442\u0435\u0443",
        "uz": "Yuklash",
    },
    "synth.load_manifest_tip": {
        "en": "Load a chunk manifest for synthesis.",
        "ru": "\u0417\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c manifest \u0447\u0430\u043d\u043a\u043e\u0432 \u0434\u043b\u044f \u0441\u0438\u043d\u0442\u0435\u0437\u0430.",
        "zh": "\u52a0\u8f7d\u7528\u4e8e\u5408\u6210\u7684\u5206\u5757\u6e05\u5355\u3002",
        "kk": "\u0421\u0438\u043d\u0442\u0435\u0437\u0433\u0435 \u0430\u0440\u043d\u0430\u043b\u0493\u0430\u043d \u0447\u0430\u043d\u043a manifest \u0444\u0430\u0439\u043b\u044b\u043d \u0436\u04af\u043a\u0442\u0435\u0443.",
        "uz": "Sintez uchun chunk manifestini yuklash.",
    },
    "synth.compact_load_manifest": {
        "en": "Open",
        "ru": "\u041e\u0442\u043a\u0440.",
        "zh": "打开",
        "kk": "Ашу",
        "uz": "Och",
    },
    "synth.mode_custom_voice": {
        "en": "Custom Voice",
        "ru": "Свой голос",
        "zh": "自定义声音",
        "kk": "Өз дауысы",
        "uz": "O'z ovozi",
    },
    "synth.mode_preset_speakers": {
        "en": "Built-in Speakers",
        "ru": "Готовые голоса",
        "zh": "内置声音",
        "kk": "Дайын дауыстар",
        "uz": "Tayyor ovozlar",
    },
    "synth.mode_advanced": {
        "en": "Advanced",
        "ru": "Дополнительно",
        "zh": "高级",
        "kk": "Қосымша",
        "uz": "Qo'shimcha",
    },
    "synth.preset_title": {
        "en": "Built-in Qwen speakers",
        "ru": "Готовые голоса Qwen",
    },
    "synth.preset_desc": {
        "en": (
            "Use the speaker assignments from the Voices step. No reference audio is "
            "needed; this is the simplest and most stable mode."
        ),
        "ru": (
            "Использует роли и голоса из шага «Голоса». Reference audio не нужен; "
            "это самый простой и стабильный режим."
        ),
    },
    "synth.advanced_title": {
        "en": "Advanced run settings",
        "ru": "Дополнительные настройки запуска",
    },
    "synth.advanced_desc": {
        "en": "These settings affect speed, file layout, and recovery after interruption.",
        "ru": "Эти параметры влияют на скорость, файлы на выходе и продолжение после обрыва.",
    },
    "synth.comfyui_url": {"en": "ComfyUI URL:", "ru": "ComfyUI URL:"},
    "synth.workflow": {"en": "Workflow:", "ru": "Workflow:"},
    "synth.choose_file": {"en": "Choose...", "ru": "Выбрать..."},
    "synth.workflow_hint": {
        "en": (
            "Recommended path: v2 manifests are synthesized through ComfyUI. "
            "The template must contain {{TEXT}}, {{SPEAKER}}, {{INSTRUCT}}, "
            "and {{OUTPUT_FILENAME}} placeholders."
        ),
        "ru": (
            "Рекомендуемый путь: v2-манифесты синтезируются через ComfyUI. "
            "Шаблон должен содержать {{TEXT}}, {{SPEAKER}}, {{INSTRUCT}} "
            "и {{OUTPUT_FILENAME}}."
        ),
    },
    "synth.model": {"en": "Model:", "ru": "\u041c\u043e\u0434\u0435\u043b\u044c:"},
    "synth.model_hint": {
        "en": (
            "1.7B \u2014 best quality, 18% fewer errors (WER) vs 0.6B. "
            "Needs ~4 GB VRAM. ~80\u2013120 s per chunk.\n"
            "0.6B \u2014 faster, needs ~2 GB VRAM. ~30\u201360 s per chunk. "
            "Good for drafts and previews."
        ),
        "ru": (
            "1.7B \u2014 лучшее качество, на 18% меньше ошибок (WER). "
            "Нужно ~4 ГБ VRAM. ~80\u2013120 сек/чанк.\n"
            "0.6B \u2014 быстрее, нужно ~2 ГБ VRAM. ~30\u201360 сек/чанк. "
            "Подходит для черновиков и превью."
        ),
    },
    "synth.models_dir": {
        "en": "Models dir:",
        "ru": "Папка моделей:",
    },
    "synth.voice_library_dir": {
        "en": "Voice library:",
        "ru": "Библиотека голосов:",
    },
    "synth.output_dir": {
        "en": "Save files to:",
        "ru": "\u0421\u043e\u0445\u0440\u0430\u043d\u044f\u0442\u044c \u0444\u0430\u0439\u043b\u044b \u0432:",
    },
    "synth.models_dir_hint": {
        "en": (
            "ComfyUI/model setup uses this shared folder. Default points to "
            "D:\\ComfyUI-external\\models and expects Qwen folders in audio_encoders."
        ),
        "ru": (
            "ComfyUI/model setup использует эту общую папку моделей. "
            "По умолчанию: D:\\ComfyUI-external\\models; Qwen ожидается в audio_encoders."
        ),
    },
    "synth.choose_dir": {"en": "Choose...", "ru": "Выбрать..."},
    "synth.install_models": {
        "en": "Install models",
        "ru": "Скачать модели",
    },
    "synth.install_models_help": {
        "en": (
            "Download the TTS model required by the current synthesis mode "
            "from Hugging Face into the selected models folder. Downloads are large."
        ),
        "ru": (
            "Скачивает TTS-модели для текущего режима синтеза из Hugging Face "
            "в выбранную папку моделей. Файлы большие."
        ),
    },
    "synth.models_installing": {
        "en": "Installing TTS models into {dir}. This may take a long time.",
        "ru": "Скачивание TTS-моделей в {dir}. Это может занять много времени.",
    },
    "synth.models_installed": {
        "en": "TTS models ready: downloaded {downloaded}, already present {skipped}. Folder: {dir}",
        "ru": "TTS-модели готовы: скачано {downloaded}, уже было {skipped}. Папка: {dir}",
    },
    "synth.models_present": {
        "en": "Required TTS models are already present in {dir}.",
        "ru": "Нужные TTS-модели уже есть в {dir}.",
    },
    "synth.models_install_error": {
        "en": "TTS model installation failed: {msg}",
        "ru": "Не удалось скачать TTS-модели: {msg}",
    },
    "synth.batch_size": {
        "en": "Batch Size:",
        "ru": "\u0420\u0430\u0437\u043c\u0435\u0440 \u0431\u0430\u0442\u0447\u0430:",
    },
    "synth.batch_hint": {
        "en": (
            "How many chunks are synthesized at once.\n"
            "1 \u2014 sequential, minimal VRAM (~4 GB for 1.7B). Most stable.\n"
            "2\u20134 \u2014 moderate speedup, needs 6\u201310 GB VRAM.\n"
            "5\u20138 \u2014 max throughput, needs 12+ GB VRAM. "
            "Risk of OOM errors on smaller GPUs."
        ),
        "ru": (
            "Сколько чанков синтезируются одновременно.\n"
            "1 \u2014 последовательно, минимум VRAM (~4 ГБ для 1.7B). "
            "Самый стабильный.\n"
            "2\u20134 \u2014 умеренное ускорение, нужно 6\u201310 ГБ VRAM.\n"
            "5\u20138 \u2014 макс. скорость, нужно 12+ ГБ VRAM. "
            "Риск ошибок нехватки памяти на слабых GPU."
        ),
    },
    "synth.chunk_timeout": {
        "en": "Chunk timeout:",
        "ru": "Таймаут чанка:",
    },
    "synth.chunk_timeout_hint": {
        "en": (
            "Max seconds to wait for a single chunk before skipping it.\n"
            "Useful when corrupted text causes the model to hang.\n"
            "Default: 300 s (5 min). Increase for very long chunks."
        ),
        "ru": (
            "Максимальное время ожидания одного чанка перед пропуском.\n"
            "Помогает, когда поврежденный текст вешает модель.\n"
            "По умолчанию: 300 с (5 мин). Увеличьте для очень длинных чанков."
        ),
    },
    "synth.output_format": {
        "en": "Output format:",
        "ru": "Формат аудио:",
    },
    "synth.merge_chapters": {
        "en": "Chapters:",
        "ru": "Главы:",
    },
    "synth.merge_chapters_check": {
        "en": "Merge chunks into chapter files",
        "ru": "Собрать чанки в файлы глав",
    },
    "synth.sample_enable": {
        "en": "Use sample voice for this book",
        "ru": "Использовать sample voice для этой книги",
    },
    "synth.sample_title": {
        "en": "CustomVoice Sample",
        "ru": "CustomVoice Sample",
    },
    "synth.sample_desc": {
        "en": (
            "Use this only when the whole book should sound like your own sample "
            "or a reusable saved voice."
        ),
        "ru": (
            "Нужно только если вся книга должна звучать как ваш образец "
            "или сохраненный голос."
        ),
    },
    "synth.custom_strategy": {
        "en": "Voice source:",
        "ru": "Источник голоса:",
    },
    "synth.strategy_sample_all": {
        "en": "New sample for whole book",
        "ru": "Новый sample на всю книгу",
    },
    "synth.strategy_saved_all": {
        "en": "Saved voice for whole book",
        "ru": "Сохраненный голос на всю книгу",
    },
    "synth.strategy_saved_roles": {
        "en": "Saved voices by role",
        "ru": "Сохраненные голоса по ролям",
    },
    "synth.saved_voice": {
        "en": "Saved voice:",
        "ru": "Сохраненный голос:",
    },
    "synth.refresh_saved_voices": {
        "en": "Refresh",
        "ru": "Обновить",
    },
    "synth.no_saved_voices": {
        "en": "No saved voices yet",
        "ru": "Сохраненных голосов пока нет",
    },
    "synth.role_builtin": {
        "en": "Use built-in speaker",
        "ru": "Готовый Qwen-спикер",
    },
    "synth.role_narrator": {"en": "Narrator:", "ru": "Диктор:"},
    "synth.role_male": {"en": "Male roles:", "ru": "Мужские роли:"},
    "synth.role_female": {"en": "Female roles:", "ru": "Женские роли:"},
    "synth.saved_voice_name": {
        "en": "Save as:",
        "ru": "Сохранить как:",
    },
    "synth.save_local_voice": {
        "en": "Save Voice",
        "ru": "Сохранить голос",
    },
    "synth.compact_save_local_voice": {
        "en": "Save",
        "ru": "Сохр.",
        "zh": "保存",
        "kk": "Сақт.",
        "uz": "Saql.",
    },
    "synth.saved_voice_all_hint": {
        "en": "The selected saved voice will be used for every chunk; previous voice markup stays in the manifest but does not affect timbre.",
        "ru": "Выбранный сохраненный голос будет использован для всех чанков; разметка голосов останется в манифесте, но не повлияет на тембр.",
    },
    "synth.saved_voice_roles_hint": {
        "en": "Mapped roles use saved voices. Roles left on built-in speaker keep their Qwen preset from the Voices step.",
        "ru": "Назначенные роли используют сохраненные голоса. Роли с готовым спикером сохраняют Qwen-пресет из шага «Голоса».",
    },
    "synth.saved_voice_missing": {
        "en": "Choose a saved voice, or fill sample audio, transcript, and voice name.",
        "ru": "Выберите сохраненный голос или заполните sample audio, текст и имя голоса.",
    },
    "synth.saved_voice_saving": {
        "en": "Saving reusable voice '{name}'...",
        "ru": "Сохраняю reusable voice '{name}'...",
    },
    "synth.saved_voice_saved": {
        "en": "Saved reusable voice '{name}'.",
        "ru": "Голос '{name}' сохранен для повторного использования.",
    },
    "synth.saved_voice_error": {
        "en": "Could not save voice: {msg}",
        "ru": "Не удалось сохранить голос: {msg}",
    },
    "synth.voice_tuning_show": {
        "en": "Show fine voice settings",
        "ru": "\u041f\u043e\u043a\u0430\u0437\u0430\u0442\u044c \u0442\u043e\u043d\u043a\u0443\u044e \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0443 \u0433\u043e\u043b\u043e\u0441\u0430",
    },
    "synth.voice_tuning_hide": {
        "en": "Hide fine voice settings",
        "ru": "\u0421\u043a\u0440\u044b\u0442\u044c \u0442\u043e\u043d\u043a\u0443\u044e \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0443 \u0433\u043e\u043b\u043e\u0441\u0430",
    },
    "synth.sample_audio": {
        "en": "Sample audio:",
        "ru": "Sample audio:",
    },
    "synth.sample_preview": {
        "en": "Preview:",
        "ru": "Прослушать:",
    },
    "synth.sample_play": {
        "en": "Play",
        "ru": "Play",
    },
    "synth.sample_pause": {
        "en": "Pause",
        "ru": "Pause",
    },
    "synth.sample_transcript": {
        "en": "Sample text:",
        "ru": "Текст sample voice:",
    },
    "synth.sample_idle": {
        "en": "Sample voice is optional; when enabled, prompt extraction runs before chunks.",
        "ru": "Образец голоса необязателен; если он включен, извлечение голосового промпта выполнится перед фрагментами.",
    },
    "synth.sample_ready": {
        "en": "Sample audio loaded. Enter the exact transcript before synthesis.",
        "ru": "Sample audio загружен. Перед синтезом введите точный текст образца.",
    },
    "synth.sample_duration": {
        "en": "Sample length: {sec}s. Prompt extraction estimate: {eta}.",
        "ru": "Длина образца: {sec} с. Оценка извлечения промпта: {eta}.",
    },
    "synth.sample_missing": {
        "en": "Choose sample audio and enter the exact sample text.",
        "ru": "Выберите sample audio и введите точный текст образца.",
    },
    "synth.sample_extracting": {
        "en": "Extracting voice prompt from sample audio...",
        "ru": "Извлекаю голосовой промпт из аудио образца...",
    },
    "synth.sample_extracted": {
        "en": "Voice prompt {done}/{total} ready in {sec:.1f}s.",
        "ru": "Голосовой промпт {done}/{total} готов за {sec:.1f} с.",
    },
    "synth.temperature": {
        "en": "Temperature (0.10-2.00):",
        "ru": "Temperature (0.10-2.00):",
    },
    "synth.top_p": {
        "en": "Top-p (0.10-1.00):",
        "ru": "Top-p (0.10-1.00):",
    },
    "synth.top_k": {
        "en": "Top-k (1-200):",
        "ru": "Top-k (1-200):",
    },
    "synth.repetition_penalty": {
        "en": "Repetition penalty (0.80-2.00):",
        "ru": "Repetition penalty (0.80-2.00):",
    },
    "synth.max_new_tokens": {
        "en": "Max new tokens (128-8192):",
        "ru": "Max new tokens (128-8192):",
    },
    "synth.speech_rate": {
        "en": "Speech speed:",
        "ru": "\u0421\u043a\u043e\u0440\u043e\u0441\u0442\u044c \u0440\u0435\u0447\u0438:",
    },
    "synth.speech_rate_slow": {
        "en": "slower",
        "ru": "\u043c\u0435\u0434\u043b\u0435\u043d\u043d\u0435\u0435",
    },
    "synth.speech_rate_normal": {
        "en": "normal",
        "ru": "\u0441\u0440\u0435\u0434\u043d\u0435",
    },
    "synth.speech_rate_fast": {
        "en": "faster",
        "ru": "\u0431\u044b\u0441\u0442\u0440\u0435\u0435",
    },
    "synth.seed": {
        "en": "Seed (-1=random):",
        "ru": "Seed (-1=random):",
    },
    "synth.model_help": {
        "en": "Choose the Qwen CustomVoice model for built-in speakers. 1.7B is better quality; 0.6B is faster and lighter.",
        "ru": "Модель Qwen CustomVoice для готовых спикеров. 1.7B качественнее; 0.6B быстрее и легче.",
    },
    "synth.models_dir_help": {
        "en": "Folder with downloaded models used by the v2 ComfyUI synthesis workflow.",
        "ru": "Папка с уже скачанными моделями для v2 ComfyUI synthesis workflow.",
    },
    "synth.voice_library_dir_help": {
        "en": "Shared folder for reusable .voice.pt prompts. Saved voices can be reused across books without prompt extraction.",
        "ru": "Общая папка для reusable .voice.pt prompt'ов. Сохраненные голоса можно переиспользовать в разных книгах без prompt extraction.",
    },
    "synth.output_dir_help": {
        "en": "Folder where v2 synthesis files are written: audio_chunks, tts_test_preview, synthesis_log.txt, and merged chapters.",
        "ru": "\u041f\u0430\u043f\u043a\u0430, \u043a\u0443\u0434\u0430 \u043f\u0438\u0448\u0443\u0442\u0441\u044f \u0444\u0430\u0439\u043b\u044b \u0441\u0438\u043d\u0442\u0435\u0437\u0430: audio_chunks, tts_test_preview, synthesis_log.txt, synthesis_manifest.json \u0438 \u0441\u043e\u0431\u0440\u0430\u043d\u043d\u044b\u0435 \u0433\u043b\u0430\u0432\u044b.",
    },
    "synth.batch_help": {
        "en": "How many chunks to render at once. 1 is safest; larger values can be faster but need more VRAM.",
        "ru": "Сколько чанков рендерить одновременно. 1 — самый стабильный вариант; больше — быстрее, но требует больше VRAM.",
    },
    "synth.chunk_timeout_help": {
        "en": "Maximum time for one chunk. If the model hangs on bad text, the chunk is skipped instead of blocking the whole book.",
        "ru": "Максимальное время на один чанк. Если модель зависнет на проблемном тексте, чанк будет пропущен, а книга продолжит рендериться.",
    },
    "synth.output_format_help": {
        "en": "Audio format for generated chunks and merged chapter files. FLAC is compact and lossless; WAV is most compatible.",
        "ru": "Формат чанков и собранных глав. FLAC компактный и без потерь; WAV максимально совместимый.",
    },
    "synth.merge_chapters_help": {
        "en": "Also create one merged audio file per chapter while keeping individual chunk files.",
        "ru": "Дополнительно собирать один аудиофайл на главу, сохраняя отдельные чанки.",
    },
    "synth.chapter_help": {
        "en": "Render the whole book or only one selected chapter.",
        "ru": "Рендерить всю книгу или только выбранную главу.",
    },
    "synth.resume_help": {
        "en": "Skip chunks that already have audio files. Useful after stopping or a crash.",
        "ru": "Пропускать чанки, для которых уже есть аудио. Полезно после остановки или сбоя.",
    },
    "synth.compile_help": {
        "en": "torch.compile can speed up later chunks after a slower warm-up. Leave it off if you want the most predictable run.",
        "ru": "torch.compile может ускорить следующие чанки после более медленного прогрева. Оставьте выключенным для максимально предсказуемого запуска.",
    },
    "synth.sage_help": {
        "en": "SageAttention is an optional faster attention kernel for the local TTS Python environment. Enable only if it is installed and tested on your GPU.",
        "ru": "SageAttention — опциональное ускорение attention для локального TTS Python. Включайте только если оно установлено и проверено на вашей GPU.",
    },
    "synth.sample_audio_help": {
        "en": "A short clean recording of the target voice. WAV/FLAC is best; noisy audio gives worse cloning.",
        "ru": "Короткая чистая запись нужного голоса. Лучше WAV/FLAC; шумный файл ухудшит клонирование.",
    },
    "synth.sample_preview_help": {
        "en": "Play the selected sample so you can verify it is the right voice and text.",
        "ru": "Прослушивание выбранного sample, чтобы проверить голос и соответствие тексту.",
    },
    "synth.sample_transcript_help": {
        "en": "Exact text spoken in the sample audio. The closer it matches, the better the voice prompt.",
        "ru": "Точный текст, произнесенный в sample audio. Чем точнее совпадение, тем лучше voice prompt.",
    },
    "synth.temperature_help": {
        "en": (
            "Range: 0.10-2.00. Default: 1.00.\n"
            "Lower values make pronunciation steadier and more predictable.\n"
            "Higher values add variation and expression, but can increase artifacts, odd pauses, or unstable speech.\n"
            "Good first moves: 0.80-0.95 for stability, 1.05-1.15 for a slightly livelier voice."
        ),
        "ru": (
            "Диапазон: 0.10-2.00. По умолчанию: 1.00.\n"
            "Ниже - речь ровнее и предсказуемее.\n"
            "Выше - больше вариативности и эмоции, но выше риск артефактов, странных пауз и нестабильной речи.\n"
            "Для пробы: 0.80-0.95 для стабильности, 1.05-1.15 если голос слишком ровный."
        ),
    },
    "synth.top_p_help": {
        "en": (
            "Range: 0.10-1.00. Default: 0.80.\n"
            "Top-p keeps only the smallest group of likely choices whose total probability reaches this value.\n"
            "Lower values are stricter and can reduce strange phrasing. Higher values allow more alternatives.\n"
            "Try 0.70-0.85 for audiobooks; 0.90+ only if the voice sounds too constrained."
        ),
        "ru": (
            "Диапазон: 0.10-1.00. По умолчанию: 0.80.\n"
            "Top-p оставляет только наиболее вероятные варианты, пока их суммарный шанс не достигнет этого числа.\n"
            "Ниже - строже и меньше странных фраз. Выше - больше альтернатив.\n"
            "Для книг обычно 0.70-0.85; 0.90+ имеет смысл, если голос слишком зажат."
        ),
    },
    "synth.top_k_help": {
        "en": (
            "Range: 1-200. Default: 20.\n"
            "At each generation step the model can choose only from the top K most likely audio tokens.\n"
            "1 is almost deterministic and can sound flat or stuck. 10-30 is a safe audiobook range.\n"
            "50-100 gives more variety, but can add pronunciation drift. 100+ is experimental."
        ),
        "ru": (
            "Диапазон: 1-200. По умолчанию: 20.\n"
            "На каждом шаге модель выбирает только из K самых вероятных аудио-токенов.\n"
            "1 - почти без случайности; может звучать плоско или застревать. 10-30 - спокойный диапазон для аудиокниг.\n"
            "50-100 - больше разнообразия, но выше риск съезда произношения. 100+ - эксперимент."
        ),
    },
    "synth.repetition_penalty_help": {
        "en": (
            "Range: 0.80-2.00. Default: 1.05. 1.00 means no penalty.\n"
            "This penalizes recently generated audio/text tokens, so it can stop loops like repeated syllables, words, breaths, or stuck sounds.\n"
            "1.03-1.10 is usually safe. Try 1.12-1.20 if speech repeats. Above 1.30 can make speech choppy or skip natural repeated words."
        ),
        "ru": (
            "Диапазон: 0.80-2.00. По умолчанию: 1.05. 1.00 - без штрафа.\n"
            "Штрафует то, что модель только что сгенерировала: аудио-токены, слоги, слова, дыхание, зацикленные звуки.\n"
            "1.03-1.10 обычно безопасно. 1.12-1.20 - если речь повторяется. Выше 1.30 может сделать речь рубленой или выкидывать естественные повторы."
        ),
    },
    "synth.max_new_tokens_help": {
        "en": (
            "Range: 128-8192. Default: 2048.\n"
            "Hard cap for generated audio tokens in one chunk. It is a safety limit, not a quality knob.\n"
            "Too low can cut the phrase off. Increase only when long chunks end early; otherwise keep the default."
        ),
        "ru": (
            "Диапазон: 128-8192. По умолчанию: 2048.\n"
            "Жесткий лимит аудио-токенов на один чанк; это защитный предел, а не ручка качества.\n"
            "Слишком низко - фраза может обрезаться. Повышайте только если длинные чанки заканчиваются раньше текста."
        ),
    },
    "synth.speech_rate_help": {
        "en": (
            "Post-process tempo for generated speech. 1.00x keeps the model output, "
            "0.85-0.95x is useful for slower narration, and 1.05-1.15x makes it faster. "
            "When you save a custom voice, this value is stored with that voice."
        ),
        "ru": (
            "\u0422\u0435\u043c\u043f \u0433\u043e\u0442\u043e\u0432\u043e\u0439 \u0440\u0435\u0447\u0438 \u043f\u043e\u0441\u043b\u0435 \u0433\u0435\u043d\u0435\u0440\u0430\u0446\u0438\u0438. "
            "1.00x \u043e\u0441\u0442\u0430\u0432\u043b\u044f\u0435\u0442 \u0432\u044b\u0445\u043e\u0434 \u043c\u043e\u0434\u0435\u043b\u0438 \u043a\u0430\u043a \u0435\u0441\u0442\u044c; "
            "0.85-0.95x \u0443\u0434\u043e\u0431\u043d\u043e \u0434\u043b\u044f \u0431\u043e\u043b\u0435\u0435 \u043c\u0435\u0434\u043b\u0435\u043d\u043d\u043e\u0433\u043e \u0434\u0438\u043a\u0442\u043e\u0440\u0430; "
            "1.05-1.15x \u0443\u0441\u043a\u043e\u0440\u044f\u0435\u0442. "
            "\u041f\u0440\u0438 \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0438\u0438 custom voice \u044d\u0442\u043e \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435 \u0437\u0430\u043f\u0438\u0448\u0435\u0442\u0441\u044f \u0432 \u0433\u043e\u043b\u043e\u0441."
        ),
    },
    "synth.seed_help": {
        "en": (
            "Range: -1 or 0-2147483647. Default: -1.\n"
            "-1 means random every run, so the same text/settings can sound slightly different.\n"
            "Set any fixed number, for example 42, when you want repeatable previews and reruns.\n"
            "Changing the seed is useful when settings are good but one fragment came out unlucky."
        ),
        "ru": (
            "Диапазон: -1 или 0-2147483647. По умолчанию: -1.\n"
            "-1 - новая случайная версия при каждом запуске: тот же текст и настройки могут звучать чуть иначе.\n"
            "Любое фиксированное число, например 42, делает превью и повторный рендер более повторяемыми.\n"
            "Меняйте seed, если настройки уже нормальные, но конкретный фрагмент получился неудачно."
        ),
    },
    "synth.chapter": {
        "en": "Chapter:",
        "ru": "Глава:",
    },
    "synth.all_chapters": {
        "en": "All chapters",
        "ru": "Все главы",
    },
    "synth.chapter_item": {
        "en": "Chapter {num}  ({chunks} chunks)",
        "ru": "Глава {num}  ({chunks} чанков)",
    },
    "synth.chapter_info": {
        "en": "{chapters} chapters, {chunks} chunks total",
        "ru": "{chapters} глав, {chunks} чанков всего",
    },
    "synth.chunks_word": {
        "en": "chunks",
        "ru": "чанков",
    },
    "synth.test_source_title": {
        "en": "Test fragment source",
        "ru": "\u0418\u0441\u0442\u043e\u0447\u043d\u0438\u043a \u0442\u0435\u0441\u0442\u043e\u0432\u043e\u0433\u043e \u0444\u0440\u0430\u0433\u043c\u0435\u043d\u0442\u0430",
    },
    "synth.test_source_desc": {
        "en": "Pick one book chunk for a quick preview before running the whole book, or switch to custom text.",
        "ru": "Выберите один чанк для быстрой проверки перед полной озвучкой или переключитесь на свой текст.",
    },
    "synth.test_source": {
        "en": "Test from:",
        "ru": "\u0422\u0435\u0441\u0442 \u0438\u0437:",
    },
    "synth.test_source_chunk": {
        "en": "Book chunk",
        "ru": "\u0427\u0430\u043d\u043a \u043a\u043d\u0438\u0433\u0438",
    },
    "synth.test_source_custom": {
        "en": "Custom text",
        "ru": "\u0421\u0432\u043e\u0439 \u0442\u0435\u043a\u0441\u0442",
    },
    "synth.test_source_help": {
        "en": "Book chunk uses the selected chunk exactly as it appears in the manifest. Custom text creates a one-off preview chunk.",
        "ru": "\u0427\u0430\u043d\u043a \u043a\u043d\u0438\u0433\u0438 \u0431\u0435\u0440\u0435\u0442\u0441\u044f \u0440\u043e\u0432\u043d\u043e \u0438\u0437 \u043c\u0430\u043d\u0438\u0444\u0435\u0441\u0442\u0430. \u0421\u0432\u043e\u0439 \u0442\u0435\u043a\u0441\u0442 \u0441\u043e\u0437\u0434\u0430\u0435\u0442 \u0440\u0430\u0437\u043e\u0432\u044b\u0439 preview-\u0447\u0430\u043d\u043a.",
    },
    "synth.test_chunk": {
        "en": "Book chunk:",
        "ru": "\u0427\u0430\u043d\u043a \u043a\u043d\u0438\u0433\u0438:",
    },
    "synth.test_chunk_item": {
        "en": "Chunk {num} (will use: {voice}, {chars} chars): {preview}",
        "ru": "\u0427\u0430\u043d\u043a {num} (\u043e\u0437\u0432\u0443\u0447\u0438\u0442: {voice}, {chars} \u0441\u0438\u043c\u0432.): {preview}",
    },
    "synth.test_voice_custom_sample": {
        "en": "CustomVoice sample",
        "ru": "CustomVoice sample",
    },
    "synth.test_voice_saved": {
        "en": "CustomVoice: {voice}",
        "ru": "CustomVoice: {voice}",
    },
    "synth.test_voice_builtin": {
        "en": "built-in preset: {voice}",
        "ru": "\u0432\u0441\u0442\u0440\u043e\u0435\u043d\u043d\u044b\u0439 preset: {voice}",
    },
    "synth.test_voice": {
        "en": "Voice for custom text:",
        "ru": "\u0413\u043e\u043b\u043e\u0441 \u0434\u043b\u044f \u0441\u0432\u043e\u0435\u0433\u043e \u0442\u0435\u043a\u0441\u0442\u0430:",
    },
    "synth.test_chunk_text": {
        "en": "Selected chunk text:",
        "ru": "\u0422\u0435\u043a\u0441\u0442 \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u043e\u0433\u043e \u0447\u0430\u043d\u043a\u0430:",
    },
    "synth.test_custom_text": {
        "en": "Custom text:",
        "ru": "\u0421\u0432\u043e\u0439 \u0442\u0435\u043a\u0441\u0442:",
    },
    "synth.test_custom_placeholder": {
        "en": "Paste any text you want to test with the current voice settings.",
        "ru": "\u0412\u0441\u0442\u0430\u0432\u044c\u0442\u0435 \u043b\u044e\u0431\u043e\u0439 \u0442\u0435\u043a\u0441\u0442, \u043a\u043e\u0442\u043e\u0440\u044b\u0439 \u043d\u0443\u0436\u043d\u043e \u043f\u0440\u043e\u0433\u043d\u0430\u0442\u044c \u0441 \u0442\u0435\u043a\u0443\u0449\u0438\u043c\u0438 \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430\u043c\u0438 \u0433\u043e\u043b\u043e\u0441\u0430.",
    },
    "synth.test_custom_missing": {
        "en": "Enter custom text for the test fragment.",
        "ru": "\u0412\u0432\u0435\u0434\u0438\u0442\u0435 \u0441\u0432\u043e\u0439 \u0442\u0435\u043a\u0441\u0442 \u0434\u043b\u044f \u0442\u0435\u0441\u0442\u043e\u0432\u043e\u0433\u043e \u0444\u0440\u0430\u0433\u043c\u0435\u043d\u0442\u0430.",
    },
    "synth.chunk_editor_placeholder": {
        "en": "Edit the selected chunk here, then save it back to the manifest before synthesis.",
        "ru": "\u041f\u0440\u0430\u0432\u044c\u0442\u0435 \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u044b\u0439 \u0447\u0430\u043d\u043a \u0437\u0434\u0435\u0441\u044c \u0438 \u0441\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u0435 \u0432 manifest \u043f\u0435\u0440\u0435\u0434 \u0441\u0438\u043d\u0442\u0435\u0437\u043e\u043c.",
    },
    "synth.chunk_editor_save": {
        "en": "Save chunk text",
        "ru": "\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u0447\u0430\u043d\u043a",
    },
    "synth.compact_chunk_editor_save": {
        "en": "Save",
        "ru": "\u0421\u043e\u0445\u0440. \u0447\u0430\u043d\u043a",
        "zh": "\u4fdd\u5b58",
        "kk": "\u0421\u0430\u049b\u0442.",
        "uz": "Saql.",
    },
    "synth.chunk_editor_split": {
        "en": "Split",
        "ru": "\u0420\u0430\u0437\u0434\u0435\u043b\u0438\u0442\u044c",
        "zh": "\u5206\u5272",
        "kk": "\u0411\u04e9\u043b\u0443",
        "uz": "Bo'lish",
    },
    "synth.chunk_editor_split_tip": {
        "en": "Split the selected chunk at the cursor.",
        "ru": "\u0420\u0430\u0437\u0434\u0435\u043b\u0438\u0442\u044c \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u044b\u0439 \u0447\u0430\u043d\u043a \u0432 \u043c\u0435\u0441\u0442\u0435 \u043a\u0443\u0440\u0441\u043e\u0440\u0430.",
        "zh": "\u5728\u5149\u6807\u5904\u5206\u5272\u9009\u4e2d\u7684\u5206\u5757\u3002",
        "kk": "\u0422\u0430\u04a3\u0434\u0430\u043b\u0493\u0430\u043d \u0447\u0430\u043d\u043a\u0442\u044b \u043a\u0443\u0440\u0441\u043e\u0440 \u0442\u04b1\u0440\u0493\u0430\u043d \u0436\u0435\u0440\u0434\u0435\u043d \u0431\u04e9\u043b\u0443.",
        "uz": "Tanlangan bo'lakni kursor turgan joydan bo'lish.",
    },
    "synth.chunk_editor_merge": {
        "en": "Merge next",
        "ru": "\u0421\u043a\u043b\u0435\u0438\u0442\u044c \u0441\u043e \u0441\u043b\u0435\u0434.",
    },
    "synth.compact_chunk_editor_merge": {
        "en": "Merge",
        "ru": "\u0421\u043a\u043b\u0435\u0438\u0442\u044c",
        "zh": "\u5408\u5e76",
        "kk": "\u0411\u0456\u0440\u0456\u043a.",
        "uz": "Birlasht.",
    },
    "synth.chunk_editor_saved": {
        "en": "Chunk manifest saved. Synthesis will use the edited text.",
        "ru": "\u041c\u0430\u043d\u0438\u0444\u0435\u0441\u0442 \u0447\u0430\u043d\u043a\u043e\u0432 \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d. \u0421\u0438\u043d\u0442\u0435\u0437 \u0432\u043e\u0437\u044c\u043c\u0435\u0442 \u043e\u0442\u0440\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u044b\u0439 \u0442\u0435\u043a\u0441\u0442.",
    },
    "synth.no_test_chunks": {
        "en": "No chunks loaded",
        "ru": "\u0427\u0430\u043d\u043a\u0438 \u043d\u0435 \u0437\u0430\u0433\u0440\u0443\u0436\u0435\u043d\u044b",
    },
    "synth.start": {
        "en": "Start Synthesis",
        "ru": "\u0417\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u044c \u0441\u0438\u043d\u0442\u0435\u0437",
    },
    "synth.test_start": {
        "en": "Test Fragment",
        "ru": "\u0422\u0435\u0441\u0442\u043e\u0432\u044b\u0439 \u0444\u0440\u0430\u0433\u043c\u0435\u043d\u0442",
    },
    "synth.test_play": {
        "en": "Play Test",
        "ru": "\u041f\u0440\u043e\u0441\u043b\u0443\u0448\u0430\u0442\u044c \u0442\u0435\u0441\u0442",
    },
    "synth.test_pause": {
        "en": "Pause Test",
        "ru": "\u041f\u0430\u0443\u0437\u0430",
    },
    "synth.test_help": {
        "en": (
            "Render one short chunk from the selected chapter with the current voice and generation settings. "
            "The preview is saved separately and does not mark the book as synthesized."
        ),
        "ru": (
            "\u041e\u0437\u0432\u0443\u0447\u0438\u0442 \u043e\u0434\u0438\u043d \u043a\u043e\u0440\u043e\u0442\u043a\u0438\u0439 \u0447\u0430\u043d\u043a \u0438\u0437 \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u043e\u0439 \u0433\u043b\u0430\u0432\u044b \u0441 \u0442\u0435\u043a\u0443\u0449\u0438\u043c \u0433\u043e\u043b\u043e\u0441\u043e\u043c \u0438 \u043f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u0430\u043c\u0438. "
            "\u041f\u0440\u0435\u0432\u044c\u044e \u0441\u043e\u0445\u0440\u0430\u043d\u044f\u0435\u0442\u0441\u044f \u043e\u0442\u0434\u0435\u043b\u044c\u043d\u043e \u0438 \u043d\u0435 \u043f\u043e\u043c\u0435\u0447\u0430\u0435\u0442 \u043a\u043d\u0438\u0433\u0443 \u043a\u0430\u043a \u0441\u0438\u043d\u0442\u0435\u0437\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u0443\u044e."
        ),
    },
    "synth.stop": {
        "en": "Stop",
        "ru": "\u0421\u0442\u043e\u043f",
    },
    "synth.waiting": {
        "en": "Waiting for manifest\u2026",
        "ru": "\u041e\u0436\u0438\u0434\u0430\u043d\u0438\u0435 \u043c\u0430\u043d\u0438\u0444\u0435\u0441\u0442\u0430\u2026",
    },
    "synth.in_progress": {
        "en": "Synthesis in progress\u2026 (each chunk may take 1\u20132 min)",
        "ru": "\u0421\u0438\u043d\u0442\u0435\u0437 \u0432 \u043f\u0440\u043e\u0446\u0435\u0441\u0441\u0435\u2026 "
        "(\u043a\u0430\u0436\u0434\u044b\u0439 \u0447\u0430\u043d\u043a \u043c\u043e\u0436\u0435\u0442 \u0437\u0430\u043d\u044f\u0442\u044c 1\u20132 \u043c\u0438\u043d)",
    },
    "synth.test_in_progress": {
        "en": "Rendering a short test fragment with current settings...",
        "ru": "\u041e\u0437\u0432\u0443\u0447\u0438\u0432\u0430\u044e \u043a\u043e\u0440\u043e\u0442\u043a\u0438\u0439 \u0442\u0435\u0441\u0442\u043e\u0432\u044b\u0439 \u0444\u0440\u0430\u0433\u043c\u0435\u043d\u0442 \u0441 \u0442\u0435\u043a\u0443\u0449\u0438\u043c\u0438 \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430\u043c\u0438...",
    },
    "synth.test_no_chunk": {
        "en": "No non-empty chunk found for a test fragment.",
        "ru": "\u041d\u0435 \u043d\u0430\u0448\u0435\u043b\u0441\u044f \u043d\u0435\u043f\u0443\u0441\u0442\u043e\u0439 \u0447\u0430\u043d\u043a \u0434\u043b\u044f \u0442\u0435\u0441\u0442\u0430.",
    },
    "synth.progress_status": {
        "en": "Chunk {current}/{total} \u2022 ETA: {eta}",
        "ru": "\u0427\u0430\u043d\u043a {current}/{total} \u2022 \u041e\u0441\u0442\u0430\u043b\u043e\u0441\u044c: {eta}",
    },
    "synth.progress_status_no_eta": {
        "en": "Chunk {current}/{total}",
        "ru": "\u0427\u0430\u043d\u043a {current}/{total}",
    },
    "synth.progress_chapter": {
        "en": "Ch. {chapter} \u2022 Chunk {current}/{total} \u2022 ETA: {eta}",
        "ru": "\u0413\u043b. {chapter} \u2022 \u0427\u0430\u043d\u043a {current}/{total} \u2022 \u041e\u0441\u0442\u0430\u043b\u043e\u0441\u044c: {eta}",
    },
    "synth.progress_chapter_no_eta": {
        "en": "Ch. {chapter} \u2022 Chunk {current}/{total}",
        "ru": "\u0413\u043b. {chapter} \u2022 \u0427\u0430\u043d\u043a {current}/{total}",
    },
    "synth.progress_done": {
        "en": "Processed {current}/{total} chunks",
        "ru": "\u041e\u0431\u0440\u0430\u0431\u043e\u0442\u0430\u043d\u043e {current}/{total} \u0447\u0430\u043d\u043a\u043e\u0432",
    },
    "synth.progress_remaining": {
        "en": "{n} left",
        "ru": "\u043e\u0441\u0442\u0430\u043b\u043e\u0441\u044c {n}",
    },
    "synth.progress_last_chunk": {
        "en": "last: {chars} chars in {sec:.1f}s",
        "ru": "\u043f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0439: {chars} \u0441\u0438\u043c\u0432. \u0437\u0430 {sec:.1f} \u0441",
    },
    "synth.progress_chars": {
        "en": "{done}/{total} chars ({left} left)",
        "ru": "{done}/{total} \u0441\u0438\u043c\u0432. (\u043e\u0441\u0442. {left})",
    },
    "synth.progress_eta": {
        "en": "ETA: {eta}",
        "ru": "\u041e\u0441\u0442\u0430\u043b\u043e\u0441\u044c: {eta}",
    },
    "synth.log_placeholder": {
        "en": "Log will appear here when synthesis runs\u2026",
        "ru": "\u041b\u043e\u0433 \u043f\u043e\u044f\u0432\u0438\u0442\u0441\u044f \u043f\u0440\u0438 \u0437\u0430\u043f\u0443\u0441\u043a\u0435 \u0441\u0438\u043d\u0442\u0435\u0437\u0430\u2026",
    },
    "synth.log_path": {
        "en": "Log file: {path}",
        "ru": "\u041b\u043e\u0433: {path}",
    },
    "synth.test_log_path": {
        "en": "Test preview folder: {path}",
        "ru": "\u041f\u0430\u043f\u043a\u0430 \u0442\u0435\u0441\u0442\u043e\u0432\u043e\u0433\u043e \u043f\u0440\u0435\u0432\u044c\u044e: {path}",
    },
    "synth.resume": {
        "en": "Resume:",
        "ru": "Продолжить:",
    },
    "synth.resume_check": {
        "en": "Skip already synthesized chunks",
        "ru": "Пропустить уже синтезированные чанки",
    },
    "synth.resume_hint": {
        "en": (
            "If checked, chunks that already have WAV files "
            "will be skipped. Useful to continue after interruption."
        ),
        "ru": (
            "Если включено, чанки с уже готовыми WAV-файлами "
            "будут пропущены. Полезно для продолжения после обрыва."
        ),
    },
    "synth.retry_failed": {"en": "Retry:", "ru": "Повтор:"},
    "synth.retry_failed_check": {
        "en": "Retry failed chunks only",
        "ru": "Повторить только упавшие чанки",
    },
    "synth.retry_failed_hint": {
        "en": (
            "For ComfyUI v2 manifests, run only chunks marked failed=true. "
            "Leave off for normal resume."
        ),
        "ru": (
            "Для ComfyUI v2-манифестов запускает только чанки с failed=true. "
            "Для обычного продолжения оставьте выключенным."
        ),
    },
    "synth.compile": {
        "en": "torch.compile:",
        "ru": "torch.compile:",
    },
    "synth.compile_check": {
        "en": "Enable JIT compilation (+20–40% speed)",
        "ru": "Включить JIT-компиляцию (+20–40% скорости)",
    },
    "synth.compile_hint": {
        "en": (
            "Compiles model with torch.compile(). "
            "First chunk will be slower (JIT warmup), "
            "all subsequent chunks will run faster. "
            "Requires PyTorch 2.0+."
        ),
        "ru": (
            "Компилирует модель через torch.compile(). "
            "Первый чанк будет медленнее (прогрев JIT), "
            "все последующие — быстрее. "
            "Требует PyTorch 2.0+."
        ),
    },
    "synth.sage_attention": {
        "en": "SageAttention:",
        "ru": "SageAttention:",
    },
    "synth.sage_check": {
        "en": "Enable SageAttention (~2-3x faster attention)",
        "ru": "Включить SageAttention (~2-3x быстрее attention)",
    },
    "synth.sage_hint": {
        "en": (
            "SageAttention replaces SDPA with quantized attention kernels.\n"
            "Requires SageAttention in the local TTS Python environment; GitHub v2 is preferred:\n"
            "  pip install git+https://github.com/thu-ml/SageAttention.git\n"
            "If enabled and unavailable, synthesis stops with an explicit error."
        ),
        "ru": (
            "SageAttention заменяет SDPA квантованными attention-ядрами.\n"
            "Нужен SageAttention в локальном TTS Python; GitHub v2 предпочтительнее:\n"
            "  pip install git+https://github.com/thu-ml/SageAttention.git\n"
            "Если включено, но пакет недоступен, синтез остановится с явной ошибкой."
        ),
    },
    "synth.clone_enable": {
        "en": "Voice Cloning — use a real audio sample as voice",
        "ru": "Клонирование голоса — использовать реальный аудио-образец",
    },
    "synth.clone_title": {
        "en": "🎤  Voice Cloning",
        "ru": "🎤  Клонирование голоса",
    },
    "synth.clone_desc": {
        "en": (
            "Load a short audio clip (5–15 sec) of any voice + its transcript. "
            "The model will synthesize the entire book in that voice. "
            "You can add multiple voices for narrator / characters."
        ),
        "ru": (
            "Загрузите короткий аудио-фрагмент (5–15 сек) любого голоса + транскрипт. "
            "Модель озвучит всю книгу этим голосом. "
            "Можно добавить несколько голосов для диктора и персонажей."
        ),
    },
    "synth.clone_add_voice": {
        "en": "+ Add voice",
        "ru": "+ Добавить голос",
    },
    "synth.clone_col_role": {
        "en": "Voice role",
        "ru": "Роль голоса",
    },
    "synth.clone_col_wav": {
        "en": "Audio file (WAV/MP3/FLAC)",
        "ru": "Аудиофайл (WAV/MP3/FLAC)",
    },
    "synth.clone_col_transcript": {
        "en": "↳ Transcript: exactly what is said in the audio clip",
        "ru": "↳ Транскрипт: точный текст, который произносится в аудиофрагменте",
    },
    "synth.clone_transcript_ph": {
        "en": "Type the exact words spoken in the audio file…",
        "ru": "Введите точный текст, который произносится в аудиофайле…",
    },
    "synth.train_title": {
        "en": "ComfyUI Saved Voice",
        "ru": "Сохранение голоса ComfyUI",
    },
    "synth.train_desc": {
        "en": (
            "Extract a reusable custom voice through ComfyUI. The saved name will "
            "appear in FB_Qwen3TTSLoadSpeaker and can be used by ComfyUI dialogue workflows."
        ),
        "ru": (
            "Извлекает reusable custom voice через ComfyUI. Сохраненное имя появится "
            "в FB_Qwen3TTSLoadSpeaker и подойдет для ComfyUI dialogue workflows."
        ),
    },
    "synth.train_url": {"en": "ComfyUI URL:", "ru": "ComfyUI URL:"},
    "synth.train_name": {"en": "Save as:", "ru": "Сохранить как:"},
    "synth.train_audio": {"en": "Reference audio:", "ru": "Аудио-образец:"},
    "synth.train_transcript": {"en": "Transcript:", "ru": "Транскрипт:"},
    "synth.browse_audio": {"en": "Browse...", "ru": "Обзор..."},
    "synth.train_start": {"en": "Save Voice", "ru": "Сохранить голос"},
    "synth.train_idle": {
        "en": "ComfyUI voice save is idle.",
        "ru": "Сохранение голоса в ComfyUI ожидает запуска.",
    },
    "synth.train_missing": {
        "en": "Choose an audio file and voice name first.",
        "ru": "Сначала выберите аудио и имя голоса.",
    },
    "synth.train_starting": {"en": "Starting voice save...", "ru": "Запуск сохранения голоса..."},
    "synth.train_connecting": {"en": "Connecting to ComfyUI...", "ru": "Подключение к ComfyUI..."},
    "synth.train_uploading": {
        "en": "Uploading {file} to ComfyUI...",
        "ru": "Загрузка {file} в ComfyUI...",
    },
    "synth.train_extracting": {
        "en": "Extracting and saving voice '{name}'...",
        "ru": "Извлечение и сохранение голоса '{name}'...",
    },
    "synth.train_done": {
        "en": "Saved '{name}'. Available speakers: {speakers}",
        "ru": "Голос '{name}' сохранен. Доступные голоса: {speakers}",
    },
    "synth.train_error": {"en": "Voice save failed: {msg}", "ru": "Не удалось сохранить голос: {msg}"},
    "synth.train_err_comfyui": {
        "en": "ComfyUI is not reachable at {url}.",
        "ru": "ComfyUI недоступен по адресу {url}.",
    },
    "synth.train_none": {"en": "(none)", "ru": "(нет)"},
    "synth.loading_model": {
        "en": "Loading TTS model\u2026 (may take 1\u20132 min)",
        "ru": "Загрузка TTS модели\u2026 (может занять 1\u20132 мин)",
    },
    "synth.test_loading_model": {
        "en": "Loading TTS model for test fragment...",
        "ru": "\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 TTS-\u043c\u043e\u0434\u0435\u043b\u0438 \u0434\u043b\u044f \u0442\u0435\u0441\u0442\u043e\u0432\u043e\u0433\u043e \u0444\u0440\u0430\u0433\u043c\u0435\u043d\u0442\u0430...",
    },
    "synth.loading_model_elapsed": {
        "en": "Loading TTS model\u2026 {sec}s elapsed",
        "ru": "Загрузка TTS модели\u2026 {sec} сек",
    },
    "synth.model_ready": {
        "en": "\u2714 Model loaded in {sec}s. Synthesizing\u2026",
        "ru": "\u2714 Модель загружена за {sec} сек. Синтез\u2026",
    },
    "synth.test_model_ready": {
        "en": "\u2714 Model loaded in {sec}s. Rendering test fragment...",
        "ru": "\u2714 \u041c\u043e\u0434\u0435\u043b\u044c \u0437\u0430\u0433\u0440\u0443\u0436\u0435\u043d\u0430 \u0437\u0430 {sec} \u0441\u0435\u043a. \u0420\u0435\u043d\u0434\u0435\u0440 \u0442\u0435\u0441\u0442\u0430...",
    },
    "synth.synthesizing": {
        "en": "Synthesizing first chunk\u2026",
        "ru": "\u0421\u0438\u043d\u0442\u0435\u0437 \u043f\u0435\u0440\u0432\u043e\u0433\u043e \u0447\u0430\u043d\u043a\u0430\u2026",
    },
    "synth.test_synthesizing": {
        "en": "Synthesizing test fragment...",
        "ru": "\u0421\u0438\u043d\u0442\u0435\u0437 \u0442\u0435\u0441\u0442\u043e\u0432\u043e\u0433\u043e \u0444\u0440\u0430\u0433\u043c\u0435\u043d\u0442\u0430...",
    },
    "synth.err_no_chunks": {
        "en": "No chunks in manifest to synthesize.",
        "ru": "В манифесте нет чанков для синтеза.",
    },
    "synth.cancelled": {
        "en": "Synthesis cancelled by user.",
        "ru": "Синтез отменён пользователем.",
    },
    "synth.err_exit_code": {
        "en": "TTS process exited with code {code}.",
        "ru": "TTS-процесс завершился с кодом {code}.",
    },
    "synth.complete": {
        "en": "Synthesis complete!",
        "ru": "Синтез завершён!",
    },
    "synth.test_done": {
        "en": "Test fragment is ready. Output: {path}",
        "ru": "\u0422\u0435\u0441\u0442\u043e\u0432\u044b\u0439 \u0444\u0440\u0430\u0433\u043c\u0435\u043d\u0442 \u0433\u043e\u0442\u043e\u0432. \u0424\u0430\u0439\u043b: {path}",
    },
    "synth.test_done_no_file": {
        "en": "Test run finished, but no audio file was found in {path}. Check the log above.",
        "ru": "\u0422\u0435\u0441\u0442 \u0437\u0430\u0432\u0435\u0440\u0448\u0438\u043b\u0441\u044f, \u043d\u043e \u0430\u0443\u0434\u0438\u043e\u0444\u0430\u0439\u043b \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d \u0432 {path}. \u041f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 \u043b\u043e\u0433 \u0432\u044b\u0448\u0435.",
    },
    "synth.test_next_step": {
        "en": "If the test sounds right, save the voice; the app will switch to that saved voice for the full synthesis.",
        "ru": "\u0415\u0441\u043b\u0438 \u0442\u0435\u0441\u0442 \u0437\u0432\u0443\u0447\u0438\u0442 \u0445\u043e\u0440\u043e\u0448\u043e, \u0441\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u0435 \u0433\u043e\u043b\u043e\u0441; \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u0435 \u0441\u0430\u043c\u043e \u043f\u0435\u0440\u0435\u043a\u043b\u044e\u0447\u0438\u0442 \u043f\u043e\u043b\u043d\u044b\u0439 \u0441\u0438\u043d\u0442\u0435\u0437 \u043d\u0430 \u044d\u0442\u043e\u0442 \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u043d\u044b\u0439 \u0433\u043e\u043b\u043e\u0441.",
    },
    "synth.done_detail": {
        "en": (
            "\u2714 Synthesis complete!\n"
            "Synthesized: {synthesized} chunks, skipped: {skipped}\n"
            "Output: {path}"
        ),
        "ru": (
            "\u2714 Синтез завершён!\n"
            "Синтезировано: {synthesized} чанков, пропущено: {skipped}\n"
            "Папка: {path}"
        ),
    },

    # ── Assembly page ──
    "asm.no_dir": {
        "en": "No audio directory selected",
        "ru": "\u041f\u0430\u043f\u043a\u0430 \u0430\u0443\u0434\u0438\u043e \u043d\u0435 \u0432\u044b\u0431\u0440\u0430\u043d\u0430",
    },
    "asm.select_dir": {
        "en": "Select Audio Dir",
        "ru": "\u0412\u044b\u0431\u0440\u0430\u0442\u044c \u043f\u0430\u043f\u043a\u0443 \u0430\u0443\u0434\u0438\u043e",
    },
    "asm.pause_same": {
        "en": "Pause (same voice):",
        "ru": "\u041f\u0430\u0443\u0437\u0430 (\u0442\u043e\u0442 \u0436\u0435 \u0433\u043e\u043b\u043e\u0441):",
    },
    "asm.pause_same_help": {
        "en": "Pause inserted between adjacent chunks with the same voice. Small values keep narration tight; larger values add breathing room.",
        "ru": "\u041f\u0430\u0443\u0437\u0430 \u043c\u0435\u0436\u0434\u0443 \u0441\u043e\u0441\u0435\u0434\u043d\u0438\u043c\u0438 \u0447\u0430\u043d\u043a\u0430\u043c\u0438 \u0441 \u0442\u0435\u043c \u0436\u0435 \u0433\u043e\u043b\u043e\u0441\u043e\u043c. \u041c\u0430\u043b\u044b\u0435 \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u044f \u0434\u0435\u043b\u0430\u044e\u0442 \u0447\u0442\u0435\u043d\u0438\u0435 \u043f\u043b\u043e\u0442\u043d\u0435\u0435, \u0431\u043e\u043b\u044c\u0448\u0438\u0435 \u0434\u043e\u0431\u0430\u0432\u043b\u044f\u044e\u0442 \u0432\u043e\u0437\u0434\u0443\u0445\u0430.",
    },
    "asm.pause_change": {
        "en": "Pause (voice change):",
        "ru": "\u041f\u0430\u0443\u0437\u0430 (\u0441\u043c\u0435\u043d\u0430 \u0433\u043e\u043b\u043e\u0441\u0430):",
    },
    "asm.pause_change_help": {
        "en": "Pause inserted when the next chunk uses another voice. Usually a bit longer than the same-voice pause so dialogue transitions are clearer.",
        "ru": "\u041f\u0430\u0443\u0437\u0430 \u043f\u0440\u0438 \u0441\u043c\u0435\u043d\u0435 \u0433\u043e\u043b\u043e\u0441\u0430 \u043c\u0435\u0436\u0434\u0443 \u0447\u0430\u043d\u043a\u0430\u043c\u0438. \u041e\u0431\u044b\u0447\u043d\u043e \u0447\u0443\u0442\u044c \u0434\u043b\u0438\u043d\u043d\u0435\u0435 \u043e\u0431\u044b\u0447\u043d\u043e\u0439 \u043f\u0430\u0443\u0437\u044b, \u0447\u0442\u043e\u0431\u044b \u043f\u0435\u0440\u0435\u0445\u043e\u0434\u044b \u0432 \u0434\u0438\u0430\u043b\u043e\u0433\u0430\u0445 \u0431\u044b\u043b\u0438 \u043f\u043e\u043d\u044f\u0442\u043d\u0435\u0435.",
    },
    "asm.run": {
        "en": "Assemble All Chapters",
        "ru": "\u0421\u043e\u0431\u0440\u0430\u0442\u044c \u0432\u0441\u0435 \u0433\u043b\u0430\u0432\u044b",
    },
    "asm.assembling": {
        "en": "Assembling\u2026",
        "ru": "\u0421\u0431\u043e\u0440\u043a\u0430\u2026",
    },
    "asm.complete": {
        "en": "Assembly complete!",
        "ru": "Сборка завершена!",
    },
    "asm.no_wav_found": {
        "en": "No WAV files found — run synthesis first.",
        "ru": "WAV-файлы не найдены — сначала запустите синтез.",
    },
    "asm.no_wav_in": {
        "en": "No WAV chunks in",
        "ru": "Нет WAV чанков в",
    },
    "asm.no_chapters_in": {
        "en": "No chapter dirs found in",
        "ru": "Папки глав не найдены в",
    },
    "asm.chunk_stats": {
        "en": "{chunks} chunks -> {duration}s",
        "ru": "{chunks} чанков \u2192 {duration} сек",
    },

    # ── Progress widget ──
    "asm.production_title": {
        "en": "Production preflight",
        "ru": "Production-проверка",
        "zh": "制作预检",
        "kk": "Production алдын ала тексеру",
        "uz": "Production tekshiruvi",
    },
    "asm.production_desc": {
        "en": "Build character bible, casting plan, director score, production QA, and optional package metadata from the current v2 manifest.",
        "ru": "Создаёт character bible, кастинг, режиссёрскую партитуру, production QA и метаданные пакета из текущего v2-манифеста.",
        "zh": "从当前 v2 清单生成角色档案、配音方案、导演标注、制作 QA 和可选包元数据。",
        "kk": "Ағымдағы v2 манифестінен character bible, кастинг жоспарын, режиссерлік партитураны, production QA және пакет метадеректерін жасайды.",
        "uz": "Joriy v2 manifestdan character bible, kasting rejasi, rejissyor partiturasi, production QA va ixtiyoriy paket metama'lumotlarini yaratadi.",
    },
    "asm.production_preflight": {
        "en": "Run production preflight",
        "ru": "Запустить production preflight",
        "zh": "运行制作预检",
        "kk": "Production preflight іске қосу",
        "uz": "Production preflight ishga tushirish",
    },
    "asm.production_package": {
        "en": "Prepare package",
        "ru": "Подготовить пакет",
        "zh": "准备包",
        "kk": "Пакетті дайындау",
        "uz": "Paketni tayyorlash",
    },
    "asm.production_running": {
        "en": "Running production preflight...",
        "ru": "Выполняется production preflight...",
        "zh": "正在运行制作预检...",
        "kk": "Production preflight орындалуда...",
        "uz": "Production preflight bajarilmoqda...",
    },
    "asm.production_complete": {
        "en": "Production preflight complete.",
        "ru": "Production preflight завершён.",
        "zh": "制作预检完成。",
        "kk": "Production preflight аяқталды.",
        "uz": "Production preflight tugadi.",
    },
    "asm.production_done": {
        "en": "Production report: {path}",
        "ru": "Production-отчёт: {path}",
        "zh": "制作报告：{path}",
        "kk": "Production есебі: {path}",
        "uz": "Production hisoboti: {path}",
    },
    "asm.production_package_done": {
        "en": "Production report: {run}\nPackage report: {package}",
        "ru": "Production-отчёт: {run}\nОтчёт пакета: {package}",
        "zh": "制作报告：{run}\n包报告：{package}",
        "kk": "Production есебі: {run}\nПакет есебі: {package}",
        "uz": "Production hisoboti: {run}\nPaket hisoboti: {package}",
    },

    "progress.ready": {"en": "Ready", "ru": "\u0413\u043e\u0442\u043e\u0432\u043e"},
    "progress.eta": {"en": "ETA: {eta}", "ru": "\u041e\u0441\u0442\u0430\u043b\u043e\u0441\u044c: {eta}"},
    "progress.remaining_chunks": {
        "en": "{n} left",
        "ru": "\u043e\u0441\u0442\u0430\u043b\u043e\u0441\u044c {n}",
    },

    # ── Status bar messages ──
    "status.norm_done": {
        "en": "Normalization complete. {n} chapters. Extract roles next.",
        "ru": "\u041d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0430. {n} \u0433\u043b\u0430\u0432. \u0414\u0430\u043b\u044c\u0448\u0435 \u0438\u0437\u0432\u043b\u0435\u043a\u0438\u0442\u0435 \u0440\u043e\u043b\u0438.",
        "zh": "\u89c4\u8303\u5316\u5b8c\u6210\uff1a{n} \u7ae0\u3002\u4e0b\u4e00\u6b65\u63d0\u53d6\u89d2\u8272\u3002",
        "kk": "\u041d\u043e\u0440\u043c\u0430\u043b\u0434\u0430\u0443 \u0430\u044f\u049b\u0442\u0430\u043b\u0434\u044b: {n} \u0442\u0430\u0440\u0430\u0443. \u0415\u043d\u0434\u0456 \u0440\u04e9\u043b\u0434\u0435\u0440\u0434\u0456 \u0430\u043b\u044b\u04a3\u044b\u0437.",
        "uz": "Normallashtirish tugadi: {n} bob. Keyin rollarni ajrating.",
    },
    "status.roles_done": {
        "en": "Roles and smart segments are ready. Review chunks next.",
        "ru": "\u0420\u043e\u043b\u0438 \u0438 \u0443\u043c\u043d\u044b\u0435 \u0441\u0435\u0433\u043c\u0435\u043d\u0442\u044b \u0433\u043e\u0442\u043e\u0432\u044b. \u0414\u0430\u043b\u044c\u0448\u0435 \u043f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 \u0447\u0430\u043d\u043a\u0438.",
        "zh": "\u89d2\u8272\u548c\u667a\u80fd\u7247\u6bb5\u5df2\u5c31\u7eea\u3002\u4e0b\u4e00\u6b65\u68c0\u67e5\u5206\u5757\u3002",
        "kk": "\u0420\u04e9\u043b\u0434\u0435\u0440 \u043c\u0435\u043d \u0430\u049b\u044b\u043b\u0434\u044b \u0441\u0435\u0433\u043c\u0435\u043d\u0442\u0442\u0435\u0440 \u0434\u0430\u0439\u044b\u043d. \u0415\u043d\u0434\u0456 \u0447\u0430\u043d\u043a\u0442\u0430\u0440\u0434\u044b \u0442\u0435\u043a\u0441\u0435\u0440\u0456\u04a3\u0456\u0437.",
        "uz": "Rollar va aqlli segmentlar tayyor. Keyin bo\u02bblaklarni tekshiring.",
    },
    "status.voices_done": {
        "en": "Chunks are ready. Go to Voices tab.",
        "ru": "\u0427\u0430\u043d\u043a\u0438 \u0433\u043e\u0442\u043e\u0432\u044b. \u041f\u0435\u0440\u0435\u0439\u0434\u0438\u0442\u0435 \u043d\u0430 \u0432\u043a\u043b\u0430\u0434\u043a\u0443 \u00ab\u0413\u043e\u043b\u043e\u0441\u0430\u00bb.",
        "zh": "\u5206\u5757\u5df2\u5c31\u7eea\u3002\u8fdb\u5165\u58f0\u97f3\u9875\u3002",
        "kk": "\u0427\u0430\u043d\u043a\u0442\u0430\u0440 \u0434\u0430\u0439\u044b\u043d. \u0414\u0430\u0443\u044b\u0441\u0442\u0430\u0440 \u049b\u043e\u0439\u044b\u043d\u0434\u044b\u0441\u044b\u043d\u0430 \u04e9\u0442\u0456\u04a3\u0456\u0437.",
        "uz": "Bo\u02bblaklar tayyor. Ovozlar sahifasiga o\u02bbting.",
    },
}


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
    entry = TRANSLATIONS.get(key)
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
        for key, text in catalog.items():
            TRANSLATIONS[key][lang] = text

    polished = {
        "app.title": {
            "zh": "书籍转音频",
            "kk": "Кітаптарды аудиоға",
            "uz": "Kitoblarni audioga",
        },
        "app.subtitle": {"en": "", "ru": "", "zh": "", "kk": "", "uz": ""},
        "app.lang_label": {"zh": "语言：", "kk": "Тіл:", "uz": "Til:"},
        "tab.voices": {"zh": "4. 声音", "kk": "4. Дауыстар", "uz": "4. Ovozlar"},
        "tab.voices_short": {"zh": "4. 声音", "kk": "4. Дауыс", "uz": "4. Ovoz"},
        "tab.synthesize": {"zh": "4. 声音", "kk": "4. Дауыстар", "uz": "4. Ovozlar"},
        "tab.synthesize_short": {"zh": "4. 声音", "kk": "4. Дауыс", "uz": "4. Ovoz"},
        "tab.assemble": {"zh": "5. 章节", "kk": "5. Тараулар", "uz": "5. Boblar"},
        "tab.assemble_short": {"zh": "5. 章节", "kk": "5. Тарау", "uz": "5. Bob"},
        "synth.mode_custom_voice": {
            "ru": "Свой голос",
            "zh": "自定义声音",
            "kk": "Өз дауысы",
            "uz": "O'z ovozi",
        },
        "synth.mode_preset_speakers": {
            "ru": "Готовые голоса",
            "zh": "内置声音",
            "kk": "Дайын дауыстар",
            "uz": "Tayyor ovozlar",
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
            "en": "✔ Built {n} TTS chunks! Go to the Voices tab to choose or train voices.",
            "ru": "✔ Собрано {n} TTS-чанков! Перейдите на вкладку «Голоса», чтобы выбрать или обучить голоса.",
            "zh": "✔ 已生成 {n} 个 TTS 分块。下一步进入“声音”页选择或训练声音。",
            "kk": "✔ {n} TTS чанкі дайын. Енді «Дауыстар» қойындысында дауыстарды таңдаңыз не үйретіңіз.",
            "uz": "✔ {n} TTS bo‘lagi tayyor. Endi “Ovozlar” sahifasida ovoz tanlang yoki o‘rgating.",
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
            "en": "Chunks are ready. Go to Voices tab.",
            "ru": "Чанки готовы. Перейдите на вкладку «Голоса».",
            "zh": "分块已就绪。进入“声音”页。",
            "kk": "Чанктар дайын. «Дауыстар» қойындысына өтіңіз.",
            "uz": "Bo‘laklar tayyor. “Ovozlar” sahifasiga o‘ting.",
        },
        "synth.chunks_word": {"zh": "分块"},
    }
    for key, values in polished.items():
        TRANSLATIONS[key].update(values)

    TRANSLATIONS.update(
        {
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
    )

    TRANSLATIONS.update(
        {
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
    for key, values in localized_runtime_updates.items():
        if key in TRANSLATIONS:
            TRANSLATIONS[key].update(values)
        else:
            TRANSLATIONS[key] = values

    for key, entry in TRANSLATIONS.items():
        if key.startswith("synth.asr_") or key == "synth.compact_asr_run_now":
            for code in ("zh", "kk", "uz"):
                entry.setdefault(code, entry["en"])


_install_extra_translations()
