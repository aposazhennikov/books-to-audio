#!/usr/bin/env python3
"""Assemble chapter WAV files from chunks_manifest_v2.json."""

from __future__ import annotations

import argparse
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from book_normalizer.tts.manifest_assembly import assemble_from_manifest, load_manifest_v2


def _wav_duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as wav:
            return wav.getnframes() / wav.getframerate()
    except (wave.Error, OSError, ZeroDivisionError):
        return 0.0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Assemble v2 manifest audio chunks into chapter WAV files.")
    parser.add_argument("--manifest", required=True, help="Path to chunks_manifest_v2.json.")
    parser.add_argument("--out", required=True, help="Output directory for chapter_NNN.wav files.")
    parser.add_argument("--all", action="store_true", help="Assemble all chapters.")
    parser.add_argument("--chapter", type=int, default=None, help="Assemble a specific 1-based chapter number.")
    parser.add_argument("--pause-same", type=int, default=300, help="Pause between same-voice chunks in ms.")
    parser.add_argument("--pause-change", type=int, default=600, help="Pause when the voice changes in ms.")
    parser.add_argument("--strict-missing", action="store_true", help="Fail when a synthesized audio_file is missing.")
    args = parser.parse_args(argv)

    if not args.all and args.chapter is None:
        parser.error("Specify --all or --chapter N.")

    try:
        manifest = load_manifest_v2(Path(args.manifest))
        results = assemble_from_manifest(
            manifest,
            Path(args.out),
            pause_same_voice_ms=args.pause_same,
            pause_voice_change_ms=args.pause_change,
            chapter_filter=args.chapter,
            strict_missing=args.strict_missing,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    for result in results:
        for message in result.messages:
            print(f"  {message}")
        if result.output_path:
            duration = _wav_duration(result.output_path)
            size_mb = result.output_path.stat().st_size / 1024 / 1024
            print(f"  {result.output_path.name}: {result.chunks} chunks -> {duration:.1f}s ({size_mb:.1f} MB)")
        elif result.skipped:
            print(f"  Chapter {result.chapter_number:03d}: no synthesized chunks found, skipping.")


if __name__ == "__main__":
    main()

