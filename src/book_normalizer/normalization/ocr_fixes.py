"""Automatic OCR artifact fixes for the normalization pipeline."""

from __future__ import annotations

import re

# Latin characters that look identical to Cyrillic and can be safely replaced.
_LATIN_TO_CYRILLIC: dict[str, str] = {
    "a": "\u0430", "A": "\u0410",
    "e": "\u0435", "E": "\u0415",
    "o": "\u043e", "O": "\u041e",
    "p": "\u0440", "P": "\u0420",
    "c": "\u0441", "C": "\u0421",
    "x": "\u0445", "X": "\u0425",
    "H": "\u041d",
    "K": "\u041a",
    "M": "\u041c",
    "T": "\u0422",
    "B": "\u0412",
    "y": "\u0443",
}

_MAPPABLE_LATIN = set(_LATIN_TO_CYRILLIC.keys())
_HAS_CYRILLIC = re.compile(r"[а-яёА-ЯЁ]")
_HAS_LATIN = re.compile(r"[a-zA-Z]")
_ONLY_LATIN = re.compile(r"^[a-zA-Z]+$")
_WORD_RE = re.compile(r"\S+")

# Maximum length for a purely Latin word to be auto-corrected.
_MAX_AUTOFIX_LEN = 5

# Stray OCR artifacts: single low-comma, guillemets, backticks in Cyrillic context.
_STRAY_PUNCT_IN_CYR = re.compile(
    r"(?<=[а-яёА-ЯЁ])['\u2018\u2019`\u201A\u201B\u2039\u203A‹›](?=\s|[а-яёА-ЯЁ]|$)"
)

# Spurious period inside a short OCR-broken word: "за. столом" -> "за столом".
_PERIOD_INSIDE_WORD = re.compile(
    r"\b([а-яёА-ЯЁ]{1,3})\.\s(?=[а-яёА-ЯЁ])"
)

# Native PDF extraction can drop the initial capital in "Утром" after a
# chapter heading, leaving the non-word "тром голова...".
_DROPPED_INITIAL_U = re.compile(
    r"(?<![0-9A-Za-z\u0400-\u04ff])тром(?=\s+[\u0430-\u044f\u0451])"
)

_DROPPED_INITIAL_P_PRIEM = re.compile(
    r"(?<![0-9A-Za-z\u0400-\u04ff])рием(?=\s+шел\b)"
)

_MISSING_PREPOSITION_FIXES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bс одной планет Зенов\b", re.IGNORECASE), "с одной из планет Зенов"),
    (
        re.compile(r"\bискать кристаллы оставленной кланом планете\b", re.IGNORECASE),
        "искать кристаллы на оставленной кланом планете",
    ),
    (
        re.compile(r"\bПилигримы записывали них информацию\b"),
        "Пилигримы записывали в них информацию",
    ),
    (
        re.compile(r"\bбежать не от («[^»]+»), а ней\b"),
        r"бежать не от \1, а за ней",
    ),
)

# Lone garbage characters surrounded by whitespace in Cyrillic text.
_LONE_GARBAGE = re.compile(
    r"(?<=\s)[=<>|#№\u2021\u2020\u00A7\u00B6]+(?=\s)"
)

# Square brackets can replace initial Cyrillic letters in OCR output.
_BRACKET_INITIAL_T = re.compile(r"(?<![\w\u0400-\u04ff])\](?=[ыо])", re.IGNORECASE)
_BRACKET_INITIAL_GD = re.compile(r"(?<![\w\u0400-\u04ff])\[(?=д)", re.IGNORECASE)
_BRACKET_INITIAL_G = re.compile(r"(?<![\w\u0400-\u04ff])\[(?=о)", re.IGNORECASE)
_BRACKET_INITIAL_P = re.compile(r"(?<![\w\u0400-\u04ff])\[(?=р)", re.IGNORECASE)
_BRACKET_BEFORE_RECOGNIZED_CAPITAL = re.compile(r"(?<![\w\u0400-\u04ff])\[(?=[А-ЯЁ])")
_BRACKET_AFTER_CYRILLIC_WORD = re.compile(r"(?<=[\u0400-\u04ff])\](?=\W|$)")
_GLUED_SHORT_RU_WORDS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?<![\w\u0400-\u04ff])сэтим(?![\w\u0400-\u04ff])", re.IGNORECASE), "с этим"),
    (re.compile(r"(?<![\w\u0400-\u04ff])Тоесть(?![\w\u0400-\u04ff])"), "То есть"),
    (re.compile(r"(?<![\w\u0400-\u04ff])тоесть(?![\w\u0400-\u04ff])"), "то есть"),
    (re.compile(r"(?<![\w\u0400-\u04ff])Авы(?=[,\s])"), "А вы"),
    (re.compile(r"(?<![\w\u0400-\u04ff])Ноты(?=\s+же(?![\w\u0400-\u04ff]))"), "Но ты"),
)

