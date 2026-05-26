"""Director score generation for audiobook chunk manifests."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from book_normalizer.chunking.manifest_v2 import ensure_v2_manifest

DIRECTOR_SCORE_VERSION = 1
DEFAULT_DIRECTOR_SCORE_NAME = "director_score.json"

_NEUTRAL_TONES = {"", "neutral", "calm"}
_SCENE_BREAK_MS = 1500
_SPEAKER_CHANGE_PAUSE_MS = 650
_SAME_SPEAKER_PAUSE_MS = 280
_ELLIPSIS_PAUSE_MS = 520

_HIGH_TENSION = {
    "angry",
    "anger",
    "fearful",
    "afraid",
    "tense",
    "panic",
    "furious",
    "shout",
    "shouting",
}
_LOW_ENERGY = {"sad", "tired", "weak", "whisper", "quiet", "melancholy", "exhausted"}
_BRIGHT_ENERGY = {"joyful", "happy", "excited", "playful", "cheerful"}


def build_director_score(manifest: dict[str, Any]) -> dict[str, Any]:
    """Create a deterministic director score for every manifest chunk."""
    record = ensure_v2_manifest(manifest).to_record()
    pairs = _flatten_chunks(record)
    chunk_scores: list[dict[str, Any]] = []
    scenes: list[dict[str, Any]] = []
    scene_number_by_chapter: dict[int, int] = {}
    current_scene: dict[str, Any] | None = None

    for index, (chapter, chunk) in enumerate(pairs):
        prev_chunk = pairs[index - 1][1] if index > 0 else None
        next_chunk = pairs[index + 1][1] if index + 1 < len(pairs) else None
        chapter_index = int(chapter.get("chapter_index") or 0)
        scene_starts = _starts_new_scene(chunk, prev_chunk)
        if current_scene is None or scene_starts:
            scene_no = scene_number_by_chapter.get(chapter_index, 0) + 1
            scene_number_by_chapter[chapter_index] = scene_no
            current_scene = {
                "scene_id": f"ch{chapter_index + 1:03d}_scene{scene_no:02d}",
                "chapter_index": chapter_index,
                "chapter_title": str(chapter.get("chapter_title") or ""),
                "start_chunk_index": int(chunk.get("chunk_index") or 0),
                "end_chunk_index": int(chunk.get("chunk_index") or 0),
                "chunk_count": 0,
                "tension_counts": Counter(),
            }
            scenes.append(current_scene)

        director = _score_chunk(
            chunk,
            next_chunk=next_chunk,
            scene_id=str(current_scene["scene_id"]),
        )
        current_scene["chunk_count"] += 1
        current_scene["end_chunk_index"] = int(chunk.get("chunk_index") or 0)
        current_scene["tension_counts"][director["tension"]] += 1
        chunk_scores.append(
            {
                "chunk_key": _chunk_key(chunk),
                "chapter_index": int(chunk.get("chapter_index") or chapter_index),
                "chunk_index": int(chunk.get("chunk_index") or 0),
                "speaker": str(chunk.get("canonical_speaker") or chunk.get("speaker") or ""),
                "voice_label": str(chunk.get("voice_label") or ""),
                "director": director,
                "pause_after_ms": int(director.get("pause_after_ms") or 0),
                "voice_tone": _voice_tone(chunk, director),
            }
        )

    serializable_scenes = []
    for scene in scenes:
        tension_counts = scene.pop("tension_counts")
        serializable_scenes.append(
            {
                **scene,
                "dominant_tension": tension_counts.most_common(1)[0][0] if tension_counts else "low",
            }
        )

    director_counts = Counter(item["director"]["tension"] for item in chunk_scores)
    return {
        "version": DIRECTOR_SCORE_VERSION,
        "book_title": str(record.get("book_title") or ""),
        "language": str(record.get("language") or "ru"),
        "total_chunks": len(chunk_scores),
        "scenes": serializable_scenes,
        "chunks": chunk_scores,
        "summary": {
            "scenes": len(serializable_scenes),
            "high_tension_chunks": int(director_counts.get("high", 0)),
            "medium_tension_chunks": int(director_counts.get("medium", 0)),
            "low_tension_chunks": int(director_counts.get("low", 0)),
        },
    }


def apply_director_score_to_manifest(
    manifest: dict[str, Any],
    score: dict[str, Any],
) -> dict[str, Any]:
    """Attach director metadata and pauses to manifest chunks."""
    record = ensure_v2_manifest(manifest).to_record()
    by_key = {
        str(item.get("chunk_key") or ""): item
        for item in score.get("chunks", [])
        if isinstance(item, dict)
    }

    for chapter in record.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        for chunk in chapter.get("chunks", []):
            if not isinstance(chunk, dict):
                continue
            item = by_key.get(_chunk_key(chunk))
            if not item:
                continue
            director = item.get("director")
            if isinstance(director, dict):
                chunk["director"] = director
                chunk["pause_after_ms"] = max(
                    int(chunk.get("pause_after_ms") or 0),
                    int(item.get("pause_after_ms") or director.get("pause_after_ms") or 0),
                )
            tone = str(item.get("voice_tone") or "")
            if tone and str(chunk.get("voice_tone") or "").strip().casefold() in _NEUTRAL_TONES:
                chunk["voice_tone"] = tone
    return record


def write_director_score(path: Path, score: dict[str, Any]) -> Path:
    """Write director_score.json."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(score, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _flatten_chunks(manifest: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for chapter in manifest.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        for chunk in chapter.get("chunks", []):
            if isinstance(chunk, dict):
                pairs.append((chapter, chunk))
    return pairs


