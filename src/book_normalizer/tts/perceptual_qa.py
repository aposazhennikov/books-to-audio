"""Perceptual speech-quality gates for synthesized audiobook chunks."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from book_normalizer.chunking.manifest_v2 import chunk_is_excluded, ensure_v2_manifest
from book_normalizer.tts.quality_gate import (
    BAD_QA_STATUSES,
    compact_issue_reason,
    normalize_statuses,
    reset_chunk_for_resynthesis,
)

PERCEPTUAL_QA_SCHEMA_VERSION = 1
DEFAULT_PERCEPTUAL_REPORT_NAME = "perceptual_qa_report.json"
DEFAULT_PERCEPTUAL_BACKENDS = ("nisqa-v2", "mosnet")
NISQA_DIMENSIONS = ("mos", "noisiness", "discontinuity", "coloration", "loudness")


@dataclass
class PerceptualQaConfig:
    """Thresholds for non-intrusive perceptual quality prediction."""

    backends: tuple[str, ...] = DEFAULT_PERCEPTUAL_BACKENDS
    min_mos: float = 2.70
    warn_mos: float = 3.30
    min_dimension_score: float = 2.20
    warn_dimension_score: float = 3.00


@dataclass
class PerceptualIssue:
    """One perceptual quality finding."""

    kind: str
    severity: str
    message: str
    score: float | None = None
    backend: str = ""

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "kind": self.kind,
            "severity": self.severity,
            "message": self.message,
        }
        if self.backend:
            data["backend"] = self.backend
        if self.score is not None:
            data["score"] = round(self.score, 4)
        return data


@dataclass
class PerceptualPrediction:
    """Scores from one perceptual QA backend for one audio file."""

    backend: str
    scores: dict[str, float]


@dataclass
class PerceptualChunkResult:
    """Perceptual QA result for one manifest chunk."""

    chapter_index: int
    chunk_index: int
    audio_file: str = ""
    status: str = "skipped"
    scores: dict[str, dict[str, float]] = field(default_factory=dict)
    issues: list[PerceptualIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_index": self.chapter_index,
            "chunk_index": self.chunk_index,
            "audio_file": self.audio_file,
            "status": self.status,
            "scores": {
                backend: {key: round(value, 4) for key, value in scores.items()}
                for backend, scores in self.scores.items()
            },
            "issues": [issue.to_dict() for issue in self.issues],
        }

    def to_manifest_block(self, *, report_path: Path | str | None, created_at: str) -> dict[str, Any]:
        return {
            "schema_version": PERCEPTUAL_QA_SCHEMA_VERSION,
            "status": self.status,
            "issues": [issue.kind for issue in self.issues],
            "scores": {
                backend: {key: round(value, 4) for key, value in scores.items()}
                for backend, scores in self.scores.items()
            },
            "report_path": str(report_path or ""),
            "created_at": created_at,
        }


@dataclass
class PerceptualQaResult:
    """Book-level perceptual QA report."""

    backends: list[str]
    created_at: str
    chunks: list[PerceptualChunkResult] = field(default_factory=list)

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
            "schema_version": PERCEPTUAL_QA_SCHEMA_VERSION,
            "status": self.status,
            "backends": self.backends,
            "created_at": self.created_at,
            "summary": self.summary,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
        }


class PerceptualBackend(Protocol):
    """Minimal backend contract for speech-quality predictors."""

    name: str

    def predict(self, audio_path: Path) -> PerceptualPrediction:
        """Predict MOS-like quality scores for one file."""


class NisqaV2Backend:
    """NISQA v2 zero-reference quality predictor via TorchMetrics."""

    name = "nisqa-v2"

    def __init__(self, *, sample_rate: int = 16000, device: str = "cpu") -> None:
        self.sample_rate = sample_rate
        self.device = device
        self._metric: Any | None = None

    def _load_metric(self) -> Any:
        if self._metric is not None:
            return self._metric
        try:
            import torch
            from torchmetrics.functional.audio.nisqa import non_intrusive_speech_quality_assessment
        except ImportError as exc:
            raise RuntimeError(
                "NISQA v2 dependencies are missing. Install them with "
                "`pip install 'book-normalizer[perceptual]'` or rerun install.py."
            ) from exc
        self._torch = torch
        self._nisqa_fn = non_intrusive_speech_quality_assessment
        self._metric = object()
        return self._metric

    def predict(self, audio_path: Path) -> PerceptualPrediction:
        self._load_metric()
        waveform, sample_rate = _load_audio_tensor(audio_path, target_sample_rate=self.sample_rate)
        scores_tensor = self._nisqa_fn(waveform, fs=sample_rate)
        scores = _tensor_to_floats(scores_tensor)
        return PerceptualPrediction(
            backend=self.name,
            scores={
                key: value
                for key, value in zip(NISQA_DIMENSIONS, scores, strict=False)
            },
        )


class MosNetBackend:
    """MOSNet adapter for speechmetrics-compatible installations."""

    name = "mosnet"

    def __init__(self) -> None:
        self._metric: Any | None = None

    def _load_metric(self) -> Any:
        if self._metric is not None:
            return self._metric
        try:
            import speechmetrics
        except ImportError as exc:
            raise RuntimeError(
                "MOSNet backend requires the optional `speechmetrics` package. "
                "Install it separately if you want MOSNet scores; NISQA v2 remains available "
                "from `book-normalizer[perceptual]`."
            ) from exc
        self._metric = speechmetrics.load("mosnet", window=None)
        return self._metric

    def predict(self, audio_path: Path) -> PerceptualPrediction:
        metric = self._load_metric()
        raw = metric(str(audio_path))
        value = _extract_mosnet_score(raw)
        return PerceptualPrediction(backend=self.name, scores={"mos": value})


def run_perceptual_qa(
    manifest: dict[str, Any],
    *,
    config: PerceptualQaConfig | None = None,
    manifest_path: Path | None = None,
    backends: list[PerceptualBackend] | None = None,
) -> PerceptualQaResult:
    """Run configured perceptual QA predictors over active manifest chunks."""
    cfg = config or PerceptualQaConfig()
    backend_objs = backends or _build_backends(cfg.backends)
    manifest_record = ensure_v2_manifest(manifest).to_record()
    result = PerceptualQaResult(
        backends=[backend.name for backend in backend_objs],
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
            audio_path = _resolve_audio_path(str(chunk.get("audio_file") or ""), manifest_path)
            if audio_path is None:
                item = PerceptualChunkResult(chapter_index, chunk_index)
                item.status = "warning"
                item.issues.append(
                    PerceptualIssue("missing_audio_file_field", "warning", "Chunk has no audio_file.")
                )
                result.chunks.append(item)
                continue
            result.chunks.append(_run_chunk_perceptual_qa(chapter_index, chunk_index, audio_path, backend_objs, cfg))
    return result


def annotate_manifest_with_perceptual(
    manifest: dict[str, Any],
    result: PerceptualQaResult,
    *,
    report_path: Path | str | None = None,
    reset_bad_chunks: bool = False,
    resynth_statuses: set[str] | list[str] | tuple[str, ...] | None = None,
    max_resynthesis_attempts: int = 2,
) -> None:
    """Attach compact perceptual QA blocks and optionally reset bad chunks."""
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
            chunk["perceptual_qa"] = chunk_result.to_manifest_block(
                report_path=report_path,
                created_at=result.created_at,
            )
            if reset_bad_chunks and chunk_result.status in statuses:
                reason = compact_issue_reason("perceptual_qa", chunk_result.issues)
                reset_chunk_for_resynthesis(
                    chunk,
                    reason=reason,
                    max_attempts=max_resynthesis_attempts,
                )


def write_perceptual_report(path: Path, result: PerceptualQaResult) -> None:
    """Write perceptual QA report JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def _build_backends(names: tuple[str, ...]) -> list[PerceptualBackend]:
    backends: list[PerceptualBackend] = []
    for name in names:
        normalized = name.strip().lower()
        if normalized in {"nisqa", "nisqa-v2", "nisqa_v2"}:
            backends.append(NisqaV2Backend())
        elif normalized == "mosnet":
            backends.append(MosNetBackend())
        elif normalized:
            raise ValueError(f"Unknown perceptual QA backend: {name}")
    if not backends:
        raise ValueError("At least one perceptual QA backend is required.")
    return backends


