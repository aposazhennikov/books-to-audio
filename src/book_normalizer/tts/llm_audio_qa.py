"""Local multimodal LLM reviewer for synthesized audiobook chunks."""

from __future__ import annotations

import base64
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
from book_normalizer.tts.voice_library import default_voice_library_dir, normalize_voice_library_dir

LLM_AUDIO_QA_SCHEMA_VERSION = 1
DEFAULT_LLM_AUDIO_QA_REPORT_NAME = "llm_audio_qa_report.json"
DEFAULT_LLM_AUDIO_QA_MODEL = "Qwen/Qwen3-Omni-30B-A3B-Instruct"
DEFAULT_LLM_AUDIO_QA_FAVORITES_NAME = "qa_favorites.jsonl"
DEFAULT_LLM_AUDIO_QA_PROMPT = (
    "Оцени качество звука, интонации, паузы, ударения.\n"
    "Это сгенерированный мной AI голос озвучки текста книги.\n"
    "Будь критичен, не надо \"подсуживать\" мне.\n"
    "Язык текста -- русский, как и язык аудиофайла.\n"
    "Также сравни аудио с ожидаемой ролью, персонажем, настроением, эмоцией, "
    "типом фрагмента и режиссерскими указаниями. Если эмоция или роль не совпадают, "
    "считай это проблемой качества.\n"
    "Верни только JSON: status passed|warning|failed, score 0-100, review, "
    "issues [{kind,severity,message,start_seconds,end_seconds}], recommendations "
    "{temperature_delta, repetition_penalty_delta, speech_rate_delta}."
)
_KNOWN_GENERATION_KEYS = {
    "temperature",
    "top_p",
    "top_k",
    "repetition_penalty",
    "max_new_tokens",
    "speech_rate",
}


@dataclass(frozen=True)
class LlmAudioQaConfig:
    """Configuration for local LLM audio QA."""

    model: str = DEFAULT_LLM_AUDIO_QA_MODEL
    prompt: str = DEFAULT_LLM_AUDIO_QA_PROMPT
    language: str | None = None
    endpoint: str = ""
    timeout_seconds: float = 240.0
    min_score: int = 82
    warn_score: int = 90
    max_audio_bytes: int = 64 * 1024 * 1024


@dataclass
class LlmAudioQaIssue:
    """One LLM-reported audio quality issue."""

    kind: str
    severity: str
    message: str
    start_seconds: float | None = None
    end_seconds: float | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "kind": self.kind,
            "severity": self.severity,
            "message": self.message,
        }
        if self.start_seconds is not None:
            data["start_seconds"] = round(float(self.start_seconds), 3)
        if self.end_seconds is not None:
            data["end_seconds"] = round(float(self.end_seconds), 3)
        return data


@dataclass
class LlmAudioQaReview:
    """Normalized per-chunk LLM review."""

    status: str
    score: int
    review: str
    issues: list[LlmAudioQaIssue] = field(default_factory=list)
    recommendations: dict[str, Any] = field(default_factory=dict)

    def normalized_status(self, config: LlmAudioQaConfig) -> str:
        status = str(self.status or "").strip().lower()
        if any(issue.severity in {"error", "failed", "resynthesize"} for issue in self.issues):
            return "failed"
        if any(issue.severity in {"warning", "review"} for issue in self.issues):
            return "warning" if status != "failed" else "failed"
        if status in {"passed", "warning", "failed", "skipped", "error"}:
            return status
        if self.score < config.min_score:
            return "failed"
        if self.score < config.warn_score:
            return "warning"
        return "passed"

    def to_dict(self, config: LlmAudioQaConfig) -> dict[str, Any]:
        return {
            "status": self.normalized_status(config),
            "score": max(0, min(100, int(self.score))),
            "review": self.review,
            "issues": [issue.to_dict() for issue in self.issues],
            "recommendations": self.recommendations,
        }


class LlmAudioQaBackend(Protocol):
    """Minimal multimodal LLM audio reviewer contract."""

    name: str
    model: str

    def review_chunk(
        self,
        audio_path: Path,
        *,
        expected_text: str,
        language: str,
        expected_context: dict[str, Any],
    ) -> LlmAudioQaReview:
        """Review one audio chunk against the text it should pronounce."""


