"""Voice-annotated chunking for multi-voice TTS synthesis.

Splits annotated chapters into chunks where each chunk belongs
to a single speaker role, respecting max character limits.
"""

from __future__ import annotations

import logging

from book_normalizer.chunking.splitter import (
    DEFAULT_MAX_CHUNK_CHARS,
    DEFAULT_MAX_SENTENCE_CHARS,
    chunk_text,
)
from book_normalizer.dialogue.models import (
    AnnotatedChapter,
    DialogueLine,
    SpeakerRole,
    VoiceAnnotatedChunk,
)

logger = logging.getLogger(__name__)

VOICE_ID_MAP: dict[SpeakerRole, str] = {
    SpeakerRole.NARRATOR: "narrator",
    SpeakerRole.MALE: "male",
    SpeakerRole.FEMALE: "female",
    SpeakerRole.UNKNOWN: "narrator",
}


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

        effective_role = role if role != SpeakerRole.UNKNOWN else SpeakerRole.NARRATOR

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
            sub_chunks = chunk_text(combined, max_chunk_chars, max_sentence_chars)
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
    """Chunk all annotated chapters, returning a dict keyed by chapter index."""
    result: dict[int, list[VoiceAnnotatedChunk]] = {}
    total_chunks = 0
    for chapter in chapters:
        ch_chunks = chunk_annotated_chapter(
            chapter, max_chunk_chars, max_sentence_chars
        )
        result[chapter.chapter_index] = ch_chunks
        total_chunks += len(ch_chunks)

    logger.info(
        "Voice-annotated chunking: %d chapter(s), %d total chunks",
        len(chapters),
        total_chunks,
    )
    return result


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
        return line.role if line.role != SpeakerRole.UNKNOWN else SpeakerRole.NARRATOR
    return SpeakerRole.NARRATOR
