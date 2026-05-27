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
DEFAULT_PARAGRAPH_PAUSE_MS = 450
DEFAULT_SCENE_PAUSE_MS = 900
DEFAULT_CHAPTER_PAUSE_MS = 1500


@dataclass
class TextChunk:
    """A single chunk of text ready for TTS."""

    index: int
    text: str
    chapter_index: int
    pause_after_ms: int = 0
    boundary_after: str = ""


def split_into_sentences(text: str) -> list[str]:
    """
    Split text into sentences using punctuation boundaries.

    Keeps the terminating punctuation with the sentence.
    Handles Russian text conventions (dialogue dashes, ellipsis).
    """
    stripped = text.strip()
    if not stripped:
        return []

    try:
        from razdel import sentenize
    except ImportError:
        sentenize = None

    if sentenize is not None:
        parts = [part.text.strip() for part in sentenize(stripped)]
        return [p for p in parts if p]

    parts = _SENTENCE_END_RE.split(stripped)
    return [p.strip() for p in parts if p.strip()]


def _break_long_sentence(sentence: str, max_chars: int) -> list[str]:
    """Break a sentence that exceeds max_chars without cutting words."""
    if len(sentence) <= max_chars:
        return [sentence]

    clause_parts = _CLAUSE_SPLIT_RE.split(sentence)
    parts: list[str] = []
    for part in clause_parts:
        stripped = part.strip()
        if not stripped:
            continue
        if len(stripped) > max_chars and " " in stripped:
            parts.extend(stripped.split())
        else:
            parts.append(stripped)

    if len(parts) <= 1:
        parts = sentence.split()
    if not parts:
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

    fragments: list[str] = []
    for sent in sentences:
        if len(sent) <= max_chunk_chars:
            fragments.append(sent)
            continue

        # Break only sentences that cannot fit a single TTS chunk. The
        # sentence limit remains a soft target for genuinely oversized prose.
        sentence_limit = max(1, min(max_sentence_chars, max_chunk_chars))
        fragments.extend(_break_long_sentence(sent, sentence_limit))

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

    chunks = _move_dangling_sentence_starts(chunks)
    return _merge_tiny_continuation_chunks(chunks, max_chunk_chars)


def _move_dangling_sentence_starts(chunks: list[str]) -> list[str]:
    """Move tiny sentence starts from the end of one chunk to the next chunk."""

    if len(chunks) < 2:
        return chunks

    result = list(chunks)
    index = 0
    while index < len(result) - 1:
        current = result[index].strip()
        next_chunk = result[index + 1].strip()
        split = _dangling_sentence_start_split(current)
        if split is None or not next_chunk:
            index += 1
            continue

        kept, dangling = split
        result[index] = kept
        result[index + 1] = f"{dangling} {next_chunk}".strip()
        index += 1

    return [chunk for chunk in result if chunk.strip()]


def _dangling_sentence_start_split(text: str) -> tuple[str, str] | None:
    """Return (kept, dangling_start) when a chunk ends with an orphan sentence start."""

    match = list(re.finditer(r"(?<=[.!?…])\s+", text))
    if not match:
        return None

    boundary = match[-1].end()
    kept = text[:boundary].strip()
    tail = text[boundary:].strip()
    if not kept or not tail:
        return None
    if re.search(r"[.!?…]$", tail):
        return None

    words = re.findall(r"[A-Za-zА-Яа-яЁё]+", tail)
    if not words or len(words) > 2:
        return None
    if len(tail) > 16:
        return None
    return kept, tail


def _merge_tiny_continuation_chunks(chunks: list[str], max_chunk_chars: int) -> list[str]:
    """Merge one-word/interjection chunks back into nearby text when possible."""

    result = [chunk.strip() for chunk in chunks if chunk.strip()]
    index = 0
    while index < len(result):
        chunk = result[index]
        if not _is_tiny_continuation_chunk(chunk):
            index += 1
            continue

        merged = False
        if index > 0:
            candidate = f"{result[index - 1]} {chunk}".strip()
            if len(candidate) <= max_chunk_chars:
                result[index - 1] = candidate
                del result[index]
                merged = True
        if not merged and index + 1 < len(result):
            candidate = f"{chunk} {result[index + 1]}".strip()
            if len(candidate) <= max_chunk_chars:
                result[index + 1] = candidate
                del result[index]
                merged = True
        if not merged:
            index += 1
    return result


def _is_tiny_continuation_chunk(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) > 24:
        return False
    words = re.findall(r"[A-Za-zА-Яа-яЁё]+", stripped)
    if len(words) > 2:
        return False
    if re.search(r"[.!?]$", stripped):
        return False
    return bool(words)


def _is_scene_break(paragraph: str) -> bool:
    """Return True for common standalone scene-break markers."""
    stripped = paragraph.strip()
    return bool(re.fullmatch(r"(?:[*#~]\s*){1,5}", stripped))


def _make_chunk(
    index: int,
    text: str,
    chapter_index: int,
    *,
    boundary_after: str = "",
    pause_after_ms: int = 0,
) -> TextChunk:
    """Create a TextChunk with optional structural pause metadata."""
    return TextChunk(
        index=index,
        text=text,
        chapter_index=chapter_index,
        boundary_after=boundary_after,
        pause_after_ms=pause_after_ms,
    )


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
        if _is_scene_break(para):
            if current_parts:
                combined = "\n\n".join(current_parts)
                all_chunks.append(
                    _make_chunk(
                        chunk_idx,
                        combined,
                        chapter_index,
                        boundary_after="scene",
                        pause_after_ms=DEFAULT_SCENE_PAUSE_MS,
                    )
                )
                chunk_idx += 1
                current_parts = []
                current_len = 0
            continue

        para_len = len(para)
        separator_len = 2 if current_parts else 0

        if para_len > max_chunk_chars:
            # Flush accumulated content first.
            if current_parts:
                for ch in chunk_text(
                    "\n\n".join(current_parts), max_chunk_chars, max_sentence_chars
                ):
                    all_chunks.append(_make_chunk(chunk_idx, ch, chapter_index))
                    chunk_idx += 1
                current_parts = []
                current_len = 0

            # Chunk the oversized paragraph by itself.
            para_chunks = chunk_text(para, max_chunk_chars, max_sentence_chars)
            for offset, ch in enumerate(para_chunks):
                is_last_para_chunk = offset == len(para_chunks) - 1
                all_chunks.append(
                    _make_chunk(
                        chunk_idx,
                        ch,
                        chapter_index,
                        boundary_after="scene" if is_last_para_chunk and _is_scene_break(para) else (
                            "paragraph" if is_last_para_chunk else ""
                        ),
                        pause_after_ms=DEFAULT_SCENE_PAUSE_MS
                        if is_last_para_chunk and _is_scene_break(para)
                        else (DEFAULT_PARAGRAPH_PAUSE_MS if is_last_para_chunk else 0),
                    )
                )
                chunk_idx += 1

        elif current_len + separator_len + para_len > max_chunk_chars and current_parts:
            # Flush current accumulation.
            combined = "\n\n".join(current_parts)
            all_chunks.append(
                _make_chunk(
                    chunk_idx,
                    combined,
                    chapter_index,
                    boundary_after="paragraph",
                    pause_after_ms=DEFAULT_PARAGRAPH_PAUSE_MS,
                )
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
            _make_chunk(
                chunk_idx,
                combined,
                chapter_index,
                boundary_after="chapter",
                pause_after_ms=DEFAULT_CHAPTER_PAUSE_MS,
            )
        )

    return all_chunks
