#!/usr/bin/env python3
"""Full end-to-end pipeline: book file → normalized chapters → chunks → audio.

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

  Stage 3 — Chunking
      In the default LLM mode, sends each chapter to Ollama for voice + tone annotation.
      In heuristic mode, runs the native rule-based chunk exporter with no LLM server.
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

Usage (offline smoke — normalize + heuristic chunks, no LLM):
    python scripts/run_pipeline.py \\
        --book books/mybook.pdf \\
        --out output/ \\
        --chunk-mode heuristic

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
                        (default: hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M).
    --llm-endpoint      Native Ollama endpoint
                        (default: http://localhost:11434).
    --llm-normalize     Run LLM grammar/punctuation/yofication pass.
    --chunk-mode        llm (default) or heuristic (offline rule-based chunks).
    --synthesize        Run ComfyUI synthesis after chunking.
    --asr-qa-after-synthesis
                        Run local faster-whisper ASR QA after synthesis and before assembly.
    --workflow          Path to ComfyUI workflow JSON template (required with --synthesize).
    --comfyui-url       ComfyUI URL (default: http://localhost:8188).
    --assemble          Assemble audio chunks into chapter WAV files.
    --chapter N         Process only chapter N (1-based).
    --skip-stage1       Skip rule-based normalization (use existing TXT files).
    --ocr-mode          PDF OCR mode: auto|off|force (default: auto).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
from collections.abc import Callable
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")
sys.path.insert(0, _SRC_DIR)

from book_normalizer.cli import process_command  # noqa: E402
from book_normalizer.languages import SUPPORTED_LANGUAGE_CODES, normalize_book_language  # noqa: E402
from book_normalizer.llm.model_router import PRIMARY_QWEN3_MODEL  # noqa: E402

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
    args = [
        str(book_path),
        "--out", str(output_root),
        "--ocr-mode", ocr_mode,
        "-v",
    ]
    print(f"Running in-process: normalize-book process {' '.join(args)}")
    try:
        process_command.main(
            args=args,
            prog_name="normalize-book process",
            standalone_mode=False,
        )
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        if code:
            print(f"ERROR: normalize-book process exited with code {code}")
            sys.exit(code)

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
    language: str,
    chapter_filter: int | None,
) -> None:
    """Apply LLM grammar/punctuation/yofication correction to each chapter."""
    from book_normalizer.normalization.llm_normalizer import LlmNormalizer

    cache_dir = book_dir / "llm_norm_cache"
    normalizer = LlmNormalizer(
        endpoint=llm_endpoint,
        model=llm_model,
        cache_dir=cache_dir,
        language=language,
        review_report_path=book_dir / "llm_normalization_review_report.json",
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
    language: str,
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
        "language": language,
        "review_report_path": book_dir / "llm_chunking_review_report.json",
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


def run_stage3_heuristic_chunking(
    book_dir: Path,
    max_chunk_chars: int,
    chapter_filter: int | None,
) -> Path:
    """Create v2 chunks manifest using the native heuristic exporter."""
    args = [
        "--book-dir",
        str(book_dir),
        "--mode",
        "heuristic",
        "--max-chunk-chars",
        str(max_chunk_chars),
    ]
    print(f"Running in-process: export_chunks.py {' '.join(args)}")
    _run_script_main("export_chunks.py", args)

    manifest_path = book_dir / "chunks_manifest_v2.json"
    if not manifest_path.exists():
        print(f"ERROR: Expected manifest not found: {manifest_path}")
        sys.exit(1)

    if chapter_filter is not None:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        chapters = [
            chapter
            for chapter in manifest.get("chapters", [])
            if int(chapter.get("chapter_index", -1)) + 1 == chapter_filter
        ]
        if not chapters:
            print("ERROR: No matching chapters for heuristic chunking (check --chapter).")
            sys.exit(1)
        manifest["chapters"] = chapters
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        total = sum(len(chapter.get("chunks", [])) for chapter in chapters)
        print(f"Manifest filtered to chapter {chapter_filter}: {total} chunk(s)")

    return manifest_path


# ── Stage 4: ComfyUI synthesis ────────────────────────────────────────────────


def run_stage4_synthesize(
    manifest_path: Path,
    out_dir: Path,
    comfyui_url: str,
    workflow_path: str,
    chapter_filter: int | None,
    *,
    quality_loop: bool = False,
    artifact_qa: bool = False,
    asr_qa_after_synthesis: bool = False,
    asr_model: str = "small",
    max_resynth_attempts: int = 2,
) -> None:
    """Synthesize audio chunks via ComfyUI."""
    args = [
        "--chunks-json", str(manifest_path),
        "--out", str(out_dir),
        "--workflow", workflow_path,
        "--comfyui-url", comfyui_url,
    ]
    if chapter_filter is not None:
        args += ["--chapter", str(chapter_filter)]
    if quality_loop:
        args += ["--quality-loop", "--max-resynth-attempts", str(max_resynth_attempts)]
    if artifact_qa:
        args.append("--artifact-qa")
    if asr_qa_after_synthesis:
        args += ["--asr-qa-after-synthesis", "--asr-model", asr_model]

    print(f"Running in-process: synthesize_comfyui.py {' '.join(args)}")
    _run_script_main("synthesize_comfyui.py", args)


# ── Stage 5: Assembly ─────────────────────────────────────────────────────────


def run_stage5_assemble(
    manifest_path: Path,
    out_dir: Path,
    chapter_filter: int | None,
) -> None:
    """Assemble audio chunks into chapter WAV files."""
    args = [
        "--manifest", str(manifest_path),
        "--out", str(out_dir),
    ]
    if chapter_filter is not None:
        args += ["--chapter", str(chapter_filter)]
    else:
        args.append("--all")

    print(f"Running in-process: assemble_chapter.py {' '.join(args)}")
    _run_script_main("assemble_chapter.py", args)


# ── Stage 5: ASR QA ──────────────────────────────────────────────────────────


def run_stage5_asr_qa(
    manifest_path: Path,
    *,
    asr_model: str,
    max_wer: float,
    max_cer: float,
    min_match_ratio: float,
    timeout_seconds: float,
    mark_failed_on_asr: bool,
) -> Path:
    """Run WAV QA, then ASR QA, then write a combined report and manifest annotations."""
    from book_normalizer.chunking.manifest_v2 import save_manifest
    from book_normalizer.tts.asr_qa import (
        AsrQaConfig,
        FasterWhisperBackend,
        annotate_manifest_with_asr,
        run_asr_qa,
    )
    from book_normalizer.tts.audio_qa import run_audio_qa

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report_path = manifest_path.with_name("asr_qa_report.json")

    print("Audio QA: checking WAV files before ASR...")
    audio_result = run_audio_qa(manifest)
    print(
        f"Audio QA: checked {audio_result.checked_files}/{audio_result.synthesized_chunks} "
        f"synthesized chunks, {len(audio_result.issues)} issue(s)."
    )

    print(f"ASR QA: backend=faster-whisper model={asr_model}")
    asr_result = run_asr_qa(
        manifest,
        config=AsrQaConfig(
            model=asr_model,
            timeout_seconds=timeout_seconds,
            max_wer=max_wer,
            max_cer=max_cer,
            min_match_ratio=min_match_ratio,
        ),
        backend=FasterWhisperBackend(asr_model),
        manifest_path=manifest_path,
    )
    summary = asr_result.summary
    print(
        "ASR QA: "
        f"checked {summary['checked_chunks']}/{summary['total_chunks']} chunks, "
        f"status={asr_result.status.value}, failed={summary['failed']}, "
        f"warnings={summary['warning']}, errors={summary['error']}."
    )

    payload = {
        "schema_version": 1,
        "manifest_path": str(manifest_path),
        "audio_qa": audio_result.to_dict(),
        "asr_qa": asr_result.to_dict(),
    }
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    annotate_manifest_with_asr(
        manifest,
        asr_result,
        report_path=report_path.resolve(),
        mark_failed_on_asr=mark_failed_on_asr,
    )
    save_manifest(manifest_path, manifest)
    print(f"ASR QA report: {report_path}")
    print(f"Manifest ASR annotations updated: {manifest_path}")
    return report_path


def _run_script_main(script_name: str, argv: list[str]) -> None:
    """Run a sibling script main(argv) inside this Python process."""
    main_func = _load_script_main(Path(__file__).resolve().parent / script_name)
    try:
        main_func(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        if code:
            sys.exit(code)


def _load_script_main(script: Path) -> Callable[[list[str] | None], None]:
    """Load a sibling script module and return its argv-aware main function."""
    spec = importlib.util.spec_from_file_location(f"books_to_audio_{script.stem}", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load script: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    main_func = getattr(module, "main", None)
    if not callable(main_func):
        raise RuntimeError(f"Script has no callable main(): {script}")
    return main_func


# ── Main ──────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Full books-to-audio pipeline (normalize → chunk → synthesize → assemble)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--book", required=True, help="Path to book file (PDF/EPUB/FB2/TXT/DOCX).")
    parser.add_argument("--out", required=True, help="Output root directory.")
    parser.add_argument(
        "--llm-model", default=PRIMARY_QWEN3_MODEL,
        help=f"Ollama model for normalization and chunking (default: {PRIMARY_QWEN3_MODEL}).",
    )
    parser.add_argument(
        "--llm-endpoint", default="http://localhost:11434",
        help="Native Ollama endpoint (default: http://localhost:11434).",
    )
    parser.add_argument(
        "--language",
        default="ru",
        choices=SUPPORTED_LANGUAGE_CODES,
        help="Book language for LLM routing (default: ru).",
    )
    parser.add_argument(
        "--llm-normalize", action="store_true",
        help="Run LLM grammar/punctuation/yofication pass (Stage 2).",
    )
    parser.add_argument(
        "--chunk-mode",
        choices=["llm", "heuristic"],
        default="llm",
        help="Stage 3 chunking mode: llm for smart local Ollama markup, heuristic for offline rule-based chunks.",
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
        "--quality-loop",
        action="store_true",
        help="Run synthesize -> artifact/ASR QA -> resynthesize bad chunks loop.",
    )
    parser.add_argument(
        "--artifact-qa",
        action="store_true",
        help="Run artifact QA for clipping, silence, dropouts, and repeated audio.",
    )
    parser.add_argument(
        "--asr-qa-after-synthesis",
        action="store_true",
        help="Run report-first local faster-whisper ASR QA after synthesis and before assembly.",
    )
    parser.add_argument(
        "--asr-model",
        default="small",
        help="faster-whisper model for ASR QA (default: small).",
    )
    parser.add_argument(
        "--max-wer",
        type=float,
        default=0.30,
        help="ASR QA fail threshold for word error rate (default: 0.30).",
    )
    parser.add_argument(
        "--max-cer",
        type=float,
        default=0.18,
        help="ASR QA fail threshold for character error rate (default: 0.18).",
    )
    parser.add_argument(
        "--min-match-ratio",
        type=float,
        default=0.78,
        help="ASR QA warning threshold for expected-word match ratio (default: 0.78).",
    )
    parser.add_argument(
        "--asr-timeout-seconds",
        type=float,
        default=180.0,
        help="Per-chunk ASR timeout in seconds (default: 180).",
    )
    parser.add_argument(
        "--mark-failed-on-asr",
        action="store_true",
        help="Also mark chunks failed when ASR status is failed/error.",
    )
    parser.add_argument(
        "--max-resynth-attempts",
        type=int,
        default=2,
        help="Max automatic resynthesis attempts per bad chunk (default: 2).",
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
    args = parser.parse_args(argv)
    if args.max_chunk_chars < 30:
        parser.error("--max-chunk-chars must be at least 30.")
    args.language = normalize_book_language(args.language)

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
    print(f"Model:  {args.llm_model if args.chunk_mode == 'llm' or args.llm_normalize else 'not used'}")
    print(f"Chunk mode: {args.chunk_mode}")
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
            book_dir, args.llm_endpoint, args.llm_model, args.language, args.chapter
        )
    else:
        stage_banner(2, "LLM normalization — SKIPPED (use --llm-normalize to enable)")

    # ── Stage 3 ───────────────────────────────────────────────────────────────
    if args.chunk_mode == "llm":
        stage_banner(3, "LLM chunking (voice + tone annotation)")
        manifest_path = run_stage3_llm_chunking(
            book_dir,
            args.llm_endpoint,
            args.llm_model,
            args.language,
            args.chapter,
            args.llm_max_retries,
            args.max_chunk_chars,
        )
    else:
        stage_banner(3, "Heuristic chunking (offline rule-based)")
        manifest_path = run_stage3_heuristic_chunking(
            book_dir,
            args.max_chunk_chars,
            args.chapter,
        )

    # ── Stage 4 ───────────────────────────────────────────────────────────────
    audio_dir = book_dir / "audio_chunks"
    if args.synthesize:
        stage_banner(4, "ComfyUI synthesis")
        run_stage4_synthesize(
            manifest_path,
            audio_dir,
            args.comfyui_url,
            args.workflow,
            args.chapter,
            quality_loop=args.quality_loop,
            artifact_qa=args.artifact_qa or args.quality_loop,
            asr_qa_after_synthesis=args.asr_qa_after_synthesis,
            asr_model=args.asr_model,
            max_resynth_attempts=args.max_resynth_attempts,
        )
    else:
        stage_banner(4, "ComfyUI synthesis — SKIPPED (use --synthesize to enable)")

    # ── Stage 5 ───────────────────────────────────────────────────────────────
    if args.asr_qa_after_synthesis and not args.quality_loop:
        stage_banner(5, "ASR QA: report-first transcript check")
        run_stage5_asr_qa(
            manifest_path,
            asr_model=args.asr_model,
            max_wer=args.max_wer,
            max_cer=args.max_cer,
            min_match_ratio=args.min_match_ratio,
            timeout_seconds=args.asr_timeout_seconds,
            mark_failed_on_asr=args.mark_failed_on_asr,
        )
    elif args.asr_qa_after_synthesis:
        stage_banner(5, "ASR QA handled inside quality loop")
    else:
        stage_banner(5, "ASR QA — SKIPPED (use --asr-qa-after-synthesis to enable)")

    # ── Stage 6 ───────────────────────────────────────────────────────────────
    if args.assemble:
        stage_banner(6, "Assembly: merge chunks into chapter WAV files")
        run_stage5_assemble(manifest_path, book_dir, args.chapter)
    else:
        stage_banner(6, "Assembly — SKIPPED (use --assemble to enable)")

    elapsed = time.monotonic() - t_start
    print(f"\n{'═' * 60}")
    print(f"  Pipeline complete in {elapsed:.1f}s")
    print(f"  Output directory: {book_dir}")
    print(f"  Manifest:         {manifest_path}")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    main()
