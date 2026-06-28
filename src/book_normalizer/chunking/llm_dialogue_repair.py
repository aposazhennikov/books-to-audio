"""Post-process LLM segment rows for dialogue metadata and delivery cues."""

from __future__ import annotations

import logging
import re
from typing import Any

from book_normalizer.chunking.llm_dialogue_markers import (
    _contains_ru_attribution_word,
    _dash_starts_narrator_tag,
)
from book_normalizer.chunking.llm_dialogue_speaker import (
    _clean_speaker,
    _has_direct_speech_marker,
    _infer_dialogue_speaker,
    _narration_continuation_speaker,
    _remember_dialogue_speaker,
    _repair_dialogue_metadata,
)
from book_normalizer.chunking.llm_dialogue_splitter import (
    _repair_dialogue_segment_boundaries,
    _split_mixed_dialogue_segments,
)
from book_normalizer.chunking.llm_segmenter_config import (
    _DELIVERY_CUE_RE_BY_LANGUAGE,
    _SYSTEM_SECTION_KINDS,
    ROLE_TO_VOICE_ID,
)
from book_normalizer.chunking.llm_segmenter_fields import (
    _clean_intonation,
    _clean_optional,
    _clean_section_kind,
    _is_dialogue_segment,
    _normalize_role,
)
from book_normalizer.chunking.llm_source_preservation import _segments_preserve_source
from book_normalizer.languages import normalize_book_language

logger = logging.getLogger(__name__)

def repair_segment_dialogue_boundaries(
    segments: list[dict[str, Any]],
    *,
    language: str,
) -> list[dict[str, Any]]:
    """Repair LLM/manual segment rows before grouping them into TTS chunks."""

    from book_normalizer.chunking.manifest_v2 import role_for_voice_id
    from book_normalizer.tts.voice_mapping import auto_builtin_voice_id_for_segment

    source_text = " ".join(str(segment.get("text") or "") for segment in segments)
    recent_dialogue_speakers: list[tuple[str, str]] = []
    recent_narration_texts: list[str] = []
    pending_continuation_speaker: tuple[str, str] | None = None
    previous_was_dialogue = False
    repaired_segments = _split_mixed_dialogue_segments(
        _repair_dialogue_segment_boundaries(segments),
        language=language,
    )
    rows: list[dict[str, Any]] = []
    for segment in repaired_segments:
        row = dict(segment)
        original_role = _normalize_role(row.get("role"))
        role = original_role
        text = str(row.get("text") or "")
        speaker = _clean_speaker(row.get("speaker"), language)
        section_kind = _clean_section_kind(row.get("section_kind"), role)
        character_description = _clean_optional(
            row.get("character_description")
            or row.get("role_description")
            or row.get("description")
        )
        applied_continuation_speaker = False
        speaker_matches_pending = _speaker_matches_pending_continuation(
            speaker,
            pending_continuation_speaker,
        )
        if speaker and (
            (
                _llm_speaker_needs_local_support(
                    speaker,
                    text,
                    language,
                    recent_narration_texts=recent_narration_texts,
                )
                and not speaker_matches_pending
            )
            or (
                previous_was_dialogue
                and _llm_speaker_conflicts_with_turn_taking(
                    speaker,
                    text,
                    language,
                    recent_dialogue_speakers,
                )
                and not speaker_matches_pending
            )
        ):
            speaker = ""
            character_description = ""
        if (
            pending_continuation_speaker is not None
            and (section_kind == "dialogue" or _has_direct_speech_marker(text, language))
            and not speaker
            and role in {"unknown", "narrator"}
        ):
            pending_speaker, pending_role = pending_continuation_speaker
            speaker = pending_speaker
            section_kind = "dialogue"
            applied_continuation_speaker = True
            if pending_role in {"male", "female"}:
                role = pending_role
            if speaker and not character_description:
                character_description = (
                    "Direct-speech character inferred from adjacent author tag."
                )
        role, speaker, section_kind, character_description = _repair_dialogue_metadata(
            role=role,
            speaker=speaker,
            section_kind=section_kind,
            character_description=character_description,
            text=text,
            language=language,
            recent_dialogue_speakers=recent_dialogue_speakers,
            force_narration=bool(row.get("_narration_repaired")),
            force_dialogue=(
                bool(row.get("_direct_speech_repaired"))
                or applied_continuation_speaker
                or (bool(speaker) and role in {"male", "female", "unknown"})
            ),
        )
        is_dialogue = _is_dialogue_segment(
            role=role,
            section_kind=section_kind,
            speaker=speaker,
            text=text,
        )
        if is_dialogue:
            _remember_dialogue_speaker(
                recent_dialogue_speakers,
                speaker=speaker,
                role=role,
            )
            pending_continuation_speaker = None
            previous_was_dialogue = True
        elif section_kind == "narration":
            recent_narration_texts.append(text)
            del recent_narration_texts[:-4]
            pending_continuation_speaker = _narration_continuation_speaker(
                str(row.get("text") or ""),
                language=language,
                recent_dialogue_speakers=recent_dialogue_speakers,
            )
            previous_was_dialogue = False
        else:
            pending_continuation_speaker = None
            previous_was_dialogue = False
        row["role"] = role
        row["speaker"] = speaker
        row["section_kind"] = section_kind
        row["character_description"] = character_description
        row["is_dialogue"] = is_dialogue
        existing_voice_id = str(row.get("voice_id") or "")
        existing_voice_role = role_for_voice_id(existing_voice_id, fallback="")
        voice_role_conflicts = (
            existing_voice_role in {"male", "female", "narrator"}
            and role in {"male", "female", "narrator"}
            and existing_voice_role != role
        )
        repaired_voice_conflicts = voice_role_conflicts and (
            role != original_role
            or is_dialogue
            or bool(row.get("_direct_speech_repaired"))
            or bool(row.get("_narration_repaired"))
        )
        if (
            row.get("_direct_speech_repaired")
            or row.get("_narration_repaired")
            or not existing_voice_id
            or existing_voice_id == ROLE_TO_VOICE_ID.get(original_role)
            or repaired_voice_conflicts
        ):
            row["voice_id"] = auto_builtin_voice_id_for_segment(row)
        row.pop("_direct_speech_repaired", None)
        row.pop("_narration_repaired", None)
        rows.append(row)
    rows = _apply_inner_thought_author_tags(
        rows,
        language=language,
        voice_id_for_segment=auto_builtin_voice_id_for_segment,
    )
    rows = _apply_backward_author_tag_speakers(
        rows,
        language=language,
        voice_id_for_segment=auto_builtin_voice_id_for_segment,
    )
    rows = _apply_delivery_cues(rows, language=language)
    if source_text and not _segments_preserve_source(source_text, rows):
        logger.warning(
            "Dialogue boundary repair changed segment text order/content; "
            "falling back to per-segment repairs."
        )
        return _repair_each_segment_preserving_text(
            segments,
            language=language,
            voice_id_for_segment=auto_builtin_voice_id_for_segment,
        )
    return rows


