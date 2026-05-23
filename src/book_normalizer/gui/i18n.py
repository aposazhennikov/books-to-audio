"""Internationalization (i18n) support for GUI."""

# ruff: noqa: E501

from __future__ import annotations

from typing import Any

_LANG: str = "ru"

SUPPORTED_LANGUAGES: tuple[tuple[str, str], ...] = (
    ("ru", "🇷🇺  Русский"),
    ("en", "🇬🇧  English"),
    ("zh", "🇨🇳  中文"),
    ("kk", "🇰🇿  Қазақша"),
    ("uz", "🇺🇿  Oʻzbekcha"),
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
    "norm.ocr_psm": {"en": "Tesseract PSM:", "ru": "Tesseract PSM:"},
    "norm.ocr_psm_hint": {
        "en": "Choose the layout that best matches the rendered page.",
        "ru": "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0440\u0430\u0437\u043c\u0435\u0442\u043a\u0443, \u043a\u043e\u0442\u043e\u0440\u0430\u044f \u0431\u043b\u0438\u0436\u0435 \u0432\u0441\u0435\u0433\u043e \u043a \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u0435 \u043f\u043e\u0441\u043b\u0435 \u0440\u0435\u043d\u0434\u0435\u0440\u0430.",
    },
    "norm.ocr_psm_3": {
        "en": "3 - Auto: unknown page layout",
        "ru": "3 - \u0410\u0432\u0442\u043e: \u043d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430\u044f \u0440\u0430\u0437\u043c\u0435\u0442\u043a\u0430 \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u044b",
    },
    "norm.ocr_psm_4": {
        "en": "4 - One column: normal book page",
        "ru": "4 - \u041e\u0434\u043d\u0430 \u043a\u043e\u043b\u043e\u043d\u043a\u0430: \u043e\u0431\u044b\u0447\u043d\u0430\u044f \u043a\u043d\u0438\u0436\u043d\u0430\u044f \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u0430",
    },
    "norm.ocr_psm_6": {
        "en": "6 - One block: cropped body text",
        "ru": "6 - \u041e\u0434\u0438\u043d \u0431\u043b\u043e\u043a: \u043e\u0431\u0440\u0435\u0437\u0430\u043d\u043d\u044b\u0439 \u043e\u0441\u043d\u043e\u0432\u043d\u043e\u0439 \u0442\u0435\u043a\u0441\u0442",
    },
    "norm.ocr_psm_11": {
        "en": "11 - Sparse: captions/forms/fragments",
        "ru": "11 - \u0420\u0430\u0437\u0440\u0435\u0436\u0435\u043d\u043d\u044b\u0439: \u043f\u043e\u0434\u043f\u0438\u0441\u0438, \u0444\u043e\u0440\u043c\u044b, \u0444\u0440\u0430\u0433\u043c\u0435\u043d\u0442\u044b",
    },
    "norm.ocr_psm_13": {
        "en": "13 - One raw line: short text strip",
        "ru": "13 - \u041e\u0434\u043d\u0430 \u0441\u0442\u0440\u043e\u043a\u0430: \u043a\u043e\u0440\u043e\u0442\u043a\u0438\u0439 \u0444\u0440\u0430\u0433\u043c\u0435\u043d\u0442 \u0431\u0435\u0437 \u0432\u0435\u0440\u0441\u0442\u043a\u0438",
    },
    "norm.ocr_psm_tip": {
        "en": (
            "Tesseract Page Segmentation Mode (PSM):\n"
            "3 auto = unknown layout or several blocks.\n"
            "4 one column = a normal book page with one continuous text column.\n"
            "6 one block = page already cropped to the main body text; best default for clean scans.\n"
            "11 sparse = scattered captions, forms, stamps, or fragmented OCR areas.\n"
            "13 raw line = exactly one short line; rarely useful for full pages."
        ),
        "ru": (
            "\u0420\u0435\u0436\u0438\u043c \u0441\u0435\u0433\u043c\u0435\u043d\u0442\u0430\u0446\u0438\u0438 \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u044b Tesseract (PSM):\n"
            "3 \u0430\u0432\u0442\u043e = \u043d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u0430\u044f \u0440\u0430\u0437\u043c\u0435\u0442\u043a\u0430 \u0438\u043b\u0438 \u043d\u0435\u0441\u043a\u043e\u043b\u044c\u043a\u043e \u0431\u043b\u043e\u043a\u043e\u0432.\n"
            "4 \u043e\u0434\u043d\u0430 \u043a\u043e\u043b\u043e\u043d\u043a\u0430 = \u043e\u0431\u044b\u0447\u043d\u0430\u044f \u043a\u043d\u0438\u0436\u043d\u0430\u044f \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u0430 \u0441 \u043e\u0434\u043d\u043e\u0439 \u043d\u0435\u043f\u0440\u0435\u0440\u044b\u0432\u043d\u043e\u0439 \u043a\u043e\u043b\u043e\u043d\u043a\u043e\u0439.\n"
            "6 \u043e\u0434\u0438\u043d \u0431\u043b\u043e\u043a = \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u0430 \u0443\u0436\u0435 \u043e\u0431\u0440\u0435\u0437\u0430\u043d\u0430 \u0434\u043e \u043e\u0441\u043d\u043e\u0432\u043d\u043e\u0433\u043e \u0442\u0435\u043a\u0441\u0442\u0430; \u043b\u0443\u0447\u0448\u0438\u0439 \u0434\u0435\u0444\u043e\u043b\u0442 \u0434\u043b\u044f \u0447\u0438\u0441\u0442\u044b\u0445 \u0441\u043a\u0430\u043d\u043e\u0432.\n"
            "11 \u0440\u0430\u0437\u0440\u0435\u0436\u0435\u043d\u043d\u044b\u0439 = \u043f\u043e\u0434\u043f\u0438\u0441\u0438, \u0444\u043e\u0440\u043c\u044b, \u0448\u0442\u0430\u043c\u043f\u044b \u0438\u043b\u0438 \u0440\u0430\u0437\u0440\u043e\u0437\u043d\u0435\u043d\u043d\u044b\u0435 OCR-\u043e\u0431\u043b\u0430\u0441\u0442\u0438.\n"
            "13 \u043e\u0434\u043d\u0430 \u0441\u0442\u0440\u043e\u043a\u0430 = \u0440\u043e\u0432\u043d\u043e \u043e\u0434\u043d\u0430 \u043a\u043e\u0440\u043e\u0442\u043a\u0430\u044f \u0441\u0442\u0440\u043e\u043a\u0430; \u0434\u043b\u044f \u043f\u043e\u043b\u043d\u043e\u0439 \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u044b \u043f\u043e\u0447\u0442\u0438 \u043d\u0435 \u043d\u0443\u0436\u0435\u043d."
        ),
    },
    "norm.ocr_not_applicable": {
        "en": "OCR settings apply only to PDF files",
        "ru": "\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438 OCR \u043f\u0440\u0438\u043c\u0435\u043d\u0438\u043c\u044b \u0442\u043e\u043b\u044c\u043a\u043e \u043a PDF",
    },
    "norm.llm_normalize": {
        "en": "LLM/GPU normalization:",
        "ru": "LLM/GPU \u043d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f:",
    },
    "norm.llm_normalize_check": {
        "en": "Use local model after rules",
        "ru": "\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u044c \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u0443\u044e \u043c\u043e\u0434\u0435\u043b\u044c \u043f\u043e\u0441\u043b\u0435 \u043f\u0440\u0430\u0432\u0438\u043b",
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
    "norm.loading": {
        "en": "Loading book\u2026",
        "ru": "\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u043a\u043d\u0438\u0433\u0438\u2026",
    },
    "norm.ocr_unavailable_native": {
        "en": "Tesseract is not installed; using native PDF text extraction. Run install.bat/install.sh to add OCR tools.",
        "ru": "Tesseract \u043d\u0435 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d; \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u044e \u0432\u0441\u0442\u0440\u043e\u0435\u043d\u043d\u043e\u0435 \u0438\u0437\u0432\u043b\u0435\u0447\u0435\u043d\u0438\u0435 \u0442\u0435\u043a\u0441\u0442\u0430 PDF. \u0417\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u0435 install.bat/install.sh, \u0447\u0442\u043e\u0431\u044b \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c OCR-\u0443\u0442\u0438\u043b\u0438\u0442\u044b.",
    },
    "norm.err_tesseract_missing_force": {
        "en": "Tesseract is not installed. Run install.bat/install.sh to add OCR tools, or switch OCR mode to auto/off.",
        "ru": "Tesseract \u043d\u0435 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d. \u0417\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u0435 install.bat/install.sh, \u0447\u0442\u043e\u0431\u044b \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c OCR-\u0443\u0442\u0438\u043b\u0438\u0442\u044b, \u0438\u043b\u0438 \u043f\u0435\u0440\u0435\u043a\u043b\u044e\u0447\u0438\u0442\u0435 OCR \u0432 auto/off.",
    },
    "norm.err_tesseract_missing_scanned": {
        "en": "The PDF text layer is missing or unreadable, and Tesseract is not installed. Run install.bat/install.sh to add OCR tools, then run normalization again.",
        "ru": "\u0422\u0435\u043a\u0441\u0442\u043e\u0432\u044b\u0439 \u0441\u043b\u043e\u0439 PDF \u043e\u0442\u0441\u0443\u0442\u0441\u0442\u0432\u0443\u0435\u0442 \u0438\u043b\u0438 \u043d\u0435\u0447\u0438\u0442\u0430\u0435\u043c, \u0430 Tesseract \u043d\u0435 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d. \u0417\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u0435 install.bat/install.sh, \u0447\u0442\u043e\u0431\u044b \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c OCR-\u0443\u0442\u0438\u043b\u0438\u0442\u044b, \u0438 \u0437\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u0435 \u043d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044e \u0441\u043d\u043e\u0432\u0430.",
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
    "roles.done": {
        "en": "Role inventory ready: {n} role(s).",
        "ru": "\u0421\u043f\u0438\u0441\u043e\u043a \u0440\u043e\u043b\u0435\u0439 \u0433\u043e\u0442\u043e\u0432: {n}.",
        "zh": "\u89d2\u8272\u6e05\u5355\u5df2\u5c31\u7eea\uff1a{n} \u4e2a\u89d2\u8272\u3002",
        "kk": "\u0420\u04e9\u043b\u0434\u0435\u0440 \u0442\u0456\u0437\u0456\u043c\u0456 \u0434\u0430\u0439\u044b\u043d: {n}.",
        "uz": "Rollar ro\u02bbyxati tayyor: {n}.",
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
    "roles.col_speech": {
        "en": "Direct speech",
        "ru": "\u041f\u0440\u044f\u043c\u0430\u044f \u0440\u0435\u0447\u044c",
        "zh": "\u76f4\u63a5\u5bf9\u8bdd",
        "kk": "\u0422\u0456\u043a\u0435\u043b\u0435\u0439 \u0441\u04e9\u0437",
        "uz": "Bevosita nutq",
    },
    "roles.col_emotions": {
        "en": "Emotion spectrum",
        "ru": "\u042d\u043c\u043e\u0446\u0438\u0438",
        "zh": "\u60c5\u7eea\u9891\u8c31",
        "kk": "\u042d\u043c\u043e\u0446\u0438\u044f\u043b\u0430\u0440",
        "uz": "Hissiyotlar",
    },
    "roles.col_segments": {
        "en": "Segments",
        "ru": "\u0421\u0435\u0433\u043c\u0435\u043d\u0442\u044b",
        "zh": "\u7247\u6bb5",
        "kk": "\u0421\u0435\u0433\u043c\u0435\u043d\u0442\u0442\u0435\u0440",
        "uz": "Segmentlar",
    },

    # ── Voices page ──
    "voice.speaker_mode": {
        "en": "Dialogue Attribution:",
        "ru": "\u0420\u0430\u0437\u043c\u0435\u0442\u043a\u0430 \u0440\u0435\u043f\u043b\u0438\u043a:",
    },
    "voice.speaker_mode_heuristic": {
        "en": "Rules (fast)",
        "ru": "\u041f\u0440\u0430\u0432\u0438\u043b\u0430 (\u0431\u044b\u0441\u0442\u0440\u043e)",
    },
    "voice.speaker_mode_llm": {
        "en": "LLM (smarter)",
        "ru": "LLM (\u0443\u043c\u043d\u0435\u0435)",
    },
    "voice.speaker_mode_manual": {
        "en": "Manual",
        "ru": "\u0412\u0440\u0443\u0447\u043d\u0443\u044e",
    },
    "voice.speaker_mode_hint": {
        "en": (
            "Rules (fast) - finds narrator/speech and guesses male/female "
            "dialogue by verb endings. No network.\n"
            "LLM (smarter) - asks a model to assign narrator, male, and "
            "female roles. Needs a local LLM server or OpenAI API key.\n"
            "Manual - creates segments, then lets you choose voices in the "
            "table."
        ),
        "ru": (
            "\u041f\u0440\u0430\u0432\u0438\u043b\u0430 (\u0431\u044b\u0441\u0442\u0440\u043e) - \u0438\u0449\u0435\u0442 \u0430\u0432\u0442\u043e\u0440\u0441\u043a\u0438\u0439 \u0442\u0435\u043a\u0441\u0442/\u0440\u0435\u0447\u044c \u0438 \u0443\u0433\u0430\u0434\u044b\u0432\u0430\u0435\u0442 \u043c\u0443\u0436./\u0436\u0435\u043d. "
            "\u0440\u0435\u043f\u043b\u0438\u043a\u0438 \u043f\u043e \u043e\u043a\u043e\u043d\u0447\u0430\u043d\u0438\u044f\u043c. \u0411\u0435\u0437 \u0441\u0435\u0442\u0438.\n"
            "LLM (\u0443\u043c\u043d\u0435\u0435) - \u043f\u0440\u043e\u0441\u0438\u0442 \u043c\u043e\u0434\u0435\u043b\u044c \u0440\u0430\u0437\u043c\u0435\u0442\u0438\u0442\u044c \u0440\u043e\u043b\u0438: \u0430\u0432\u0442\u043e\u0440, "
            "\u043c\u0443\u0436\u0441\u043a\u043e\u0439, \u0436\u0435\u043d\u0441\u043a\u0438\u0439. \u041d\u0443\u0436\u0435\u043d \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0439 LLM \u0438\u043b\u0438 OpenAI API \u043a\u043b\u044e\u0447.\n"
            "\u0412\u0440\u0443\u0447\u043d\u0443\u044e - \u0441\u043e\u0437\u0434\u0430\u0435\u0442 \u0441\u0435\u0433\u043c\u0435\u043d\u0442\u044b, \u0430 \u0433\u043e\u043b\u043e\u0441\u0430 \u0432\u044b\u0431\u0438\u0440\u0430\u044e\u0442\u0441\u044f \u0440\u0443\u043a\u0430\u043c\u0438 \u0432 \u0442\u0430\u0431\u043b\u0438\u0446\u0435."
        ),
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
        "en": "Detect Segments",
        "ru": "Определить сегменты",
    },
    "voice.build_chunks": {
        "en": "Build TTS Chunks",
        "ru": "Собрать чанки для TTS",
    },
    "voice.load_manifest": {
        "en": "Load Manifest",
        "ru": "Загрузить манифест",
    },
    "voice.save_manifest": {
        "en": "Save Manifest",
        "ru": "Сохранить манифест",
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
    "voice.col_voice": {"en": "Voice", "ru": "Голос"},
    "voice.col_intonation": {
        "en": "Intonation",
        "ru": "Интонация",
    },
    "voice.col_audio": {"en": "Audio", "ru": "Аудио"},
    "voice.col_retry": {"en": "Retry", "ru": "Повтор"},
    "voice.play_audio": {"en": "Play", "ru": "Play"},
    "voice.mark_retry": {"en": "Retry", "ru": "Повтор"},
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
        "en": "Split at cursor",
        "ru": "\u0420\u0430\u0437\u0434\u0435\u043b\u0438\u0442\u044c \u043f\u043e \u043a\u0443\u0440\u0441\u043e\u0440\u0443",
    },
    "voice.editor_merge_next": {
        "en": "Merge next",
        "ru": "\u0421\u043a\u043b\u0435\u0438\u0442\u044c \u0441\u043e \u0441\u043b\u0435\u0434.",
    },
    "voice.editor_delete_empty": {
        "en": "Delete if empty",
        "ru": "\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u043f\u0443\u0441\u0442\u043e\u0439",
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
        "en": "Detecting dialogue segments\u2026",
        "ru": "Определяем сегменты диалогов\u2026",
    },
    "voice.detecting_dialogue": {
        "en": "Detecting dialogue\u2026",
        "ru": "Определение диалогов\u2026",
    },
    "voice.attributing": {
        "en": "Speaker attribution ({mode})\u2026",
        "ru": "Атрибуция дикторов ({mode})\u2026",
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
        "en": "\u2714 {n} segments detected. Assign voices, then click "
              "'Build TTS Chunks'.",
        "ru": "\u2714 {n} сегментов найдено. Назначьте голоса, "
              "затем нажмите \u00abСобрать чанки для TTS\u00bb.",
    },
    "voice.chunks_done": {
        "en": "\u2714 Built {n} TTS chunks! "
              "Go to the Synthesize tab to start synthesis.",
        "ru": "\u2714 Собрано {n} TTS-чанков! "
              "Перейдите на вкладку \u00abСинтез\u00bb для запуска.",
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
        "en": "Load Manifest",
        "ru": "\u0417\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u043c\u0430\u043d\u0438\u0444\u0435\u0441\u0442",
    },
    "synth.mode_custom_voice": {
        "en": "Custom Voice",
        "ru": "Custom Voice",
    },
    "synth.mode_preset_speakers": {
        "en": "Built-in Speakers",
        "ru": "Готовые спикеры",
    },
    "synth.mode_advanced": {
        "en": "Advanced",
        "ru": "Дополнительно",
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
            "Choose an audio sample, listen to it, enter the exact spoken text, "
            "then synthesize all chunks directly in this app without ComfyUI nodes."
        ),
        "ru": (
            "Выберите аудио-образец, прослушайте его, введите точный произнесенный текст, "
            "и приложение озвучит все чанки напрямую без ComfyUI-нод."
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
        "ru": "Sample voice необязателен; если включен, prompt extraction выполнится перед чанками.",
    },
    "synth.sample_ready": {
        "en": "Sample audio loaded. Enter the exact transcript before synthesis.",
        "ru": "Sample audio загружен. Перед синтезом введите точный текст образца.",
    },
    "synth.sample_duration": {
        "en": "Sample length: {sec}s. Prompt extraction estimate: {eta}.",
        "ru": "Длина sample: {sec} с. Оценка prompt extraction: {eta}.",
    },
    "synth.sample_missing": {
        "en": "Choose sample audio and enter the exact sample text.",
        "ru": "Выберите sample audio и введите точный текст образца.",
    },
    "synth.sample_extracting": {
        "en": "Extracting voice prompt from sample audio...",
        "ru": "Извлекаю voice prompt из sample audio...",
    },
    "synth.sample_extracted": {
        "en": "Voice prompt {done}/{total} ready in {sec:.1f}s.",
        "ru": "Voice prompt {done}/{total} готов за {sec:.1f} с.",
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
        "en": "Choose an exact book chunk for preview, or paste custom text to test the current CustomVoice settings.",
        "ru": "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0442\u043e\u0447\u043d\u044b\u0439 \u0447\u0430\u043d\u043a \u0438\u0437 \u043a\u043d\u0438\u0433\u0438 \u0438\u043b\u0438 \u0432\u0441\u0442\u0430\u0432\u044c\u0442\u0435 \u0441\u0432\u043e\u0439 \u0442\u0435\u043a\u0441\u0442 \u0434\u043b\u044f \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438 \u0442\u0435\u043a\u0443\u0449\u0438\u0445 CustomVoice-\u043d\u0430\u0441\u0442\u0440\u043e\u0435\u043a.",
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
    "synth.chunk_editor_split": {
        "en": "Split at cursor",
        "ru": "\u0420\u0430\u0437\u0434\u0435\u043b\u0438\u0442\u044c \u043f\u043e \u043a\u0443\u0440\u0441\u043e\u0440\u0443",
    },
    "synth.chunk_editor_merge": {
        "en": "Merge next",
        "ru": "\u0421\u043a\u043b\u0435\u0438\u0442\u044c \u0441\u043e \u0441\u043b\u0435\u0434.",
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
    "progress.ready": {"en": "Ready", "ru": "\u0413\u043e\u0442\u043e\u0432\u043e"},
    "progress.eta": {"en": "ETA: {eta}", "ru": "\u041e\u0441\u0442\u0430\u043b\u043e\u0441\u044c: {eta}"},
    "progress.remaining_chunks": {
        "en": "{n} chunks left",
        "ru": "\u043e\u0441\u0442. {n} \u0447\u0430\u043d\u043a\u043e\u0432",
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
        "norm.ocr_psm_3": {
            "zh": "3 - 自动：未知页面版式",
            "kk": "3 - Авто: бет орналасуы белгісіз",
            "uz": "3 - Avto: sahifa tuzilmasi noma'lum",
        },
        "norm.ocr_psm_4": {
            "zh": "4 - 单栏：普通书页",
            "kk": "4 - Бір баған: кәдімгі кітап беті",
            "uz": "4 - Bir ustun: oddiy kitob sahifasi",
        },
        "norm.ocr_psm_6": {
            "zh": "6 - 单块：裁剪后的正文",
            "kk": "6 - Бір блок: қиылған негізгі мәтін",
            "uz": "6 - Bir blok: kesilgan asosiy matn",
        },
        "norm.ocr_psm_11": {
            "zh": "11 - 稀疏：题注/表单/片段",
            "kk": "11 - Сирек: жазулар, формалар, фрагменттер",
            "uz": "11 - Siyrak: izohlar, shakllar, bo'laklar",
        },
        "norm.ocr_psm_13": {
            "zh": "13 - 单行：短文本条",
            "kk": "13 - Бір жол: қысқа мәтін жолағы",
            "uz": "13 - Bir qator: qisqa matn bo'lagi",
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
        "voice.col_chunk": {"zh": "分块"},
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


_install_extra_translations()
