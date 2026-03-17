"""Split chapter text into TTS-friendly chunks."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Sentence-ending punctuation followed by a space or end of string.
_SENTENCE_END_RE = re.compile(r"(?<=[.!?…»\"\)])\s+")

# Secondary split points (clause boundaries) for long sentences.
_CLAUSE_SPLIT_RE = re.compile(r"(?<=[,;])\s+|(?<=\s[—–])\s+")

DEFAULT_MAX_CHUNK_CHARS = 900
DEFAULT_MAX_SENTENCE_CHARS = 200


@dataclass
class TextChunk:
    """A single chunk of text ready for TTS."""

    index: int
    text: str
    chapter_index: int


def split_into_sentences(text: str) -> list[str]:
    """
    Split text into sentences using punctuation boundaries.

    Keeps the terminating punctuation with the sentence.
    Handles Russian text conventions (dialogue dashes, ellipsis).
    """
    parts = _SENTENCE_END_RE.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


def _break_long_sentence(sentence: str, max_chars: int) -> list[str]:
    """Break a sentence that exceeds max_chars at clause boundaries."""
    if len(sentence) <= max_chars:
        return [sentence]

    parts = _CLAUSE_SPLIT_RE.split(sentence)
    if len(parts) <= 1:
        return [sentence]

    result: list[str] = []
    current = parts[0]

    for part in parts[1:]:
        candidate = current + " " + part
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current.strip():
                result.append(current.strip())
            current = part

    if current.strip():
        result.append(current.strip())

    return result if result else [sentence]


def chunk_text(
    text: str,
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
    max_sentence_chars: int = DEFAULT_MAX_SENTENCE_CHARS,
) -> list[str]:
    """
    Split text into chunks suitable for TTS inference.

    Groups sentences into chunks that do not exceed max_chunk_chars.
    Long sentences are broken at clause boundaries before grouping.
    Each chunk ends at a natural sentence or clause boundary.
    """
    if not text or not text.strip():
        return []

    sentences = split_into_sentences(text)

    # Break long sentences at clause boundaries.
    fragments: list[str] = []
    for sent in sentences:
        fragments.extend(_break_long_sentence(sent, max_sentence_chars))

    chunks: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    for frag in fragments:
        frag_len = len(frag)
        separator_len = 1 if current_parts else 0

        if current_len + separator_len + frag_len > max_chunk_chars and current_parts:
            chunks.append(" ".join(current_parts))
            current_parts = [frag]
            current_len = frag_len
        else:
            current_parts.append(frag)
            current_len += separator_len + frag_len

    if current_parts:
        chunks.append(" ".join(current_parts))

    return chunks


def chunk_chapter(
    chapter_text: str,
    chapter_index: int,
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
    max_sentence_chars: int = DEFAULT_MAX_SENTENCE_CHARS,
) -> list[TextChunk]:
    """
    Split a chapter into indexed TextChunk objects.

    Paragraphs are preserved by chunking within paragraph groups.
    """
    paragraphs = [p.strip() for p in chapter_text.split("\n\n") if p.strip()]

    all_chunks: list[TextChunk] = []
    chunk_idx = 0
    current_parts: list[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)
        separator_len = 2 if current_parts else 0

        if para_len > max_chunk_chars:
            # Flush accumulated content first.
            if current_parts:
                for ch in chunk_text(
                    "\n\n".join(current_parts), max_chunk_chars, max_sentence_chars
                ):
                    all_chunks.append(
                        TextChunk(index=chunk_idx, text=ch, chapter_index=chapter_index)
                    )
                    chunk_idx += 1
                current_parts = []
                current_len = 0

            # Chunk the oversized paragraph by itself.
            for ch in chunk_text(para, max_chunk_chars, max_sentence_chars):
                all_chunks.append(
                    TextChunk(index=chunk_idx, text=ch, chapter_index=chapter_index)
                )
                chunk_idx += 1

        elif current_len + separator_len + para_len > max_chunk_chars and current_parts:
            # Flush current accumulation.
            combined = "\n\n".join(current_parts)
            all_chunks.append(
                TextChunk(index=chunk_idx, text=combined, chapter_index=chapter_index)
            )
            chunk_idx += 1
            current_parts = [para]
            current_len = para_len
        else:
            current_parts.append(para)
            current_len += separator_len + para_len

    if current_parts:
        combined = "\n\n".join(current_parts)
        all_chunks.append(
            TextChunk(index=chunk_idx, text=combined, chapter_index=chapter_index)
        )

    return all_chunks
