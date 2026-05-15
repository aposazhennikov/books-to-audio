#!/usr/bin/env python3
"""Export voice-annotated chunks as JSON for the WSL TTS runner.

Usage (from Windows, in project root):
    # Heuristic mode (fast, rule-based):
    python scripts/export_chunks.py --book-dir output/mybook_pdf --speaker-mode heuristic

    # LLM mode (Ollama, voice + mood detection):
    python scripts/export_chunks.py --book-dir output/mybook_pdf --mode llm --llm-model gemma3:4b

    # LLM mode with custom endpoint:
    python scripts/export_chunks.py --book-dir output/mybook_pdf --mode llm \\
        --llm-model gemma3:12b --llm-endpoint http://localhost:11434/v1

Output:
    heuristic → chunks_manifest.json  (v1 format, backward compatible)
    llm       → chunks_manifest_v2.json  (v2 format with voice + mood)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from book_normalizer.chunking.voice_splitter import chunk_annotated_book
from book_normalizer.dialogue.attribution import SpeakerMode, create_attributor
from book_normalizer.dialogue.detector import DialogueDetector
from book_normalizer.models.book import Book, Chapter, Paragraph

HEURISTIC_DEFAULT_MAX_CHUNK_CHARS = 600


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


def export_heuristic(
    book: Book,
    args: argparse.Namespace,
    book_dir: Path,
) -> None:
    """Build v1 manifest using heuristic or LLM attribution (old pipeline)."""
    detector = DialogueDetector()
    annotated = detector.detect_book(book)
    total_dialogue = sum(ch.dialogue_count for ch in annotated)
    print(f"Dialogue lines detected: {total_dialogue}")

    attr_mode = SpeakerMode(args.speaker_mode)
    attributor = create_attributor(attr_mode, cache_dir=book_dir / "speaker_cache")
    result = attributor.attribute(annotated)
    print(
        f"Attribution ({result.strategy}): "
        f"male={result.male_lines}, female={result.female_lines}, narrator={result.narrator_lines}"
    )

    max_chunk_chars = (
        args.max_chunk_chars
        if args.max_chunk_chars is not None
        else HEURISTIC_DEFAULT_MAX_CHUNK_CHARS
    )
    chunked = chunk_annotated_book(annotated, max_chunk_chars=max_chunk_chars)
    total_chunks = sum(len(v) for v in chunked.values())
    print(f"Total chunks: {total_chunks}")

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
    out_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Manifest written: {out_path} ({len(manifest)} chunks)")


def run_llm_normalize_book(
    book: Book,
    book_dir: Path,
    llm_endpoint: str,
    llm_model: str,
) -> Book:
    """Apply LLM normalization to all paragraphs in a book.

    Each paragraph is sent to Ollama for grammar/punctuation/yofication
    correction.  The TextPreservationValidator rejects outputs that change
    the text too much (anti-hallucination guard).

    Returns the book with corrected paragraph text.
    """
    from book_normalizer.normalization.llm_normalizer import LlmNormalizer

    cache_dir = book_dir / "llm_norm_cache"
    normalizer = LlmNormalizer(
        endpoint=llm_endpoint,
        model=llm_model,
        cache_dir=cache_dir,
    )

    print(f"LLM normalizer: model={llm_model}, endpoint={llm_endpoint}")
    total_accepted = total_rejected = 0

    for chapter in book.chapters:
        for para in chapter.paragraphs:
            original = para.normalized_text or para.raw_text
            if not original.strip():
                continue
            result = normalizer.normalize_paragraph(
                original, chapter.index, para.index_in_chapter
            )
            if result.is_valid:
                para.normalized_text = result.corrected
                total_accepted += 1
            else:
                total_rejected += 1

    print(
        f"LLM normalization: {total_accepted} paragraphs corrected, "
        f"{total_rejected} kept original."
    )
    return book


def export_llm(
    book: Book,
    args: argparse.Namespace,
    book_dir: Path,
) -> None:
    """Build v2 manifest using LLM-based chunking with voice + tone annotation."""
    from book_normalizer.chunking.llm_chunker import (
        DEFAULT_MAX_CHUNK_CHARS,
        LlmChunker,
    )

    endpoint = getattr(args, "llm_endpoint", "http://localhost:11434/v1")
    model = getattr(args, "llm_model", "gemma3:4b")
    max_chunk_chars = (
        args.max_chunk_chars
        if args.max_chunk_chars is not None
        else DEFAULT_MAX_CHUNK_CHARS
    )
    cache_dir = book_dir / "speaker_cache"

    # Optional LLM normalization pass.
    if getattr(args, "llm_normalize", False):
        print("\nRunning LLM normalization pass first...")
        book = run_llm_normalize_book(book, book_dir, endpoint, model)

    print(
        f"\nLLM chunker: model={model}, endpoint={endpoint}, "
        f"max_chunk_chars={max_chunk_chars}"
    )

    chunker = LlmChunker(
        endpoint=endpoint,
        model=model,
        cache_dir=cache_dir,
        max_chunk_chars=max_chunk_chars,
    )

    all_chunk_specs = []
    for chapter in book.chapters:
        chapter_text = "\n\n".join(
            p.normalized_text or p.raw_text
            for p in chapter.paragraphs
            if (p.normalized_text or p.raw_text).strip()
        )
        if not chapter_text.strip():
            continue

        print(f"  Chunking chapter {chapter.index + 1} ({len(chapter_text)} chars)...")
        specs = chunker.chunk_chapter(chapter.index, chapter_text)
        all_chunk_specs.extend(specs)
        print(f"    → {len(specs)} chunks")

    print(f"Total LLM chunks: {len(all_chunk_specs)}")

    # Build v2 manifest grouped by chapter.
    chapters_map: dict[int, dict] = {}
    for spec in all_chunk_specs:
        ch_idx = spec.chapter_index
        if ch_idx not in chapters_map:
            chapters_map[ch_idx] = {
                "chapter_index": ch_idx,
                "chapter_title": f"Chapter {ch_idx + 1}",
                "chunks": [],
            }
        chapters_map[ch_idx]["chunks"].append(spec.to_dict())

    # Infer book title from directory name.
    book_title = book_dir.name

    manifest_v2 = {
        "version": 2,
        "book_title": book_title,
        "chunker": "llm",
        "model": model,
        "max_chunk_chars": max_chunk_chars,
        "chapters": [chapters_map[i] for i in sorted(chapters_map)],
    }

    out_path = Path(args.out) if args.out else book_dir / "chunks_manifest_v2.json"
    out_path.write_text(
        json.dumps(manifest_v2, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Manifest v2 written: {out_path} ({len(all_chunk_specs)} chunks)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export voice-annotated chunks for TTS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--book-dir", required=True, help="Directory with chapter TXT files.")
    parser.add_argument(
        "--mode", default="heuristic",
        choices=["heuristic", "llm"],
        help="Chunking mode: heuristic (fast, rule-based) or llm (Ollama, voice+mood).",
    )
    parser.add_argument(
        "--speaker-mode", default="heuristic",
        choices=["heuristic", "llm", "manual"],
        help="Speaker attribution mode (heuristic mode only).",
    )
    parser.add_argument(
        "--llm-model", default="gemma3:4b",
        help="Ollama model for LLM chunking and normalization (default: gemma3:4b).",
    )
    parser.add_argument(
        "--llm-endpoint", default="http://localhost:11434/v1",
        help="OpenAI-compatible endpoint for LLM (default: http://localhost:11434/v1).",
    )
    parser.add_argument(
        "--llm-normalize", action="store_true",
        help=(
            "Run LLM grammar/punctuation/yofication correction before chunking. "
            "Only applies when --mode llm. "
            "Uses TextPreservationValidator to prevent hallucination."
        ),
    )
    parser.add_argument(
        "--max-chunk-chars", type=int, default=None,
        help=(
            "Soft max chars per chunk. The splitter prefers sentence/clause "
            "boundaries and never cuts inside a word. Defaults: 600 heuristic, "
            "400 LLM."
        ),
    )
    parser.add_argument(
        "--stress-mode", default="strip",
        choices=["strip", "keep_acute"],
        help="Stress mark handling: strip (remove) or keep_acute (preserve for TTS).",
    )
    parser.add_argument(
        "--out", default=None,
        help="Output JSON path (default: book_dir/chunks_manifest.json or chunks_manifest_v2.json).",
    )
    args = parser.parse_args()
    if args.max_chunk_chars is not None and args.max_chunk_chars < 30:
        parser.error("--max-chunk-chars must be at least 30.")

    book_dir = Path(args.book_dir)
    book = load_book_from_chapters(book_dir)
    print(f"Loaded {len(book.chapters)} chapter(s) from {book_dir}")

    if args.mode == "llm":
        export_llm(book, args, book_dir)
    else:
        export_heuristic(book, args, book_dir)


if __name__ == "__main__":
    main()
