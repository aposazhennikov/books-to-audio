"""Split mixed narration and dialogue segments."""

from __future__ import annotations

import re
from typing import Any

from book_normalizer.chunking.llm_dialogue_markers import (
    _coalesce_dialogue_parts,
    _contains_ru_attribution_word,
    _continues_after_author_tag,
    _dash_starts_narrator_tag,
    _find_nested_dialogue_after_narrator_tag,
    _opening_quote_starts_direct_speech,
    _ru_attribution_pattern,
    _ru_speech_prefix_is_indirect,
    _split_inline_attribution,
    _starts_with_dash_dialogue,
    _starts_with_dialogue_marker,
    _starts_with_direct_speech_marker,
    _starts_with_opening_quote,
    _take_dash_speech,
    _take_narrator_tail,
    _take_quoted_speech,
    _trailing_dialogue_opener,
)
from book_normalizer.chunking.llm_segmenter_config import (
    _CLOSING_QUOTE_BY_OPENING,
    _DASH_CHARS,
    _OPENING_QUOTE_CHARS,
    _QUOTE_CHARS,
    _SYSTEM_SECTION_KINDS,
)
from book_normalizer.chunking.llm_segmenter_fields import _clean_optional, _clean_section_kind, _normalize_role
from book_normalizer.languages import normalize_book_language


