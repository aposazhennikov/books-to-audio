"""Whitespace normalization transformations."""

from __future__ import annotations

import re


def normalize_whitespace(text: str) -> str:
    """
    Normalize various whitespace anomalies in Russian text.

    - Collapse multiple spaces into one.
    - Remove trailing whitespace from lines.
    - Normalize non-breaking spaces to regular spaces.
    - Remove zero-width characters.
    - Remove form-feed and vertical tab characters.
    """
    text = text.replace("\u00a0", " ")
    text = text.replace("\u200b", "")
    text = text.replace("\u200c", "")
    text = text.replace("\u200d", "")
    text = text.replace("\ufeff", "")
    text = text.replace("\f", "")
    text = text.replace("\v", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" +$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^ +", "", text, flags=re.MULTILINE)
    return text


def repair_broken_lines(text: str) -> str:
    """
    Repair lines broken mid-word by line-wrap artifacts.

    Joins lines where one ends with a lowercase letter and the next
    begins with a lowercase letter, indicating an unwanted line break.
    """
    text = re.sub(r"([а-яё,])\n([а-яё])", r"\1 \2", text)
    return text


def repair_hyphenated_words(text: str) -> str:
    """
    Rejoin words split across lines with a soft hyphen or trailing dash.

    Common in PDF extraction where "при-\nмер" should become "пример".
    Only joins when the next line starts with a lowercase Cyrillic letter.
    """
    text = re.sub(r"(\w)\u00ad\n(\w)", r"\1\2", text)
    text = re.sub(
        r"([а-яёА-ЯЁ])\([ \t]*\r?\n(?:[ \t]*\r?\n)*[ \t]*([а-яё])",
        r"\1\2",
        text,
    )
    text = re.sub(r"([а-яёА-ЯЁ])-\n([а-яё])", r"\1\2", text)
    return text


_PDF_SPLIT_RU_WORD_RE = re.compile(
    r"\b(?P<head>[А-ЯЁа-яё]{2,16})\s+"
    r"(?P<tail>(?:быва(?:ть|л[аио]?|ет|ют)|дажн[а-яё]{2,8}|неч[а-яё]{1,8}))\b"
)


def repair_pdf_split_russian_words(text: str) -> str:
    """Rejoin conservative native-PDF Russian word splits without a hyphen.

    Some native PDF text layers lose the visual hyphen and leave one word as two
    tokens, for example ``расхлё бывать`` or ``абор дажном``.  The rule is
    deliberately narrow: it only joins tails observed in common line-wrap
    artifacts and leaves ordinary short function-word sequences untouched.
    """

    return _PDF_SPLIT_RU_WORD_RE.sub(lambda match: match.group("head") + match.group("tail"), text)


def normalize_spacing_around_punctuation(text: str) -> str:
    """
    Fix common spacing issues around punctuation marks.

    - Remove space before comma, period, colon, semicolon, exclamation, question.
    - Ensure space after comma, period, colon, semicolon (if followed by a letter).
    - Remove double spaces introduced by these fixes.
    """
    text = re.sub(r"\s+([,.:;!?])", r"\1", text)
    text = re.sub(r"([,.:;!?])([А-ЯЁа-яёA-Za-z])", r"\1 \2", text)
    text = re.sub(r"  +", " ", text)
    return text
