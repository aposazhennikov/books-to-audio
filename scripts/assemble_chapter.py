#!/usr/bin/env python3
"""Assemble chapter WAV chunks into a single chapter audio file.

Supports two operating modes:

1. **File-scan mode** (default, backward compatible):
   Scans chunk_*.wav files in a directory, sorted by filename.

   Single chapter:
       python scripts/assemble_chapter.py \\
           --audio-dir output/mybook/audio_chunks/chapter_003 \\
           --out output/mybook/chapter_003.wav

   All chapters at once:
       python scripts/assemble_chapter.py \\
           --audio-dir output/mybook/audio_chunks \\
           --out output/mybook \\
           --all

2. **Manifest mode** (v2 manifest from synthesize_comfyui.py):
   Reads chunk order and voice info from chunks_manifest_v2.json.
   Only includes chunks where ``synthesized`` is True.

   All chapters:
       python scripts/assemble_chapter.py \\
           --manifest output/mybook/chunks_manifest_v2.json \\
           --out output/mybook \\
           --all

   Single chapter:
       python scripts/assemble_chapter.py \\
           --manifest output/mybook/chunks_manifest_v2.json \\
           --out output/mybook \\
           --chapter 3
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

# ── Audio helpers ─────────────────────────────────────────────────────────────


def add_silence(duration_ms: int, sample_rate: int) -> np.ndarray:
    """Generate silence of given duration in milliseconds."""
    n_samples = int(sample_rate * duration_ms / 1000)
    return np.zeros(n_samples, dtype=np.float32)


def assemble_from_wav_files(
    wav_files: list[Path],
    out_path: Path,
    pause_same_voice_ms: int,
    pause_voice_change_ms: int,
    voice_labels: list[str] | None = None,
) -> None:
    """Concatenate a list of WAV files with inter-chunk pauses.

    Args:
        wav_files: Ordered list of WAV file paths to concatenate.
        out_path: Destination WAV file path.
        pause_same_voice_ms: Silence between consecutive same-voice chunks (ms).
        pause_voice_change_ms: Silence when the voice changes (ms).
        voice_labels: Optional parallel list of voice labels matching wav_files.
            If None, voice is inferred from the filename (chunk_NNN_VOICE.wav).
    """
    if not wav_files:
        print(f"  No WAV files to assemble for {out_path.name}")
        return

    segments: list[np.ndarray] = []
    sample_rate: int | None = None
    prev_voice: str | None = None

    for idx, wav_path in enumerate(wav_files):
        if voice_labels:
            voice = voice_labels[idx]
        else:
            match = re.search(r"chunk_\d+_(\w+)\.wav", wav_path.name)
            voice = match.group(1) if match else "unknown"

        data, sr = sf.read(str(wav_path), dtype="float32")
        if sample_rate is None:
            sample_rate = sr

        if prev_voice is not None:
            pause_ms = (
                pause_voice_change_ms if voice != prev_voice else pause_same_voice_ms
            )
            segments.append(add_silence(pause_ms, sample_rate))

        # Mono-fy stereo audio for consistent concatenation.
        if data.ndim > 1:
            data = data.mean(axis=1)
        segments.append(data)
        prev_voice = voice

    if not segments or sample_rate is None:
        return

    full_audio = np.concatenate(segments)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_path), full_audio, sample_rate)

    duration = len(full_audio) / sample_rate
    size_mb = out_path.stat().st_size / 1024 / 1024
    print(f"  {out_path.name}: {len(wav_files)} chunks → {duration:.1f}s ({size_mb:.1f} MB)")


# ── File-scan mode ────────────────────────────────────────────────────────────


def assemble_chapter_dir(
    chunk_dir: Path,
    out_path: Path,
    pause_same_voice_ms: int,
    pause_voice_change_ms: int,
) -> None:
    """Assemble all chunk_*.wav files found in chunk_dir (file-scan mode)."""
    wav_files = sorted(chunk_dir.glob("chunk_*.wav"))
    assemble_from_wav_files(
        wav_files, out_path, pause_same_voice_ms, pause_voice_change_ms
    )


# ── Manifest mode ─────────────────────────────────────────────────────────────


def load_manifest_v2(manifest_path: Path) -> dict:
    """Load and validate a v2 chunks manifest."""
    if not manifest_path.exists():
        print(f"ERROR: Manifest not found: {manifest_path}")
        sys.exit(1)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if data.get("version", 1) != 2:
        print(
            f"WARNING: Expected manifest version 2, got {data.get('version', 1)}. "
            "Attempting to process anyway."
        )
    return data


def assemble_from_manifest(
    manifest: dict,
    out_dir: Path,
    pause_same_voice_ms: int,
    pause_voice_change_ms: int,
    chapter_filter: int | None,
) -> None:
    """Assemble chapters using audio_file paths stored in the v2 manifest.

    Only chunks with ``synthesized: true`` and a valid ``audio_file`` path
    are included.  Chunks are assembled in the order they appear in the
    manifest (which matches synthesis order).
    """
    chapters = manifest.get("chapters", [])
    if not chapters:
        print("ERROR: No chapters found in manifest.")
        sys.exit(1)

    for chapter_entry in chapters:
        ch_idx = chapter_entry.get("chapter_index", 0)
        ch_num = ch_idx + 1

        if chapter_filter is not None and ch_num != chapter_filter:
            continue

        chunks = chapter_entry.get("chunks", [])
        synthesized_chunks = [
            c for c in chunks
            if c.get("synthesized", False) and c.get("audio_file")
        ]

        if not synthesized_chunks:
            print(f"  Chapter {ch_num:03d}: no synthesized chunks found, skipping.")
            continue

        wav_files: list[Path] = []
        voice_labels: list[str] = []
        missing = 0

        for chunk in synthesized_chunks:
            audio_path = Path(chunk["audio_file"])
            if not audio_path.exists():
                print(f"  WARNING: Missing audio file {audio_path}, skipping chunk.")
                missing += 1
                continue
            wav_files.append(audio_path)
            voice_labels.append(chunk.get("voice", "narrator"))

        if missing:
            print(
                f"  Chapter {ch_num:03d}: {missing} chunk(s) missing on disk — "
                "re-run synthesize_comfyui.py to regenerate them."
            )

        if not wav_files:
            print(f"  Chapter {ch_num:03d}: no audio files available, skipping.")
            continue

        out_path = out_dir / f"chapter_{ch_num:03d}.wav"
        assemble_from_wav_files(
            wav_files, out_path, pause_same_voice_ms, pause_voice_change_ms, voice_labels
        )


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assemble WAV chunks into chapter audio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Source: either a directory (file-scan) or a manifest (v2).
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--audio-dir",
        help="Directory with chapter_NNN/ subdirs or a single chapter dir (file-scan mode).",
    )
    source_group.add_argument(
        "--manifest",
        help="Path to chunks_manifest_v2.json (manifest mode).",
    )

    parser.add_argument(
        "--out", required=True,
        help="Output path (single WAV with --audio-dir) or output dir (with --all or --manifest).",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Process all chapter_NNN subdirs (file-scan mode) or all chapters (manifest mode).",
    )
    parser.add_argument(
        "--chapter", type=int, default=None,
        help="Process only a specific chapter number (1-based).",
    )
    parser.add_argument(
        "--pause-same", type=int, default=300,
        help="Pause between same-voice chunks (ms, default: 300).",
    )
    parser.add_argument(
        "--pause-change", type=int, default=600,
        help="Pause on voice change (ms, default: 600).",
    )
    args = parser.parse_args()

    # ── Manifest mode ──────────────────────────────────────────────────────
    if args.manifest:
        manifest = load_manifest_v2(Path(args.manifest))
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)

        chapter_filter = args.chapter
        if not args.all and chapter_filter is None:
            print("ERROR: Specify --all or --chapter N when using --manifest.")
            sys.exit(1)

        assemble_from_manifest(
            manifest, out_dir, args.pause_same, args.pause_change, chapter_filter
        )
        return

    # ── File-scan mode ─────────────────────────────────────────────────────
    audio_dir = Path(args.audio_dir)

    if args.all or args.chapter:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)

        if args.chapter:
            ch_dir = audio_dir / f"chapter_{args.chapter:03d}"
            if not ch_dir.exists():
                print(f"ERROR: Chapter directory not found: {ch_dir}")
                sys.exit(1)
            out_path = out_dir / f"chapter_{args.chapter:03d}.wav"
            assemble_chapter_dir(ch_dir, out_path, args.pause_same, args.pause_change)
        else:
            ch_dirs = sorted(
                d for d in audio_dir.iterdir()
                if d.is_dir() and d.name.startswith("chapter_")
            )
            if not ch_dirs:
                print(f"No chapter dirs found in {audio_dir}")
                sys.exit(1)
            for ch_dir in ch_dirs:
                out_path = out_dir / f"{ch_dir.name}.wav"
                assemble_chapter_dir(ch_dir, out_path, args.pause_same, args.pause_change)
    else:
        # Single chapter directory → single output WAV.
        assemble_chapter_dir(audio_dir, Path(args.out), args.pause_same, args.pause_change)


if __name__ == "__main__":
    main()