def _repair_each_segment_preserving_text(
    segments: list[dict[str, Any]],
    *,
    language: str,
    voice_id_for_segment: Any,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for segment in segments:
        source_text = str(segment.get("text") or "")
        repaired = _split_mixed_dialogue_segments(
            _repair_dialogue_segment_boundaries([dict(segment)]),
            language=language,
        )
        if not repaired or not _segments_preserve_source(source_text, repaired):
            rows.append(dict(segment))
            continue
        for row in repaired:
            row = dict(row)
            role = _normalize_role(row.get("role"))
            section_kind = _clean_section_kind(row.get("section_kind"), role)
            speaker = _clean_speaker(row.get("speaker"), language)
            row["role"] = role
            row["speaker"] = speaker
            row["section_kind"] = section_kind
            row["is_dialogue"] = _is_dialogue_segment(
                role=role,
                section_kind=section_kind,
                speaker=speaker,
                text=str(row.get("text") or ""),
            )
            row["voice_id"] = voice_id_for_segment(row)
            row.pop("_direct_speech_repaired", None)
            row.pop("_narration_repaired", None)
            row.pop("_inner_thought_repaired", None)
            rows.append(row)
    return rows


def _llm_speaker_needs_local_support(
    speaker: str,
    text: str,
    language: str,
    *,
    recent_narration_texts: list[str] | None = None,
) -> bool:
    """Return true when an LLM-provided Russian speaker is not locally proven."""

    if normalize_book_language(language) != "ru":
        return False
    if not speaker or not text:
        return False
    if len(speaker.split()) <= 1:
        return False
    if _speaker_supported_by_recent_narration(speaker, recent_narration_texts or []):
        return False
    return speaker.casefold() not in text.casefold()


def _speaker_matches_pending_continuation(
    speaker: str,
    pending_continuation_speaker: tuple[str, str] | None,
) -> bool:
    if not speaker or pending_continuation_speaker is None:
        return False
    pending_speaker, _pending_role = pending_continuation_speaker
    return speaker == pending_speaker


def _speaker_supported_by_recent_narration(
    speaker: str,
    recent_narration_texts: list[str],
) -> bool:
    if not speaker or not recent_narration_texts:
        return False
    recent_text = "\n".join(recent_narration_texts[-4:]).casefold()
    if speaker.casefold() in recent_text:
        return True
    parts = [part for part in re.split(r"\s+", speaker.strip()) if part]
    if len(parts) < 2:
        return False
    distinctive = parts[-1]
    if len(distinctive) < 3:
        return False
    return bool(
        re.search(
            rf"(?<![А-Яа-яЁё-]){re.escape(distinctive)}[а-яё-]{{0,4}}(?![А-Яа-яЁё-])",
            recent_text,
            re.IGNORECASE,
        )
    )


def _llm_speaker_conflicts_with_turn_taking(
    speaker: str,
    text: str,
    language: str,
    recent_dialogue_speakers: list[tuple[str, str]],
) -> bool:
    """Return true for unsupported repeated speaker tags in two-person dialogue."""

    if normalize_book_language(language) != "ru":
        return False
    if not speaker or speaker.casefold() in str(text or "").casefold():
        return False
    if len(recent_dialogue_speakers) < 2:
        return False
    previous_speaker = recent_dialogue_speakers[-1][0]
    if speaker != previous_speaker:
        return False
    return any(other and other != previous_speaker for other, _role in recent_dialogue_speakers[:-1])


def _apply_inner_thought_author_tags(
    rows: list[dict[str, Any]],
    *,
    language: str,
    voice_id_for_segment: Any,
) -> list[dict[str, Any]]:
    """Keep quoted inner thoughts with their author tag in the narrator voice."""

    if normalize_book_language(language) != "ru" or len(rows) < 2:
        return rows
    result = [dict(row) for row in rows]
    for index in range(len(result) - 1):
        row = result[index]
        next_row = result[index + 1]
        if str(row.get("section_kind") or "") != "dialogue":
            continue
        text = str(row.get("text") or "").lstrip()
        if not text or text[0] not in "«“\"":
            continue
        if str(next_row.get("section_kind") or "") != "narration":
            continue
        if not _is_inner_thought_author_tag(str(next_row.get("text") or "")):
            continue
        row["role"] = "narrator"
        row["speaker"] = ""
        row["section_kind"] = "narration"
        row["character_description"] = ""
        row["is_dialogue"] = False
        row["voice_id"] = voice_id_for_segment(row)
    return result


def _is_inner_thought_author_tag(text: str) -> bool:
    stripped = str(text or "").strip().casefold()
    if not stripped.startswith(("-", "—", "–")):
        return False
    return bool(
        re.search(
            r"\b(?:себе|подумал|подумала|думал|думала|вспомнил|вспомнила|"
            r"напомнил|напомнила|решил|решила|сообразил|сообразила)\b",
            stripped,
        )
    )


def _apply_backward_author_tag_speakers(
    rows: list[dict[str, Any]],
    *,
    language: str,
    voice_id_for_segment: Any,
) -> list[dict[str, Any]]:
    """Use a following Russian author tag to correct the previous dialogue speaker."""

    if normalize_book_language(language) != "ru" or len(rows) < 2:
        return rows

    speaker_roles: dict[str, str] = {}
    for row in rows:
        speaker = str(row.get("speaker") or "").strip()
        if not speaker:
            continue
        role = str(row.get("role") or "").strip()
        if speaker not in speaker_roles or role in {"male", "female"}:
            speaker_roles[speaker] = role
    if not speaker_roles:
        return rows

    result = [dict(row) for row in rows]
    for index in range(1, len(result)):
        tag_row = result[index]
        tag_text = str(tag_row.get("text") or "")
        if str(tag_row.get("section_kind") or "") != "narration":
            continue
        if not _dash_starts_narrator_tag(tag_text, language):
            continue
        if not _contains_ru_attribution_word(tag_text):
            continue

        previous = result[index - 1]
        previous_text = str(previous.get("text") or "")
        if str(previous.get("section_kind") or "") != "dialogue":
            continue
        if not _has_direct_speech_marker(previous_text, language):
            continue

        inferred_speaker, inferred_role = _infer_dialogue_speaker(tag_text, language)
        speaker = inferred_speaker or _speaker_named_in_author_tag(tag_text, speaker_roles.keys())
        if not speaker:
            continue
        role = speaker_roles.get(speaker) or inferred_role or str(previous.get("role") or "")
        previous["speaker"] = speaker
        if role in {"male", "female", "unknown"}:
            previous["role"] = role
        previous["character_description"] = (
            previous.get("character_description")
            or "Direct-speech character inferred from following author tag."
        )
        previous["voice_id"] = voice_id_for_segment(previous)

    return result


def _speaker_named_in_author_tag(text: str, candidates: Any) -> str:
    """Return the known speaker explicitly named in an author tag."""

    for speaker in sorted((str(candidate) for candidate in candidates), key=len, reverse=True):
        if re.search(rf"(?<![А-Яа-яЁё-]){re.escape(speaker)}(?![А-Яа-яЁё-])", text, re.IGNORECASE):
            return speaker
    return ""


def _apply_delivery_cues(
    rows: list[dict[str, Any]],
    *,
    language: str,
) -> list[dict[str, Any]]:
    """Apply emotional delivery to dialogue adjacent to speech tags."""

    if not rows:
        return rows
    cues_by_index = {
        index: cues
        for index, row in enumerate(rows)
        if (cues := _delivery_cues_for_text(str(row.get("text") or ""), language))
    }
    if not cues_by_index:
        return rows

    result = [dict(row) for row in rows]
    for index, cues in cues_by_index.items():
        if _row_is_explicit_dialogue(result[index]):
            _mark_row_delivery(result[index], cues)
            if _has_direct_speech_marker(str(result[index].get("text") or ""), language):
                continue

        previous_index = _adjacent_dialogue_index(result, index, step=-1)
        if previous_index is not None:
            _mark_row_delivery(result[previous_index], cues)

        next_index = _adjacent_dialogue_index(result, index, step=1)
        if next_index is not None:
            _mark_row_delivery(result[next_index], cues)

    return result

def _delivery_cues_for_text(text: str, language: str) -> list[str]:
    patterns = _DELIVERY_CUE_RE_BY_LANGUAGE.get(
        normalize_book_language(language),
        _DELIVERY_CUE_RE_BY_LANGUAGE["ru"],
    )
    return [emotion for emotion, regex in patterns if regex.search(text or "")]

def _adjacent_dialogue_index(
    rows: list[dict[str, Any]],
    start_index: int,
    *,
    step: int,
) -> int | None:
    index = start_index + step
    if index < 0 or index >= len(rows):
        return None
    row = rows[index]
    if str(row.get("section_kind") or "") in _SYSTEM_SECTION_KINDS:
        return None
    if _row_is_dialogue(row):
        return index
    return None

def _row_is_dialogue(row: dict[str, Any]) -> bool:
    text = str(row.get("text") or "").lstrip()
    return (
        _row_is_explicit_dialogue(row)
        or bool(text and text[0] in "\"“”«»‹›「」『』《》—–-")
    )

def _row_is_explicit_dialogue(row: dict[str, Any]) -> bool:
    return bool(row.get("is_dialogue")) or str(row.get("section_kind") or "") == "dialogue"

def _mark_row_delivery(row: dict[str, Any], cues: list[str]) -> None:
    emotion = cues[0] if cues else ""
    if not emotion:
        return
    intonation = _clean_intonation(row.get("intonation") or row.get("voice_tone") or "")
    if intonation and intonation not in {"calm", "neutral", emotion}:
        if not intonation.startswith(emotion):
            row["intonation"] = f"{emotion} {intonation}"
    else:
        row["intonation"] = emotion

    current_emotion = _clean_intonation(row.get("emotion") or "")
    if not current_emotion or current_emotion in {"calm", "neutral"}:
        row["emotion"] = emotion
