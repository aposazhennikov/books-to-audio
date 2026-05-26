"""Supported book language metadata for OCR, chunking, and TTS."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_BOOK_LANGUAGE = "ru"
SUPPORTED_LANGUAGE_CODES = ("ru", "en", "zh", "kk", "uz")


@dataclass(frozen=True)
class BookLanguage:
    """Runtime settings derived from a user-facing book language."""

    code: str
    english_name: str
    qwen_tts_language: str
    tesseract_lang: str
    script: str


SUPPORTED_BOOK_LANGUAGES: dict[str, BookLanguage] = {
    "ru": BookLanguage("ru", "Russian", "Russian", "rus", "cyrillic"),
    "en": BookLanguage("en", "English", "English", "eng", "latin"),
    "zh": BookLanguage("zh", "Chinese", "Chinese", "chi_sim", "han"),
    "kk": BookLanguage("kk", "Kazakh", "Kazakh", "kaz", "cyrillic"),
    "uz": BookLanguage("uz", "Uzbek", "Uzbek", "uzb", "latin"),
}

_LANGUAGE_ALIASES = {
    "": DEFAULT_BOOK_LANGUAGE,
    "rus": "ru",
    "russian": "ru",
    "ru-ru": "ru",
    "eng": "en",
    "english": "en",
    "en-us": "en",
    "en-gb": "en",
    "chi": "zh",
    "chi-sim": "zh",
    "chi_sim": "zh",
    "chinese": "zh",
    "zh-cn": "zh",
    "zh-hans": "zh",
    "kaz": "kk",
    "kazakh": "kk",
    "kz": "kk",
    "uzb": "uz",
    "uzbek": "uz",
}


def normalize_book_language(language: str | None) -> str:
    """Return a supported language code, falling back to Russian."""
    raw = str(language or "").strip().replace("_", "-").lower()
    if raw in SUPPORTED_BOOK_LANGUAGES:
        return raw
    base = raw.split("-", 1)[0]
    if base in SUPPORTED_BOOK_LANGUAGES:
        return base
    return _LANGUAGE_ALIASES.get(raw, _LANGUAGE_ALIASES.get(base, DEFAULT_BOOK_LANGUAGE))


def get_book_language(language: str | None) -> BookLanguage:
    """Return metadata for a supported language code or alias."""
    return SUPPORTED_BOOK_LANGUAGES[normalize_book_language(language)]


def is_russian_language(language: str | None) -> bool:
    """Return true when Russian-only processing rules are safe to run."""
    return normalize_book_language(language) == "ru"


def tesseract_language(language: str | None) -> str:
    """Return the Tesseract language code for OCR."""
    return get_book_language(language).tesseract_lang


def qwen_tts_language(language: str | None) -> str:
    """Return the Qwen/ComfyUI language value for synthesis workflows."""
    return get_book_language(language).qwen_tts_language


def target_script_char_count(text: str, language: str | None) -> int:
    """Count characters that belong to the selected book language script."""
    script = get_book_language(language).script
    return sum(1 for ch in text if _is_target_script_char(ch, script))


def target_script_ratio(text: str, language: str | None) -> float:
    """Return target-script share among alphabetic/CJK characters."""
    sample = text[:10000]
    candidates = [
        ch
        for ch in sample
        if ch.isalpha() or _is_target_script_char(ch, "han")
    ]
    if not candidates:
        return 0.0
    return sum(
        1
        for ch in candidates
        if _is_target_script_char(ch, get_book_language(language).script)
    ) / len(candidates)


def readable_word_ratio(text: str, language: str | None) -> float:
    """Estimate word readability for script-based OCR quality gates."""
    script = get_book_language(language).script
    if script == "han":
        return 1.0 if target_script_char_count(text, language) >= 12 else 0.0

    words: list[str] = []
    current: list[str] = []
    for ch in text:
        if _is_target_script_char(ch, script):
            current.append(ch)
            continue
        if current:
            words.append("".join(current))
            current = []
    if current:
        words.append("".join(current))
    if not words:
        return 0.0
    readable = sum(1 for word in words if len(word) >= 3)
    return readable / len(words)


def text_unreadable(text: str, language: str | None, min_ratio: float = 0.3) -> bool:
    """Return true when text is empty or does not match the selected language."""
    stripped = text.strip()
    if not stripped:
        return True
    return target_script_ratio(stripped, language) < min_ratio


def _is_target_script_char(ch: str, script: str) -> bool:
    code = ord(ch)
    if script == "cyrillic":
        return 0x0400 <= code <= 0x04FF
    if script == "latin":
        return ("A" <= ch <= "Z") or ("a" <= ch <= "z") or (0x00C0 <= code <= 0x024F)
    if script == "han":
        return (
            0x3400 <= code <= 0x4DBF
            or 0x4E00 <= code <= 0x9FFF
            or 0xF900 <= code <= 0xFAFF
        )
    return ch.isalpha()
