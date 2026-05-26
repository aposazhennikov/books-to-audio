"""Audio artifact quality gate for synthesized audiobook chunks.

This gate looks for defects that ASR alone can miss: clipping/harsh overload,
mostly silent output, suspicious duration, sudden dropouts, and short repeated
audio loops that often sound like stutter.
"""

from __future__ import annotations

import json
import math
import wave
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from book_normalizer.chunking.manifest_v2 import chunk_is_excluded, ensure_v2_manifest
from book_normalizer.tts.quality_gate import (
    BAD_QA_STATUSES,
    compact_issue_reason,
    normalize_statuses,
    reset_chunk_for_resynthesis,
)

ARTIFACT_QA_SCHEMA_VERSION = 1
DEFAULT_ARTIFACT_REPORT_NAME = "artifact_qa_report.json"


@dataclass
class ArtifactQaConfig:
    """Thresholds for artifact detection."""

    min_seconds_per_100_chars: float = 2.0
    max_seconds_per_100_chars: float = 18.0
    silence_rms_threshold: float = 1e-4
    clipping_ratio_threshold: float = 0.01
    near_peak_threshold: float = 0.985
    harsh_crest_db_threshold: float = 3.0
    spike_crest_db_threshold: float = 28.0
    dropout_window_ms: int = 80
    dropout_rms_ratio: float = 0.08
    repeated_audio_threshold: float = 0.20


@dataclass
class ArtifactIssue:
    """One artifact finding."""

    kind: str
    severity: str
    message: str
    score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "kind": self.kind,
            "severity": self.severity,
            "message": self.message,
        }
        if self.score is not None:
            data["score"] = round(self.score, 4)
        return data


@dataclass
class ArtifactChunkResult:
    """Artifact QA result for one manifest chunk."""

    chapter_index: int
    chunk_index: int
    audio_file: str = ""
    status: str = "skipped"
    duration_seconds: float = 0.0
    scores: dict[str, float] = field(default_factory=dict)
    issues: list[ArtifactIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_index": self.chapter_index,
            "chunk_index": self.chunk_index,
            "audio_file": self.audio_file,
            "status": self.status,
            "duration_seconds": round(self.duration_seconds, 3),
            "scores": {key: round(value, 4) for key, value in self.scores.items()},
            "issues": [issue.to_dict() for issue in self.issues],
        }

    def to_manifest_block(self, *, report_path: Path | str | None, created_at: str) -> dict[str, Any]:
        return {
            "schema_version": ARTIFACT_QA_SCHEMA_VERSION,
            "status": self.status,
            "issues": [issue.kind for issue in self.issues],
            "scores": {key: round(value, 4) for key, value in self.scores.items()},
            "report_path": str(report_path or ""),
            "created_at": created_at,
        }


@dataclass
class ArtifactQaResult:
    """Book-level artifact QA report."""

    created_at: str
    chunks: list[ArtifactChunkResult] = field(default_factory=list)

    @property
    def status(self) -> str:
        statuses = [chunk.status for chunk in self.chunks]
        if any(status in {"failed", "error"} for status in statuses):
            return "failed"
        if any(status == "warning" for status in statuses):
            return "warning"
        if statuses and all(status == "skipped" for status in statuses):
            return "skipped"
        return "passed"

    @property
    def summary(self) -> dict[str, Any]:
        counts = {"passed": 0, "warning": 0, "failed": 0, "skipped": 0, "error": 0}
        issue_counts: dict[str, int] = {}
        for chunk in self.chunks:
            counts[chunk.status] = counts.get(chunk.status, 0) + 1
            for issue in chunk.issues:
                issue_counts[issue.kind] = issue_counts.get(issue.kind, 0) + 1
        return {
            "total_chunks": len(self.chunks),
            "issue_counts": issue_counts,
            **counts,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": ARTIFACT_QA_SCHEMA_VERSION,
            "status": self.status,
            "created_at": self.created_at,
            "summary": self.summary,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
        }


