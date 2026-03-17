#!/usr/bin/env python3
"""Assemble chapter WAV chunks into a single chapter audio file.

Usage (from WSL):
    source ~/venvs/qwen3tts/bin/activate
    python scripts/assemble_chapter.py --audio-dir output/master_magii_1_pdf/audio_chunks/chapter_003 --out output/master_magii_1_pdf/chapter_003.wav

Or for all chapters:
    python scripts/assemble_chapter.py --audio-dir output/master_magii_1_pdf/audio_chunks --out output/master_magii_1_pdf --all
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf


def add_silence(duration_ms: int, sample_rate: int) -> np.ndarray:
    """Generate silence of given duration."""
    n_samples = int(sample_rate * duration_ms / 1000)
    return np.zeros(n_samples, dtype=np.float32)


def assemble_chapter(
    chunk_dir: Path,
    out_path: Path,
    pause_same_voice_ms: int = 300,
    pause_voice_change_ms: int = 600,
) -> None:
    """Merge WAV chunks from a single chapter into one WAV file."""
    wav_files = sorted(chunk_dir.glob("chunk_*.wav"))
    if not wav_files:
        print(f"  No WAV chunks in {chunk_dir}")
        return

    segments: list[np.ndarray] = []
    sample_rate = None
    prev_voice = None

    for wav_path in wav_files:
        match = re.search(r"chunk_\d+_(\w+)\.wav", wav_path.name)
        voice = match.group(1) if match else "unknown"

        data, sr = sf.read(str(wav_path), dtype="float32")
        if sample_rate is None:
            sample_rate = sr

        if prev_voice is not None:
            pause_ms = pause_voice_change_ms if voice != prev_voice else pause_same_voice_ms
            segments.append(add_silence(pause_ms, sample_rate))

        segments.append(data)
        prev_voice = voice

    if not segments or sample_rate is None:
        return

    full_audio = np.concatenate(segments)
    sf.write(str(out_path), full_audio, sample_rate)

    duration = len(full_audio) / sample_rate
    print(f"  {out_path.name}: {len(wav_files)} chunks -> {duration:.1f}s ({out_path.stat().st_size / 1024 / 1024:.1f} MB)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Assemble WAV chunks into chapter audio")
    parser.add_argument("--audio-dir", required=True, help="Directory with chapter_NNN/ subdirs or a single chapter dir.")
    parser.add_argument("--out", required=True, help="Output path (single WAV) or output dir (with --all).")
    parser.add_argument("--all", action="store_true", help="Process all chapter_NNN subdirs.")
    parser.add_argument("--pause-same", type=int, default=300, help="Pause between same-voice chunks (ms).")
    parser.add_argument("--pause-change", type=int, default=600, help="Pause on voice change (ms).")
    args = parser.parse_args()

    audio_dir = Path(args.audio_dir)

    if args.all:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        ch_dirs = sorted(d for d in audio_dir.iterdir() if d.is_dir() and d.name.startswith("chapter_"))
        if not ch_dirs:
            print(f"No chapter dirs found in {audio_dir}")
            sys.exit(1)
        for ch_dir in ch_dirs:
            out_path = out_dir / f"{ch_dir.name}.wav"
            assemble_chapter(ch_dir, out_path, args.pause_same, args.pause_change)
    else:
        assemble_chapter(audio_dir, Path(args.out), args.pause_same, args.pause_change)


if __name__ == "__main__":
    main()