_FUNCTION_WORD_JOIN_RE = re.compile(
    r"(?<![А-Яа-яЁё-])"
    r"(?P<prefix>вокруг|внутри|возле|около|после|перед|между)"
    r"(?P<tail>"
    r"не(?:кому|чему|кого|чего|кем|чем)|"
    r"ни(?:кому|чему|кого|чего|кем|чем)|"
    r"(?:меня|тебя|себя|него|нее|неё|нас|вас|них|нам|вам|ним|ней)"
    r")"
    r"(?![А-Яа-яЁё-])",
    re.IGNORECASE,
)
_PAST_PLURAL_VERB_PLUS_U_RE = re.compile(
    r"(?<![А-Яа-яЁё-])(?P<verb>[а-яё]{3,}ли)у(?=\s+(?:их|его|нее|неё|них|нас|вас|меня|тебя|себя)\b)",
    re.IGNORECASE,
)
_CAPITALIZED_CYRILLIC_WORD_RE = re.compile(r"\b[А-ЯЁ][а-яё]{4,}\b")
_MID_PHRASE_CAPITALIZED_CYRILLIC_WORD_RE = re.compile(
    r"(?<![.!?…:\n]\s)(?<!^)\b[А-ЯЁ][а-яё]{4,}\b"
)
_DOUBLED_CYRILLIC_CONSONANT_RE = re.compile(r"([бвгджзклмнпрстфхцчшщ])\1", re.IGNORECASE)

# Two or more stray single characters separated by spaces (OCR junk).
_SCATTERED_CHARS = re.compile(
    r"\b([а-яёА-ЯЁa-zA-Z])\s+([а-яёА-ЯЁa-zA-Z])\s+([а-яёА-ЯЁa-zA-Z])\b"
)

_HYPHEN_PARTICLE_BASES = (
    "откуда",
    "почему",
    "зачем",
    "сколько",
    "когда",
    "какого",
    "какому",
    "какими",
    "каких",
    "каким",
    "каком",
    "какую",
    "какая",
    "какое",
    "какие",
    "какой",
    "куда",
    "кого",
    "кому",
    "кем",
    "ком",
    "кто",
    "чего",
    "чему",
    "чем",
    "чём",
    "что",
    "где",
    "как",
    "чей",
    "чья",
    "чье",
    "чьё",
    "чьи",
)
_HYPHEN_PARTICLE_RE = re.compile(
    r"(?<![А-Яа-яЁё-])"
    rf"(?P<base>{'|'.join(_HYPHEN_PARTICLE_BASES)})"
    r"(?P<particle>нибудь|либо|то)"
    r"(?![А-Яа-яЁё-])",
    re.IGNORECASE,
)

_PRONOUN_PARTICLE_BASES = (
    "меня",
    "тебя",
    "себя",
    "него",
    "нее",
    "неё",
    "нам",
    "вам",
    "мне",
    "тебе",
    "ему",
    "ней",
    "неё",
    "ним",
    "них",
    "нас",
    "вас",
    "них",
    "им",
    "ей",
    "их",
    "он",
    "она",
    "оно",
    "они",
    "мы",
    "ты",
    "вы",
    "я",
)
_PRONOUN_PARTICLE_RE = re.compile(
    r"(?<![А-Яа-яЁё-])"
    rf"(?P<base>{'|'.join(_PRONOUN_PARTICLE_BASES)})"
    r"то"
    r"(?![А-Яа-яЁё-])",
    re.IGNORECASE,
)