def _score_chunk(
    chunk: dict[str, Any],
    *,
    next_chunk: dict[str, Any] | None,
    scene_id: str,
) -> dict[str, Any]:
    text = str(chunk.get("text") or chunk.get(str(chunk.get("voice_label") or "")) or "")
    emotion = str(chunk.get("emotion") or chunk.get("voice_tone") or "").strip().lower()
    section = str(chunk.get("section_kind") or "").strip().lower()
    speaker = str(chunk.get("canonical_speaker") or chunk.get("speaker") or "").strip()
    tension = _tension(text, emotion, section)
    pace = _pace(text, emotion, tension, section)
    volume = _volume(text, emotion, tension, section)
    delivery = _delivery(text, emotion, section)
    pause_ms = _pause_after_ms(chunk, next_chunk, text, section)
    return {
        "scene": scene_id,
        "pace": pace,
        "pause": _pause_instruction(pause_ms, next_chunk),
        "volume": volume,
        "tension": tension,
        "delivery": delivery,
        "pause_after_ms": pause_ms,
        "speaker_focus": speaker,
        "emphasis": _emphasis(text),
    }


def _starts_new_scene(chunk: dict[str, Any], prev_chunk: dict[str, Any] | None) -> bool:
    if prev_chunk is None:
        return True
    if int(prev_chunk.get("pause_after_ms") or 0) >= _SCENE_BREAK_MS:
        return True
    if str(prev_chunk.get("boundary_after") or "").strip().lower() in {"scene", "chapter"}:
        return True
    section = str(chunk.get("section_kind") or "").strip().lower()
    return section in {"chapter_title", "preface", "epilogue", "annotation"}


def _pause_after_ms(
    chunk: dict[str, Any],
    next_chunk: dict[str, Any] | None,
    text: str,
    section: str,
) -> int:
    base = int(chunk.get("pause_after_ms") or 0)
    boundary = str(chunk.get("boundary_after") or "").strip().lower()
    if boundary in {"scene", "chapter"}:
        base = max(base, _SCENE_BREAK_MS)
    if section in {"chapter_title", "preface", "epilogue", "annotation"}:
        base = max(base, 900)
    if "..." in text or "…" in text:
        base = max(base, _ELLIPSIS_PAUSE_MS)
    if next_chunk is not None and _speaker_key(chunk) != _speaker_key(next_chunk):
        base = max(base, _SPEAKER_CHANGE_PAUSE_MS)
    elif next_chunk is not None:
        base = max(base, _SAME_SPEAKER_PAUSE_MS)
    return base