class OpenAICompatibleAudioBackend:
    """Local OpenAI-compatible endpoint backend, intended for vLLM-served Qwen3-Omni."""

    name = "openai-compatible-audio"

    def __init__(self, config: LlmAudioQaConfig) -> None:
        self.config = config
        self.model = config.model

    def review_chunk(
        self,
        audio_path: Path,
        *,
        expected_text: str,
        language: str,
        expected_context: dict[str, Any],
    ) -> LlmAudioQaReview:
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover - optional runtime dependency
            raise RuntimeError(
                "LLM audio QA endpoint mode requires httpx. Install the llm extra or rerun install.py."
            ) from exc
        if not self.config.endpoint:
            raise RuntimeError("LLM audio QA endpoint is not configured.")
        if audio_path.stat().st_size > self.config.max_audio_bytes:
            raise RuntimeError(f"Audio chunk is too large for LLM QA: {audio_path.stat().st_size} bytes.")

        encoded = base64.b64encode(audio_path.read_bytes()).decode("ascii")
        media_type = _audio_media_type(audio_path)
        prompt = _build_prompt(self.config.prompt, expected_text, language, expected_context)
        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "audio_url",
                            "audio_url": {"url": f"data:{media_type};base64,{encoded}"},
                        },
                    ],
                }
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        url = self.config.endpoint.rstrip("/") + "/chat/completions"
        with httpx.Client(timeout=self.config.timeout_seconds) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return review_from_json(content, config=self.config)


@dataclass
class LlmAudioQaChunkResult:
    """LLM audio QA result for one manifest chunk."""

    chapter_index: int
    chunk_index: int
    audio_file: str = ""
    status: str = "skipped"
    score: int = 0
    review: str = ""
    issues: list[LlmAudioQaIssue] = field(default_factory=list)
    recommendations: dict[str, Any] = field(default_factory=dict)
    expected_context: dict[str, Any] = field(default_factory=dict)
    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_index": self.chapter_index,
            "chunk_index": self.chunk_index,
            "audio_file": self.audio_file,
            "status": self.status,
            "score": self.score,
            "review": self.review,
            "issues": [issue.to_dict() for issue in self.issues],
            "recommendations": self.recommendations,
            "expected_context": self.expected_context,
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
            "schema_version": LLM_AUDIO_QA_SCHEMA_VERSION,
            "status": self.status,
            "score": self.score,
            "issues": [issue.kind for issue in self.issues],
            "review": self.review,
            "recommendations": self.recommendations,
            "expected_context": self.expected_context,
            "report_path": str(report_path or ""),
            "backend": backend,
            "model": model,
            "created_at": created_at,
        }


@dataclass
class LlmAudioQaResult:
    """Book-level local LLM audio QA report."""

    backend: str
    model: str
    language: str
    created_at: str
    chunks: list[LlmAudioQaChunkResult] = field(default_factory=list)

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
        return {"total_chunks": len(self.chunks), "issue_counts": issue_counts, **counts}

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": LLM_AUDIO_QA_SCHEMA_VERSION,
            "status": self.status,
            "backend": self.backend,
            "model": self.model,
            "language": self.language,
            "created_at": self.created_at,
            "summary": self.summary,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
        }


def run_llm_audio_qa(
    manifest: dict[str, Any],
    *,
    config: LlmAudioQaConfig | None = None,
    backend: LlmAudioQaBackend | None = None,
    manifest_path: Path | None = None,
) -> LlmAudioQaResult:
    """Run local multimodal LLM audio QA over active manifest chunks."""
    cfg = config or LlmAudioQaConfig()
    manifest_record = ensure_v2_manifest(manifest).to_record()
    language = normalize_book_language(cfg.language or manifest_record.get("language"))
    backend_obj = backend or OpenAICompatibleAudioBackend(cfg)
    result = LlmAudioQaResult(
        backend=backend_obj.name,
        model=backend_obj.model,
        language=language,
        created_at=datetime.now(timezone.utc).isoformat(),
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
                    _skipped_chunk(chapter_index, chunk_index, "missing_audio_file_field")
                )
                continue
            try:
                audio_path = resolve_manifest_audio_path(audio_file, manifest_path)
            except ManifestAudioPathError as exc:
                result.chunks.append(
                    _skipped_chunk(chapter_index, chunk_index, "unsafe_audio_file_path", message=str(exc))
                )
                continue
            result.chunks.append(
                _run_chunk_llm_audio_qa(
                    chapter_index,
                    chunk_index,
                    audio_path,
                    str(chunk.get("text") or ""),
                    _chunk_expected_context(chunk),
                    language,
                    backend_obj,
                    cfg,
                )
            )
    return result