def _transliterate(word: str) -> str:
    """Replace Latin lookalikes with Cyrillic equivalents."""
    return "".join(_LATIN_TO_CYRILLIC.get(ch, ch) for ch in word)


def _all_chars_mappable(word: str) -> bool:
    """Check if every Latin letter in the word has a Cyrillic equivalent."""
    return all(ch in _MAPPABLE_LATIN for ch in word if ch.isalpha())


def fix_mixed_script(text: str) -> str:
    """
    Fix OCR-induced Latin characters in Cyrillic text.

    Two strategies:
    1. Mixed-script words (both Cyrillic and Latin) — replace Latin chars.
    2. Short purely-Latin words (<=5 chars) where ALL letters have Cyrillic
       lookalikes AND the surrounding text is Cyrillic — replace the whole word.
       This catches 'Ha'->'На', 'OH'->'ОН', 'HO'->'НО' etc.
    """
    words = _WORD_RE.findall(text)
    offsets = list(_WORD_RE.finditer(text))

    if not offsets:
        return text

    # Determine which words are Cyrillic for context checks.
    is_cyrillic = [bool(_HAS_CYRILLIC.search(w)) for w in words]

    result_parts: list[str] = []
    prev_end = 0

    for i, m in enumerate(offsets):
        result_parts.append(text[prev_end:m.start()])
        word = m.group(0)

        if _HAS_CYRILLIC.search(word) and _HAS_LATIN.search(word):
            result_parts.append(_transliterate(word))
        elif (
            _ONLY_LATIN.match(word)
            and len(word) <= _MAX_AUTOFIX_LEN
            and _all_chars_mappable(word)
            and _has_cyrillic_context(is_cyrillic, i)
        ):
            result_parts.append(_transliterate(word))
        else:
            result_parts.append(word)

        prev_end = m.end()

    result_parts.append(text[prev_end:])
    return "".join(result_parts)


def _has_cyrillic_context(is_cyrillic: list[bool], idx: int) -> bool:
    """Check if neighboring words (within 2 positions) contain Cyrillic."""
    for offset in (-1, 1, -2, 2):
        neighbor = idx + offset
        if 0 <= neighbor < len(is_cyrillic) and is_cyrillic[neighbor]:
            return True
    return False


def fix_russian_particle_hyphens(text: str) -> str:
    """Restore hyphens in Russian pronoun/adverb particles lost by OCR."""

    text = _HYPHEN_PARTICLE_RE.sub(r"\g<base>-\g<particle>", text)
    return _PRONOUN_PARTICLE_RE.sub(r"\g<base>-то", text)


def fix_square_bracket_ocr_artifacts(text: str) -> str:
    """Repair square brackets substituted for initial Cyrillic letters."""

    text = _BRACKET_INITIAL_T.sub("Т", text)
    text = _BRACKET_INITIAL_GD.sub("Г", text)
    text = _BRACKET_INITIAL_G.sub("Г", text)
    text = _BRACKET_INITIAL_P.sub("П", text)
    text = _BRACKET_BEFORE_RECOGNIZED_CAPITAL.sub("", text)
    return _BRACKET_AFTER_CYRILLIC_WORD.sub("", text)


def fix_glued_short_russian_words(text: str) -> str:
    """Restore spaces in short Russian function-word OCR joins."""

    for pattern, replacement in _GLUED_SHORT_RU_WORDS:
        text = pattern.sub(replacement, text)
    text = _FUNCTION_WORD_JOIN_RE.sub(r"\g<prefix> \g<tail>", text)
    text = _PAST_PLURAL_VERB_PLUS_U_RE.sub(r"\g<verb> у", text)
    return text


def collect_contextual_capitalized_words(text: str) -> set[str]:
    """Collect likely proper names/entities capitalized away from sentence starts."""

    return set(_MID_PHRASE_CAPITALIZED_CYRILLIC_WORD_RE.findall(text))


