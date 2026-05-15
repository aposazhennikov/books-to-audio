#!/usr/bin/env python3
"""Full end-to-end pipeline: book file → normalized chapters → LLM chunks → audio.

This script orchestrates all stages in order:

  Stage 1 — Rule-based normalization
      Loads the book, splits into chapters, applies the 19-stage normalization
      pipeline (encoding fixes, OCR cleanup, yofication, etc.), and saves one
      TXT file per chapter.

  Stage 2 — LLM normalization (optional, --llm-normalize)
      Sends each paragraph to a local Ollama model for grammar/punctuation
      correction.  The TextPreservationValidator rejects any LLM output that
      changes the text substantially (anti-hallucination guard).
      Overwrites the chapter files with the LLM-corrected versions.

  Stage 3 — LLM chunking
      Sends each chapter to Ollama for voice + tone annotation.
      Produces ``chunks_manifest_v2.json`` with per-chunk records like::

          {"narrator": "Он вошёл в комнату.", "voice_tone": "calm", ...}
          {"men": "— Кто здесь?", "voice_tone": "tense", ...}
          {"women": "— Всё в порядке.", "voice_tone": "warm and gentle", ...}

  Stage 4 — ComfyUI synthesis (optional, --synthesize)
      Reads the v2 manifest and synthesizes audio chunks via ComfyUI + Qwen3-TTS.
      Requires ``--workflow`` pointing to the ComfyUI workflow template JSON.

  Stage 5 — Assembly (optional, --assemble)
      Merges audio chunks into one WAV file per chapter.

Usage (minimal — normalize + chunk only):
    python scripts/run_pipeline.py \\
        --book books/mybook.pdf \\
        --out output/

Usage (full pipeline with ComfyUI):
    python scripts/run_pipeline.py \\
        --book books/mybook.pdf \\
        --out output/ \\
        --llm-normalize \\
        --synthesize \\
        --workflow comfyui_workflows/qwen3_tts_template.json \\
        --assemble

Usage (specific chapter only):
    python scripts/run_pipeline.py \\
        --book books/mybook.pdf \\
        --out output/ \\
        --chapter 3

Options:
    --book              Path to the book file (PDF/EPUB/FB2/TXT/DOCX).
    --out               Output root directory.
    --llm-model         Ollama model for both normalization and chunking
                        (default: gemma3:4b).
    --llm-endpoint      Ollama OpenAI-compatible endpoint
                        (default: http://localhost:11434/v1).
    --llm-normalize     Run LLM grammar/punctuation/yofication pass.
    --synthesize        Run ComfyUI synthesis after chunking.
    --workflow          Path to ComfyUI workflow JSON template (required with --synthesize).
    --comfyui-url       ComfyUI URL (default: http://localhost:8188).
    --assemble          Assemble audio chunks into chapter WAV files.
    --chapter N         Process only chapter N (1-based).
    --skip-stage1       Skip rule-based normalization (use existing TXT files).
    --ocr-mode          PDF OCR mode: auto|off|force (default: auto).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")
sys.path.insert(0, _SRC_DIR)


def _subprocess_env() -> dict[str, str]:
    """Return env dict with PYTHONPATH and PYTHONUTF8 set for child processes."""
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{_SRC_DIR}{os.pathsep}{existing}" if existing else _SRC_DIR
    env["PYTHONUTF8"] = "1"
    return env


# ── Stage helpers ─────────────────────────────────────────────────────────────


def stage_banner(n: int, title: str) -> None:
    """Print a visible stage separator."""
    print(f"\n{'─' * 60}")
    print(f"  Stage {n}: {title}")
    print(f"{'─' * 60}")


def find_book_dir(output_root: Path, book_path: Path) -> Path:
    """Derive the book output directory from the root and book filename."""
    stem = book_path.stem.lower().replace(" ", "_")
    suffix = book_path.suffix.lower().lstrip(".")
    return output_root / f"{stem}_{suffix}"


def load_chapter_texts(book_dir: Path) -> list[tuple[int, str]]:
    """Return list of (chapter_index, text) for all chapter TXT files."""
    chapters: list[tuple[int, str]] = []
    idx = 0
    while True:
        # Matches filenames like 001_chapter_01.txt, 002_chapter_02.txt, etc.
        ch_file = book_dir / f"{idx + 1:03d}_chapter_{idx + 1:02d}.txt"
        if not ch_file.exists():
            break
        chapters.append((idx, ch_file.read_text(encoding="utf-8")))
        idx += 1
    return chapters


# ── Stage 1: Rule-based normalization ────────────────────────────────────────


def run_stage1_normalize(
    book_path: Path,
    output_root: Path,
    ocr_mode: str,
) -> Path:
    """Run the normalize-book CLI to extract and normalize chapters."""
    cmd = [
        sys.executable, "-m", "book_normalizer.cli",
        "process", str(book_path),
        "--out", str(output_root),
        "--ocr-mode", ocr_mode,
        "-v",
    ]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False, env=_subprocess_env())
    if result.returncode != 0:
        print(f"WARNING: normalize-book exited with code {result.returncode}")

    book_dir = find_book_dir(output_root, book_path)
    if not book_dir.exists():
        print(f"ERROR: Expected output directory not found: {book_dir}")
        sys.exit(1)

    chapters = load_chapter_texts(book_dir)
    print(f"Normalization complete: {len(chapters)} chapter(s) in {book_dir}")
    return book_dir


# ── Stage 2: LLM normalization ────────────────────────────────────────────────


def run_stage2_llm_normalize(
    book_dir: Path,
    llm_endpoint: str,
    llm_model: str,
    chapter_filter: int | None,
) -> None:
    """Apply LLM grammar/punctuation/yofication correction to each chapter."""
    from book_normalizer.normalization.llm_normalizer import LlmNormalizer

    cache_dir = book_dir / "llm_norm_cache"
    normalizer = LlmNormalizer(
        endpoint=llm_endpoint,
        model=llm_model,
        cache_dir=cache_dir,
    )

    chapters = load_chapter_texts(book_dir)
    if not chapters:
        print("No chapter files found — skipping LLM normalization.")
        return

    # Filter chapters according to chapter_filter for consistent progress reporting.
    targets: list[tuple[int, str]] = [
        (ch_idx, text)
        for ch_idx, text in chapters
        if chapter_filter is None or ch_idx + 1 == chapter_filter
    ]
    total = len(targets)
    if total == 0:
        print("No matching chapters for LLM normalization (check --chapter).")
        return

    processed = 0
    stage_t0 = time.monotonic()
    for ch_idx, text in targets:
        ch_file = book_dir / f"{ch_idx + 1:03d}_chapter_{ch_idx + 1:02d}.txt"
        print(f"  LLM normalising chapter {ch_idx + 1} ({len(text)} chars)...")

        t0 = time.monotonic()
        corrected = normalizer.normalize_chapter(text, chapter_index=ch_idx)
        elapsed = time.monotonic() - t0

        ch_file.write_text(corrected, encoding="utf-8")
        processed += 1

        total_elapsed = time.monotonic() - stage_t0
        avg_per_ch = total_elapsed / processed
        remaining = total - processed
        eta = remaining * avg_per_ch

        print(
            f"    Done in {elapsed:.1f}s → saved {ch_file.name} "
            f"(elapsed {total_elapsed:.1f}s, eta ≈ {eta:.1f}s, {processed}/{total} chapters)"
        )

    print(f"LLM normalization complete: {processed} chapter(s) processed in {total_elapsed:.1f}s.")


# ── Stage 3: LLM chunking ─────────────────────────────────────────────────────


def run_stage3_llm_chunking(
    book_dir: Path,
    llm_endpoint: str,
    llm_model: str,
    chapter_filter: int | None,
    llm_max_retries: int | None,
    max_chunk_chars: int,
) -> Path:
    """Create v2 chunks manifest using LLM chunker."""
    from book_normalizer.chunking.llm_chunker import DEFAULT_WINDOW_CHARS, LlmChunker

    cache_dir = book_dir / "speaker_cache"
    init_kwargs: dict[str, object] = {
        "endpoint": llm_endpoint,
        "model": llm_model,
        "cache_dir": cache_dir,
        "max_chunk_chars": max_chunk_chars,
    }
    if llm_max_retries is not None:
        init_kwargs["max_retries"] = llm_max_retries

    chunker = LlmChunker(**init_kwargs)

    chapters = load_chapter_texts(book_dir)
    if not chapters:
        print("No chapter files found — cannot chunk.")
        sys.exit(1)

    # Filter chapters according to chapter_filter for consistent progress reporting.
    targets: list[tuple[int, str]] = [
        (ch_idx, text)
        for ch_idx, text in chapters
        if chapter_filter is None or ch_idx + 1 == chapter_filter
    ]
    if not targets:
        print("No matching chapters for LLM chunking (check --chapter).")
        sys.exit(1)

    def _estimate_windows(text: str, max_chars: int) -> int:
        """Roughly estimate how many windows this chapter will be split into.

        We do not reimplement the exact paragraph-based windowing logic here;
        an average based on character length is sufficient for ETA.
        """
        length = max(len(text), 1)
        return max(1, math.ceil(length / max_chars))

    all_specs = []
    stage_t0 = time.monotonic()

    total_windows = sum(_estimate_windows(text, DEFAULT_WINDOW_CHARS) for _, text in targets)
    processed_windows = 0

    for ch_idx, text in targets:
        est_windows = _estimate_windows(text, DEFAULT_WINDOW_CHARS)
        print(
            f"  Chunking chapter {ch_idx + 1} "
            f"({len(text)} chars, ~{est_windows} window(s))..."
        )
        t0 = time.monotonic()
        specs = chunker.chunk_chapter(ch_idx, text)
        elapsed = time.monotonic() - t0
        all_specs.extend(specs)

        processed_windows += est_windows
        total_elapsed = time.monotonic() - stage_t0
        avg_per_window = total_elapsed / processed_windows
        remaining_windows = max(total_windows - processed_windows, 0)
        eta = remaining_windows * avg_per_window

        print(
            f"    → {len(specs)} chunks in {elapsed:.1f}s "
            f"(elapsed {total_elapsed:.1f}s, eta ≈ {eta:.1f}s, "
            f"{processed_windows}/{total_windows} estimated windows)"
        )

    # Build v2 manifest.
    chapters_map: dict[int, dict] = {}
    for spec in all_specs:
        ci = spec.chapter_index
        if ci not in chapters_map:
            chapters_map[ci] = {
                "chapter_index": ci,
                "chapter_title": f"Chapter {ci + 1}",
                "chunks": [],
            }
        chapters_map[ci]["chunks"].append(spec.to_dict())

    manifest = {
        "version": 2,
        "book_title": book_dir.name,
        "chunker": "llm",
        "model": llm_model,
        "max_chunk_chars": max_chunk_chars,
        "chapters": [chapters_map[i] for i in sorted(chapters_map)],
    }

    manifest_path = book_dir / "chunks_manifest_v2.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    total = sum(len(c["chunks"]) for c in manifest["chapters"])
    print(f"Manifest written: {manifest_path} ({total} chunks total)")
    return manifest_path


# ── Stage 4: ComfyUI synthesis ────────────────────────────────────────────────


def run_stage4_synthesize(
    manifest_path: Path,
    out_dir: Path,
    comfyui_url: str,
    workflow_path: str,
    chapter_filter: int | None,
) -> None:
    """Synthesize audio chunks via ComfyUI."""
    cmd = [
        sys.executable,
        str(Path(__file__).parent / "synthesize_comfyui.py"),
        "--chunks-json", str(manifest_path),
        "--out", str(out_dir),
        "--workflow", workflow_path,
        "--comfyui-url", comfyui_url,
    ]
    if chapter_filter is not None:
        cmd += ["--chapter", str(chapter_filter)]

    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=False, env=_subprocess_env())


# ── Stage 5: Assembly ─────────────────────────────────────────────────────────


def run_stage5_assemble(
    manifest_path: Path,
    out_dir: Path,
    chapter_filter: int | None,
) -> None:
    """Assemble audio chunks into chapter WAV files."""
    cmd = [
        sys.executable,
        str(Path(__file__).parent / "assemble_chapter.py"),
        "--manifest", str(manifest_path),
        "--out", str(out_dir),
    ]
    if chapter_filter is not None:
        cmd += ["--chapter", str(chapter_filter)]
    else:
        cmd.append("--all")

    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=False, env=_subprocess_env())


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Full books-to-audio pipeline (normalize → chunk → synthesize → assemble)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--book", required=True, help="Path to book file (PDF/EPUB/FB2/TXT/DOCX).")
    parser.add_argument("--out", required=True, help="Output root directory.")
    parser.add_argument(
        "--llm-model", default="gemma3:4b",
        help="Ollama model for normalization and chunking (default: gemma3:4b).",
    )
    parser.add_argument(
        "--llm-endpoint", default="http://localhost:11434/v1",
        help="Ollama OpenAI-compatible endpoint (default: http://localhost:11434/v1).",
    )
    parser.add_argument(
        "--llm-normalize", action="store_true",
        help="Run LLM grammar/punctuation/yofication pass (Stage 2).",
    )
    parser.add_argument(
        "--llm-max-retries",
        type=int,
        default=None,
        help=(
            "Max retries per LLM window (default: internal constant). "
            "Use -1 for infinite retries (until success or manual stop)."
        ),
    )
    parser.add_argument(
        "--max-chunk-chars",
        type=int,
        default=400,
        help=(
            "Soft max chars per LLM chunk (default: 400). The splitter prefers "
            "sentence/clause boundaries and never cuts inside a word."
        ),
    )
    parser.add_argument(
        "--synthesize", action="store_true",
        help="Run ComfyUI synthesis after chunking (Stage 4).",
    )
    parser.add_argument(
        "--workflow", default=None,
        help="Path to ComfyUI workflow JSON template (required with --synthesize).",
    )
    parser.add_argument(
        "--comfyui-url", default="http://localhost:8188",
        help="ComfyUI URL (default: http://localhost:8188).",
    )
    parser.add_argument(
        "--assemble", action="store_true",
        help="Assemble audio chunks into chapter WAV files (Stage 5).",
    )
    parser.add_argument(
        "--chapter", type=int, default=None,
        help="Process only chapter N (1-based). Omit for all chapters.",
    )
    parser.add_argument(
        "--skip-stage1", action="store_true",
        help="Skip rule-based normalization (use existing chapter TXT files).",
    )
    parser.add_argument(
        "--ocr-mode", default="auto",
        choices=["auto", "off", "force"],
        help="PDF OCR mode (default: auto).",
    )
    args = parser.parse_args()
    if args.max_chunk_chars < 30:
        parser.error("--max-chunk-chars must be at least 30.")

    book_path = Path(args.book)
    output_root = Path(args.out)
    output_root.mkdir(parents=True, exist_ok=True)

    if not book_path.exists():
        print(f"ERROR: Book file not found: {book_path}")
        sys.exit(1)

    if args.synthesize and not args.workflow:
        print("ERROR: --workflow is required when using --synthesize.")
        sys.exit(1)

    t_start = time.monotonic()
    print("\nBooks-to-Audio Pipeline")
    print(f"Book:   {book_path}")
    print(f"Output: {output_root}")
    print(f"Model:  {args.llm_model}")
    print(f"Chunks: <= {args.max_chunk_chars} chars")

    # ── Stage 1 ───────────────────────────────────────────────────────────────
    if not args.skip_stage1:
        stage_banner(1, "Rule-based normalization")
        book_dir = run_stage1_normalize(book_path, output_root, args.ocr_mode)
    else:
        book_dir = find_book_dir(output_root, book_path)
        if not book_dir.exists():
            print(f"ERROR: Book directory not found (--skip-stage1): {book_dir}")
            sys.exit(1)
        stage_banner(1, "Rule-based normalization — SKIPPED")
        print(f"  Using existing directory: {book_dir}")

    # ── Stage 2 ───────────────────────────────────────────────────────────────
    if args.llm_normalize:
        stage_banner(2, "LLM normalization (grammar + punctuation + yofication)")
        run_stage2_llm_normalize(
            book_dir, args.llm_endpoint, args.llm_model, args.chapter
        )
    else:
        stage_banner(2, "LLM normalization — SKIPPED (use --llm-normalize to enable)")

    # ── Stage 3 ───────────────────────────────────────────────────────────────
    stage_banner(3, "LLM chunking (voice + tone annotation)")
    manifest_path = run_stage3_llm_chunking(
        book_dir,
        args.llm_endpoint,
        args.llm_model,
        args.chapter,
        args.llm_max_retries,
        args.max_chunk_chars,
    )

    # ── Stage 4 ───────────────────────────────────────────────────────────────
    audio_dir = book_dir / "audio_chunks"
    if args.synthesize:
        stage_banner(4, "ComfyUI synthesis")
        run_stage4_synthesize(
            manifest_path, audio_dir, args.comfyui_url, args.workflow, args.chapter
        )
    else:
        stage_banner(4, "ComfyUI synthesis — SKIPPED (use --synthesize to enable)")

    # ── Stage 5 ───────────────────────────────────────────────────────────────
    if args.assemble:
        stage_banner(5, "Assembly: merge chunks into chapter WAV files")
        run_stage5_assemble(manifest_path, book_dir, args.chapter)
    else:
        stage_banner(5, "Assembly — SKIPPED (use --assemble to enable)")

    elapsed = time.monotonic() - t_start
    print(f"\n{'═' * 60}")
    print(f"  Pipeline complete in {elapsed:.1f}s")
    print(f"  Output directory: {book_dir}")
    print(f"  Manifest:         {manifest_path}")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    main()