def run_artifact_qa(
    manifest: dict[str, Any],
    *,
    config: ArtifactQaConfig | None = None,
    manifest_path: Path | None = None,
) -> ArtifactQaResult:
    """Run artifact QA over active manifest chunks."""
    cfg = config or ArtifactQaConfig()
    manifest_record = ensure_v2_manifest(manifest).to_record()
    result = ArtifactQaResult(created_at=datetime.now(timezone.utc).isoformat())
    for chapter in manifest_record.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter_index = int(chapter.get("chapter_index", 0))
        for chunk in chapter.get("chunks", []):
            if not isinstance(chunk, dict) or chunk_is_excluded(chunk):
                continue
            chunk_index = int(chunk.get("chunk_index", 0))
            audio_path = _resolve_audio_path(str(chunk.get("audio_file") or ""), manifest_path)
            if audio_path is None:
                item = ArtifactChunkResult(chapter_index, chunk_index)
                item.status = "warning"
                item.issues.append(
                    ArtifactIssue("missing_audio_file_field", "warning", "Chunk has no audio_file.")
                )
                result.chunks.append(item)
                continue
            result.chunks.append(
                _run_chunk_artifact_qa(
                    chapter_index,
                    chunk_index,
                    audio_path,
                    str(chunk.get("text") or ""),
                    cfg,
                )
            )
    return result


def annotate_manifest_with_artifacts(
    manifest: dict[str, Any],
    result: ArtifactQaResult,
    *,
    report_path: Path | str | None = None,
    reset_bad_chunks: bool = False,
    resynth_statuses: set[str] | list[str] | tuple[str, ...] | None = None,
    max_resynthesis_attempts: int = 2,
) -> None:
    """Attach compact artifact QA blocks and optionally reset bad chunks."""
    statuses = normalize_statuses(resynth_statuses or set(BAD_QA_STATUSES))
    by_chunk = {
        (chunk.chapter_index, chunk.chunk_index): chunk
        for chunk in result.chunks
    }
    for chapter in manifest.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter_index = int(chapter.get("chapter_index", 0))
        for chunk in chapter.get("chunks", []):
            if not isinstance(chunk, dict):
                continue
            key = (chapter_index, int(chunk.get("chunk_index", 0)))
            chunk_result = by_chunk.get(key)
            if chunk_result is None:
                continue
            chunk["artifact_qa"] = chunk_result.to_manifest_block(
                report_path=report_path,
                created_at=result.created_at,
            )
            if reset_bad_chunks and chunk_result.status in statuses:
                reason = compact_issue_reason("artifact_qa", chunk_result.issues)
                reset_chunk_for_resynthesis(
                    chunk,
                    reason=reason,
                    max_attempts=max_resynthesis_attempts,
                )


