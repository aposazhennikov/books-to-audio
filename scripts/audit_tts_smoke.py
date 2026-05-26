#!/usr/bin/env python3
"""Audit a live TTS smoke output without loading any model."""

from __future__ import annotations

import argparse
import json
import math
import sys
import wave
from array import array
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BAD_FRONT_MATTER_TERMS = ("royallib", "http", "приятного")
DEFAULT_MAX_SILENCE_SECONDS = 2.5
DEFAULT_MAX_CLIPPING_RATIO = 0.001
SILENCE_THRESHOLD = 80
CLIPPING_THRESHOLD = 32700


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit a live TTS smoke directory.")
    parser.add_argument("smoke_dir", type=Path)
    parser.add_argument("--min-duration", type=float, default=10.0)
    parser.add_argument("--expect-chunks", type=int, default=2)
    parser.add_argument("--max-silence-seconds", type=float, default=DEFAULT_MAX_SILENCE_SECONDS)
    parser.add_argument("--max-clipping-ratio", type=float, default=DEFAULT_MAX_CLIPPING_RATIO)
    parser.add_argument("--write-report", type=Path, default=None)
    args = parser.parse_args(argv)

    try:
        report = audit_tts_smoke(
            args.smoke_dir,
            min_duration=args.min_duration,
            expect_chunks=args.expect_chunks,
            max_silence_seconds=args.max_silence_seconds,
            max_clipping_ratio=args.max_clipping_ratio,
        )
    except (OSError, ValueError, KeyError) as exc:
        print(f"Audit failed: {exc}", file=sys.stderr)
        return 1

    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(payload)
    if args.write_report is not None:
        args.write_report.parent.mkdir(parents=True, exist_ok=True)
        args.write_report.write_text(payload + "\n", encoding="utf-8")
    return 0


def audit_tts_smoke(
    smoke_dir: Path,
    *,
    min_duration: float = 10.0,
    expect_chunks: int = 2,
    max_silence_seconds: float = DEFAULT_MAX_SILENCE_SECONDS,
    max_clipping_ratio: float = DEFAULT_MAX_CLIPPING_RATIO,
) -> dict[str, Any]:
    """Return a strict audit report for a live TTS smoke output directory."""
    live_report = json.loads((smoke_dir / "live_tts_smoke_report.json").read_text(encoding="utf-8"))
    manifest = json.loads((smoke_dir / "chunks_manifest_v2.json").read_text(encoding="utf-8"))
    chunks = manifest["chapters"][0]["chunks"]
    text = "\n".join(str(chunk.get("text", "")) for chunk in chunks)
    bad_terms = [
        term
        for term in BAD_FRONT_MATTER_TERMS
        if term.casefold() in text.casefold()
    ]
    wav_path = smoke_dir / "chapter_001.wav"
    wav_stats = _wav_stats(wav_path)
    failures: list[str] = []

    if live_report.get("status") != "ok":
        failures.append(f"status={live_report.get('status')!r}")
    if live_report.get("audio_qa", {}).get("ok") is not True:
        failures.append("audio_qa_not_ok")
    if live_report.get("synthesis", {}).get("synthesized") != expect_chunks:
        failures.append(f"synthesized={live_report.get('synthesis', {}).get('synthesized')!r}")
    if len(chunks) != expect_chunks:
        failures.append(f"chunks={len(chunks)!r}")
    if bad_terms:
        failures.append(f"front_matter_terms={bad_terms!r}")
    if wav_stats["channels"] != 1:
        failures.append(f"wav_channels={wav_stats['channels']!r}")
    if wav_stats["sample_rate"] != 24000:
        failures.append(f"wav_sample_rate={wav_stats['sample_rate']!r}")
    if wav_stats["sample_width"] != 2:
        failures.append(f"wav_sample_width={wav_stats['sample_width']!r}")
    if wav_stats["duration_seconds"] < min_duration:
        failures.append(f"duration_seconds={wav_stats['duration_seconds']!r}")
    if wav_stats["rms"] <= 0 or wav_stats["peak"] <= 0:
        failures.append("silent_wav")
    if wav_stats["longest_silence_seconds"] > max_silence_seconds:
        failures.append(f"longest_silence_seconds={wav_stats['longest_silence_seconds']!r}")
    if wav_stats["clipping_ratio"] > max_clipping_ratio:
        failures.append(f"clipping_ratio={wav_stats['clipping_ratio']!r}")

    return {
        "ok": not failures,
        "smoke_dir": str(smoke_dir),
        "status": live_report.get("status"),
        "audio_qa_ok": live_report.get("audio_qa", {}).get("ok"),
        "synthesized": live_report.get("synthesis", {}).get("synthesized"),
        "chunks": len(chunks),
        "bad_front_matter_terms": bad_terms,
        "wav": wav_stats,
        "limits": {
            "min_duration_seconds": min_duration,
            "max_silence_seconds": max_silence_seconds,
            "max_clipping_ratio": max_clipping_ratio,
        },
        "failures": failures,
    }


def _wav_stats(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_rate = wav.getframerate()
        sample_width = wav.getsampwidth()
        frames_count = wav.getnframes()
        frames = wav.readframes(frames_count)
    if sample_width != 2:
        samples: list[int] = []
    else:
        samples_array = array("h")
        samples_array.frombytes(frames)
        if sys.byteorder != "little":
            samples_array.byteswap()
        samples = list(samples_array)
    if samples:
        peak = max(abs(sample) for sample in samples)
        rms = int(math.sqrt(sum(sample * sample for sample in samples) / len(samples)))
        clipping_samples = sum(1 for sample in samples if abs(sample) >= CLIPPING_THRESHOLD)
        clipping_ratio = clipping_samples / len(samples)
        longest_silence_samples = _longest_silence_run(samples)
    else:
        peak = 0
        rms = 0
        clipping_ratio = 0.0
        longest_silence_samples = 0
    return {
        "path": str(path),
        "channels": channels,
        "sample_rate": sample_rate,
        "sample_width": sample_width,
        "frames": frames_count,
        "duration_seconds": round(frames_count / sample_rate, 2) if sample_rate else 0,
        "rms": rms,
        "peak": peak,
        "clipping_ratio": round(clipping_ratio, 6),
        "longest_silence_seconds": (
            round(longest_silence_samples / (sample_rate * channels), 2)
            if sample_rate and channels
            else 0
        ),
    }


def _longest_silence_run(samples: list[int]) -> int:
    longest = 0
    current = 0
    for sample in samples:
        if abs(sample) <= SILENCE_THRESHOLD:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


if __name__ == "__main__":
    raise SystemExit(main())
