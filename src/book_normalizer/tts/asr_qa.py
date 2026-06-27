"""ASR quality gate for synthesized audiobook chunks.

The v1 gate is intentionally report-first: it detects suspicious chunks,
writes structured reports, and annotates the manifest without resynthesizing.
"""

from __future__ import annotations

import concurrent.futures
import json
import re
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from book_normalizer.chunking.manifest_v2 import chunk_is_excluded, ensure_v2_manifest
from book_normalizer.languages import normalize_book_language
from book_normalizer.tts.manifest_audio_paths import ManifestAudioPathError, resolve_manifest_audio_path
from book_normalizer.tts.quality_gate import (
    BAD_QA_STATUSES,
    compact_issue_reason,
    normalize_statuses,
    reset_chunk_for_resynthesis,
)

ASR_QA_SCHEMA_VERSION = 1
DEFAULT_ASR_MODEL = "small"
DEFAULT_ASR_REPORT_NAME = "asr_qa_report.json"


class AsrQaStatus(str, Enum):
    """Supported ASR QA chunk/book statuses."""

    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class AsrTranscript:
    """Normalized backend transcript payload."""

    text: str
    language: str = ""
    confidence: float | None = None
    segments: list[dict[str, Any]] = field(default_factory=list)
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "language": self.language,
            "confidence": self.confidence,
            "segments": self.segments,
            "duration_seconds": round(self.duration_seconds, 3),
        }


class AsrBackend(Protocol):
    """Minimal ASR backend contract."""

    name: str
    model: str

    def transcribe(self, audio_path: Path, *, language: str | None = None) -> AsrTranscript:
        """Transcribe an audio file."""


class FasterWhisperBackend:
    """Local faster-whisper backend loaded lazily."""

    name = "faster-whisper"

    def __init__(
        self,
        model: str = DEFAULT_ASR_MODEL,
        *,
        device: str = "auto",
        compute_type: str = "default",
        vad_filter: bool = False,
        beam_size: int = 5,
    ) -> None:
        self.model = model
        self.device = device
        self.compute_type = compute_type
        self.vad_filter = vad_filter
        self.beam_size = beam_size
        self._model_obj: Any | None = None

    def _load_model(self) -> Any:
        if self._model_obj is not None:
            return self._model_obj
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "ASR dependencies are missing. Install them with "
                "`pip install 'book-normalizer[asr]'` or rerun the installer with `--with-asr`."
            ) from exc

        kwargs: dict[str, Any] = {"device": self.device}
        if self.compute_type and self.compute_type != "default":
            kwargs["compute_type"] = self.compute_type
        self._model_obj = WhisperModel(self.model, **kwargs)
        return self._model_obj

    def transcribe(self, audio_path: Path, *, language: str | None = None) -> AsrTranscript:
        model = self._load_model()
        segments_iter, info = model.transcribe(
            str(audio_path),
            language=language or None,
            beam_size=self.beam_size,
            vad_filter=self.vad_filter,
        )
        text_parts: list[str] = []
        segments: list[dict[str, Any]] = []
        confidences: list[float] = []
        for segment in segments_iter:
            segment_text = str(getattr(segment, "text", "") or "").strip()
            if segment_text:
                text_parts.append(segment_text)
            record = {
                "start": float(getattr(segment, "start", 0.0) or 0.0),
                "end": float(getattr(segment, "end", 0.0) or 0.0),
                "text": segment_text,
            }
            avg_logprob = getattr(segment, "avg_logprob", None)
            if avg_logprob is not None:
                record["avg_logprob"] = float(avg_logprob)
            no_speech_prob = getattr(segment, "no_speech_prob", None)
            if no_speech_prob is not None:
                record["no_speech_prob"] = float(no_speech_prob)
                confidences.append(max(0.0, min(1.0, 1.0 - float(no_speech_prob))))
            segments.append(record)

        language_probability = getattr(info, "language_probability", None)
        if language_probability is not None:
            confidences.append(float(language_probability))
        duration = float(getattr(info, "duration", 0.0) or 0.0)
        if not duration and segments:
            duration = float(segments[-1].get("end") or 0.0)
        confidence = sum(confidences) / len(confidences) if confidences else None
        return AsrTranscript(
            text=" ".join(text_parts),
            language=str(getattr(info, "language", "") or ""),
            confidence=confidence,
            segments=segments,
            duration_seconds=duration,
        )