def write_artifact_report(path: Path, result: ArtifactQaResult) -> None:
    """Write artifact QA report JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def _run_chunk_artifact_qa(
    chapter_index: int,
    chunk_index: int,
    audio_path: Path,
    text: str,
    config: ArtifactQaConfig,
) -> ArtifactChunkResult:
    item = ArtifactChunkResult(chapter_index, chunk_index, audio_file=str(audio_path))
    try:
        stats = inspect_artifacts(audio_path, config=config)
    except (OSError, ValueError, wave.Error) as exc:
        item.status = "error"
        item.issues.append(ArtifactIssue("unreadable_wav", "error", f"Cannot read WAV: {exc}"))
        return item

    item.duration_seconds = stats["duration_seconds"]
    item.scores = {
        key: value
        for key, value in stats.items()
        if key != "duration_seconds"
    }
    _score_artifacts(item, stats, text, config)
    item.status = _status_from_issues(item.issues)
    return item


def inspect_artifacts(path: Path, *, config: ArtifactQaConfig | None = None) -> dict[str, float]:
    """Inspect one PCM WAV and return artifact scores."""
    cfg = config or ArtifactQaConfig()
    samples, sample_rate = _read_wav_samples(path)
    duration = len(samples) / sample_rate if sample_rate else 0.0
    if not samples:
        return {
            "duration_seconds": duration,
            "rms": 0.0,
            "peak": 0.0,
            "near_peak_ratio": 0.0,
            "crest_factor_db": 0.0,
            "dropout_score": 0.0,
            "repeated_audio_score": 0.0,
        }
    abs_samples = [abs(value) for value in samples]
    peak = max(abs_samples)
    rms = math.sqrt(sum(value * value for value in samples) / len(samples))
    crest = 20 * math.log10(max(peak, 1e-9) / max(rms, 1e-9)) if rms else 0.0
    near_peak = sum(1 for value in abs_samples if value >= cfg.near_peak_threshold) / len(samples)
    return {
        "duration_seconds": duration,
        "rms": rms,
        "peak": peak,
        "near_peak_ratio": near_peak,
        "crest_factor_db": crest,
        "dropout_score": _dropout_score(samples, sample_rate, cfg),
        "repeated_audio_score": _repeated_audio_score(samples, sample_rate),
    }


def _score_artifacts(
    item: ArtifactChunkResult,
    stats: dict[str, float],
    text: str,
    config: ArtifactQaConfig,
) -> None:
    duration = stats["duration_seconds"]
    rms = stats["rms"]
    peak = stats["peak"]
    near_peak_ratio = stats["near_peak_ratio"]
    crest = stats["crest_factor_db"]
    dropout = stats["dropout_score"]
    repeated = stats["repeated_audio_score"]

    if duration <= 0:
        item.issues.append(ArtifactIssue("zero_duration", "error", "WAV has zero duration."))
    if rms <= config.silence_rms_threshold:
        item.issues.append(ArtifactIssue("mostly_silent", "error", "Audio is mostly silent.", score=rms))
    if near_peak_ratio > config.clipping_ratio_threshold:
        item.issues.append(
            ArtifactIssue(
                "clipping",
                "error",
                f"Audio may be clipped ({near_peak_ratio:.2%} samples near peak).",
                score=near_peak_ratio,
            )
        )
    if peak > 0.80 and crest < config.harsh_crest_db_threshold:
        item.issues.append(
            ArtifactIssue(
                "harsh_overload",
                "error",
                f"Crest factor {crest:.1f} dB suggests harsh overload/distortion.",
                score=crest,
            )
        )
    if rms > config.silence_rms_threshold and crest > config.spike_crest_db_threshold:
        item.issues.append(
            ArtifactIssue(
                "peak_rms_imbalance",
                "warning",
                f"Crest factor {crest:.1f} dB suggests sharp isolated spikes.",
                score=crest,
            )
        )
    if dropout > 0:
        item.issues.append(
            ArtifactIssue(
                "sudden_dropout",
                "warning",
                "Audio contains sudden low-energy gaps between louder windows.",
                score=dropout,
            )
        )
    if repeated > config.repeated_audio_threshold:
        item.issues.append(
            ArtifactIssue(
                "repeated_audio",
                "error",
                "Audio contains repeated waveform windows that may sound like stutter.",
                score=repeated,
            )
        )

    text_len = len(text)
    if text_len and duration > 0:
        seconds_per_100 = duration / max(text_len / 100, 0.01)
        if seconds_per_100 < config.min_seconds_per_100_chars:
            item.issues.append(
                ArtifactIssue(
                    "too_short_for_text",
                    "warning",
                    f"Audio duration looks too short for text ({seconds_per_100:.1f}s/100 chars).",
                    score=seconds_per_100,
                )
            )
        if seconds_per_100 > config.max_seconds_per_100_chars:
            item.issues.append(
                ArtifactIssue(
                    "too_long_for_text",
                    "warning",
                    f"Audio duration looks too long for text ({seconds_per_100:.1f}s/100 chars).",
                    score=seconds_per_100,
                )
            )


def _status_from_issues(issues: list[ArtifactIssue]) -> str:
    if any(issue.severity == "error" for issue in issues):
        return "failed"
    if any(issue.severity == "warning" for issue in issues):
        return "warning"
    return "passed"


def _resolve_audio_path(audio_file: str, manifest_path: Path | None) -> Path | None:
    if not audio_file:
        return None
    path = Path(audio_file)
    if not path.is_absolute() and manifest_path is not None:
        path = manifest_path.parent / path
    return path


def _read_wav_samples(path: Path) -> tuple[list[float], int]:
    with wave.open(str(path), "rb") as wav:
        n_frames = wav.getnframes()
        channels = wav.getnchannels()
        sample_rate = wav.getframerate()
        sampwidth = wav.getsampwidth()
        frames = wav.readframes(n_frames)
    if n_frames == 0 or not frames:
        return [], sample_rate

    samples: list[float] = []
    step = sampwidth * channels
    for frame_start in range(0, len(frames) - step + 1, step):
        total = 0.0
        for channel in range(channels):
            start = frame_start + (channel * sampwidth)
            raw = frames[start:start + sampwidth]
            if sampwidth == 1:
                value = (raw[0] - 128) / 128.0
            elif sampwidth == 2:
                value = int.from_bytes(raw, "little", signed=True) / 32768.0
            elif sampwidth == 4:
                value = int.from_bytes(raw, "little", signed=True) / 2147483648.0
            else:
                raise ValueError(f"Unsupported WAV sample width: {sampwidth}")
            total += value
        samples.append(total / max(channels, 1))
    return samples, sample_rate


def _window_rms(samples: list[float], window_size: int) -> list[float]:
    if window_size <= 0:
        return []
    windows: list[float] = []
    for start in range(0, len(samples), window_size):
        chunk = samples[start:start + window_size]
        if not chunk:
            continue
        windows.append(math.sqrt(sum(value * value for value in chunk) / len(chunk)))
    return windows


def _dropout_score(samples: list[float], sample_rate: int, config: ArtifactQaConfig) -> float:
    window_size = max(1, int(sample_rate * config.dropout_window_ms / 1000))
    windows = _window_rms(samples, window_size)
    if len(windows) < 3:
        return 0.0
    high = max(windows)
    if high <= config.silence_rms_threshold:
        return 0.0
    low_cutoff = high * config.dropout_rms_ratio
    hits = 0
    for index in range(1, len(windows) - 1):
        if windows[index] < low_cutoff and windows[index - 1] > low_cutoff * 3 and windows[index + 1] > low_cutoff * 3:
            hits += 1
    return hits / len(windows)


def _repeated_audio_score(samples: list[float], sample_rate: int) -> float:
    if sample_rate <= 0 or len(samples) < sample_rate // 2:
        return 0.0
    best = 0.0
    for window_ms in (100, 200, 400, 800):
        window_size = int(sample_rate * window_ms / 1000)
        if window_size <= 0 or len(samples) < window_size * 3:
            continue
        fingerprints = [
            _fingerprint(samples[start:start + window_size])
            for start in range(0, len(samples) - window_size + 1, window_size)
        ]
        if len(fingerprints) < 3:
            continue
        repeated = 0
        comparisons = 0
        for left, right in zip(fingerprints, fingerprints[1:]):
            comparisons += 1
            if _fingerprint_distance(left, right) <= 1:
                repeated += 1
        if comparisons:
            best = max(best, repeated / comparisons)
    return best


def _fingerprint(window: list[float], bins: int = 12) -> tuple[int, ...]:
    if not window:
        return ()
    bin_size = max(1, len(window) // bins)
    values: list[int] = []
    for start in range(0, len(window), bin_size):
        part = window[start:start + bin_size]
        if not part:
            continue
        mean_abs = sum(abs(value) for value in part) / len(part)
        values.append(int(round(mean_abs * 32)))
        if len(values) == bins:
            break
    return tuple(values)


def _fingerprint_distance(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    if len(left) != len(right):
        return max(len(left), len(right))
    return sum(abs(a - b) for a, b in zip(left, right))
