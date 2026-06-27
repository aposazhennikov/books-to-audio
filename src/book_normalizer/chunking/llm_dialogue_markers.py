"""Dialogue marker and inline-attribution parsing helpers."""

from __future__ import annotations

import re

from book_normalizer.chunking.llm_segmenter_config import (
    _CLOSING_QUOTE_BY_OPENING,
    _DASH_CHARS,
    _OPENING_QUOTE_CHARS,
    _QUOTE_CHARS,
    _RU_FEMALE_ATTRIBUTION,
    _RU_MALE_ATTRIBUTION,
    _RU_NEUTRAL_ATTRIBUTION,
    _RU_SPEAKER_TOKEN,
)


def _trailing_dialogue_opener(text: str) -> str:
    stripped = text.rstrip()
    if not stripped:
        return ""
    last = stripped[-1]
    if last in _OPENING_QUOTE_CHARS or last in _DASH_CHARS:
        return stripped[len(stripped.rstrip("".join(_OPENING_QUOTE_CHARS | _DASH_CHARS))):]
    return ""

def _starts_with_dialogue_marker(text: str) -> bool:
    stripped = text.lstrip()
    return bool(stripped and (stripped[0] in _QUOTE_CHARS or stripped[0] in _DASH_CHARS))

def _starts_with_direct_speech_marker(text: str, language: str) -> bool:
    stripped = text.lstrip()
    if not stripped:
        return False
    if stripped[0] in _DASH_CHARS:
        return not _dash_starts_narrator_tag(stripped, language)
    if stripped[0] in _OPENING_QUOTE_CHARS:
        return _opening_quote_starts_direct_speech(stripped, language)
    return False

def _starts_with_opening_quote(text: str) -> bool:
    stripped = text.lstrip()
    return bool(stripped and stripped[0] in _OPENING_QUOTE_CHARS)

def _starts_with_dash_dialogue(text: str) -> bool:
    stripped = text.lstrip()
    return bool(stripped and stripped[0] in _DASH_CHARS)

def _take_quoted_speech(text: str) -> tuple[str, str]:
    stripped = text.lstrip()
    leading_ws = len(text) - len(stripped)
    quote = stripped[0]
    close_quote = _CLOSING_QUOTE_BY_OPENING.get(quote, quote)
    close_index = stripped.find(close_quote, 1)
    if close_index < 0:
        inline = _split_inline_attribution_at_start(stripped, "ru")
        if inline is not None:
            speech, tail = inline
            return speech, tail
        return text.strip(), ""

    end = leading_ws + close_index + 1
    while end < len(text) and text[end] in ",.;:!?…":
        end += 1
    return text[:end].strip(), text[end:].strip()

def _opening_quote_starts_direct_speech(text: str, language: str) -> bool:
    speech, tail = _take_quoted_speech(text)
    if not speech:
        return False
    if _quoted_speech_has_attribution_tail(speech, tail, language):
        return True

    core = _quoted_speech_core(speech)
    if not core:
        return False
    words = re.findall(r"[\wА-Яа-яЁё]+", core, flags=re.UNICODE)
    if len(words) <= 3 and not re.search(r"[!?…！？]|\.{3}", core):
        return False
    return bool(re.search(r"[.!?…。！？]\s*$", core))

def _quoted_speech_has_attribution_tail(speech: str, tail: str, language: str) -> bool:
    from book_normalizer.chunking.llm_dialogue_speaker import _infer_dialogue_speaker

    probe = f"{speech} {tail[:120]}".strip()
    if language == "ru":
        if _split_inline_attribution_at_start(probe, language) is not None:
            return True
        return _dash_starts_attribution_tag(tail, language)

    inferred_speaker, inferred_role = _infer_dialogue_speaker(probe, language)
    if inferred_speaker or inferred_role:
        return True
    if _split_inline_attribution(probe, language) is not None:
        return True
    if tail and _dash_starts_narrator_tag(tail, language):
        return True
    return False

