"""Shared manifest helpers for audio quality gates and resynthesis."""

from __future__ import annotations

import copy
from collections import defaultdict
from typing import Any

BAD_QA_STATUSES = frozenset({"failed", "warning", "error"})
BLOCKING_QA_STATUSES = frozenset({"failed", "warning", "error"})


def normalize_statuses(statuses: set[str] | list[str] | tuple[str, ...] | None) -> set[str]:
    """Return a normalized non-empty status set."""
    if not statuses:
        return set(BAD_QA_STATUSES)
    return {str(status).strip().lower() for status in statuses if str(status).strip()}


def compact_issue_reason(prefix: str, issues: list[Any] | None) -> str:
    """Build a short human-readable reason from issue objects or strings."""
    names: list[str] = []
    for issue in issues or []:
        if isinstance(issue, str):
            name = issue
        elif isinstance(issue, dict):
            name = str(issue.get("kind") or issue.get("message") or "")
        else:
            name = str(getattr(issue, "kind", "") or getattr(issue, "message", "") or "")
        name = name.strip()
        if name:
            names.append(name)
    suffix = ", ".join(names[:4]) if names else "quality gate failed"
    return f"{prefix}: {suffix}"


def reset_chunk_for_resynthesis(
    chunk: dict[str, Any],
    *,
    reason: str,
    max_attempts: int = 2,
) -> bool:
    """Mark a bad chunk for another synthesis pass.

    Returns True when the chunk was reset and should be picked up by
    ``failed_only`` synthesis. Returns False once the attempt limit is reached.
    """
    attempts = int(chunk.get("resynthesis_attempt") or 0)
    chunk["failed"] = True
    chunk["error"] = reason
    chunk["resynthesis_reason"] = reason

    if attempts >= max(0, int(max_attempts)):
        return False

    audio_file = str(chunk.get("audio_file") or "").strip()
    if audio_file:
        rejected = list(chunk.get("rejected_audio_files") or [])
        if audio_file not in rejected:
            rejected.append(audio_file)
        chunk["rejected_audio_files"] = rejected

    chunk["resynthesis_attempt"] = attempts + 1
    chunk["synthesized"] = False
    chunk["audio_file"] = None
    return True


def chunk_quality_status(chunk: dict[str, Any]) -> str:
    """Return the worst compact status from artifact and ASR QA blocks."""
    statuses: list[str] = []
    for key in ("artifact_qa", "asr_qa"):
        block = chunk.get(key)
        if isinstance(block, dict):
            statuses.append(str(block.get("status") or "").lower())
    if any(status in {"failed", "error"} for status in statuses):
        return "failed"
    if any(status == "warning" for status in statuses):
        return "warning"
    if statuses and all(status == "passed" for status in statuses):
        return "passed"
    return "unchecked"


def has_blocking_quality_issue(
    chunk: dict[str, Any],
    *,
    blocking_statuses: set[str] | None = None,
) -> bool:
    """Return True when a chunk should block final assembly/mastering."""
    status = chunk_quality_status(chunk)
    statuses = blocking_statuses or set(BLOCKING_QA_STATUSES)
    return status in statuses or bool(chunk.get("failed"))


def quality_summary_by_chapter(manifest: dict[str, Any]) -> dict[int, dict[str, int]]:
    """Count compact quality statuses per chapter for GUI/CLI summaries."""
    summary: dict[int, dict[str, int]] = defaultdict(
        lambda: {
            "total": 0,
            "passed": 0,
            "warning": 0,
            "failed": 0,
            "unchecked": 0,
        }
    )
    for chapter in manifest.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter_index = int(chapter.get("chapter_index", 0))
        for chunk in chapter.get("chunks", []):
            if not isinstance(chunk, dict):
                continue
            if chunk.get("deleted") or chunk.get("excluded_from_tts"):
                continue
            status = chunk_quality_status(chunk)
            if status == "error":
                status = "failed"
            bucket = summary[chapter_index]
            bucket["total"] += 1
            bucket[status if status in bucket else "unchecked"] += 1
    return dict(summary)


def split_problem_chunks_for_retry(
    manifest: dict[str, Any],
    *,
    min_chars: int = 180,
) -> int:
    """Split repeated/overlong failed chunks before a later retry pass."""
    split_count = 0
    for chapter in manifest.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chunks = chapter.get("chunks", [])
        if not isinstance(chunks, list):
            continue
        index = 0
        while index < len(chunks):
            chunk = chunks[index]
            if not isinstance(chunk, dict) or chunk.get("deleted") or chunk.get("excluded_from_tts"):
                index += 1
                continue
            if not _should_split_for_retry(chunk, min_chars=min_chars):
                index += 1
                continue
            text = _chunk_text(chunk)
            split_at = _best_split_offset(text)
            if split_at <= 0:
                index += 1
                continue
            left = text[:split_at].strip()
            right = text[split_at:].strip()
            if not left or not right:
                index += 1
                continue

            right_chunk = copy.deepcopy(chunk)
            _set_chunk_text(chunk, left)
            _set_chunk_text(right_chunk, right)
            split_number = int(chunk.get("resynthesis_split_count") or 0) + 1
            reason = str(chunk.get("resynthesis_reason") or "quality retry split")
            for part in (chunk, right_chunk):
                part["synthesized"] = False
                part["failed"] = True
                part["audio_file"] = None
                part["error"] = reason
                part["resynthesis_reason"] = f"{reason}; split for retry"
                part["resynthesis_split_count"] = split_number
                part["artifact_qa"] = None
                part["asr_qa"] = None
            chunks.insert(index + 1, right_chunk)
            _renumber_chapter_chunks(chapter)
            split_count += 1
            index += 2
    return split_count


def _should_split_for_retry(chunk: dict[str, Any], *, min_chars: int) -> bool:
    if int(chunk.get("resynthesis_attempt") or 0) < 2:
        return False
    if int(chunk.get("resynthesis_split_count") or 0) > 0:
        return False
    if len(_chunk_text(chunk)) < min_chars:
        return False
    artifact = chunk.get("artifact_qa")
    if not isinstance(artifact, dict):
        return False
    issues = {str(issue).strip() for issue in artifact.get("issues") or []}
    return bool(issues & {"repeated_audio", "too_long_for_text"})


def _chunk_text(chunk: dict[str, Any]) -> str:
    voice_label = str(chunk.get("voice_label") or "")
    return str(chunk.get("text") or chunk.get(voice_label) or "")


def _set_chunk_text(chunk: dict[str, Any], text: str) -> None:
    chunk["text"] = text
    voice_label = str(chunk.get("voice_label") or "")
    if voice_label:
        chunk[voice_label] = text


def _best_split_offset(text: str) -> int:
    midpoint = len(text) // 2
    candidates = [". ", "! ", "? ", "; ", ": ", ", ", " "]
    best = -1
    best_distance = len(text)
    for marker in candidates:
        start = 0
        while True:
            found = text.find(marker, start)
            if found < 0:
                break
            offset = found + len(marker)
            if 20 <= offset <= len(text) - 20:
                distance = abs(offset - midpoint)
                if distance < best_distance:
                    best = offset
                    best_distance = distance
            start = found + 1
    return best


def _renumber_chapter_chunks(chapter: dict[str, Any]) -> None:
    chapter_index = int(chapter.get("chapter_index", 0))
    chunks = chapter.get("chunks", [])
    if not isinstance(chunks, list):
        return
    for index, chunk in enumerate(chunks):
        if isinstance(chunk, dict):
            chunk["chapter_index"] = chapter_index
            chunk["chunk_index"] = index