def _repair_dialogue_segment_boundaries(
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Move orphan opening dialogue punctuation to the following segment."""

    repaired = [dict(segment) for segment in segments]
    for index in range(len(repaired) - 1):
        text = str(repaired[index].get("text") or "")
        opener = _trailing_dialogue_opener(text)
        if not opener:
            continue
        next_text = str(repaired[index + 1].get("text") or "")
        if not next_text.strip() or _starts_with_dialogue_marker(next_text):
            continue

        repaired[index]["text"] = text[: -len(opener)].rstrip()
        repaired[index + 1]["text"] = _attach_dialogue_opener(opener, next_text)

    return [segment for segment in repaired if str(segment.get("text") or "").strip()]

def _attach_dialogue_opener(opener: str, text: str) -> str:
    marker = opener.strip()
    if not marker:
        return text.lstrip()
    if marker[-1] in _DASH_CHARS:
        return f"{marker[-1]} {text.lstrip()}"
    return marker + text.lstrip()

def _split_mixed_dialogue_segments(
    segments: list[dict[str, Any]],
    *,
    language: str,
) -> list[dict[str, Any]]:
    """Split direct speech away from author tags inside one LLM segment."""
    from book_normalizer.chunking.llm_dialogue_speaker import _infer_dialogue_speaker

    result: list[dict[str, Any]] = []
    for segment in segments:
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
        role = _normalize_role(segment.get("role"))
        if (
            _clean_section_kind(segment.get("section_kind"), role)
            in _SYSTEM_SECTION_KINDS
        ):
            result.append(segment)
            continue

        if (
            role not in {"male", "female", "unknown"}
            and not _contains_embedded_direct_speech(text, language)
        ):
            result.append(segment)
            continue
        parts = _split_dialogue_and_narration_text(
            text,
            language=language,
            role_is_dialogue=role in {"male", "female", "unknown"},
        )
        if len(parts) <= 1:
            result.append(segment)
            continue

        for part_index, (kind, part_text) in enumerate(parts):
            row = dict(segment)
            row["text"] = part_text
            if part_index < len(parts) - 1:
                row["pause_after_ms"] = 0
                row["boundary_after"] = ""
            if kind == "narrator":
                row["role"] = "narrator"
                row["speaker"] = ""
                row["character_description"] = ""
                row["section_kind"] = "narration"
                row["emotion"] = "calm"
                row["intonation"] = "calm"
                row["_narration_repaired"] = True
                row.pop("_direct_speech_repaired", None)
            elif kind == "inner_thought":
                inferred_speaker, inferred_role = _infer_dialogue_speaker(
                    _speaker_context_for_part(parts, part_index),
                    language,
                )
                if inferred_speaker and not _clean_optional(row.get("speaker")):
                    row["speaker"] = inferred_speaker
                if inferred_role in {"male", "female"}:
                    row["role"] = inferred_role
                elif _normalize_role(row.get("role")) == "narrator":
                    row["role"] = "unknown"
                if row.get("speaker") and not row.get("character_description"):
                    row["character_description"] = (
                        "Inner-thought character inferred from local attribution."
                    )
                row["section_kind"] = "inner_thought"
                row["_inner_thought_repaired"] = True
                row.pop("_direct_speech_repaired", None)
                row.pop("_narration_repaired", None)
            else:
                inferred_speaker, inferred_role = _infer_dialogue_speaker(
                    _speaker_context_for_part(parts, part_index),
                    language,
                )
                if inferred_speaker and not _clean_optional(row.get("speaker")):
                    row["speaker"] = inferred_speaker
                if inferred_role in {"male", "female"}:
                    row["role"] = inferred_role
                elif _normalize_role(row.get("role")) == "narrator":
                    row["role"] = "unknown"
                if row.get("speaker") and not row.get("character_description"):
                    row["character_description"] = (
                        "Direct-speech character inferred from local dialogue context."
                    )
                row["section_kind"] = "dialogue"
                row["_direct_speech_repaired"] = True
                row.pop("_narration_repaired", None)
            result.append(row)
    return result

def _speaker_context_for_part(parts: list[tuple[str, str]], part_index: int) -> str:
    context = parts[part_index][1]
    if part_index + 1 < len(parts) and parts[part_index + 1][0] == "narrator":
        context = f"{context} {parts[part_index + 1][1]}"
    if part_index > 0 and parts[part_index - 1][0] == "narrator":
        context = f"{parts[part_index - 1][1]} {context}"
    return context

def _split_dialogue_and_narration_text(
    text: str,
    *,
    language: str,
    role_is_dialogue: bool,
) -> list[tuple[str, str]]:
    remaining = text.strip()
    parts: list[tuple[str, str]] = []

    while remaining:
        if not role_is_dialogue:
            if not _starts_with_dialogue_marker(remaining):
                prefix, remaining_after_prefix = _take_narration_before_direct_speech(
                    remaining,
                    language,
                )
                if prefix:
                    parts.append(("narrator", prefix))
                    remaining = remaining_after_prefix
                    continue

        quoted_inner_thought = _split_quoted_inner_thought_at_start(remaining, language)
        if quoted_inner_thought is not None:
            split_parts, remaining = quoted_inner_thought
            parts.extend(split_parts)
            continue

        quoted_thought_with_tail = _split_quoted_thought_with_external_tag(
            remaining,
            language,
        )
        if quoted_thought_with_tail is not None:
            split_parts, remaining = quoted_thought_with_tail
            parts.extend(split_parts)
            continue

        if _starts_with_opening_quote(remaining) and (
            role_is_dialogue
            or _opening_quote_starts_direct_speech(remaining, language)
            or _previous_narrator_tag_invites_quoted_speech(parts, language)
        ):
            speech, remaining = _take_quoted_speech(remaining)
            parts.append(("speech", speech))
            if remaining:
                narrator, remaining = _take_narrator_tail(remaining)
                if narrator:
                    nested = _split_dialogue_and_narration_text(
                        narrator,
                        language=language,
                        role_is_dialogue=False,
                    )
                    parts.extend(nested or [("narrator", narrator)])
            continue

        if (
            not role_is_dialogue
            and _starts_with_dash_dialogue(remaining)
            and _dash_starts_narrator_tag(remaining, language)
            and not _continues_after_author_tag(parts, remaining)
        ):
            narrator, remaining = _take_narrator_tail(remaining)
            if narrator:
                parts.append(("narrator", narrator))
            continue

        if (
            role_is_dialogue
            and _starts_with_dash_dialogue(remaining)
            and _dash_starts_narrator_tag(remaining, language)
            and _find_nested_dialogue_after_narrator_tag(remaining) is not None
        ):
            narrator, remaining = _take_narrator_tail(remaining)
            if narrator:
                parts.append(("narrator", narrator))
            continue

        if (
            role_is_dialogue
            and language == "ru"
            and _starts_with_dash_dialogue(remaining)
            and _dash_starts_narrator_tag(remaining, language)
            and _contains_ru_attribution_word(remaining)
        ):
            narrator, remaining = _take_narrator_tail(remaining)
            if narrator:
                parts.append(("narrator", narrator))
            continue

        if _starts_with_dash_dialogue(remaining):
            speech, remaining = _take_dash_speech(remaining, language)
            parts.append(("speech", speech))
            if remaining and _dash_starts_narrator_tag(remaining, language):
                narrator, remaining = _take_narrator_tail(remaining)
                if narrator:
                    nested = _split_dialogue_and_narration_text(
                        narrator,
                        language=language,
                        role_is_dialogue=False,
                    )
                    parts.extend(nested or [("narrator", narrator)])
            elif (
                remaining
                and language == "ru"
                and _contains_ru_attribution_word(remaining)
                and not _starts_with_direct_speech_marker(remaining, language)
            ):
                narrator, remaining = _take_narrator_tail(remaining)
                if narrator:
                    nested = _split_dialogue_and_narration_text(
                        narrator,
                        language=language,
                        role_is_dialogue=False,
                    )
                    parts.extend(nested or [("narrator", narrator)])
            continue

        inline = _split_inline_attribution(remaining, language)
        if inline is not None:
            speech, tail = inline
            parts.append(("speech", speech))
            narrator, remaining = _take_narrator_tail(tail)
            if narrator:
                nested = _split_dialogue_and_narration_text(
                    narrator,
                    language=language,
                    role_is_dialogue=False,
                )
                parts.extend(nested or [("narrator", narrator)])
            continue

        parts.append(("speech" if role_is_dialogue else "narrator", remaining))
        break

    return _coalesce_dialogue_parts(parts)

def _split_quoted_inner_thought_at_start(
    text: str,
    language: str,
) -> tuple[list[tuple[str, str]], str] | None:
    if normalize_book_language(language) != "ru":
        return None

    stripped = text.lstrip()
    if not stripped or stripped[0] not in _OPENING_QUOTE_CHARS:
        return None

    quote = stripped[0]
    close_quote = _CLOSING_QUOTE_BY_OPENING.get(quote, quote)
    close_index = stripped.find(close_quote, 1)
    if close_index < 0:
        return None

    body = stripped[1:close_index]
    split = _split_inner_thought_body(body)
    if split is None:
        return None

    first, narrator, rest = split
    after_quote = close_index + 1
    while after_quote < len(stripped) and stripped[after_quote] in ",.;:!?…":
        after_quote += 1
    quote_suffix = stripped[close_index:after_quote]
    remaining = stripped[after_quote:].strip()

    parts: list[tuple[str, str]] = [("inner_thought", f"{quote}{first}".strip())]
    if rest:
        parts.append(("narrator", narrator.strip()))
        parts.append(("inner_thought", f"{rest.strip()}{quote_suffix}".strip()))
    else:
        parts.append(("narrator", f"{narrator.strip()}{quote_suffix}".strip()))
    return parts, remaining

def _split_inner_thought_body(body: str) -> tuple[str, str, str] | None:
    for match in re.finditer(r"\s+[—–-]\s+", body):
        dash_index = match.start() + 1
        first = body[:dash_index].rstrip()
        tail = body[dash_index:].strip()
        if not first or not _dash_starts_narrator_tag(tail, "ru"):
            continue
        narrator, rest = _take_narrator_tail(tail)
        if not narrator or not _contains_ru_attribution_word(narrator):
            continue
        return first, narrator, rest
    return None

def _split_quoted_thought_with_external_tag(
    text: str,
    language: str,
) -> tuple[list[tuple[str, str]], str] | None:
    if normalize_book_language(language) != "ru":
        return None
    if not _starts_with_opening_quote(text):
        return None

    speech, tail = _take_quoted_speech(text)
    if not speech or not tail or not _dash_starts_narrator_tag(tail, language):
        return None
    narrator, remaining = _take_narrator_tail(tail)
    if not narrator or not _contains_ru_inner_thought_attribution(narrator):
        return None
    return [("inner_thought", speech), ("narrator", narrator)], remaining

def _contains_ru_inner_thought_attribution(text: str) -> bool:
    return bool(
        re.search(
            r"\b(?:подумал|подумала|думал|думала|решил|решила|"
            r"вспомнил|вспомнила|сообразил|сообразила|понял|поняла|"
            r"догадался|догадалась|напомнил|напомнила)\b",
            text or "",
            re.IGNORECASE,
        )
    )

def _contains_embedded_direct_speech(text: str, language: str) -> bool:
    if _starts_with_direct_speech_marker(text, language):
        return True
    if language == "ru" and _dash_starts_narrator_tag(text, language):
        return (
            _find_nested_dialogue_after_narrator_tag(text) is not None
            or _find_next_dialogue_marker(text, language) is not None
        )
    if _find_next_dialogue_marker(text, language) is not None:
        return True
    return _split_inline_attribution(text, language) is not None

def _take_narration_before_direct_speech(text: str, language: str) -> tuple[str, str]:
    marker_index = _find_next_dialogue_marker(text, language)
    inline_index = _find_next_inline_attribution_start(text, language)
    candidates = [index for index in (marker_index, inline_index) if index is not None and index > 0]
    if not candidates:
        return "", text
    split_at = min(candidates)
    return text[:split_at].strip(), text[split_at:].strip()

def _find_next_dialogue_marker(text: str, language: str) -> int | None:
    for index, char in enumerate(text):
        if index == 0:
            continue
        if (
            char in _OPENING_QUOTE_CHARS
            and (
                _opening_quote_starts_direct_speech(text[index:], language)
                or _quote_after_ru_attribution_colon(text, index, language)
            )
        ):
            return index
        if char in _DASH_CHARS and _dash_can_start_embedded_dialogue(text, index, language):
            return index
    return None

def _quote_after_ru_attribution_colon(text: str, quote_index: int, language: str) -> bool:
    """Return true for short quoted speech introduced by a Russian speech tag."""
    if normalize_book_language(language) != "ru":
        return False
    before = text[:quote_index].rstrip()
    if not before.endswith(":"):
        return False
    probe = before[:-1].rstrip()
    return bool(re.search(rf"\b(?:{_ru_attribution_pattern()})\b(?:\s+[\wА-Яа-яЁё-]+){{0,4}}$", probe, re.IGNORECASE))

def _previous_narrator_tag_invites_quoted_speech(
    parts: list[tuple[str, str]],
    language: str,
) -> bool:
    if not parts or normalize_book_language(language) != "ru":
        return False
    kind, text = parts[-1]
    if kind != "narrator":
        return False
    stripped = text.rstrip()
    if not stripped.endswith(":"):
        return False
    probe = stripped[:-1].rstrip()
    return bool(re.search(rf"\b(?:{_ru_attribution_pattern()})\b(?:\s+[\wА-Яа-яЁё-]+){{0,4}}$", probe, re.IGNORECASE))

def _dash_can_start_embedded_dialogue(text: str, index: int, language: str) -> bool:
    before = text[:index].rstrip()
    after = text[index + 1 :].lstrip()
    if not after:
        return False
    if not (not before or re.search(r"[.!?…:]\s*$", before)):
        return False
    if language == "ru":
        return not _dash_starts_narrator_tag(text[index:], language)
    return after[:1].isupper() or after[:1] in _QUOTE_CHARS

def _find_next_inline_attribution_start(text: str, language: str) -> int | None:
    if language == "ru":
        pattern = rf"(?P<speech>[^.!?…]+?,)\s*[—–-]\s*(?:\w+\s+){{0,3}}(?:{_ru_attribution_pattern()})\b"
    elif language == "en":
        pattern = (
            r"(?P<speech>[^.!?…]+?[,.!?])\s*(?:he|she|[A-Z][A-Za-z'-]{1,40})\s+"
            r"(?:said|asked|replied|shouted|whispered|cried|muttered)\b"
        )
    else:
        return None
    for match in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
        speech_start = match.start("speech")
        if language == "ru" and _ru_speech_prefix_is_indirect(match.group("speech")):
            continue
        if speech_start == 0 or re.search(r"[.!?…]\s*$", text[:speech_start]):
            return speech_start
    return None