def _dash_starts_attribution_tag(text: str, language: str) -> bool:
    stripped = text.lstrip()
    if not stripped or stripped[0] not in _DASH_CHARS:
        return False
    after_dash = stripped[1:].lstrip()
    if language == "ru":
        return bool(re.match(rf"(?:{_ru_attribution_pattern()})\b", after_dash, re.IGNORECASE))
    return _dash_starts_narrator_tag(text, language)

def _quoted_speech_core(text: str) -> str:
    stripped = text.strip()
    while stripped and stripped[-1] in ",.;:!?…，。！？":
        stripped = stripped[:-1].rstrip()
    if len(stripped) >= 2 and stripped[0] in _OPENING_QUOTE_CHARS:
        close_quote = _CLOSING_QUOTE_BY_OPENING.get(stripped[0], stripped[0])
        if stripped.endswith(close_quote):
            stripped = stripped[1:-1].strip()
    return stripped

def _take_dash_speech(text: str, language: str) -> tuple[str, str]:
    stripped = text.strip()
    dash_chars = re.escape("".join(_DASH_CHARS))
    for match in re.finditer(rf"\s*[{dash_chars}]\s*", stripped[1:]):
        split_at = match.start() + 1
        speech = stripped[:split_at].rstrip()
        tail = stripped[split_at:].strip()
        boundary_found = False
        if re.search(r"[,.!?…]\s*$", speech) and _dash_starts_narrator_tag(tail, language):
            boundary_found = True
        if re.search(r"[.!?…]\s*$", speech) and _dash_starts_new_direct_speech(tail, language):
            boundary_found = True
        if not boundary_found:
            continue
        inline = _split_dash_speech_at_inline_attribution(speech, language)
        if inline is not None:
            inline_speech, inline_tail = inline
            return inline_speech, f"{inline_tail} {tail}".strip()
        return speech, tail
    inline = _split_dash_speech_at_inline_attribution(stripped, language)
    if inline is not None:
        return inline
    narration_tail = _split_dash_speech_before_narration_tail(stripped)
    if narration_tail is not None:
        return narration_tail
    return stripped, ""

def _split_dash_speech_at_inline_attribution(text: str, language: str) -> tuple[str, str] | None:
    if not text.lstrip().startswith(("-", "—", "–")):
        return None
    bare_inline = _split_dash_speech_at_bare_inline_attribution(text, language)
    if bare_inline is not None:
        return bare_inline
    inline = _split_inline_attribution_at_start(text, language)
    if inline is None:
        return None
    speech, tag = inline
    if _dash_starts_narrator_tag(tag, language):
        return None
    return speech, tag

def _split_dash_speech_at_bare_inline_attribution(
    text: str,
    language: str,
) -> tuple[str, str] | None:
    if language != "ru":
        return None
    stripped = text.strip()
    if not stripped or stripped[0] not in _DASH_CHARS:
        return None
    speaker_after_verb = rf"(?:я|он|она|мы|{_RU_SPEAKER_TOKEN})"
    pattern = (
        rf"[,，]{{1,2}}\s*(?P<tag>(?:[\wА-Яа-яЁё-]+\s+){{0,4}}"
        rf"(?:{_ru_attribution_pattern()})\b\s+{speaker_after_verb}\b.*)"
    )
    for match in re.finditer(pattern, stripped, re.IGNORECASE | re.DOTALL):
        speech = stripped[: match.start()].rstrip()
        delimiter_match = re.match(r"[,，]{1,2}", stripped[match.start():])
        delimiter = delimiter_match.group(0) if delimiter_match else ","
        if len(re.findall(r"[\wА-Яа-яЁё-]+", speech, re.UNICODE)) < 2:
            continue
        return f"{speech}{delimiter}", match.group("tag").strip()
    return None

def _split_dash_speech_before_narration_tail(text: str) -> tuple[str, str] | None:
    stripped = text.strip()
    if not stripped or stripped[0] not in _DASH_CHARS:
        return None
    for pattern in (
        r"(?P<speech>^[—–-]\s*.+?[!?…][»”\"]\.?)\s+(?P<tail>[А-ЯЁ][^—–-].*)",
        r"(?P<speech>^[—–-]\s*.+?[!?…])\s+(?P<tail>[А-ЯЁ][^—–-]{1,240}:\s*[—–-]\s+.+)",
    ):
        match = re.search(pattern, stripped, re.DOTALL)
        if match:
            return match.group("speech").strip(), match.group("tail").strip()
    return None

