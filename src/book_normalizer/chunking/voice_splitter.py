"""Voice-annotated chunking for multi-voice TTS synthesis.

Splits annotated chapters into segments (finest granularity)
and then groups segments into chunks for TTS synthesis.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from book_normalizer.chunking.splitter import (
    DEFAULT_CHAPTER_PAUSE_MS,
    DEFAULT_MAX_CHUNK_CHARS,
    DEFAULT_MAX_SENTENCE_CHARS,
    DEFAULT_PARAGRAPH_PAUSE_MS,
    DEFAULT_SCENE_PAUSE_MS,
    chunk_text,
)
from book_normalizer.dialogue.models import (
    AnnotatedChapter,
    DialogueLine,
    SpeakerRole,
    VoiceAnnotatedChunk,
    VoiceSegment,
)

logger = logging.getLogger(__name__)

VOICE_ID_MAP: dict[SpeakerRole, str] = {
    SpeakerRole.NARRATOR: "narrator",
    SpeakerRole.MALE: "male",
    SpeakerRole.FEMALE: "female",
    SpeakerRole.UNKNOWN: "narrator",
}

NEW_VOICE_ID_MAP: dict[SpeakerRole, str] = {
    SpeakerRole.NARRATOR: "narrator_calm",
    SpeakerRole.MALE: "male_young",
    SpeakerRole.FEMALE: "female_warm",
    SpeakerRole.UNKNOWN: "narrator_calm",
}

DEFAULT_SPEAKER_PAUSE_MS = 600
_BOUNDARY_PRIORITY = {
    "": 0,
    "speaker": 1,
    "paragraph": 2,
    "scene": 3,
    "chapter": 4,
}


# ── Segment-level extraction (for interactive voice assignment) ──


def extract_segments_chapter(
    chapter: AnnotatedChapter,
) -> list[VoiceSegment]:
    """Extract individual voice segments from an annotated chapter.

    Each segment is a contiguous block of dialogue or narrator text
    with a single speaker role. Segments are the finest granularity
    for voice assignment by the user.
    """
    segments: list[VoiceSegment] = []
    seg_idx = 0

    for para in chapter.paragraphs:
        lines = [line for line in para.lines if line.text.strip()]
        if not lines:
            continue

        paragraph_text = " ".join(line.text.strip() for line in lines)
        if _is_scene_break_text(paragraph_text):
            _mark_last_segment_pause(
                segments,
                boundary_after="scene",
                pause_after_ms=DEFAULT_SCENE_PAUSE_MS,
            )
            continue

        paragraph_start = len(segments)
        groups = _group_by_role(lines)
        for role, group_lines in groups:
            combined = " ".join(line.text for line in group_lines)
            if not combined.strip():
                continue

            is_dialogue = any(ln.is_dialogue for ln in group_lines)
            effective_role = role
            voice_role = (
                role if role != SpeakerRole.UNKNOWN else SpeakerRole.NARRATOR
            )

            segments.append(
                VoiceSegment(
                    segment_index=seg_idx,
                    chapter_index=chapter.chapter_index,
                    is_dialogue=is_dialogue,
                    role=effective_role,
                    voice_id=NEW_VOICE_ID_MAP[voice_role],
                    intonation="neutral",
                    text=combined,
                )
            )
            seg_idx += 1

        if len(segments) > paragraph_start:
            _mark_last_segment_pause(
                segments,
                boundary_after="paragraph",
                pause_after_ms=DEFAULT_PARAGRAPH_PAUSE_MS,
            )

    _mark_last_segment_pause(
        segments,
        boundary_after="chapter",
        pause_after_ms=DEFAULT_CHAPTER_PAUSE_MS,
    )

    return segments


def extract_segments_book(
    chapters: list[AnnotatedChapter],
) -> list[VoiceSegment]:
    """Extract all segments from all chapters, flat list."""
    segments: list[VoiceSegment] = []
    for chapter in chapters:
        segments.extend(extract_segments_chapter(chapter))
    logger.info(
        "Segment extraction: %d chapter(s), %d total segments",
        len(chapters),
        len(segments),
    )
    return segments


# ── Build TTS chunks from user-assigned segments ──


def build_chunks_from_segments(
    segments: list[dict[str, Any]],
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
    max_sentence_chars: int = DEFAULT_MAX_SENTENCE_CHARS,
) -> list[dict[str, Any]]:
    """Group user-assigned segments into TTS chunks.

    Consecutive segments with the same voice_id + intonation
    within the same chapter are merged up to max_chunk_chars.
    """
    if not segments:
        return []

    from book_normalizer.chunking.llm_segmenter import repair_segment_dialogue_boundaries

    language = next(
        (str(seg.get("language") or "").strip() for seg in segments if seg.get("language")),
        "ru",
    )
    segments = repair_segment_dialogue_boundaries(
        [dict(seg) for seg in segments],
        language=language,
    )

    chunks: list[dict[str, Any]] = []
    chunk_indices: dict[int, int] = {}

    pending_text_parts: list[str] = []
    pending_chapter = segments[0].get("chapter_index", 0)
    pending_voice = segments[0].get("voice_id", "narrator_calm")
    pending_intonation = segments[0].get("intonation", "neutral")
    pending_role = _role_from_segment(segments[0])
    pending_language = str(segments[0].get("language") or "").strip()
    pending_meta = _segment_role_metadata(segments[0])
    pending_pause_after_ms = 0
    pending_boundary_after = ""

    def _next_chunk_index(chapter_index: int) -> int:
        current = chunk_indices.get(chapter_index, 0)
        chunk_indices[chapter_index] = current + 1
        return current

    def _flush() -> None:
        nonlocal pending_text_parts, pending_pause_after_ms, pending_boundary_after
        if not pending_text_parts:
            return
        combined = " ".join(pending_text_parts)
        if len(combined) <= max_chunk_chars:
            record = {
                "chapter_index": pending_chapter,
                "chunk_index": _next_chunk_index(pending_chapter),
                "role": pending_role,
                "voice_id": pending_voice,
                "language": pending_language,
                "intonation": pending_intonation,
                "text": combined,
                **pending_meta,
            }
            _add_pause_fields(
                record,
                pending_pause_after_ms,
                pending_boundary_after,
            )
            chunks.append(record)
        else:
            sub_chunks = chunk_text(
                combined, max_chunk_chars, max_sentence_chars,
            )
            for offset, sub in enumerate(sub_chunks):
                record = {
                    "chapter_index": pending_chapter,
                    "chunk_index": _next_chunk_index(pending_chapter),
                    "role": pending_role,
                    "voice_id": pending_voice,
                    "language": pending_language,
                    "intonation": pending_intonation,
                    "text": sub,
                    **pending_meta,
                }
                if offset == len(sub_chunks) - 1:
                    _add_pause_fields(
                        record,
                        pending_pause_after_ms,
                        pending_boundary_after,
                    )
                chunks.append(record)
        pending_text_parts = []
        pending_pause_after_ms = 0
        pending_boundary_after = ""

    def _apply_pending_pause(boundary_after: str, pause_after_ms: int) -> None:
        nonlocal pending_pause_after_ms, pending_boundary_after
        pending_pause_after_ms = max(pending_pause_after_ms, pause_after_ms)
        pending_boundary_after = _stronger_boundary(
            pending_boundary_after,
            boundary_after,
        )

    for seg in segments:
        seg_chapter = seg.get("chapter_index", 0)
        seg_voice = seg.get("voice_id", "narrator_calm")
        seg_intonation = seg.get("intonation", "neutral")
        seg_role = _role_from_segment(seg)
        seg_language = str(seg.get("language") or "").strip()
        seg_meta = _segment_role_metadata(seg)
        seg_text = seg.get("text", "").strip()
        if not seg_text:
            continue

        same_group = (
            seg_chapter == pending_chapter
            and seg_voice == pending_voice
            and seg_intonation == pending_intonation
            and seg_language == pending_language
            and seg_meta == pending_meta
        )

        if same_group and pending_text_parts and pending_pause_after_ms > 0:
            _flush()
            pending_text_parts = [seg_text]
            pending_chapter = seg_chapter
            pending_voice = seg_voice
            pending_intonation = seg_intonation
            pending_role = seg_role
            pending_language = seg_language
            pending_meta = seg_meta
            _apply_pending_pause(
                str(seg.get("boundary_after") or ""),
                int(seg.get("pause_after_ms") or 0),
            )
        elif same_group:
            pending_text_parts.append(seg_text)
            _apply_pending_pause(
                str(seg.get("boundary_after") or ""),
                int(seg.get("pause_after_ms") or 0),
            )
        else:
            transition_boundary = (
                "chapter" if seg_chapter != pending_chapter else "speaker"
            )
            transition_pause = (
                DEFAULT_CHAPTER_PAUSE_MS
                if seg_chapter != pending_chapter
                else DEFAULT_SPEAKER_PAUSE_MS
            )
            _apply_pending_pause(transition_boundary, transition_pause)
            _flush()
            pending_text_parts = [seg_text]
            pending_chapter = seg_chapter
            pending_voice = seg_voice
            pending_intonation = seg_intonation
            pending_role = seg_role
            pending_language = seg_language
            pending_meta = seg_meta
            _apply_pending_pause(
                str(seg.get("boundary_after") or ""),
                int(seg.get("pause_after_ms") or 0),
            )

    _flush()

    logger.info(
        "Built %d TTS chunks from %d segments",
        len(chunks),
        len(segments),
    )
    return chunks


# ── Legacy chunk-level API (kept for backward compatibility) ──


def chunk_annotated_chapter(
    chapter: AnnotatedChapter,
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
    max_sentence_chars: int = DEFAULT_MAX_SENTENCE_CHARS,
) -> list[VoiceAnnotatedChunk]:
    """Split an annotated chapter into voice-annotated chunks.

    Key rule: one chunk = one voice. When the speaker role changes,
    a new chunk starts. Within a single role, lines are grouped up
    to max_chunk_chars using sentence-boundary splitting.
    """
    all_lines = _flatten_lines(chapter)
    if not all_lines:
        return []

    groups = _group_by_role(all_lines)
    chunks: list[VoiceAnnotatedChunk] = []
    chunk_idx = 0

    for role, lines in groups:
        combined = " ".join(line.text for line in lines)
        if not combined.strip():
            continue

        effective_role = (
            role if role != SpeakerRole.UNKNOWN else SpeakerRole.NARRATOR
        )

        if len(combined) <= max_chunk_chars:
            chunks.append(
                VoiceAnnotatedChunk(
                    index=chunk_idx,
                    text=combined,
                    chapter_index=chapter.chapter_index,
                    role=effective_role,
                    voice_id=VOICE_ID_MAP[effective_role],
                )
            )
            chunk_idx += 1
        else:
            sub_chunks = chunk_text(
                combined, max_chunk_chars, max_sentence_chars,
            )
            for sub in sub_chunks:
                chunks.append(
                    VoiceAnnotatedChunk(
                        index=chunk_idx,
                        text=sub,
                        chapter_index=chapter.chapter_index,
                        role=effective_role,
                        voice_id=VOICE_ID_MAP[effective_role],
                    )
                )
                chunk_idx += 1

    return chunks


def chunk_annotated_book(
    chapters: list[AnnotatedChapter],
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
    max_sentence_chars: int = DEFAULT_MAX_SENTENCE_CHARS,
) -> dict[int, list[VoiceAnnotatedChunk]]:
    """Chunk all annotated chapters, returning dict keyed by chapter index."""
    result: dict[int, list[VoiceAnnotatedChunk]] = {}
    total_chunks = 0
    for chapter in chapters:
        ch_chunks = chunk_annotated_chapter(
            chapter, max_chunk_chars, max_sentence_chars,
        )
        result[chapter.chapter_index] = ch_chunks
        total_chunks += len(ch_chunks)

    logger.info(
        "Voice-annotated chunking: %d chapter(s), %d total chunks",
        len(chapters),
        total_chunks,
    )
    return result


# ── Internal helpers ──


def _flatten_lines(chapter: AnnotatedChapter) -> list[DialogueLine]:
    """Collect all lines from all paragraphs in order."""
    lines: list[DialogueLine] = []
    for para in chapter.paragraphs:
        lines.extend(para.lines)
    return lines


def _group_by_role(
    lines: list[DialogueLine],
) -> list[tuple[SpeakerRole, list[DialogueLine]]]:
    """Group consecutive lines that share the same effective role."""
    if not lines:
        return []

    groups: list[tuple[SpeakerRole, list[DialogueLine]]] = []
    current_role = _effective_role(lines[0])
    current_group: list[DialogueLine] = [lines[0]]

    for line in lines[1:]:
        role = _effective_role(line)
        if role == current_role:
            current_group.append(line)
        else:
            groups.append((current_role, current_group))
            current_role = role
            current_group = [line]

    groups.append((current_role, current_group))
    return groups


def _effective_role(line: DialogueLine) -> SpeakerRole:
    """Resolve UNKNOWN to NARRATOR for grouping purposes."""
    if line.is_dialogue:
        return line.role
    return SpeakerRole.NARRATOR


def _role_from_segment(seg: dict[str, Any]) -> str:
    """Infer canonical role from voice_id first, then stale role metadata."""
    role = str(seg.get("role") or "narrator").strip().lower()
    section_kind = str(seg.get("section_kind") or "").strip().lower()
    if role == "unknown" and section_kind == "dialogue":
        return "unknown"

    voice_id = str(seg.get("voice_id") or "").strip().lower()
    if voice_id == "male" or voice_id.startswith("male_"):
        return "male"
    if voice_id == "female" or voice_id.startswith("female_"):
        return "female"
    if voice_id == "narrator" or voice_id.startswith("narrator_"):
        return "narrator"

    if role in {"narrator", "male", "female", "unknown"}:
        return role
    return "narrator"


def _segment_role_metadata(seg: dict[str, Any]) -> dict[str, str]:
    """Metadata that distinguishes character/emotion chunks."""
    return {
        key: str(seg.get(key) or "").strip()
        for key in (
            "speaker",
            "character_description",
            "emotion",
            "section_kind",
        )
        if str(seg.get(key) or "").strip()
    }


def _is_scene_break_text(text: str) -> bool:
    """Return True for common standalone scene-break markers."""
    return bool(re.fullmatch(r"(?:[*#~]\s*){1,5}", text.strip()))


def _mark_last_segment_pause(
    segments: list[VoiceSegment],
    *,
    boundary_after: str,
    pause_after_ms: int,
) -> None:
    """Attach the strongest structural pause to the previous segment."""
    if not segments:
        return
    segment = segments[-1]
    segment.pause_after_ms = max(segment.pause_after_ms, pause_after_ms)
    segment.boundary_after = _stronger_boundary(
        segment.boundary_after,
        boundary_after,
    )


def _stronger_boundary(left: str, right: str) -> str:
    """Return the boundary with the stronger pause semantics."""
    if _BOUNDARY_PRIORITY.get(right, 0) > _BOUNDARY_PRIORITY.get(left, 0):
        return right
    return left


def _add_pause_fields(
    record: dict[str, Any],
    pause_after_ms: int,
    boundary_after: str,
) -> None:
    """Persist pause metadata only when it is meaningful."""
    if pause_after_ms > 0:
        record["pause_after_ms"] = pause_after_ms
    if boundary_after:
        record["boundary_after"] = boundary_after
