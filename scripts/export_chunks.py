#!/usr/bin/env python3
"""Export voice-annotated chunks as JSON for the WSL TTS runner.

Usage (from Windows, in project root):
    python scripts/export_chunks.py --book-dir output/master_magii_1_pdf --speaker-mode heuristic
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from book_normalizer.chunking.voice_splitter import chunk_annotated_book
from book_normalizer.dialogue.attribution import HeuristicAttributor, SpeakerMode, create_attributor
from book_normalizer.dialogue.detector import DialogueDetector
from book_normalizer.models.book import Book, Chapter, Paragraph


def load_book_from_chapters(book_dir: Path) -> Book:
    """Load a Book from exported chapter text files."""
    chapters = []
    idx = 0
    while True:
        ch_file = book_dir / f"{idx + 1:03d}_chapter_{idx + 1:02d}.txt"
        if not ch_file.exists():
            break
        text = ch_file.read_text(encoding="utf-8")
        paras = [
            Paragraph(raw_text=p, normalized_text=p, index_in_chapter=j)
            for j, p in enumerate(text.split("\n\n"))
            if p.strip()
        ]
        ch = Chapter(title=f"Chapter {idx + 1}", index=idx, paragraphs=paras)
        chapters.append(ch)
        idx += 1

    if not chapters:
        print(f"ERROR: No chapter files found in {book_dir}")
        sys.exit(1)

    return Book(chapters=chapters)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export voice-annotated chunks for TTS")
    parser.add_argument("--book-dir", required=True, help="Directory with chapter TXT files.")
    parser.add_argument(
        "--speaker-mode", default="heuristic",
        choices=["heuristic", "llm", "manual"],
        help="Speaker attribution mode.",
    )
    parser.add_argument("--max-chunk-chars", type=int, default=600, help="Max chars per chunk (600 for stable intonation).")
    parser.add_argument(
        "--stress-mode", default="strip",
        choices=["strip", "keep_acute"],
        help="Stress mark handling: strip (remove) or keep_acute (preserve for TTS).",
    )
    parser.add_argument("--out", default=None, help="Output JSON path (default: book_dir/chunks_manifest.json).")
    args = parser.parse_args()

    book_dir = Path(args.book_dir)
    book = load_book_from_chapters(book_dir)
    print(f"Loaded {len(book.chapters)} chapters.")

    detector = DialogueDetector()
    annotated = detector.detect_book(book)
    total_dialogue = sum(ch.dialogue_count for ch in annotated)
    print(f"Dialogue lines: {total_dialogue}")

    attr_mode = SpeakerMode(args.speaker_mode)
    attributor = create_attributor(attr_mode, cache_dir=book_dir / "speaker_cache")
    result = attributor.attribute(annotated)
    print(f"Attribution ({result.strategy}): male={result.male_lines}, female={result.female_lines}, narrator={result.narrator_lines}")

    chunked = chunk_annotated_book(annotated, max_chunk_chars=args.max_chunk_chars)
    total_chunks = sum(len(v) for v in chunked.values())
    print(f"Chunks: {total_chunks}")

    manifest = []
    for ch_idx in sorted(chunked.keys()):
        for chunk in chunked[ch_idx]:
            manifest.append({
                "chapter_index": chunk.chapter_index,
                "chunk_index": chunk.index,
                "role": chunk.role.value,
                "voice_id": chunk.voice_id,
                "text": chunk.text,
            })

    out_path = Path(args.out) if args.out else book_dir / "chunks_manifest.json"
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Manifest written: {out_path} ({len(manifest)} chunks)")


if __name__ == "__main__":
    main()