def _take_narrator_tail(text: str) -> tuple[str, str]:
    from book_normalizer.chunking.llm_dialogue_splitter import _find_next_inline_attribution_start

    stripped = text.strip()
    inline_index = _find_next_inline_attribution_start(stripped, "ru")
    if inline_index is not None and inline_index > 0:
        return stripped[:inline_index].strip(), stripped[inline_index:].strip()

    nested_index = _find_nested_dialogue_after_narrator_tag(stripped)
    if nested_index is not None:
        return stripped[:nested_index].strip(), stripped[nested_index:].strip()

    match = re.search(r"(?<=[.!?…])\s+(?=[\"“„«‹「『《〈—–-]\s*\S)", stripped)
    if not match:
        return stripped, ""
    return stripped[: match.start()].strip(), stripped[match.end():].strip()

def _find_nested_dialogue_after_narrator_tag(text: str) -> int | None:
    for match in re.finditer(r"\s+(?P<dash>[—–-])\s+", text[1:]):
        index = match.start("dash") + 1
        previous = text[index - 1] if index > 0 else ""
        if previous and not (previous.isspace() or previous in ",.!?:…"):
            continue
        before = text[:index].strip()
        after = text[index:].strip()
        after_dash = after[1:].lstrip() if after and after[0] in _DASH_CHARS else after
        resumes_after_tag = bool(
            re.search(r"[,;:]\s*$", before)
            and (
                _contains_ru_attribution_word(before)
                or _dash_starts_narrator_tag(before, "ru")
            )
        )
        if not after_dash or not (
            after_dash[0].isupper()
            or after_dash[0] in _QUOTE_CHARS
            or resumes_after_tag
        ):
            continue
        colon_intro = bool(re.search(r":\s*$", before))
        long_tag_resumes_speech = bool(
            _dash_starts_narrator_tag(text, "ru")
            and re.search(r"[.!?…]\s*$", before)
            and _dash_starts_new_direct_speech(after, "ru")
        )
        if colon_intro or len(before) <= 160 and (
            _contains_ru_attribution_word(before)
            or _dash_starts_narrator_tag(before, "ru")
        ) or long_tag_resumes_speech:
            return index
    return None

def _continues_after_author_tag(parts: list[tuple[str, str]], text: str) -> bool:
    if not parts or parts[-1][0] != "narrator":
        return False
    previous = parts[-1][1].strip()
    if not (
        previous.endswith((",", ";", ":"))
        and (_contains_ru_attribution_word(previous) or _dash_starts_narrator_tag(previous, "ru"))
    ):
        return False
    stripped = text.lstrip()
    if not stripped or stripped[0] not in _DASH_CHARS:
        return False
    after_dash = stripped[1:].lstrip()
    return bool(after_dash and after_dash[0].islower())

def _dash_starts_new_direct_speech(text: str, language: str) -> bool:
    stripped = text.lstrip()
    if not stripped or stripped[0] not in _DASH_CHARS:
        return False
    if _dash_starts_narrator_tag(stripped, language):
        return False
    after_dash = stripped[1:].lstrip()
    return bool(after_dash and (after_dash[0].isupper() or after_dash[0] in _QUOTE_CHARS))

def _dash_starts_narrator_tag(text: str, language: str) -> bool:
    stripped = text.lstrip()
    if not stripped or stripped[0] not in _DASH_CHARS:
        return False
    after_dash = stripped[1:].lstrip()
    if not after_dash:
        return False
    if language == "ru":
        if re.match(rf"(?:{_ru_attribution_pattern()})\b", after_dash, re.IGNORECASE):
            return True
        first_sentence = re.split(r"(?<=[.!?…])\s+", after_dash, maxsplit=1)[0]
        if after_dash[0].islower() and re.search(r"[!?…]", first_sentence):
            return False
        return bool(
            after_dash[0].islower()
        )
    if language == "en":
        return bool(
            re.search(
                r"\b(?:said|asked|replied|shouted|whispered|cried|muttered)\b",
                after_dash[:80],
                re.IGNORECASE,
            )
        )
    return after_dash[0].islower()

