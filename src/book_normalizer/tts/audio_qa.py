"""Audio QA checks for synthesized v2 manifests."""

from __future__ import annotations

import json
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AudioIssue:
    """A single audio QA finding."""

    severity: str
    kind: str
    message: str
    chapter_index: int | None = None
    chunk_index: int | None = None
    path: str = ""


@dataclass
class AudioQaResult:
    """Summary of QA checks."""

    total_chunks: int = 0
    synthesized_chunks: int = 0
    checked_files: int = 0
    duration_seconds: float = 0.0
    issues: list[AudioIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(issue.severity in {"error", "warning"} for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "total_chunks": self.total_chunks,
            "synthesized_chunks": self.synthesized_chunks,
            "checked_files": self.checked_files,
            "duration_seconds": round(self.duration_seconds, 3),
            "issues": [issue.__dict__ for issue in self.issues],
        }


def load_manifest(path: Path) -> dict[str, Any]:
    """Load a v2 manifest for QA."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Manifest must be a JSON object.")
    return data


def run_audio_qa(
    manifest: dict[str, Any],
    *,
    min_seconds_per_100_chars: float = 2.0,
    max_seconds_per_100_chars: float = 18.0,
    silence_rms_threshold: float = 1e-4,
    clipping_ratio_threshold: float = 0.01,
) -> AudioQaResult:
    """Check manifest/audio consistency and basic WAV health."""
    result = AudioQaResult()
    for chapter in manifest.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter_index = int(chapter.get("chapter_index", 0))
        for chunk in chapter.get("chunks", []):
            if not isinstance(chunk, dict):
                continue
            chunk_index = int(chunk.get("chunk_index", 0))
            result.total_chunks += 1
            if not chunk.get("synthesized", False):
                result.issues.append(
                    AudioIssue(
                        severity="warning",
                        kind="not_synthesized",
                        message="Chunk is not marked as synthesized.",
                        chapter_index=chapter_index,
                        chunk_index=chunk_index,
                    )
                )
                continue

            result.synthesized_chunks += 1
            audio_file = str(chunk.get("audio_file") or "")
            if not audio_file:
                result.issues.append(
                    AudioIssue(
                        severity="error",
                        kind="missing_audio_file_field",
                        message="Synthesized chunk has no audio_file path.",
                        chapter_index=chapter_index,
                        chunk_index=chunk_index,
                    )
                )
                continue

            audio_path = Path(audio_file)
            if not audio_path.exists():
                result.issues.append(
                    AudioIssue(
                        severity="error",
                        kind="missing_audio_file",
                        message=f"Audio file does not exist: {audio_path}",
                        chapter_index=chapter_index,
                        chunk_index=chunk_index,
                        path=str(audio_path),
                    )
                )
                continue
            if audio_path.stat().st_size == 0:
                result.issues.append(
                    AudioIssue(
                        severity="error",
                        kind="zero_byte_audio",
                        message=f"Audio file is empty: {audio_path}",
                        chapter_index=chapter_index,
                        chunk_index=chunk_index,
                        path=str(audio_path),
                    )
                )
                continue

            try:
                stats = inspect_wav(audio_path)
            except (wave.Error, OSError, ValueError) as exc:
                result.issues.append(
                    AudioIssue(
                        severity="error",
                        kind="unreadable_wav",
                        message=f"Cannot read WAV: {exc}",
                        chapter_index=chapter_index,
                        chunk_index=chunk_index,
                        path=str(audio_path),
                    )
                )
                continue

            result.checked_files += 1
            result.duration_seconds += stats["duration_seconds"]
            if stats["duration_seconds"] <= 0:
                result.issues.append(
                    AudioIssue(
                        "error",
                        "zero_duration",
                        "WAV has zero duration.",
                        chapter_index,
                        chunk_index,
                        str(audio_path),
                    )
                )

            text_len = len(str(chunk.get("text") or ""))
            if text_len:
                seconds_per_100 = stats["duration_seconds"] / max(text_len / 100, 0.01)
                if seconds_per_100 < min_seconds_per_100_chars:
                    result.issues.append(
                        AudioIssue(
                            "warning",
                            "too_short_for_text",
                            f"Audio duration looks too short for text ({seconds_per_100:.1f}s/100 chars).",
                            chapter_index,
                            chunk_index,
                            str(audio_path),
                        )
                    )
                if seconds_per_100 > max_seconds_per_100_chars:
                    result.issues.append(
                        AudioIssue(
                            "warning",
                            "too_long_for_text",
                            f"Audio duration looks too long for text ({seconds_per_100:.1f}s/100 chars).",
                            chapter_index,
                            chunk_index,
                            str(audio_path),
                        )
                    )

            if stats["rms"] <= silence_rms_threshold:
                result.issues.append(
                    AudioIssue(
                        "warning",
                        "mostly_silent",
                        "Audio is mostly silent.",
                        chapter_index,
                        chunk_index,
                        str(audio_path),
                    )
                )
            if stats["clipping_ratio"] > clipping_ratio_threshold:
                result.issues.append(
                    AudioIssue(
                        "warning",
                        "clipping",
                        f"Audio may be clipped ({stats['clipping_ratio']:.2%} samples near max).",
                        chapter_index,
                        chunk_index,
                        str(audio_path),
                    )
                )
    return result


def inspect_wav(path: Path) -> dict[str, float]:
    """Return duration/RMS/clipping stats for a PCM WAV file."""
    with wave.open(str(path), "rb") as wav:
        n_frames = wav.getnframes()
        framerate = wav.getframerate()
        sampwidth = wav.getsampwidth()
        frames = wav.readframes(n_frames)
        duration = n_frames / framerate if framerate else 0.0

    if n_frames == 0 or not frames:
        return {"duration_seconds": duration, "rms": 0.0, "clipping_ratio": 0.0}

    samples = _pcm_samples(frames, sampwidth)
    if not samples:
        return {"duration_seconds": duration, "rms": 0.0, "clipping_ratio": 0.0}

    max_abs = max(abs(value) for value in samples) or 1
    norm = [abs(value) / max_abs for value in samples]
    rms = (sum(value * value for value in norm) / len(norm)) ** 0.5
    clipping = sum(1 for value in norm if value >= 0.99) / len(norm)
    return {"duration_seconds": duration, "rms": rms, "clipping_ratio": clipping}


def _pcm_samples(frames: bytes, sampwidth: int) -> list[int]:
    if sampwidth == 1:
        return [byte - 128 for byte in frames]
    if sampwidth == 2:
        return [
            int.from_bytes(frames[i:i + 2], "little", signed=True)
            for i in range(0, len(frames) - 1, 2)
        ]
    if sampwidth == 4:
        return [
            int.from_bytes(frames[i:i + 4], "little", signed=True)
            for i in range(0, len(frames) - 3, 4)
        ]
    raise ValueError(f"Unsupported WAV sample width: {sampwidth}")
