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
from book_normalizer.comfyui.workflow_builder import WorkflowBuilder, WorkflowBuilderError

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


def save_manifest(path: Path, data: dict) -> None:
    """Atomically write manifest data back to disk."""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def collect_pending_chunks(
    manifest: dict,
    chapter_filter: int | None,
) -> list[tuple[dict, dict]]:
    """Return list of (chapter_entry, chunk_entry) tuples that need synthesis.

    Skips chunks where ``synthesized`` is True.
    """
    pending: list[tuple[dict, dict]] = []
    for chapter in manifest.get("chapters", []):
        ch_idx = chapter.get("chapter_index", 0)
        if chapter_filter is not None and ch_idx != chapter_filter - 1:
            continue
        for chunk in chapter.get("chunks", []):
            if not chunk.get("synthesized", False):
                pending.append((chapter, chunk))
    return pending


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
            f"  Synthesizing ch{ch_idx + 1:03d}/chunk{chunk_idx + 1:03d} "
            f"[{voice_label}/{voice_tone}] {len(text)} chars → {output_path.name}"
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


def main() -> None:
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
    args = parser.parse_args()

    manifest_path = Path(args.chunks_json)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load manifest.
    manifest = load_manifest(manifest_path)
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

    # Run synthesis.
    synthesize_all(
        manifest=manifest,
        manifest_path=manifest_path,
        client=client,
        builder=builder,
        out_dir=out_dir,
        chapter_filter=args.chapter,
        chunk_timeout=args.chunk_timeout,
    )


if __name__ == "__main__":
    main()