def fix_dropped_initials_from_context(
    text: str,
    candidates: set[str] | None = None,
) -> str:
    """Restore a dropped first letter when the full capitalized word is nearby."""

    candidate_words = sorted(
        set(_CAPITALIZED_CYRILLIC_WORD_RE.findall(text)).union(candidates or set()),
        key=len,
        reverse=True,
    )
    for candidate in candidate_words:
        suffix = candidate[1:].casefold()
        if len(suffix) < 4:
            continue
        pattern = re.compile(
            rf"(?<![А-Яа-яЁё-]){re.escape(suffix)}(?![А-Яа-яЁё-])"
        )
        text = pattern.sub(candidate, text)
    return text


def fix_contextual_proper_name_ocr_variants(
    text: str,
    candidates: set[str],
) -> str:
    """Repair OCR variants of known proper names without hardcoding the names."""

    text = fix_dropped_initials_from_context(text, candidates)
    for candidate in sorted(candidates, key=len, reverse=True):
        collapsed = _DOUBLED_CYRILLIC_CONSONANT_RE.sub(r"\1", candidate)
        if collapsed == candidate or len(collapsed) < 4:
            continue
        pattern = re.compile(
            rf"(?<![А-Яа-яЁё-]){re.escape(collapsed)}(?![А-Яа-яЁё-])",
            re.IGNORECASE,
        )
        text = pattern.sub(candidate, text)
    return text


_TRAILING_JUNK = re.compile(
    r"\s+[a-zA-Z.,;:!?\-]{1,3}\s*$"
)

_LEADING_COMMA_PERIOD = re.compile(
    r"^[‚,.:;]\s*"
)

_MULTI_SPACE = re.compile(r" {3,}")

_BROKEN_HYPHEN = re.compile(
    r"([а-яёА-ЯЁ])-\s*\n\s*([а-яё])"
)

_STRAY_LINE_PATTERN = re.compile(
    r"^[\s\W]{0,4}[а-яёА-ЯЁa-zA-Z]{1,2}[\s\W]{0,4}$"
)


def fix_ocr_artifacts(text: str) -> str:
    """Remove common OCR artifacts from Cyrillic text.

    Handles stray apostrophes/backticks, spurious periods inside words,
    lone garbage symbols, low-comma quotation marks, trailing junk characters,
    broken hyphenated words across lines, and scattered single-char noise
    typical of Tesseract misrecognition on Russian scans.
    """
    text = _STRAY_PUNCT_IN_CYR.sub("", text)
    text = _PERIOD_INSIDE_WORD.sub(r"\1 ", text)
    text = _DROPPED_INITIAL_U.sub("Утром", text)
    text = _DROPPED_INITIAL_P_PRIEM.sub("Прием", text)
    for pattern, replacement in _MISSING_PREPOSITION_FIXES:
        text = pattern.sub(replacement, text)
    text = _LONE_GARBAGE.sub("", text)
    text = fix_square_bracket_ocr_artifacts(text)
    text = fix_glued_short_russian_words(text)
    text = fix_dropped_initials_from_context(text)
    text = fix_russian_particle_hyphens(text)

    # Rejoin words broken by hyphenation across lines.
    text = _BROKEN_HYPHEN.sub(r"\1\2", text)

    # Remove excess whitespace (3+ spaces -> single space).
    text = _MULTI_SPACE.sub(" ", text)

    lines = text.split("\n")
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()

        # Skip empty lines (preserve one blank).
        if not stripped:
            if not cleaned or cleaned[-1].strip():
                cleaned.append("")
            continue

        # Skip lines that are just 1-2 stray characters (OCR noise).
        if _STRAY_LINE_PATTERN.match(stripped):
            if not stripped.isdigit() and stripped not in ("—", "«", "»", "—,"):
                continue

        # Remove leading stray comma/period from OCR.
        stripped = _LEADING_COMMA_PERIOD.sub("", stripped)

        # Remove trailing junk chars (1-3 random letters at line end).
        stripped = _TRAILING_JUNK.sub("", stripped)

        if stripped:
            cleaned.append(stripped)

    text = "\n".join(cleaned)
    return text
