"""Internationalization (i18n) support for GUI — Russian / English."""

# ruff: noqa: E501

from __future__ import annotations

from typing import Any

_LANG: str = "ru"

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
    "tab.voices": {"en": "2. Voices", "ru": "2. \u0413\u043e\u043b\u043e\u0441\u0430"},
    "tab.voices_short": {"en": "2. Voices", "ru": "2. \u0413\u043e\u043b\u043e\u0441\u0430"},
    "tab.synthesize": {
        "en": "3. Synthesize",
        "ru": "3. \u0421\u0438\u043d\u0442\u0435\u0437",
    },
    "tab.synthesize_short": {
        "en": "3. TTS",
        "ru": "3. \u0421\u0438\u043d\u0442\u0435\u0437",
    },
    "tab.assemble": {
        "en": "4. Assemble",
        "ru": "4. \u0421\u0431\u043e\u0440\u043a\u0430",
    },
    "tab.assemble_short": {
        "en": "4. Build",
        "ru": "4. \u0421\u0431\u043e\u0440\u043a\u0430",
    },

    # ── Normalize page ──
    "norm.no_file": {
        "en": "No file selected",
        "ru": "\u0424\u0430\u0439\u043b \u043d\u0435 \u0432\u044b\u0431\u0440\u0430\u043d",
    },
    "norm.browse": {"en": "Browse\u2026", "ru": "\u041e\u0431\u0437\u043e\u0440\u2026"},
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
        "en": "6 = cropped text block (recommended) | 4 = single column | 3 = auto",
        "ru": "6 = \u043e\u0431\u0440\u0435\u0437\u0430\u043d\u043d\u044b\u0439 \u0431\u043b\u043e\u043a \u0442\u0435\u043a\u0441\u0442\u0430 (\u0440\u0435\u043a\u043e\u043c.) | 4 = \u043e\u0434\u043d\u0430 \u043a\u043e\u043b\u043e\u043d\u043a\u0430 | 3 = \u0430\u0432\u0442\u043e",
    },
    "norm.ocr_psm_tip": {
        "en": (
            "Tesseract Page Segmentation Mode (PSM):\n"
            "3 = fully automatic (default Tesseract)\n"
            "4 = single column of variable-size text\n"
            "6 = uniform cropped text block (recommended after auto spread splitting)\n"
            "11 = sparse text, find as much as possible\n"
            "13 = raw line, treat as single text line"
        ),
        "ru": (
            "\u0420\u0435\u0436\u0438\u043c \u0441\u0435\u0433\u043c\u0435\u043d\u0442\u0430\u0446\u0438\u0438 \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u044b Tesseract (PSM):\n"
            "3 = \u043f\u043e\u043b\u043d\u043e\u0441\u0442\u044c\u044e \u0430\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0438\u0439\n"
            "4 = \u043e\u0434\u043d\u0430 \u043a\u043e\u043b\u043e\u043d\u043a\u0430 \u0442\u0435\u043a\u0441\u0442\u0430\n"
            "6 = \u0440\u043e\u0432\u043d\u044b\u0439 \u043e\u0431\u0440\u0435\u0437\u0430\u043d\u043d\u044b\u0439 \u0431\u043b\u043e\u043a \u0442\u0435\u043a\u0441\u0442\u0430 (\u0440\u0435\u043a\u043e\u043c. \u043f\u043e\u0441\u043b\u0435 \u0430\u0432\u0442\u043e-\u0440\u0430\u0437\u0434\u0435\u043b\u0435\u043d\u0438\u044f \u0440\u0430\u0437\u0432\u043e\u0440\u043e\u0442\u043e\u0432)\n"
            "11 = \u0440\u0430\u0437\u0440\u0435\u0436\u0435\u043d\u043d\u044b\u0439 \u0442\u0435\u043a\u0441\u0442\n"
            "13 = \u043e\u0434\u043d\u0430 \u0441\u0442\u0440\u043e\u043a\u0430 \u0442\u0435\u043a\u0441\u0442\u0430"
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
        "en": "Tesseract is not installed; using native PDF text extraction.",
        "ru": "Tesseract \u043d\u0435 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d; \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u044e \u0432\u0441\u0442\u0440\u043e\u0435\u043d\u043d\u043e\u0435 \u0438\u0437\u0432\u043b\u0435\u0447\u0435\u043d\u0438\u0435 \u0442\u0435\u043a\u0441\u0442\u0430 PDF.",
    },
    "norm.err_tesseract_missing_force": {
        "en": "Tesseract is not installed. Switch OCR mode to auto/off or install Tesseract with the Russian language pack.",
        "ru": "Tesseract \u043d\u0435 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d. \u041f\u0435\u0440\u0435\u043a\u043b\u044e\u0447\u0438\u0442\u0435 OCR \u0432 auto/off \u0438\u043b\u0438 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u0435 Tesseract \u0441 \u0440\u0443\u0441\u0441\u043a\u0438\u043c \u044f\u0437\u044b\u043a\u043e\u0432\u044b\u043c \u043f\u0430\u043a\u0435\u0442\u043e\u043c.",
    },
    "norm.err_tesseract_missing_scanned": {
        "en": "The PDF text layer is missing or unreadable, and Tesseract is not installed. Install Tesseract with the Russian language pack, then run normalization again.",
        "ru": "\u0422\u0435\u043a\u0441\u0442\u043e\u0432\u044b\u0439 \u0441\u043b\u043e\u0439 PDF \u043e\u0442\u0441\u0443\u0442\u0441\u0442\u0432\u0443\u0435\u0442 \u0438\u043b\u0438 \u043d\u0435\u0447\u0438\u0442\u0430\u0435\u043c, \u0430 Tesseract \u043d\u0435 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d. \u0423\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u0435 Tesseract \u0441 \u0440\u0443\u0441\u0441\u043a\u0438\u043c \u044f\u0437\u044b\u043a\u043e\u0432\u044b\u043c \u043f\u0430\u043a\u0435\u0442\u043e\u043c \u0438 \u0437\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u0435 \u043d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044e \u0441\u043d\u043e\u0432\u0430.",
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
        "en": "Raw text (before normalization)",
        "ru": "\u0418\u0441\u0445\u043e\u0434\u043d\u044b\u0439 \u0442\u0435\u043a\u0441\u0442 (\u0434\u043e \u043d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u0438)",
    },
    "norm.norm_placeholder": {
        "en": "Normalized text (after)",
        "ru": "\u041d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u043e\u0432\u0430\u043d\u043d\u044b\u0439 \u0442\u0435\u043a\u0441\u0442 (\u043f\u043e\u0441\u043b\u0435)",
    },
    "norm.select_file": {
        "en": "Select Book File",
        "ru": "\u0412\u044b\u0431\u0440\u0430\u0442\u044c \u0444\u0430\u0439\u043b \u043a\u043d\u0438\u0433\u0438",
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
        "en": "Generate Previews (WSL)",
        "ru": "Сгенерировать превью (WSL)",
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
        "en": "Generating previews via WSL (this takes a few minutes)\u2026",
        "ru": "\u0413\u0435\u043d\u0435\u0440\u0430\u0446\u0438\u044f \u043f\u0440\u0435\u0432\u044c\u044e \u0447\u0435\u0440\u0435\u0437 WSL (\u044d\u0442\u043e \u0437\u0430\u0439\u043c\u0451\u0442 \u043d\u0435\u0441\u043a\u043e\u043b\u044c\u043a\u043e \u043c\u0438\u043d\u0443\u0442)\u2026",
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
    "synth.models_dir_hint": {
        "en": (
            "The WSL runner looks here before HuggingFace. Default points to "
            "D:\\ComfyUI-external\\models and expects Qwen folders in audio_encoders."
        ),
        "ru": (
            "WSL-runner сначала ищет модели здесь, а уже потом в HuggingFace. "
            "По умолчанию: D:\\ComfyUI-external\\models; Qwen ожидается в audio_encoders."
        ),
    },
    "synth.choose_dir": {"en": "Choose...", "ru": "Выбрать..."},
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
    "synth.seed": {
        "en": "Seed (-1=random):",
        "ru": "Seed (-1=random):",
    },
    "synth.model_help": {
        "en": "Choose the Qwen CustomVoice model for built-in speakers. 1.7B is better quality; 0.6B is faster and lighter.",
        "ru": "Модель Qwen CustomVoice для готовых спикеров. 1.7B качественнее; 0.6B быстрее и легче.",
    },
    "synth.models_dir_help": {
        "en": "Folder with downloaded models. The WSL runner checks it before downloading from HuggingFace.",
        "ru": "Папка с уже скачанными моделями. WSL-runner сначала ищет здесь, потом уже в HuggingFace.",
    },
    "synth.voice_library_dir_help": {
        "en": "Shared folder for reusable .voice.pt prompts. Saved voices can be reused across books without prompt extraction.",
        "ru": "Общая папка для reusable .voice.pt prompt'ов. Сохраненные голоса можно переиспользовать в разных книгах без prompt extraction.",
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
        "en": "SageAttention is an optional faster attention kernel in WSL. Enable only if it is installed and tested on your GPU.",
        "ru": "SageAttention — опциональное ускорение attention в WSL. Включайте только если оно установлено и проверено на вашей GPU.",
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
            "Requires SageAttention in the WSL TTS venv; GitHub v2 is preferred:\n"
            "  pip install git+https://github.com/thu-ml/SageAttention.git\n"
            "If enabled and unavailable, synthesis stops with an explicit error."
        ),
        "ru": (
            "SageAttention заменяет SDPA квантованными attention-ядрами.\n"
            "Нужен SageAttention в WSL TTS venv; GitHub v2 предпочтительнее:\n"
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
        "en": "Normalization complete. {n} chapters. Go to Voices tab.",
        "ru": "\u041d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f \u0437\u0430\u0432\u0435\u0440\u0448\u0435\u043d\u0430. {n} \u0433\u043b\u0430\u0432. \u041f\u0435\u0440\u0435\u0439\u0434\u0438\u0442\u0435 \u043d\u0430 \u0432\u043a\u043b\u0430\u0434\u043a\u0443 \u00ab\u0413\u043e\u043b\u043e\u0441\u0430\u00bb.",
    },
    "status.voices_done": {
        "en": "Voice assignment ready. Go to Synthesize tab.",
        "ru": "\u0413\u043e\u043b\u043e\u0441\u0430 \u043d\u0430\u0437\u043d\u0430\u0447\u0435\u043d\u044b. \u041f\u0435\u0440\u0435\u0439\u0434\u0438\u0442\u0435 \u043d\u0430 \u0432\u043a\u043b\u0430\u0434\u043a\u0443 \u00ab\u0421\u0438\u043d\u0442\u0435\u0437\u00bb.",
    },
}


def set_language(lang: str) -> None:
    """Set current UI language ('en' or 'ru')."""
    global _LANG  # noqa: PLW0603
    _LANG = lang


def get_language() -> str:
    """Return current UI language code."""
    return _LANG


def t(key: str, **kwargs: Any) -> str:
    """Translate key to current language, with optional format kwargs."""
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    text = entry.get(_LANG, entry.get("en", key))
    if kwargs:
        text = text.format(**kwargs)
    return text
