"""Post-process synthesized WAV chunks for smoother audiobook pacing."""

from __future__ import annotations

import math
import wave
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SilenceSmoothingConfig:
    """Limits for accidental silence inside one synthesized chunk."""

    window_ms: int = 20
    max_internal_silence_ms: int = 450
    max_leading_silence_ms: int = 80
    max_trailing_silence_ms: int = 140
    absolute_silence_threshold: float = 0.003
    relative_peak_threshold: float = 0.018


@dataclass(frozen=True)
class SilenceSmoothingResult:
    """Summary of one smoothing pass."""

    changed: bool = False
    original_duration_ms: int = 0
    new_duration_ms: int = 0
    removed_silence_ms: int = 0
    max_silence_ms: int = 0
    compressed_runs: int = 0

    def to_dict(self) -> dict[str, int | bool]:
        return {
            "changed": self.changed,
            "original_duration_ms": self.original_duration_ms,
            "new_duration_ms": self.new_duration_ms,
            "removed_silence_ms": self.removed_silence_ms,
            "max_silence_ms": self.max_silence_ms,
            "compressed_runs": self.compressed_runs,
        }


def smooth_wav_silence(
    path: Path,
    *,
    config: SilenceSmoothingConfig | None = None,
) -> SilenceSmoothingResult:
    """Compress excessive silence in-place while preserving WAV parameters.

    The pass is intentionally conservative: normal punctuation pauses survive,
    but multi-second holes inside a generated chunk are reduced to audiobook
    scale pauses.
    """
    cfg = config or SilenceSmoothingConfig()
    with wave.open(str(path), "rb") as wav:
        params = wav.getparams()
        frames = wav.readframes(wav.getnframes())

    frame_count = params.nframes
    if frame_count <= 0 or not frames:
        return SilenceSmoothingResult()

    frame_size = params.nchannels * params.sampwidth
    window_frames = max(1, int(params.framerate * cfg.window_ms / 1000))
    windows = _analyse_windows(
        frames,
        frame_count=frame_count,
        frame_size=frame_size,
        channels=params.nchannels,
        sampwidth=params.sampwidth,
        window_frames=window_frames,
    )
    threshold = _silence_threshold(windows, cfg)
    silence_flags = [rms <= threshold for rms, _start, _end in windows]
    keep_ranges, max_silence_ms, compressed_runs = _kept_window_ranges(
        windows,
        silence_flags,
        window_ms=cfg.window_ms,
        max_internal_ms=cfg.max_internal_silence_ms,
        max_leading_ms=cfg.max_leading_silence_ms,
        max_trailing_ms=cfg.max_trailing_silence_ms,
    )

    if not compressed_runs:
        duration_ms = int(round(frame_count * 1000 / params.framerate))
        return SilenceSmoothingResult(
            changed=False,
            original_duration_ms=duration_ms,
            new_duration_ms=duration_ms,
            max_silence_ms=max_silence_ms,
        )

    output = bytearray()
    kept_frames = 0
    for start_frame, end_frame in keep_ranges:
        start_byte = start_frame * frame_size
        end_byte = end_frame * frame_size
        output.extend(frames[start_byte:end_byte])
        kept_frames += max(0, end_frame - start_frame)

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(params.nchannels)
        wav.setsampwidth(params.sampwidth)
        wav.setframerate(params.framerate)
        wav.writeframes(bytes(output))

    original_ms = int(round(frame_count * 1000 / params.framerate))
    new_ms = int(round(kept_frames * 1000 / params.framerate))
    return SilenceSmoothingResult(
        changed=True,
        original_duration_ms=original_ms,
        new_duration_ms=new_ms,
        removed_silence_ms=max(0, original_ms - new_ms),
        max_silence_ms=max_silence_ms,
        compressed_runs=compressed_runs,
    )