def _run_chunk_perceptual_qa(
    chapter_index: int,
    chunk_index: int,
    audio_path: Path,
    backends: list[PerceptualBackend],
    config: PerceptualQaConfig,
) -> PerceptualChunkResult:
    item = PerceptualChunkResult(chapter_index, chunk_index, audio_file=str(audio_path))
    if not audio_path.exists():
        item.status = "error"
        item.issues.append(PerceptualIssue("missing_audio_file", "error", f"Audio file does not exist: {audio_path}"))
        return item
    for backend in backends:
        try:
            prediction = backend.predict(audio_path)
        except Exception as exc:
            item.issues.append(
                PerceptualIssue(
                    "backend_error",
                    "info",
                    f"{backend.name} failed: {exc}",
                    backend=backend.name,
                )
            )
            continue
        item.scores[prediction.backend] = prediction.scores
        _score_prediction(item, prediction, config)
    item.status = "skipped" if not item.scores and item.issues else _status_from_issues(item.issues)
    return item


def _score_prediction(
    item: PerceptualChunkResult,
    prediction: PerceptualPrediction,
    config: PerceptualQaConfig,
) -> None:
    mos = prediction.scores.get("mos")
    if mos is not None:
        if mos < config.min_mos:
            item.issues.append(
                PerceptualIssue(
                    "low_mos",
                    "error",
                    f"{prediction.backend} MOS {mos:.2f} is below {config.min_mos:.2f}.",
                    score=mos,
                    backend=prediction.backend,
                )
            )
        elif mos < config.warn_mos:
            item.issues.append(
                PerceptualIssue(
                    "borderline_mos",
                    "warning",
                    f"{prediction.backend} MOS {mos:.2f} is below {config.warn_mos:.2f}.",
                    score=mos,
                    backend=prediction.backend,
                )
            )
    for dimension in ("noisiness", "discontinuity", "coloration", "loudness"):
        score = prediction.scores.get(dimension)
        if score is None:
            continue
        if score < config.min_dimension_score:
            item.issues.append(
                PerceptualIssue(
                    f"low_{dimension}",
                    "error",
                    f"{prediction.backend} {dimension} {score:.2f} is below {config.min_dimension_score:.2f}.",
                    score=score,
                    backend=prediction.backend,
                )
            )
        elif score < config.warn_dimension_score:
            item.issues.append(
                PerceptualIssue(
                    f"borderline_{dimension}",
                    "warning",
                    f"{prediction.backend} {dimension} {score:.2f} is below {config.warn_dimension_score:.2f}.",
                    score=score,
                    backend=prediction.backend,
                )
            )