@dataclass
class AsrQaConfig:
    """ASR QA thresholds and text normalization options."""

    model: str = DEFAULT_ASR_MODEL
    language: str | None = None
    device: str = "auto"
    compute_type: str = "default"
    timeout_seconds: float = 180.0
    max_wer: float = 0.30
    max_cer: float = 0.18
    min_match_ratio: float = 0.78
    min_confidence: float = 0.40
    max_repeated_text_score: float = 0.18
    yo_tolerance: bool = True
    normalize_numbers: bool = False
    replacements: dict[str, str] = field(default_factory=dict)


@dataclass
class AsrQaIssue:
    """One ASR QA finding."""

    kind: str
    severity: str
    message: str
    score: float | None = None
    expected_span: dict[str, Any] | None = None
    transcript_span: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "kind": self.kind,
            "severity": self.severity,
            "message": self.message,
        }
        if self.score is not None:
            data["score"] = round(self.score, 4)
        if self.expected_span is not None:
            data["expected_span"] = self.expected_span
        if self.transcript_span is not None:
            data["transcript_span"] = self.transcript_span
        return data


@dataclass
class AsrChunkResult:
    """ASR QA result for one manifest chunk."""

    chapter_index: int
    chunk_index: int
    audio_file: str = ""
    status: AsrQaStatus = AsrQaStatus.SKIPPED
    expected_text: str = ""
    transcript_text: str = ""
    normalized_expected: str = ""
    normalized_transcript: str = ""
    language: str = ""
    expected_language: str = ""
    confidence: float | None = None
    duration_seconds: float = 0.0
    wer: float = 0.0
    cer: float = 0.0
    matched_ratio: float = 0.0
    repeated_text_score: float = 0.0
    missing_spans: list[dict[str, Any]] = field(default_factory=list)
    extra_spans: list[dict[str, Any]] = field(default_factory=list)
    issues: list[AsrQaIssue] = field(default_factory=list)
    preview: str = ""
    segments: list[dict[str, Any]] = field(default_factory=list)
    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_index": self.chapter_index,
            "chunk_index": self.chunk_index,
            "audio_file": self.audio_file,
            "status": self.status.value,
            "expected_text": self.expected_text,
            "transcript_text": self.transcript_text,
            "normalized_expected": self.normalized_expected,
            "normalized_transcript": self.normalized_transcript,
            "language": self.language,
            "expected_language": self.expected_language,
            "confidence": self.confidence,
            "duration_seconds": round(self.duration_seconds, 3),
            "wer": round(self.wer, 4),
            "cer": round(self.cer, 4),
            "matched_ratio": round(self.matched_ratio, 4),
            "repeated_text_score": round(self.repeated_text_score, 4),
            "missing_spans": self.missing_spans,
            "extra_spans": self.extra_spans,
            "issues": [issue.to_dict() for issue in self.issues],
            "preview": self.preview,
            "segments": self.segments,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
        }

    def to_manifest_block(
        self,
        *,
        report_path: Path | str | None,
        backend: str,
        model: str,
        created_at: str,
    ) -> dict[str, Any]:
        return {
            "schema_version": ASR_QA_SCHEMA_VERSION,
            "status": self.status.value,
            "wer": round(self.wer, 4),
            "cer": round(self.cer, 4),
            "matched_ratio": round(self.matched_ratio, 4),
            "issues": [issue.kind for issue in self.issues],
            "preview": self.preview,
            "report_path": str(report_path or ""),
            "backend": backend,
            "model": model,
            "lang": self.language or self.expected_language,
            "created_at": created_at,
        }