def inspect_silence_gaps(
    path: Path,
    *,
    config: SilenceSmoothingConfig | None = None,
) -> dict[str, float]:
    """Return silence-gap scores without modifying the WAV."""
    cfg = config or SilenceSmoothingConfig()
    with wave.open(str(path), "rb") as wav:
        params = wav.getparams()
        frames = wav.readframes(wav.getnframes())
    if params.nframes <= 0 or not frames:
        return {"max_silence_ms": 0.0, "excessive_silence_ratio": 0.0}
    frame_size = params.nchannels * params.sampwidth
    window_frames = max(1, int(params.framerate * cfg.window_ms / 1000))
    windows = _analyse_windows(
        frames,
        frame_count=params.nframes,
        frame_size=frame_size,
        channels=params.nchannels,
        sampwidth=params.sampwidth,
        window_frames=window_frames,
    )
    threshold = _silence_threshold(windows, cfg)
    silence_flags = [rms <= threshold for rms, _start, _end in windows]
    max_run = 0
    excessive = 0
    for start, end in _runs(silence_flags):
        run_ms = (end - start) * cfg.window_ms
        max_run = max(max_run, run_ms)
        if run_ms > cfg.max_internal_silence_ms:
            excessive += run_ms - cfg.max_internal_silence_ms
    duration_ms = params.nframes * 1000 / params.framerate
    return {
        "max_silence_ms": float(max_run),
        "excessive_silence_ratio": excessive / max(duration_ms, 1.0),
    }


def _analyse_windows(
    frames: bytes,
    *,
    frame_count: int,
    frame_size: int,
    channels: int,
    sampwidth: int,
    window_frames: int,
) -> list[tuple[float, int, int]]:
    windows: list[tuple[float, int, int]] = []
    for start_frame in range(0, frame_count, window_frames):
        end_frame = min(frame_count, start_frame + window_frames)
        total = 0.0
        samples = 0
        for frame_index in range(start_frame, end_frame):
            frame_start = frame_index * frame_size
            for channel in range(channels):
                raw_start = frame_start + channel * sampwidth
                raw = frames[raw_start:raw_start + sampwidth]
                value = _sample_value(raw, sampwidth)
                total += value * value
                samples += 1
        rms = math.sqrt(total / samples) if samples else 0.0
        windows.append((rms, start_frame, end_frame))
    return windows


def _sample_value(raw: bytes, sampwidth: int) -> float:
    if sampwidth == 1:
        return (raw[0] - 128) / 128.0
    if sampwidth == 2:
        return int.from_bytes(raw, "little", signed=True) / 32768.0
    if sampwidth == 4:
        return int.from_bytes(raw, "little", signed=True) / 2147483648.0
    raise ValueError(f"Unsupported WAV sample width: {sampwidth}")


def _silence_threshold(
    windows: list[tuple[float, int, int]],
    config: SilenceSmoothingConfig,
) -> float:
    peak_rms = max((rms for rms, _start, _end in windows), default=0.0)
    return max(config.absolute_silence_threshold, peak_rms * config.relative_peak_threshold)


def _kept_window_ranges(
    windows: list[tuple[float, int, int]],
    silence_flags: list[bool],
    *,
    window_ms: int,
    max_internal_ms: int,
    max_leading_ms: int,
    max_trailing_ms: int,
) -> tuple[list[tuple[int, int]], int, int]:
    keep = [True] * len(windows)
    max_silence_ms = 0
    compressed_runs = 0
    last_window_index = len(windows) - 1
    for start, end in _runs(silence_flags):
        run_windows = end - start
        run_ms = run_windows * window_ms
        max_silence_ms = max(max_silence_ms, run_ms)
        if start == 0:
            allowed_ms = max_leading_ms
            keep_tail = True
        elif end - 1 == last_window_index:
            allowed_ms = max_trailing_ms
            keep_tail = False
        else:
            allowed_ms = max_internal_ms
            keep_tail = False
        allowed_windows = max(1, int(math.ceil(allowed_ms / window_ms)))
        if run_windows <= allowed_windows:
            continue
        compressed_runs += 1
        if keep_tail:
            drop_start = start
            drop_end = end - allowed_windows
        else:
            drop_start = start + allowed_windows
            drop_end = end
        for index in range(drop_start, drop_end):
            keep[index] = False

    ranges: list[tuple[int, int]] = []
    current_start: int | None = None
    current_end: int | None = None
    for index, should_keep in enumerate(keep):
        if not should_keep:
            if current_start is not None and current_end is not None:
                ranges.append((current_start, current_end))
            current_start = None
            current_end = None
            continue
        _rms, start_frame, end_frame = windows[index]
        if current_start is None:
            current_start = start_frame
        current_end = end_frame
    if current_start is not None and current_end is not None:
        ranges.append((current_start, current_end))
    return ranges, max_silence_ms, compressed_runs


def _runs(flags: list[bool]) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for index, flag in enumerate(flags):
        if flag and start is None:
            start = index
        elif not flag and start is not None:
            runs.append((start, index))
            start = None
    if start is not None:
        runs.append((start, len(flags)))
    return runs