def annotate_manifest_with_llm_audio_qa(
    manifest: dict[str, Any],
    result: LlmAudioQaResult,
    *,
    report_path: Path | str | None = None,
    reset_bad_chunks: bool = False,
    resynth_statuses: set[str] | list[str] | tuple[str, ...] | None = None,
    max_resynthesis_attempts: int = 2,
    favorite_library_dir: Path | str | None = None,
) -> None:
    """Attach compact LLM audio QA blocks and optionally reset bad chunks."""
    statuses = normalize_statuses(resynth_statuses or set(BAD_QA_STATUSES))
    by_chunk = {(chunk.chapter_index, chunk.chunk_index): chunk for chunk in result.chunks}
    for chapter in manifest.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter_index = int(chapter.get("chapter_index", 0))
        for chunk in chapter.get("chunks", []):
            if not isinstance(chunk, dict):
                continue
            chunk_result = by_chunk.get((chapter_index, int(chunk.get("chunk_index", 0))))
            if chunk_result is None:
                continue
            chunk["llm_audio_qa"] = chunk_result.to_manifest_block(
                report_path=report_path,
                backend=result.backend,
                model=result.model,
                created_at=result.created_at,
            )
            if reset_bad_chunks and chunk_result.status in statuses:
                next_options = _next_generation_options(
                    chunk.get("last_generation_options"),
                    chunk_result.recommendations,
                )
                if next_options:
                    chunk["next_generation_options"] = next_options
                reason = compact_issue_reason("llm_audio_qa", chunk_result.issues)
                reset_chunk_for_resynthesis(
                    chunk,
                    reason=reason,
                    max_attempts=max_resynthesis_attempts,
                )
            elif chunk_result.status == "passed" and favorite_library_dir is not None:
                _record_passed_favorite(
                    chunk,
                    chunk_result,
                    library_dir=favorite_library_dir,
                )