@dataclass
class AsrQaResult:
    """Book-level ASR QA report."""

    backend: str
    model: str
    language: str
    created_at: str
    chunks: list[AsrChunkResult] = field(default_factory=list)

    @property
    def status(self) -> AsrQaStatus:
        statuses = [chunk.status for chunk in self.chunks]
        if any(status == AsrQaStatus.ERROR for status in statuses):
            return AsrQaStatus.ERROR
        if any(status == AsrQaStatus.FAILED for status in statuses):
            return AsrQaStatus.FAILED
        if any(status == AsrQaStatus.WARNING for status in statuses):
            return AsrQaStatus.WARNING
        if statuses and all(status == AsrQaStatus.SKIPPED for status in statuses):
            return AsrQaStatus.SKIPPED
        return AsrQaStatus.PASSED

    @property
    def summary(self) -> dict[str, Any]:
        counts = {status.value: 0 for status in AsrQaStatus}
        issue_counts: dict[str, int] = {}
        checked = 0
        for chunk in self.chunks:
            counts[chunk.status.value] += 1
            if chunk.status != AsrQaStatus.SKIPPED:
                checked += 1
            for issue in chunk.issues:
                issue_counts[issue.kind] = issue_counts.get(issue.kind, 0) + 1
        return {
            "total_chunks": len(self.chunks),
            "checked_chunks": checked,
            "issue_counts": issue_counts,
            **counts,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": ASR_QA_SCHEMA_VERSION,
            "status": self.status.value,
            "backend": self.backend,
            "model": self.model,
            "language": self.language,
            "created_at": self.created_at,
            "summary": self.summary,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
        }


