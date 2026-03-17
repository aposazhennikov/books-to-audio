"""Expand common Russian abbreviations for TTS readability."""

from __future__ import annotations

import re

# ── Compound multi-word abbreviations ────────────────────────────────
# Order matters: longer / more specific patterns first.
_MULTI_WORD: list[tuple[re.Pattern[str], str]] = [
    # Combined forms must come before their parts.
    (re.compile(r"\bи\s+т\.\s*д\.\s+и\s+т\.\s*п\.", re.IGNORECASE), "и так далее и тому подобное"),
    (re.compile(r"\bв\s+т\.\s*ч\.", re.IGNORECASE), "в том числе"),
    (re.compile(r"\bт\.\s*о\.", re.IGNORECASE), "таким образом"),
    (re.compile(r"\bт\.\s*е\.", re.IGNORECASE), "то есть"),
    (re.compile(r"\bт\.\s*д\.", re.IGNORECASE), "так далее"),
    (re.compile(r"\bт\.\s*п\.", re.IGNORECASE), "тому подобное"),
    (re.compile(r"\bт\.\s*н\.", re.IGNORECASE), "так называемый"),
    (re.compile(r"\bт\.\s*к\.", re.IGNORECASE), "так как"),
    (re.compile(r"\bн\.\s*э\.", re.IGNORECASE), "нашей эры"),
    (re.compile(r"\bдо\s+н\.\s*э\.", re.IGNORECASE), "до нашей эры"),
]

# ── Year / century abbreviations ─────────────────────────────────────
_YEAR_G = re.compile(r"(\d{1,4})\s*г\.")
_YEARS_GG = re.compile(r"(\d{1,4})\s*[-–—]\s*(\d{1,4})\s*гг\.")
_CENTURY_V = re.compile(r"(\b[IVXLCDM]+|\d+)\s*в\.")
_CENTURY_VV = re.compile(r"(\b[IVXLCDM]+)\s*[-–—]\s*([IVXLCDM]+)\s*вв\.")

# ── Number-adjacent abbreviations ────────────────────────────────────
# "45 млн", "10 млрд", "5 тыс." — only after digits.
_NUM_ADJACENT: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(\d)\s*млрд\.?"), r"\1 миллиардов"),
    (re.compile(r"(\d)\s*млн\.?"), r"\1 миллионов"),
    (re.compile(r"(\d)\s*тыс\."), r"\1 тысяч"),
    (re.compile(r"(\d)\s*руб\."), r"\1 рублей"),
    (re.compile(r"(\d)\s*коп\."), r"\1 копеек"),
    (re.compile(r"(\d)\s*долл\."), r"\1 долларов"),
    (re.compile(r"(\d)\s*экз\."), r"\1 экземпляров"),
]

# ── Measurement units (GOST: no dot, but occur after numbers) ────────
_UNITS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(\d)\s*км\b"), r"\1 километров"),
    (re.compile(r"(\d)\s*кг\b"), r"\1 килограммов"),
    (re.compile(r"(\d)\s*мм\b"), r"\1 миллиметров"),
    (re.compile(r"(\d)\s*см\b"), r"\1 сантиметров"),
    (re.compile(r"(\d)\s*га\b"), r"\1 гектаров"),
]

# ── Standalone abbreviations (safe to expand unconditionally) ────────
_SIMPLE: list[tuple[re.Pattern[str], str]] = [
    # Scholarly / editorial.
    (re.compile(r"\bнапр\."), "например"),
    (re.compile(r"\bдр\."), "другие"),
    (re.compile(r"\bпр\."), "прочее"),
    (re.compile(r"\bсм\."), "смотри"),
    (re.compile(r"\bср\."), "сравни"),
    (re.compile(r"\bок\."), "около"),
    (re.compile(r"\bобл\."), "область"),
    (re.compile(r"\bул\."), "улица"),
    (re.compile(r"\bпер\."), "переулок"),
    (re.compile(r"\bпл\."), "площадь"),
    (re.compile(r"\bбул\."), "бульвар"),
    (re.compile(r"\bд\."), "дом"),
    (re.compile(r"\bкорп\."), "корпус"),
    (re.compile(r"\bстр\."), "строение"),

    # Titles / positions.
    (re.compile(r"\bпроф\."), "профессор"),
    (re.compile(r"\bакад\."), "академик"),
    (re.compile(r"\bдоц\."), "доцент"),
    (re.compile(r"\bканд\."), "кандидат"),
    (re.compile(r"\bасс\."), "ассистент"),
    (re.compile(r"\bим\."), "имени"),
    (re.compile(r"\bгр\."), "гражданин"),
    (re.compile(r"\bзав\."), "заведующий"),
    (re.compile(r"\bзам\."), "заместитель"),

    # Publication / text.
    (re.compile(r"\bизд\."), "издание"),
    (re.compile(r"\bред\."), "редакция"),
    (re.compile(r"\bрис\."), "рисунок"),
    (re.compile(r"\bтабл\."), "таблица"),
    (re.compile(r"\bгл\."), "глава"),
    (re.compile(r"\bст\."), "статья"),
    (re.compile(r"\bс\.(?=\s*\d)"), "страница"),
    (re.compile(r"\bсб\."), "сборник"),
    (re.compile(r"\bвып\."), "выпуск"),

    # Time.
    (re.compile(r"\bмин\."), "минут"),
    (re.compile(r"\bсек\."), "секунд"),
    (re.compile(r"\bч\.(?=\s*\d|\s*$)"), "часов"),

    # Geography / misc.
    (re.compile(r"\bр\.(?=\s*[А-ЯЁ])"), "река"),
    (re.compile(r"\bоз\."), "озеро"),
    (re.compile(r"\bо\.(?=\s*[А-ЯЁ])"), "остров"),
    (re.compile(r"\bп\.(?=\s*[А-ЯЁ])"), "посёлок"),
    (re.compile(r"\bг\.(?=\s*[А-ЯЁ])"), "город"),

    # Miscellaneous common.
    (re.compile(r"\bб\."), "бывший"),
    (re.compile(r"\bтел\."), "телефон"),
]


def expand_abbreviations(text: str) -> str:
    """
    Replace common Russian abbreviations with their full forms.

    Designed for TTS pipelines where abbreviated text sounds unnatural.
    Multi-word abbreviations are expanded first to avoid partial matches.
    """
    # 1. Compound abbreviations (before individual parts get expanded).
    for pattern, replacement in _MULTI_WORD:
        text = pattern.sub(replacement, text)

    # 2. Year ranges: "1941—1945 гг." → "1941–1945 годов".
    text = _YEARS_GG.sub(r"\1–\2 годов", text)
    text = _YEAR_G.sub(r"\1 года", text)

    # 3. Century ranges: "XIX—XX вв." → "XIX–XX веков".
    text = _CENTURY_VV.sub(r"\1–\2 веков", text)
    text = _CENTURY_V.sub(r"\1 века", text)

    # 4. Number-adjacent: "45 млн" → "45 миллионов".
    for pattern, replacement in _NUM_ADJACENT:
        text = pattern.sub(replacement, text)

    # 5. Measurement units: "10 км" → "10 километров".
    for pattern, replacement in _UNITS:
        text = pattern.sub(replacement, text)

    # 6. Simple standalone abbreviations.
    for pattern, replacement in _SIMPLE:
        text = pattern.sub(replacement, text)

    return text