def write_llm_audio_qa_report(path: Path, result: LlmAudioQaResult) -> None:
    """Write a standalone local LLM audio QA report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def review_from_json(payload: str | dict[str, Any], *, config: LlmAudioQaConfig) -> LlmAudioQaReview:
    """Parse a model JSON response into a normalized review."""
    data = payload if isinstance(payload, dict) else json.loads(_extract_json(str(payload)))
    issues = [
        LlmAudioQaIssue(
            kind=str(item.get("kind") or "llm_audio_issue"),
            severity=str(item.get("severity") or "review"),
            message=str(item.get("message") or ""),
            start_seconds=_optional_float(item.get("start_seconds")),
            end_seconds=_optional_float(item.get("end_seconds")),
        )
        for item in data.get("issues", [])
        if isinstance(item, dict)
    ]
    review = LlmAudioQaReview(
        status=str(data.get("status") or ""),
        score=int(float(data.get("score", 0) or 0)),
        review=str(data.get("review") or ""),
        issues=issues,
        recommendations=data.get("recommendations") if isinstance(data.get("recommendations"), dict) else {},
    )
    review.status = review.normalized_status(config)
    return review


def _run_chunk_llm_audio_qa(
    chapter_index: int,
    chunk_index: int,
    audio_path: Path,
    expected_text: str,
    expected_context: dict[str, Any],
    language: str,
    backend: LlmAudioQaBackend,
    config: LlmAudioQaConfig,
) -> LlmAudioQaChunkResult:
    started = time.monotonic()
    item = LlmAudioQaChunkResult(chapter_index, chunk_index, audio_file=str(audio_path))
    item.expected_context = expected_context
    if not audio_path.exists():
        item.status = "error"
        item.issues.append(LlmAudioQaIssue("missing_audio_file", "error", f"Audio file does not exist: {audio_path}"))
        return item
    try:
        review = backend.review_chunk(
            audio_path,
            expected_text=expected_text,
            language=language,
            expected_context=expected_context,
        )
    except Exception as exc:
        item.status = "error"
        item.review = str(exc)
        item.issues.append(LlmAudioQaIssue("llm_audio_qa_error", "error", str(exc)))
        item.elapsed_seconds = time.monotonic() - started
        return item
    data = review.to_dict(config)
    item.status = str(data["status"])
    item.score = int(data["score"])
    item.review = str(data["review"])
    item.issues = review.issues
    item.recommendations = dict(review.recommendations)
    item.elapsed_seconds = time.monotonic() - started
    return item


def _next_generation_options(base: Any, recommendations: dict[str, Any]) -> dict[str, Any]:
    options = dict(base) if isinstance(base, dict) else {}
    if not options:
        return {}
    deltas = {
        "temperature": "temperature_delta",
        "top_p": "top_p_delta",
        "repetition_penalty": "repetition_penalty_delta",
        "speech_rate": "speech_rate_delta",
    }
    for key, delta_key in deltas.items():
        if delta_key not in recommendations:
            continue
        try:
            options[key] = round(float(options.get(key, 0.0)) + float(recommendations[delta_key]), 4)
        except (TypeError, ValueError):
            continue
    if "seed_strategy" in recommendations:
        options["seed_strategy"] = str(recommendations["seed_strategy"])
    return {key: value for key, value in options.items() if key in _KNOWN_GENERATION_KEYS or key == "seed_strategy"}


def _chunk_expected_context(chunk: dict[str, Any]) -> dict[str, Any]:
    context = {
        "voice_label": str(chunk.get("voice_label") or ""),
        "voice_id": str(chunk.get("voice_id") or ""),
        "voice_tone": str(chunk.get("voice_tone") or ""),
        "speaker": str(chunk.get("canonical_speaker") or chunk.get("speaker") or ""),
        "character_id": str(chunk.get("character_id") or ""),
        "character_description": str(chunk.get("character_description") or ""),
        "emotion": str(chunk.get("emotion") or ""),
        "section_kind": str(chunk.get("section_kind") or ""),
        "role": str(chunk.get("role") or chunk.get("voice") or ""),
        "cast_voice_id": str(chunk.get("cast_voice_id") or ""),
        "voice_strategy": str(chunk.get("voice_strategy") or ""),
    }
    director = chunk.get("director")
    if isinstance(director, dict):
        context["director"] = director
    last_generation_options = chunk.get("last_generation_options")
    if isinstance(last_generation_options, dict):
        context["generation_options"] = {
            key: last_generation_options[key]
            for key in sorted(last_generation_options)
            if key in _KNOWN_GENERATION_KEYS or key == "seed"
        }
    return {key: value for key, value in context.items() if value not in ("", {}, None)}


def _record_passed_favorite(
    chunk: dict[str, Any],
    chunk_result: LlmAudioQaChunkResult,
    *,
    library_dir: Path | str | None,
) -> None:
    options = chunk.get("last_generation_options")
    if not isinstance(options, dict):
        return
    target_dir = normalize_voice_library_dir(library_dir) if library_dir else default_voice_library_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": LLM_AUDIO_QA_SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "llm_audio_qa",
        "status": chunk_result.status,
        "score": chunk_result.score,
        "review": chunk_result.review,
        "issues": [issue.to_dict() for issue in chunk_result.issues],
        "chapter_index": int(chunk.get("chapter_index") or 0),
        "chunk_index": int(chunk.get("chunk_index") or 0),
        "speaker": str(chunk.get("canonical_speaker") or chunk.get("speaker") or ""),
        "emotion": str(chunk.get("emotion") or ""),
        "voice_label": str(chunk.get("voice_label") or ""),
        "voice_id": str(chunk.get("voice_id") or ""),
        "voice_tone": str(chunk.get("voice_tone") or ""),
        "section_kind": str(chunk.get("section_kind") or ""),
        "director": chunk.get("director") if isinstance(chunk.get("director"), dict) else {},
        "generation_options": {
            key: options[key]
            for key in sorted(options)
            if key in _KNOWN_GENERATION_KEYS or key == "seed"
        },
    }
    with (target_dir / DEFAULT_LLM_AUDIO_QA_FAVORITES_NAME).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _skipped_chunk(
    chapter_index: int,
    chunk_index: int,
    issue_kind: str,
    *,
    message: str = "",
) -> LlmAudioQaChunkResult:
    item = LlmAudioQaChunkResult(chapter_index, chunk_index)
    item.status = "skipped"
    item.review = message or issue_kind
    item.issues.append(LlmAudioQaIssue(issue_kind, "warning", item.review))
    return item


def _build_prompt(
    prompt: str,
    expected_text: str,
    language: str,
    expected_context: dict[str, Any],
) -> str:
    return (
        f"{prompt}\n\n"
        f"Language: {language}\n"
        f"Expected role/mood context JSON:\n"
        f"{json.dumps(expected_context, ensure_ascii=False, indent=2, sort_keys=True)}\n"
        f"Expected text:\n{expected_text}"
    )


def _audio_media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".mp3":
        return "audio/mpeg"
    if suffix == ".flac":
        return "audio/flac"
    if suffix == ".ogg":
        return "audio/ogg"
    return "audio/wav"


def _extract_json(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if not match:
        raise ValueError("LLM audio QA response did not contain a JSON object.")
    return match.group(0)


def _optional_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