def normalize_asr_text(
    text: str,
    *,
    replacements: dict[str, str] | None = None,
    yo_tolerance: bool = True,
    normalize_numbers: bool = False,
) -> str:
    """Normalize text for ASR comparison."""
    normalized = str(text or "").lower()
    for src, dst in (replacements or {}).items():
        normalized = normalized.replace(src.lower(), dst.lower())
    if yo_tolerance:
        normalized = normalized.replace("ё", "е")
    if normalize_numbers:
        normalized = _normalize_ascii_digits(normalized)
    normalized = "".join(ch if _is_word_or_space(ch) else " " for ch in normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def run_asr_qa(
    manifest: dict[str, Any],
    *,
    config: AsrQaConfig | None = None,
    backend: AsrBackend | None = None,
    manifest_path: Path | None = None,
) -> AsrQaResult:
    """Run ASR QA over active manifest chunks, continuing after per-chunk errors."""
    cfg = config or AsrQaConfig()
    manifest_path = manifest_path or _manifest_path_from_record(manifest)
    manifest_record = ensure_v2_manifest(manifest).to_record()
    expected_language = normalize_book_language(cfg.language or manifest_record.get("language"))
    backend_obj = backend or FasterWhisperBackend(
        cfg.model,
        device=cfg.device,
        compute_type=cfg.compute_type,
    )
    created_at = datetime.now(timezone.utc).isoformat()
    result = AsrQaResult(
        backend=backend_obj.name,
        model=backend_obj.model,
        language=expected_language,
        created_at=created_at,
    )

    for chapter in manifest_record.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter_index = int(chapter.get("chapter_index", 0))
        for chunk in chapter.get("chunks", []):
            if not isinstance(chunk, dict) or chunk_is_excluded(chunk):
                continue
            chunk_index = int(chunk.get("chunk_index", 0))
            audio_file = str(chunk.get("audio_file") or "")
            if not audio_file:
                result.chunks.append(
                    _skipped_chunk(
                        chapter_index,
                        chunk_index,
                        "ASR skipped: chunk has no audio_file.",
                        issue_kind="missing_audio_file_field",
                    )
                )
                continue
            try:
                audio_path = resolve_manifest_audio_path(audio_file, manifest_path)
            except ManifestAudioPathError as exc:
                result.chunks.append(
                    _skipped_chunk(
                        chapter_index,
                        chunk_index,
                        f"ASR skipped: unsafe audio_file path. {exc}",
                        issue_kind="unsafe_audio_file_path",
                        audio_file=audio_file,
                    )
                )
                continue
            expected_text = str(chunk.get("text") or "")
            result.chunks.append(
                _run_chunk_asr_qa(
                    chapter_index,
                    chunk_index,
                    expected_text,
                    audio_path,
                    backend_obj,
                    cfg,
                    expected_language,
                )
            )

    return result


def annotate_manifest_with_asr(
    manifest: dict[str, Any],
    result: AsrQaResult,
    *,
    report_path: Path | str | None = None,
    mark_failed_on_asr: bool = False,
    reset_bad_chunks: bool = False,
    resynth_statuses: set[str] | list[str] | tuple[str, ...] | None = None,
    max_resynthesis_attempts: int = 2,
) -> None:
    """Attach compact ASR QA blocks to manifest chunks in-place."""
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
            chunk["asr_qa"] = chunk_result.to_manifest_block(
                report_path=report_path,
                backend=result.backend,
                model=result.model,
                created_at=result.created_at,
            )
            if reset_bad_chunks and chunk_result.status.value in statuses:
                reason = compact_issue_reason("asr_qa", chunk_result.issues)
                reset_chunk_for_resynthesis(
                    chunk,
                    reason=reason,
                    max_attempts=max_resynthesis_attempts,
                )
                continue
            if mark_failed_on_asr and chunk_result.status in {AsrQaStatus.FAILED, AsrQaStatus.ERROR}:
                chunk["failed"] = True
                chunk["error"] = "; ".join(issue.message for issue in chunk_result.issues[:3])


def write_asr_report(path: Path, result: AsrQaResult) -> None:
    """Write a standalone ASR report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def write_asr_diff(path: Path, result: AsrQaResult) -> None:
    """Write a compact human-readable expected/transcript diff."""
    lines = [
        f"ASR QA diff - status={result.status.value} backend={result.backend} model={result.model}",
        f"created_at={result.created_at}",
        "",
    ]
    for chunk in result.chunks:
        if chunk.status == AsrQaStatus.PASSED:
            continue
        lines.append(f"ch{chunk.chapter_index + 1:03d}/chunk{chunk.chunk_index + 1:03d} [{chunk.status.value}]")
        if chunk.issues:
            lines.append("issues: " + ", ".join(issue.kind for issue in chunk.issues))
        lines.append("expected:   " + chunk.expected_text)
        lines.append("transcript: " + chunk.transcript_text)
        lines.append("norm exp:   " + chunk.normalized_expected)
        lines.append("norm asr:   " + chunk.normalized_transcript)
        if chunk.missing_spans:
            lines.append("missing:    " + json.dumps(chunk.missing_spans, ensure_ascii=False))
        if chunk.extra_spans:
            lines.append("extra:      " + json.dumps(chunk.extra_spans, ensure_ascii=False))
        lines.append("")
    if len(lines) == 3:
        lines.append("No failed or warning ASR chunks.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _run_chunk_asr_qa(
    chapter_index: int,
    chunk_index: int,
    expected_text: str,
    audio_path: Path,
    backend: AsrBackend,
    config: AsrQaConfig,
    expected_language: str,
) -> AsrChunkResult:
    started = time.monotonic()
    base = AsrChunkResult(
        chapter_index=chapter_index,
        chunk_index=chunk_index,
        audio_file=str(audio_path),
        expected_text=expected_text,
        expected_language=expected_language,
    )
    try:
        transcript = _transcribe_with_timeout(
            backend,
            audio_path,
            language=expected_language,
            timeout_seconds=config.timeout_seconds,
        )
    except TimeoutError:
        base.status = AsrQaStatus.ERROR
        base.elapsed_seconds = time.monotonic() - started
        base.issues.append(
            AsrQaIssue(
                kind="timeout",
                severity="error",
                message=f"ASR timed out after {config.timeout_seconds:.0f}s.",
            )
        )
        base.preview = _preview(expected_text, "")
        return base
    except Exception as exc:
        base.status = AsrQaStatus.ERROR
        base.elapsed_seconds = time.monotonic() - started
        base.issues.append(
            AsrQaIssue(
                kind="asr_error",
                severity="error",
                message=str(exc),
            )
        )
        base.preview = _preview(expected_text, "")
        return base

    return _score_transcript(
        base,
        transcript,
        config,
        expected_language,
        elapsed_seconds=time.monotonic() - started,
    )


def _score_transcript(
    result: AsrChunkResult,
    transcript: AsrTranscript,
    config: AsrQaConfig,
    expected_language: str,
    *,
    elapsed_seconds: float,
) -> AsrChunkResult:
    result.transcript_text = transcript.text
    result.language = normalize_book_language(transcript.language or expected_language)
    result.confidence = transcript.confidence
    result.duration_seconds = transcript.duration_seconds
    result.segments = transcript.segments
    result.elapsed_seconds = elapsed_seconds
    result.normalized_expected = normalize_asr_text(
        result.expected_text,
        replacements=config.replacements,
        yo_tolerance=config.yo_tolerance,
        normalize_numbers=config.normalize_numbers,
    )
    result.normalized_transcript = normalize_asr_text(
        result.transcript_text,
        replacements=config.replacements,
        yo_tolerance=config.yo_tolerance,
        normalize_numbers=config.normalize_numbers,
    )
    expected_words = result.normalized_expected.split()
    transcript_words = result.normalized_transcript.split()
    result.wer = _word_error_rate(expected_words, transcript_words)
    result.cer = _char_error_rate(result.normalized_expected, result.normalized_transcript)
    result.matched_ratio = _matched_ratio(expected_words, transcript_words)
    result.repeated_text_score = _repeated_text_score(transcript_words)
    result.missing_spans, result.extra_spans = _word_spans(expected_words, transcript_words)
    result.preview = _preview(result.expected_text, result.transcript_text)

    if not result.normalized_transcript:
        result.issues.append(
            AsrQaIssue("empty_transcript", "error", "ASR returned an empty transcript.")
        )
    if result.language and result.language != expected_language:
        result.issues.append(
            AsrQaIssue(
                "language_mismatch",
                "error",
                f"Detected language {result.language!r}, expected {expected_language!r}.",
            )
        )
    if result.confidence is not None and result.confidence < config.min_confidence:
        result.issues.append(
            AsrQaIssue(
                "low_confidence",
                "warning",
                f"ASR confidence {result.confidence:.2f} is below {config.min_confidence:.2f}.",
                score=result.confidence,
            )
        )
    if result.wer > config.max_wer:
        result.issues.append(
            AsrQaIssue(
                "high_wer",
                "error",
                f"WER {result.wer:.2%} is above {config.max_wer:.2%}.",
                score=result.wer,
            )
        )
    if result.cer > config.max_cer:
        result.issues.append(
            AsrQaIssue(
                "high_cer",
                "error",
                f"CER {result.cer:.2%} is above {config.max_cer:.2%}.",
                score=result.cer,
            )
        )
    if result.matched_ratio < config.min_match_ratio:
        result.issues.append(
            AsrQaIssue(
                "missing_words",
                "warning",
                f"Matched ratio {result.matched_ratio:.2%} is below {config.min_match_ratio:.2%}.",
                score=result.matched_ratio,
                expected_span=result.missing_spans[0] if result.missing_spans else None,
            )
        )
    if result.extra_spans:
        result.issues.append(
            AsrQaIssue(
                "extra_words",
                "warning",
                "ASR transcript contains words not aligned with the expected text.",
                transcript_span=result.extra_spans[0],
            )
        )
    if result.repeated_text_score > config.max_repeated_text_score:
        result.issues.append(
            AsrQaIssue(
                "repeated_text",
                "error",
                f"Repeated text score {result.repeated_text_score:.2%} is suspicious.",
                score=result.repeated_text_score,
            )
        )
    result.status = _status_from_issues(result.issues)
    return result


def _status_from_issues(issues: list[AsrQaIssue]) -> AsrQaStatus:
    if any(issue.kind in {"asr_error", "timeout"} for issue in issues):
        return AsrQaStatus.ERROR
    if any(issue.severity == "error" for issue in issues):
        return AsrQaStatus.FAILED
    if any(issue.severity == "warning" for issue in issues):
        return AsrQaStatus.WARNING
    return AsrQaStatus.PASSED


def _transcribe_with_timeout(
    backend: AsrBackend,
    audio_path: Path,
    *,
    language: str,
    timeout_seconds: float,
) -> AsrTranscript:
    if timeout_seconds <= 0:
        return backend.transcribe(audio_path, language=language)
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(backend.transcribe, audio_path, language=language)
    try:
        return future.result(timeout=timeout_seconds)
    except concurrent.futures.TimeoutError as exc:
        future.cancel()
        raise TimeoutError from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _manifest_path_from_record(manifest: dict[str, Any]) -> Path | None:
    raw_path = str(manifest.get("_manifest_path") or "")
    return Path(raw_path) if raw_path else None


def _skipped_chunk(
    chapter_index: int,
    chunk_index: int,
    message: str,
    *,
    issue_kind: str,
    audio_file: str = "",
) -> AsrChunkResult:
    result = AsrChunkResult(chapter_index=chapter_index, chunk_index=chunk_index, audio_file=audio_file)
    result.status = AsrQaStatus.SKIPPED
    result.preview = message
    result.issues.append(AsrQaIssue(issue_kind, "warning", message))
    return result


def _is_word_or_space(ch: str) -> bool:
    if ch.isspace() or ch.isalnum():
        return True
    return unicodedata.category(ch).startswith("M")


def _normalize_ascii_digits(text: str) -> str:
    # v1 intentionally keeps full language-aware number normalization disabled
    # by default; this only canonicalizes digit runs when a caller opts in.
    return re.sub(r"\d+", lambda match: str(int(match.group(0))), text)


def _word_error_rate(expected: list[str], actual: list[str]) -> float:
    if not expected:
        return 0.0 if not actual else 1.0
    return _levenshtein(expected, actual) / len(expected)


def _char_error_rate(expected: str, actual: str) -> float:
    if not expected:
        return 0.0 if not actual else 1.0
    return _levenshtein(list(expected), list(actual)) / len(expected)


def _levenshtein(left: list[str], right: list[str]) -> int:
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for i, left_item in enumerate(left, start=1):
        current = [i]
        for j, right_item in enumerate(right, start=1):
            cost = 0 if left_item == right_item else 1
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + cost,
                )
            )
        previous = current
    return previous[-1]


def _matched_ratio(expected: list[str], actual: list[str]) -> float:
    if not expected:
        return 1.0 if not actual else 0.0
    import difflib

    matcher = difflib.SequenceMatcher(a=expected, b=actual, autojunk=False)
    matches = sum(block.size for block in matcher.get_matching_blocks())
    return matches / len(expected)


def _word_spans(
    expected: list[str],
    actual: list[str],
    *,
    limit: int = 20,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    import difflib

    missing: list[dict[str, Any]] = []
    extra: list[dict[str, Any]] = []
    matcher = difflib.SequenceMatcher(a=expected, b=actual, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag in {"replace", "delete"} and len(missing) < limit:
            missing.append({"start": i1, "end": i2, "words": expected[i1:i2]})
        if tag in {"replace", "insert"} and len(extra) < limit:
            extra.append({"start": j1, "end": j2, "words": actual[j1:j2]})
    return missing, extra


def _repeated_text_score(words: list[str]) -> float:
    if len(words) < 2:
        return 0.0
    repeated = 0
    i = 0
    while i < len(words) - 1:
        best = 0
        max_window = min(8, (len(words) - i) // 2)
        for size in range(1, max_window + 1):
            if words[i:i + size] == words[i + size:i + (2 * size)]:
                best = size
        if best:
            repeated += best
            i += best * 2
        else:
            i += 1
    return repeated / len(words)


def _preview(expected: str, transcript: str, *, limit: int = 160) -> str:
    expected_short = _short_text(expected, limit // 2)
    transcript_short = _short_text(transcript, limit // 2)
    return f"expected: {expected_short} | asr: {transcript_short}"


def _short_text(text: str, limit: int) -> str:
    compact = " ".join(str(text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: max(0, limit - 3)].rstrip() + "..."
