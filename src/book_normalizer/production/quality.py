"""Production readiness QA for audiobook manifests."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from book_normalizer.chunking.manifest_v2 import chunk_is_excluded, ensure_v2_manifest
from book_normalizer.tts.quality_gate import reset_chunk_for_resynthesis

PRODUCTION_QA_VERSION = 1
DEFAULT_PRODUCTION_QA_REPORT_NAME = "production_qa_report.json"

_RESYNTH_ARTIFACTS = {
    "repeated_audio",
    "dropout",
    "dropouts",
    "mostly_silent",
    "clipping",
    "unreadable_wav",
    "zero_duration",
}
_DIALOGUE_LABELS = {"men", "women"}
_HIGH_EMOTIONS = {"angry", "anger", "fearful", "afraid", "tense", "panic", "furious"}


@dataclass(frozen=True)
class ProductionQaConfig:
    """Thresholds for production QA scoring."""

    min_pass_score: int = 82
    min_review_score: int = 60
    max_natural_pause_ms: int = 3500
    min_speaker_handoff_pause_ms: int = 350
    require_director: bool = True
    require_casting: bool = True


def run_production_qa(
    manifest: dict[str, Any],
    *,
    config: ProductionQaConfig | None = None,
) -> dict[str, Any]:
    """Build a production QA report from manifest QA, casting, and director data."""
    cfg = config or ProductionQaConfig()
    record = ensure_v2_manifest(manifest).to_record()
    pairs = _flatten_chunks(record)
    chunk_reports: list[dict[str, Any]] = []
    for index, (_chapter, chunk) in enumerate(pairs):
        if chunk_is_excluded(chunk):
            continue
        next_chunk = pairs[index + 1][1] if index + 1 < len(pairs) else None
        chunk_reports.append(_score_chunk(chunk, next_chunk=next_chunk, config=cfg))

    counts: dict[str, int] = {"passed": 0, "review": 0, "resynthesize": 0}
    issue_counts: dict[str, int] = {}
    for item in chunk_reports:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
        for issue in item["issues"]:
            issue_counts[issue["kind"]] = issue_counts.get(issue["kind"], 0) + 1

    status = "passed"
    if counts.get("resynthesize", 0):
        status = "resynthesize"
    elif counts.get("review", 0):
        status = "review"

    return {
        "schema_version": PRODUCTION_QA_VERSION,
        "status": status,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "book_title": str(record.get("book_title") or ""),
        "language": str(record.get("language") or "ru"),
        "summary": {
            "total_chunks": len(chunk_reports),
            **counts,
            "issue_counts": issue_counts,
        },
        "chunks": chunk_reports,
    }


def annotate_manifest_with_production_qa(
    manifest: dict[str, Any],
    report: dict[str, Any],
    *,
    report_path: Path | str | None = None,
    reset_bad_chunks: bool = False,
    max_resynthesis_attempts: int = 2,
) -> None:
    """Attach perceptual QA blocks and optional resynthesis resets to manifest chunks."""
    by_key = {
        str(item.get("chunk_key") or ""): item
        for item in report.get("chunks", [])
        if isinstance(item, dict)
    }
    created_at = str(report.get("created_at") or "")
    for chapter in manifest.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        for chunk in chapter.get("chunks", []):
            if not isinstance(chunk, dict):
                continue
            item = by_key.get(_chunk_key(chunk))
            if not item:
                continue
            block = {
                "schema_version": PRODUCTION_QA_VERSION,
                "status": str(item.get("status") or ""),
                "score": int(item.get("score") or 0),
                "issues": [issue["kind"] for issue in item.get("issues", []) if isinstance(issue, dict)],
                "report_path": str(report_path or ""),
                "created_at": created_at,
            }
            chunk["perceptual_qa"] = block
            chunk["qa_status"] = str(item.get("status") or "")
            if reset_bad_chunks and item.get("status") == "resynthesize":
                reason = _compact_reason(item)
                reset_chunk_for_resynthesis(
                    chunk,
                    reason=reason,
                    max_attempts=max_resynthesis_attempts,
                )


def write_production_qa_report(path: Path, report: dict[str, Any]) -> Path:
    """Write production_qa_report.json."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _score_chunk(
    chunk: dict[str, Any],
    *,
    next_chunk: dict[str, Any] | None,
    config: ProductionQaConfig,
) -> dict[str, Any]:
    score = 100
    issues: list[dict[str, Any]] = []

    def add(kind: str, severity: str, message: str, penalty: int) -> None:
        nonlocal score
        score -= max(0, penalty)
        issues.append(
            {
                "kind": kind,
                "severity": severity,
                "message": message,
                "penalty": penalty,
            }
        )

    if not bool(chunk.get("synthesized")):
        add("not_synthesized", "resynthesize", "Chunk is not synthesized.", 60)
    _score_artifact_block(chunk, add)
    _score_asr_block(chunk, add)
    _score_llm_audio_block(chunk, add)
    _score_performance_contract(chunk, next_chunk, config, add)

    score = max(0, min(100, score))
    status = _status_from_score(score, issues, config)
    return {
        "chunk_key": _chunk_key(chunk),
        "chapter_index": int(chunk.get("chapter_index") or 0),
        "chunk_index": int(chunk.get("chunk_index") or 0),
        "speaker": str(chunk.get("canonical_speaker") or chunk.get("speaker") or ""),
        "score": score,
        "status": status,
        "issues": issues,
    }


