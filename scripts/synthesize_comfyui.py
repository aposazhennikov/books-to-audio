#!/usr/bin/env python3
"""Synthesize audio from a v2 chunks manifest using ComfyUI + Qwen3-TTS.

Reads chunks_manifest_v2.json produced by export_chunks.py --mode llm,
queues each chunk to the ComfyUI API, downloads the resulting WAV file,
and updates the manifest with synthesized=true + audio_file path.

Supports resume: already-synthesized chunks (synthesized=true) are skipped.

Usage:
    python scripts/synthesize_comfyui.py \\
        --chunks-json output/mybook/chunks_manifest_v2.json \\
        --out output/mybook/audio_chunks \\
        --workflow comfyui_workflows/qwen3_tts_template.json

    # Custom ComfyUI URL:
    python scripts/synthesize_comfyui.py \\
        --chunks-json output/mybook/chunks_manifest_v2.json \\
        --out output/mybook/audio_chunks \\
        --workflow comfyui_workflows/qwen3_tts_template.json \\
        --comfyui-url http://localhost:8188

    # Synthesize only one chapter:
    python scripts/synthesize_comfyui.py \\
        --chunks-json output/mybook/chunks_manifest_v2.json \\
        --out output/mybook/audio_chunks \\
        --workflow comfyui_workflows/qwen3_tts_template.json \\
        --chapter 2

Progress lines printed to stdout:
    PROGRESS 5/120
These are parseable by the GUI's TTSSynthesisWorker.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from book_normalizer.comfyui.client import ComfyUIClient, ComfyUIError
from book_normalizer.comfyui.generation_options import (
    DEFAULT_SEED,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_K,
    DEFAULT_TOP_P,
    GenerationOptions,
)
from book_normalizer.comfyui.synthesis import (
    collect_pending_chunks,
    localized_synthesis_line,
    save_manifest,
    synthesize_manifest,
)
from book_normalizer.comfyui.synthesis import load_manifest as load_manifest_v2
from book_normalizer.comfyui.workflow_builder import WorkflowBuilder, WorkflowBuilderError
from book_normalizer.tts.artifact_qa import (
    DEFAULT_ARTIFACT_REPORT_NAME,
    annotate_manifest_with_artifacts,
    run_artifact_qa,
    write_artifact_report,
)
from book_normalizer.tts.asr_qa import (
    DEFAULT_ASR_REPORT_NAME,
    AsrQaConfig,
    FasterWhisperBackend,
    annotate_manifest_with_asr,
    run_asr_qa,
    write_asr_diff,
    write_asr_report,
)
from book_normalizer.tts.perceptual_qa import (
    DEFAULT_PERCEPTUAL_BACKENDS,
    DEFAULT_PERCEPTUAL_REPORT_NAME,
    PerceptualQaConfig,
    annotate_manifest_with_perceptual,
    run_perceptual_qa,
    write_perceptual_report,
)
from book_normalizer.tts.quality_gate import split_problem_chunks_for_retry

# ── Manifest helpers ──────────────────────────────────────────────────────────


def load_manifest(path: Path) -> dict:
    """Load and validate a v2 manifest JSON file."""
    if not path.exists():
        print(f"ERROR: Manifest not found: {path}")
        sys.exit(1)

    data = json.loads(path.read_text(encoding="utf-8"))
    version = data.get("version", 1)

    if version == 1:
        print(
            "ERROR: This script requires a v2 manifest (chunks_manifest_v2.json).\n"
            "Generate one with:\n"
            "  python scripts/export_chunks.py --book-dir <dir> --mode llm"
        )
        sys.exit(1)

    if version != 2:
        print(f"WARNING: Unknown manifest version {version}, attempting to process anyway.")

    return data


def count_total_chunks(manifest: dict, chapter_filter: int | None) -> int:
    """Count all chunks (including already synthesized) matching the filter."""
    total = 0
    for chapter in manifest.get("chapters", []):
        ch_idx = chapter.get("chapter_index", 0)
        if chapter_filter is not None and ch_idx != chapter_filter - 1:
            continue
        total += len(chapter.get("chunks", []))
    return total


def count_done_chunks(manifest: dict, chapter_filter: int | None) -> int:
    """Count already synthesized chunks matching the filter."""
    done = 0
    for chapter in manifest.get("chapters", []):
        ch_idx = chapter.get("chapter_index", 0)
        if chapter_filter is not None and ch_idx != chapter_filter - 1:
            continue
        for chunk in chapter.get("chunks", []):
            if chunk.get("synthesized", False):
                done += 1
    return done


# ── Synthesis ─────────────────────────────────────────────────────────────────


def build_output_path(
    out_dir: Path,
    chapter_index: int,
    chunk_index: int,
    voice: str,
) -> Path:
    """Return the local WAV path for a chunk."""
    chapter_dir = out_dir / f"chapter_{chapter_index + 1:03d}"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    filename = f"chunk_{chunk_index + 1:03d}_{voice}.wav"
    return chapter_dir / filename


def synthesize_all(
    manifest: dict,
    manifest_path: Path,
    client: ComfyUIClient,
    builder: WorkflowBuilder,
    out_dir: Path,
    chapter_filter: int | None,
    chunk_timeout: float,
    log_language: str = "en",
) -> None:
    """Main synthesis loop: process each pending chunk sequentially."""
    pending = collect_pending_chunks(manifest, chapter_filter)
    total = count_total_chunks(manifest, chapter_filter)
    done_start = count_done_chunks(manifest, chapter_filter)

    if not pending:
        print(f"All {total} chunks already synthesized. Nothing to do.")
        return

    print(
        f"Chunks: {total} total, {done_start} already done, {len(pending)} to synthesize."
    )
    done = done_start

    for chapter_entry, chunk in pending:
        ch_idx = chapter_entry.get("chapter_index", 0)
        chunk_idx = chunk.get("chunk_index", 0)
        voice_label = chunk.get("voice_label", "narrator")
        voice_id = chunk.get("voice_id", "")
        voice_tone = chunk.get("voice_tone", "calm")
        text = chunk.get("text", "")

        if not text.strip():
            print(f"  Skipping empty chunk ch{ch_idx + 1:03d}/chunk{chunk_idx + 1:03d}")
            chunk["synthesized"] = True
            done += 1
            print(f"PROGRESS {done}/{total}")
            save_manifest(manifest_path, manifest)
            continue

        output_path = build_output_path(out_dir, ch_idx, chunk_idx, voice_label)
        output_filename = f"chunk_{chunk_idx + 1:03d}_{voice_label}"

        print(
            localized_synthesis_line(
                language=log_language,
                chapter=ch_idx + 1,
                chunk=chunk_idx + 1,
                voice_label=voice_label,
                voice_id=str(voice_id or ""),
                voice_tone=str(voice_tone or "calm"),
                chars=len(text),
                file_name=output_path.name,
            )
        )

        t_start = time.monotonic()
        try:
            workflow = builder.build(
                text=text,
                voice_label=voice_label,
                voice_tone=voice_tone,
                output_filename=output_filename,
            )
            client.synthesize_chunk(workflow, output_path, timeout=chunk_timeout)
        except ComfyUIError as exc:
            print(f"  ERROR: {exc}")
            print("  Skipping chunk — will retry on next run (synthesized stays false).")
            continue

        elapsed = time.monotonic() - t_start
        size_kb = output_path.stat().st_size // 1024 if output_path.exists() else 0
        print(f"    Done in {elapsed:.1f}s → {size_kb} KB")

        # Update manifest in-place.
        chunk["synthesized"] = True
        chunk["audio_file"] = str(output_path)
        done += 1

        # Progress line parseable by the GUI.
        print(f"PROGRESS {done}/{total}")

        # Persist after every chunk for resume support.
        save_manifest(manifest_path, manifest)

    synthesized_now = done - done_start
    print(
        f"\nSynthesis complete: {synthesized_now} new chunks synthesized "
        f"({done}/{total} total done)."
    )


# ── Entry point ───────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Synthesize audio chunks via ComfyUI + Qwen3-TTS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--chunks-json", required=True,
        help="Path to chunks_manifest_v2.json produced by export_chunks.py --mode llm.",
    )
    parser.add_argument(
        "--out", required=True,
        help="Output directory for audio chunks (audio_chunks/chapter_NNN/ structure).",
    )
    parser.add_argument(
        "--workflow", required=True,
        help="Path to ComfyUI workflow JSON template with {{TEXT}}, {{VOICE_ID}}, etc. placeholders.",
    )
    parser.add_argument(
        "--comfyui-url", default="http://localhost:8188",
        help="ComfyUI server base URL (default: http://localhost:8188).",
    )
    parser.add_argument(
        "--chapter", type=int, default=None,
        help="Only synthesize a specific chapter number (1-based). Omit for all chapters.",
    )
    parser.add_argument(
        "--chunk-timeout", type=float, default=300.0,
        help="Max seconds to wait for a single chunk synthesis (default: 300).",
    )
    parser.add_argument(
        "--failed-only", action="store_true",
        help="Retry only chunks previously marked as failed.",
    )
    parser.add_argument("--quality-loop", action="store_true", help="QA and resynthesize bad chunks.")
    parser.add_argument("--artifact-qa", action="store_true", help="Run artifact QA after synthesis.")
    parser.add_argument("--perceptual-qa", action="store_true", help="Run NISQA/MOSNet perceptual QA after synthesis.")
    parser.add_argument(
        "--perceptual-backend",
        action="append",
        default=[],
        help="Perceptual QA backend to run. Can be repeated. Defaults to nisqa-v2 and mosnet.",
    )
    parser.add_argument("--perceptual-min-mos", type=float, default=2.70, help="Fail below this MOS.")
    parser.add_argument("--perceptual-warn-mos", type=float, default=3.30, help="Warn below this MOS.")
    parser.add_argument("--asr-qa-after-synthesis", action="store_true", help="Run ASR QA after synthesis.")
    parser.add_argument("--asr-model", default="small", help="faster-whisper ASR model (default: small).")
    parser.add_argument(
        "--max-resynth-attempts",
        type=int,
        default=2,
        help="Max automatic resynthesis attempts per bad chunk (default: 2).",
    )
    parser.add_argument("--batch-size", type=int, default=1, help="Generation batch size metadata.")
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE, help="TTS sampling temperature.")
    parser.add_argument("--top-p", type=float, default=DEFAULT_TOP_P, help="TTS top-p sampling.")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="TTS top-k sampling.")
    parser.add_argument("--repetition-penalty", type=float, default=1.05, help="TTS repetition penalty.")
    parser.add_argument("--max-new-tokens", type=int, default=2048, help="TTS max new tokens.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="TTS seed; use -1 for random generation.")
    parser.add_argument("--speech-rate", type=float, default=1.0, help="TTS speech rate when supported.")
    parser.add_argument(
        "--log-language",
        choices=["en", "ru", "zh", "kk", "uz"],
        default="en",
        help="Language for synthesis log lines.",
    )
    args = parser.parse_args(argv)

    manifest_path = Path(args.chunks_json)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load manifest.
    try:
        manifest = load_manifest_v2(manifest_path)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    book_title = manifest.get("book_title", manifest_path.parent.name)
    print(f"Book: {book_title}")
    print(f"Manifest version: {manifest.get('version', '?')}, chunker: {manifest.get('chunker', '?')}")

    # Init ComfyUI client.
    client = ComfyUIClient(args.comfyui_url)
    if not client.is_reachable():
        print(f"ERROR: ComfyUI server not reachable at {args.comfyui_url}")
        print("Make sure ComfyUI is running before starting synthesis.")
        sys.exit(1)
    print(f"ComfyUI: connected to {args.comfyui_url}")

    # Load workflow builder.
    try:
        builder = WorkflowBuilder(args.workflow)
    except WorkflowBuilderError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    print(f"Workflow template: {args.workflow}")

    generation_options = GenerationOptions(
        batch_size=args.batch_size,
        temperature=args.temperature,
        top_p=args.top_p,
        top_k=args.top_k,
        repetition_penalty=args.repetition_penalty,
        max_new_tokens=args.max_new_tokens,
        seed=args.seed,
        speech_rate=args.speech_rate,
    )
    max_passes = max(1, int(args.max_resynth_attempts) + 1)
    for pass_index in range(max_passes):
        if pass_index:
            print(f"Quality retry pass {pass_index}/{max_passes - 1}")
        synthesize_manifest(
            manifest=manifest,
            manifest_path=manifest_path,
            client=client,
            builder=builder,
            out_dir=out_dir,
            chapter_filter=args.chapter,
            chunk_timeout=args.chunk_timeout,
            failed_only=args.failed_only or pass_index > 0,
            generation_options=generation_options,
            progress=print,
            log_language=args.log_language,
        )
        if not (args.quality_loop or args.artifact_qa or args.perceptual_qa or args.asr_qa_after_synthesis):
            break

        if args.quality_loop or args.artifact_qa:
            artifact_report = manifest_path.with_name(DEFAULT_ARTIFACT_REPORT_NAME)
            artifact_result = run_artifact_qa(manifest, manifest_path=manifest_path)
            write_artifact_report(artifact_report, artifact_result)
            annotate_manifest_with_artifacts(
                manifest,
                artifact_result,
                report_path=artifact_report.resolve(),
                reset_bad_chunks=args.quality_loop,
                max_resynthesis_attempts=args.max_resynth_attempts,
            )
            save_manifest(manifest_path, manifest)
            summary = artifact_result.summary
            print(
                "Artifact QA: "
                f"status={artifact_result.status}, failed={summary['failed']}, "
                f"warnings={summary['warning']}, errors={summary['error']}."
            )

        if args.quality_loop or args.perceptual_qa:
            selected_backends = tuple(args.perceptual_backend or DEFAULT_PERCEPTUAL_BACKENDS)
            perceptual_report = manifest_path.with_name(DEFAULT_PERCEPTUAL_REPORT_NAME)
            perceptual_result = run_perceptual_qa(
                manifest,
                config=PerceptualQaConfig(
                    backends=selected_backends,
                    min_mos=args.perceptual_min_mos,
                    warn_mos=args.perceptual_warn_mos,
                ),
                manifest_path=manifest_path,
            )
            write_perceptual_report(perceptual_report, perceptual_result)
            annotate_manifest_with_perceptual(
                manifest,
                perceptual_result,
                report_path=perceptual_report.resolve(),
                reset_bad_chunks=args.quality_loop,
                max_resynthesis_attempts=args.max_resynth_attempts,
            )
            save_manifest(manifest_path, manifest)
            summary = perceptual_result.summary
            print(
                "Perceptual QA: "
                f"status={perceptual_result.status}, failed={summary['failed']}, "
                f"warnings={summary['warning']}, errors={summary['error']}."
            )

        if args.asr_qa_after_synthesis:
            asr_report = manifest_path.with_name(DEFAULT_ASR_REPORT_NAME)
            asr_result = run_asr_qa(
                manifest,
                config=AsrQaConfig(model=args.asr_model),
                backend=FasterWhisperBackend(args.asr_model),
                manifest_path=manifest_path,
            )
            write_asr_report(asr_report, asr_result)
            write_asr_diff(asr_report.with_suffix(".diff.txt"), asr_result)
            annotate_manifest_with_asr(
                manifest,
                asr_result,
                report_path=asr_report.resolve(),
                reset_bad_chunks=args.quality_loop,
                max_resynthesis_attempts=args.max_resynth_attempts,
            )
            save_manifest(manifest_path, manifest)
            summary = asr_result.summary
            print(
                "ASR QA: "
                f"status={asr_result.status.value}, failed={summary['failed']}, "
                f"warnings={summary['warning']}, errors={summary['error']}."
            )

        if not args.quality_loop:
            break
        splits = split_problem_chunks_for_retry(manifest)
        if splits:
            save_manifest(manifest_path, manifest)
            print(f"Quality loop split {splits} repeated/overlong chunk(s) for retry.")
        retry_pending = collect_pending_chunks(manifest, args.chapter, failed_only=True)
        if not retry_pending:
            break
        if pass_index == max_passes - 1:
            print(f"Quality loop stopped: {len(retry_pending)} chunk(s) still need attention.")
            break
        print(f"Quality loop reset {len(retry_pending)} bad chunk(s) for resynthesis.")


if __name__ == "__main__":
    main()