def _tension(text: str, emotion: str, section: str) -> str:
    text_marks = text.count("!") + text.count("?")
    emotion_key = _key(emotion)
    if section in {"chapter_title", "annotation", "preface", "epilogue"}:
        return "low"
    if text_marks >= 2 or emotion_key in _HIGH_TENSION or any(word in emotion_key for word in _HIGH_TENSION):
        return "high"
    if text_marks == 1 or emotion_key in _BRIGHT_ENERGY or emotion_key in _LOW_ENERGY:
        return "medium"
    return "low"


def _pace(text: str, emotion: str, tension: str, section: str) -> str:
    emotion_key = _key(emotion)
    if section in {"chapter_title", "annotation", "preface", "epilogue"}:
        return "measured and clear"
    if emotion_key in _LOW_ENERGY or any(word in emotion_key for word in _LOW_ENERGY):
        return "slow, with room for breath"
    if tension == "high":
        return "controlled, urgent, never rushed"
    if len(text) < 80 and emotion_key in _BRIGHT_ENERGY:
        return "brisk and light"
    return "natural conversational tempo"


def _volume(text: str, emotion: str, tension: str, section: str) -> str:
    emotion_key = _key(emotion)
    if "whisper" in emotion_key or section == "aside":
        return "quiet"
    if tension == "high" or "!" in text:
        return "firm but not clipped"
    return "normal"


def _delivery(text: str, emotion: str, section: str) -> str:
    emotion_key = _key(emotion)
    if section in {"chapter_title", "annotation", "preface", "epilogue"}:
        return f"formal {section.replace('_', ' ')} narration"
    if "sarcas" in emotion_key:
        return "dry, lightly sarcastic, do not overplay"
    if "whisper" in emotion_key:
        return "intimate whisper with clean articulation"
    if emotion_key in _LOW_ENERGY:
        return "subdued, emotionally present, no melodrama"
    if emotion_key in _BRIGHT_ENERGY:
        return "open and animated, keep consonants clean"
    if "?" in text:
        return "questioning, with a clear lift before the pause"
    return "grounded and natural"


def _pause_instruction(pause_ms: int, next_chunk: dict[str, Any] | None) -> str:
    if pause_ms >= _SCENE_BREAK_MS:
        return "long scene beat after this chunk"
    if next_chunk is not None and pause_ms >= _SPEAKER_CHANGE_PAUSE_MS:
        return "clear speaker handoff beat"
    if pause_ms >= _ELLIPSIS_PAUSE_MS:
        return "hesitation beat"
    return "short natural beat"


def _voice_tone(chunk: dict[str, Any], director: dict[str, Any]) -> str:
    emotion = str(chunk.get("emotion") or "").strip()
    delivery = str(director.get("delivery") or "").strip()
    tension = str(director.get("tension") or "").strip()
    parts = [part for part in (emotion, tension, delivery) if part]
    return "; ".join(parts[:3])


def _emphasis(text: str) -> list[str]:
    quoted = re.findall(r"['\"]([^'\"]{2,48})['\"]", text)
    if quoted:
        return [item.strip() for item in quoted[:3]]
    words = re.findall(r"\b[A-Z][A-Za-z]{4,}\b", text)
    return words[:3]


def _speaker_key(chunk: dict[str, Any]) -> str:
    return _key(
        chunk.get("canonical_speaker")
        or chunk.get("speaker")
        or chunk.get("voice_label")
        or chunk.get("voice")
    )


def _chunk_key(chunk: dict[str, Any]) -> str:
    return f"{int(chunk.get('chapter_index') or 0)}:{int(chunk.get('chunk_index') or 0)}"


def _key(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()