def _score_artifact_block(chunk: dict[str, Any], add: Any) -> None:
    block = chunk.get("artifact_qa")
    if not isinstance(block, dict):
        add("artifact_qa_missing", "review", "Objective artifact QA has not run.", 8)
        return

    status = str(block.get("status") or "").strip().lower()
    issues = {str(item).strip() for item in block.get("issues") or [] if str(item).strip()}
    if status in {"failed", "error"}:
        add("artifact_qa_failed", "resynthesize", "Objective artifact QA failed.", 38)
    elif status == "warning":
        add("artifact_qa_warning", "review", "Objective artifact QA raised warnings.", 18)
    elif status and status != "passed":
        add("artifact_qa_unchecked", "review", f"Artifact QA status is {status}.", 10)

    blocking = sorted(issues & _RESYNTH_ARTIFACTS)
    if blocking:
        add(
            "perceptual_artifact_risk",
            "resynthesize",
            f"Likely audible artifact: {', '.join(blocking[:4])}.",
            24,
        )


def _score_asr_block(chunk: dict[str, Any], add: Any) -> None:
    block = chunk.get("asr_qa")
    if not isinstance(block, dict):
        add("asr_qa_missing", "review", "ASR text QA has not run.", 8)
        return
    status = str(block.get("status") or "").strip().lower()
    if status in {"failed", "error"}:
        add("asr_qa_failed", "resynthesize", "ASR comparison failed.", 35)
    elif status == "warning":
        add("asr_qa_warning", "review", "ASR comparison raised warnings.", 18)
    elif status and status != "passed":
        add("asr_qa_unchecked", "review", f"ASR QA status is {status}.", 10)


def _score_llm_audio_block(chunk: dict[str, Any], add: Any) -> None:
    block = chunk.get("llm_audio_qa")
    if not isinstance(block, dict):
        add("llm_audio_qa_missing", "review", "Local LLM audio QA has not run.", 8)
        return
    status = str(block.get("status") or "").strip().lower()
    score = int(block.get("score") or 0)
    if status in {"failed", "error"}:
        add("llm_audio_qa_failed", "resynthesize", "Local LLM audio QA failed.", 35)
    elif status == "warning":
        add("llm_audio_qa_warning", "review", "Local LLM audio QA raised warnings.", 18)
    elif status and status != "passed":
        add("llm_audio_qa_unchecked", "review", f"LLM audio QA status is {status}.", 10)
    if status == "passed" and score and score < 90:
        add("llm_audio_qa_low_score", "review", f"LLM audio QA score is borderline ({score}).", 8)


def _score_performance_contract(
    chunk: dict[str, Any],
    next_chunk: dict[str, Any] | None,
    config: ProductionQaConfig,
    add: Any,
) -> None:
    voice_label = str(chunk.get("voice_label") or "")
    if config.require_director and not isinstance(chunk.get("director"), dict):
        add("director_missing", "review", "No director performance metadata on chunk.", 12)
    if config.require_casting and voice_label in _DIALOGUE_LABELS and not str(chunk.get("cast_voice_id") or ""):
        add("cast_voice_missing", "review", "Dialogue chunk has no cast voice assignment.", 10)

    pause_ms = int(chunk.get("pause_after_ms") or 0)
    if pause_ms > config.max_natural_pause_ms:
        add("pause_too_long", "review", f"Pause after chunk is very long ({pause_ms} ms).", 8)
    if next_chunk is not None and _speaker_key(chunk) != _speaker_key(next_chunk):
        if pause_ms < config.min_speaker_handoff_pause_ms:
            add(
                "speaker_handoff_pause_short",
                "review",
                f"Speaker handoff pause is short ({pause_ms} ms).",
                8,
            )

    emotion = _key(chunk.get("emotion"))
    director = chunk.get("director") if isinstance(chunk.get("director"), dict) else {}
    tension = _key(director.get("tension"))
    if emotion in _HIGH_EMOTIONS and tension == "low":
        add(
            "emotion_director_mismatch",
            "review",
            "High-emotion line has low director tension.",
            8,
        )


def _status_from_score(
    score: int,
    issues: list[dict[str, Any]],
    config: ProductionQaConfig,
) -> str:
    if any(issue.get("severity") == "resynthesize" for issue in issues):
        return "resynthesize"
    if score >= config.min_pass_score:
        return "passed"
    if score >= config.min_review_score:
        return "review"
    return "review"


def _flatten_chunks(manifest: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for chapter in manifest.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        for chunk in chapter.get("chunks", []):
            if isinstance(chunk, dict):
                pairs.append((chapter, chunk))
    return pairs


def _compact_reason(item: dict[str, Any]) -> str:
    kinds = [
        str(issue.get("kind") or "")
        for issue in item.get("issues", [])
        if isinstance(issue, dict) and issue.get("kind")
    ]
    suffix = ", ".join(kinds[:4]) if kinds else "production QA failed"
    return f"production_qa: {suffix}"


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