def _split_inline_attribution(text: str, language: str) -> tuple[str, str] | None:
    return _split_inline_attribution_match(text, language, anchored=False)

def _split_inline_attribution_at_start(text: str, language: str) -> tuple[str, str] | None:
    return _split_inline_attribution_match(text, language, anchored=True)

def _split_inline_attribution_match(
    text: str,
    language: str,
    *,
    anchored: bool,
) -> tuple[str, str] | None:
    prefix = r"^\s*" if anchored else ""
    if language == "ru":
        for pattern in (
            rf"{prefix}(?P<speech>[^.!?…]+[,，]{{1,2}})\s*(?P<tag>[—–-]\s*(?:\w+\s+){{0,3}}(?:{_ru_attribution_pattern()})\b.*)",
            rf"{prefix}(?P<speech>[^.!?…]+[,，]{{1,2}})\s*(?P<tag>(?:\w+\s+){{0,5}}(?:{_ru_attribution_pattern()})\b.*)",
        ):
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                if _ru_speech_prefix_is_indirect(match.group("speech")):
                    continue
                if not match.group("tag").lstrip().startswith(tuple(_DASH_CHARS)):
                    speech = match.group("speech").lstrip()
                    if not speech or speech[0] not in (_QUOTE_CHARS | _DASH_CHARS):
                        continue
                return match.group("speech").strip(), match.group("tag").strip()
    if language == "en":
        match = re.search(
            rf"{prefix}(?P<speech>.+?[,.!?])\s*(?P<tag>(?:he|she|[A-Z][A-Za-z'-]{{1,40}})\s+"
            r"(?:said|asked|replied|shouted|whispered|cried|muttered)\b.*)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            return match.group("speech").strip(), match.group("tag").strip()
    return None

def _looks_like_direct_speech(text: str, language: str) -> bool:
    if _starts_with_direct_speech_marker(text, language):
        return True
    if _split_inline_attribution(text, language) is not None:
        return True
    return False

def _contains_ru_attribution_word(text: str) -> bool:
    return bool(re.search(rf"\b(?:{_ru_attribution_pattern()})\b", text or "", re.IGNORECASE))

def _ru_speech_prefix_is_indirect(text: str) -> bool:
    stripped = (text or "").lstrip()
    if not stripped or stripped[0] in _QUOTE_CHARS or stripped[0] in _DASH_CHARS:
        return False
    return bool(
        re.search(
            rf"\b(?:{_ru_attribution_pattern()})\b\s*,?\s+"
            r"(?:что|чтобы|будто|словно|как|где|куда|откуда|когда|почему|зачем|ли)\b",
            stripped,
            re.IGNORECASE,
        )
    )

def _ru_attribution_pattern() -> str:
    words = (
        *_RU_MALE_ATTRIBUTION,
        *_RU_FEMALE_ATTRIBUTION,
        *_RU_NEUTRAL_ATTRIBUTION,
        "указал",
        "указала",
    )
    return "|".join(re.escape(word) for word in words)

def _coalesce_dialogue_parts(parts: list[tuple[str, str]]) -> list[tuple[str, str]]:
    clean_parts = [(kind, re.sub(r"\s+", " ", text).strip()) for kind, text in parts if text.strip()]
    if not clean_parts:
        return []
    result: list[tuple[str, str]] = []
    for kind, text in clean_parts:
        should_keep_separate = (
            kind == "speech"
            and result
            and result[-1][0] == kind
            and _starts_with_dialogue_marker(result[-1][1])
            and _starts_with_dialogue_marker(text)
        )
        if result and result[-1][0] == kind and not should_keep_separate:
            prev_kind, prev_text = result[-1]
            result[-1] = (prev_kind, f"{prev_text} {text}".strip())
        else:
            result.append((kind, text))
    return result

