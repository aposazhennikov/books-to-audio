"""Manifest editing helpers for the synthesis GUI page."""

from __future__ import annotations

from book_normalizer.chunking.manifest_v2 import (
    DEFAULT_MANIFEST_NAME,
    ensure_v2_manifest,
    flatten_manifest,
    merge_chunk_with_next,
    role_for_voice_id,
    split_chunk_text,
    update_chunk_text,
)

_TEST_FRAGMENT_MAX_CHARS = 420
_TEST_CHUNK_LABEL_MAX_CHARS = 64

def _iter_manifest_chunks(data: object) -> list[dict]:
    """Return chunk records from a strict v2 grouped manifest."""
    return flatten_manifest(ensure_v2_manifest(data))


def _shorten_test_fragment(text: str, max_chars: int = _TEST_FRAGMENT_MAX_CHARS) -> str:
    """Return a compact, sentence-ish fragment suitable for a quick TTS check."""
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= max_chars:
        return normalized

    sentence_cut = max(
        normalized.rfind(".", 0, max_chars),
        normalized.rfind("!", 0, max_chars),
        normalized.rfind("?", 0, max_chars),
    )
    if sentence_cut >= 120:
        return normalized[: sentence_cut + 1].strip()

    word_cut = normalized.rfind(" ", 0, max_chars)
    if word_cut >= 120:
        return normalized[:word_cut].strip() + "..."

    return normalized[:max_chars].strip() + "..."


def _build_test_manifest_chunks(data: object, chapter: int | None = None) -> list[dict]:
    """Pick one non-empty manifest chunk and trim it for preview synthesis.

    ``chapter`` is 1-based to match the GUI combo and CLI argument.
    """
    chunks = _iter_manifest_chunks(data)
    if chapter is not None:
        target = chapter - 1
        chunks = [c for c in chunks if int(c.get("chapter_index", 0)) == target]

    for chunk in chunks:
        text = _shorten_test_fragment(str(chunk.get("text") or ""))
        if not text:
            continue
        preview = dict(chunk)
        preview["text"] = text
        preview["chapter_index"] = int(preview.get("chapter_index", 0))
        preview["chunk_index"] = 0
        preview["voice_id"] = str(preview.get("voice_id") or "narrator_calm")
        return [preview]

    return []


def _role_for_voice_id(voice_id: str) -> str:
    """Infer a manifest role from a Qwen voice preset id."""
    return role_for_voice_id(voice_id)


def _chunk_preview_text(text: str, max_chars: int = _TEST_CHUNK_LABEL_MAX_CHARS) -> str:
    """Return a single-line preview for chunk selectors."""
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rstrip() + "..."


def _test_manifest_chunk_from_chunk(chunk: dict) -> dict:
    """Build a single-chunk preview manifest entry from an existing chunk."""
    preview = dict(chunk)
    preview["text"] = str(preview.get("text") or "").strip()
    preview["chapter_index"] = int(preview.get("chapter_index", 0))
    preview["chunk_index"] = int(preview.get("chunk_index", 0))
    voice_id = str(preview.get("voice_id") or "narrator_calm")
    preview["voice_id"] = voice_id
    preview["role"] = str(preview.get("role") or _role_for_voice_id(voice_id))
    return preview


def _test_manifest_chunk_from_text(text: str, voice_id: str) -> dict:
    """Build a one-off preview manifest entry from manually entered text."""
    selected_voice = voice_id or "narrator_calm"
    return {
        "chapter_index": 0,
        "chunk_index": 0,
        "role": _role_for_voice_id(selected_voice),
        "voice_id": selected_voice,
        "text": text.strip(),
    }


def _set_manifest_chunk_text(chunk: dict, text: str) -> None:
    """Update all text-bearing fields in one manifest chunk."""
    chunk["text"] = text
    voice_label = str(chunk.get("voice_label") or "").strip()
    if voice_label and voice_label in chunk:
        chunk[voice_label] = text
    for label in ("narrator", "men", "women"):
        if label in chunk and (not voice_label or label == voice_label):
            chunk[label] = text
    chunk["synthesized"] = False
    chunk["audio_file"] = None
    chunk.pop("failed", None)
    chunk.pop("error", None)


def _replace_manifest_data(data: object, record: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError(f"Expected {DEFAULT_MANIFEST_NAME} object.")
    data.clear()
    data.update(record)


def _find_manifest_chunk(
    data: object,
    chapter_index: int,
    chunk_index: int,
) -> tuple[list, int, dict] | None:
    """Find a mutable chunk record in a v2 manifest object."""
    if isinstance(data, dict):
        ensure_v2_manifest(data)
        for chapter in data.get("chapters", []):
            if not isinstance(chapter, dict):
                continue
            if int(chapter.get("chapter_index", 0)) != chapter_index:
                continue
            chunks = chapter.get("chunks", [])
            if not isinstance(chunks, list):
                return None
            for idx, chunk in enumerate(chunks):
                if isinstance(chunk, dict) and int(chunk.get("chunk_index", idx)) == chunk_index:
                    return chunks, idx, chunk
    return None


def _renumber_manifest_chunks(container: list, chapter_index: int) -> None:
    """Keep chunk_index sequential after split/merge edits."""
    next_index = 0
    for chunk in container:
        if not isinstance(chunk, dict):
            continue
        if int(chunk.get("chapter_index", chapter_index)) != chapter_index:
            continue
        chunk["chunk_index"] = next_index
        next_index += 1


def _update_manifest_chunk_text(
    data: object,
    chapter_index: int,
    chunk_index: int,
    text: str,
) -> bool:
    manifest = ensure_v2_manifest(data)
    if not update_chunk_text(manifest, chapter_index, chunk_index, text):
        return False
    _replace_manifest_data(data, manifest.to_record())
    return True


def _split_manifest_chunk_text(
    data: object,
    chapter_index: int,
    chunk_index: int,
    split_at: int,
) -> bool:
    manifest = ensure_v2_manifest(data)
    if not split_chunk_text(manifest, chapter_index, chunk_index, split_at):
        return False
    _replace_manifest_data(data, manifest.to_record())
    return True


def _merge_manifest_chunk_with_next(
    data: object,
    chapter_index: int,
    chunk_index: int,
) -> bool:
    manifest = ensure_v2_manifest(data)
    if not merge_chunk_with_next(manifest, chapter_index, chunk_index):
        return False
    _replace_manifest_data(data, manifest.to_record())
    return True
