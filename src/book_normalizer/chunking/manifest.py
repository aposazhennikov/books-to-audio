"""Helpers for the v2 chunk manifest used by the ComfyUI pipeline."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

VOICE_LABEL_BY_ROLE = {
    "narrator": "narrator",
    "male": "men",
    "female": "women",
    "men": "men",
    "women": "women",
    "unknown": "narrator",
}

VOICE_BY_LABEL = {
    "narrator": "narrator",
    "men": "male",
    "women": "female",
}

VOICE_ID_BY_LABEL = {
    "narrator": "narrator_calm",
    "men": "male_young",
    "women": "female_warm",
}


def role_to_voice_label(role: str, voice_id: str = "") -> str:
    """Return the v2 voice label for a role/voice preset pair."""
    normalized = (role or "").strip().lower()
    if normalized in VOICE_LABEL_BY_ROLE:
        return VOICE_LABEL_BY_ROLE[normalized]
    if voice_id.startswith("male_"):
        return "men"
    if voice_id.startswith("female_"):
        return "women"
    return "narrator"


def chunks_to_v2_manifest(
    chunks: list[dict[str, Any]],
    *,
    book_title: str,
    chunker: str = "gui",
    model: str = "",
    max_chunk_chars: int | None = None,
) -> dict[str, Any]:
    """Build a grouped v2 manifest from flat chunk dictionaries."""
    chapters: dict[int, dict[str, Any]] = {}
    per_chapter_index: dict[int, int] = defaultdict(int)

    for chunk in chunks:
        chapter_index = int(chunk.get("chapter_index", 0))
        if chapter_index not in chapters:
            chapters[chapter_index] = {
                "chapter_index": chapter_index,
                "chapter_title": f"Chapter {chapter_index + 1}",
                "chunks": [],
            }

        voice_id = str(chunk.get("voice_id") or "")
        voice_label = str(chunk.get("voice_label") or "").strip()
        if voice_label not in VOICE_BY_LABEL:
            voice_label = role_to_voice_label(str(chunk.get("role", "narrator")), voice_id)

        voice = VOICE_BY_LABEL[voice_label]
        text = str(chunk.get("text") or "")
        chunk_index = int(chunk.get("chunk_index", per_chapter_index[chapter_index]))
        per_chapter_index[chapter_index] = max(per_chapter_index[chapter_index], chunk_index + 1)

        record = {
            "chapter_index": chapter_index,
            "chunk_index": chunk_index,
            "voice_label": voice_label,
            voice_label: text,
            "voice": voice,
            "voice_id": voice_id or VOICE_ID_BY_LABEL[voice_label],
            "voice_tone": str(chunk.get("voice_tone") or chunk.get("intonation") or "neutral"),
            "text": text,
            "audio_file": chunk.get("audio_file"),
            "synthesized": bool(chunk.get("synthesized", False)),
        }
        if "failed" in chunk:
            record["failed"] = bool(chunk.get("failed"))
        if "error" in chunk:
            record["error"] = chunk.get("error")
        chapters[chapter_index]["chunks"].append(record)

    manifest: dict[str, Any] = {
        "version": 2,
        "book_title": book_title,
        "chunker": chunker,
        "chapters": [chapters[i] for i in sorted(chapters)],
    }
    if model:
        manifest["model"] = model
    if max_chunk_chars is not None:
        manifest["max_chunk_chars"] = max_chunk_chars
    return manifest


def flatten_v2_manifest(data: object) -> list[dict[str, Any]]:
    """Return flat chunk records from a v1 list or grouped v2 manifest."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []

    chunks: list[dict[str, Any]] = []
    for chapter in data.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter_index = chapter.get("chapter_index", 0)
        for chunk in chapter.get("chunks", []):
            if isinstance(chunk, dict):
                chunks.append({"chapter_index": chapter_index, **chunk})
    return chunks