def _status_from_issues(issues: list[PerceptualIssue]) -> str:
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


def _load_audio_tensor(audio_path: Path, *, target_sample_rate: int) -> tuple[Any, int]:
    try:
        import librosa
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "Perceptual QA audio loading requires librosa and torch. Install `book-normalizer[perceptual]`."
        ) from exc
    waveform, sample_rate = librosa.load(str(audio_path), sr=target_sample_rate, mono=True)
    return torch.tensor(waveform, dtype=torch.float32), int(sample_rate)


def _tensor_to_floats(value: Any) -> list[float]:
    if hasattr(value, "detach"):
        value = value.detach().cpu().flatten().tolist()
    if isinstance(value, (float, int)):
        return [float(value)]
    return [float(item) for item in value]


def _extract_mosnet_score(raw: Any) -> float:
    if isinstance(raw, dict):
        for key in ("mosnet", "mos", "score"):
            if key in raw:
                return _extract_mosnet_score(raw[key])
        if raw:
            return _extract_mosnet_score(next(iter(raw.values())))
    if isinstance(raw, list | tuple):
        if not raw:
            raise ValueError("MOSNet returned an empty score list.")
        return _extract_mosnet_score(raw[0])
    if hasattr(raw, "mean"):
        return float(raw.mean())
    return float(raw)
