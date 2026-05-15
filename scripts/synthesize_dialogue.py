#!/usr/bin/env python3
"""Synthesize audiobook chapters using FB_Qwen3TTSDialogueInference.

Reads chunks_manifest_v2.json produced by export_chunks.py --mode llm,
groups all chunks by chapter, assembles a multi-role dialogue script, and
sends ONE ComfyUI workflow per chapter.  All voices are merged by
FB_Qwen3TTSDialogueInference into a single continuous audio file per chapter.

Prerequisites:
    Run save_voice.py once for each of the three roles before using this
    script:

        python scripts/save_voice.py --audio narrator.wav --name narrator \\
            --ref-text "Точный текст..."
        python scripts/save_voice.py --audio men.wav --name men \\
            --ref-text "Текст..."
        python scripts/save_voice.py --audio women.wav --name women \\
            --ref-text "Текст..."

Usage:
    python scripts/synthesize_dialogue.py \\
        --chunks-json output/mybook/chunks_manifest_v2.json \\
        --out output/mybook/chapters \\
        --narrator-speaker narrator \\
        --men-speaker men \\
        --women-speaker women

    # Custom workflow template:
    python scripts/synthesize_dialogue.py \\
        --chunks-json output/mybook/chunks_manifest_v2.json \\
        --out output/mybook/chapters \\
        --workflow comfyui_workflows/qwen3_dialogue_template.json \\
        --narrator-speaker narrator \\
        --men-speaker men \\
        --women-speaker women

    # Synthesize only chapter 3:
    python scripts/synthesize_dialogue.py \\
        --chunks-json output/mybook/chunks_manifest_v2.json \\
        --out output/mybook/chapters \\
        --chapter 3

Output:
    output/mybook/chapters/
        chapter_001.flac   ← full chapter audio (all voices merged)
        chapter_002.flac
        ...
    No assembly step is needed — FB_Qwen3TTSDialogueInference does it.

Progress lines printed to stdout:
    PROGRESS 3/12
These are parseable by the GUI's TTSSynthesisWorker.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from book_normalizer.comfyui.client import ComfyUIClient, ComfyUIError
from book_normalizer.comfyui.workflow_builder import WorkflowBuilder, WorkflowBuilderError

# Default paths.
_DEFAULT_WORKFLOW = str(
    Path(__file__).resolve().parent.parent
    / "comfyui_workflows"
    / "qwen3_dialogue_template.json"
)

# Max seconds to wait for one chapter synthesis.
_DEFAULT_CHAPTER_TIMEOUT = 1800.0


# ── Rich progress helpers ──────────────────────────────────────────────────────


def _make_progress():  # type: ignore[return]
    """Build a rich Progress instance with elapsed + ETA columns."""
    try:
        from rich.progress import (
            BarColumn,
            MofNCompleteColumn,
            Progress,
            SpinnerColumn,
            TaskProgressColumn,
            TextColumn,
            TimeElapsedColumn,
            TimeRemainingColumn,
        )

        return Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(bar_width=36),
            TaskProgressColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        )
    except ImportError:
        return None


def _print_header(book_title: str, chapters: list[dict], url: str) -> None:
    """Print synthesis session header."""
    total_chunks = sum(len(ch.get("chunks", [])) for ch in chapters)
    try:
        from rich.console import Console
        from rich.panel import Panel

        Console().print(
            Panel(
                f"[bold]{book_title}[/bold]\n"
                f"Chapters: [cyan]{len(chapters)}[/cyan]  "
                f"Chunks: [cyan]{total_chunks}[/cyan]  "
                f"ComfyUI: [green]{url}[/green]",
                title="[bold magenta]Dialogue Synthesis[/bold magenta]",
                expand=False,
            )
        )
    except ImportError:
        print(f"Book: {book_title}")
        print(f"Chapters: {len(chapters)}, total chunks: {total_chunks}")
        print(f"ComfyUI: {url}")
        print()


def _print_chapter_result(
    ch_num: int,
    title: str,
    n_lines: int,
    output_path: Path,
    elapsed: float,
    success: bool,
) -> None:
    """Print a one-line summary for a finished chapter."""
    try:
        from rich.console import Console

        size_kb = output_path.stat().st_size // 1024 if (success and output_path.exists()) else 0
        icon = "[green]✓[/green]" if success else "[red]✗[/red]"
        Console().print(
            f"  {icon} Chapter {ch_num:02d} [{title[:30]}]  "
            f"{n_lines} lines  {size_kb} KB  {elapsed:.0f}s"
        )
    except ImportError:
        status = "OK" if success else "FAILED"
        print(f"  [{status}] Chapter {ch_num:02d}: {n_lines} lines, {elapsed:.0f}s")


# ── Manifest helpers ───────────────────────────────────────────────────────────


def load_manifest(path: Path) -> dict[str, Any]:
    """Load and basic-validate a v2 manifest."""
    if not path.exists():
        print(f"ERROR: Manifest not found: {path}")
        sys.exit(1)
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version", 1) == 1:
        print(
            "ERROR: v1 manifest detected. Generate a v2 manifest with:\n"
            "  python scripts/export_chunks.py --book-dir <dir> --mode llm"
        )
        sys.exit(1)
    return data


def save_manifest(path: Path, data: dict[str, Any]) -> None:
    """Atomically overwrite manifest on disk."""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def get_chapters(
    manifest: dict[str, Any],
    chapter_filter: int | None,
) -> list[dict[str, Any]]:
    """Return chapters to process, respecting an optional 1-based filter."""
    chapters = manifest.get("chapters", [])
    if chapter_filter is not None:
        chapters = [
            ch for ch in chapters
            if ch.get("chapter_index", 0) == chapter_filter - 1
        ]
    return chapters


# ── Script assembly ────────────────────────────────────────────────────────────


def build_chapter_script(chunks: list[dict[str, Any]]) -> str:
    """Assemble a dialogue script string from chapter chunks.

    Each chunk becomes one line in the format::

        narrator: Он вошёл в комнату...
        men: — Кто здесь?
        women: — Всё в порядке.

    The role name is taken from ``voice_label`` (narrator / men / women).
    Text containing literal newlines is collapsed to a single space so every
    chunk occupies exactly one line in the script.
    """
    lines: list[str] = []
    for chunk in chunks:
        role = chunk.get("voice_label", "narrator")
        text = chunk.get("text", "").strip().replace("\n", " ")
        if text:
            lines.append(f"{role}: {text}")
    return "\n".join(lines)


def split_into_batches(
    chunks: list[dict[str, Any]],
    max_lines: int,
) -> list[list[dict[str, Any]]]:
    """Split chunks into batches of at most ``max_lines`` items.

    Used to avoid sending extremely long scripts to DialogueInference in a
    single workflow call.  Each batch is synthesized separately and the
    resulting audio files are named ``chapter_NNN_part_M.flac``.
    """
    return [chunks[i : i + max_lines] for i in range(0, len(chunks), max_lines)]


# ── Synthesis ──────────────────────────────────────────────────────────────────


def synthesize_all(
    manifest: dict[str, Any],
    manifest_path: Path,
    client: ComfyUIClient,
    builder: WorkflowBuilder,
    out_dir: Path,
    chapter_filter: int | None,
    speaker_map: dict[str, str],
    chapter_timeout: float,
    max_lines_per_call: int,
) -> None:
    """Main synthesis loop — one or more ComfyUI calls per chapter.

    Chapters with more chunks than ``max_lines_per_call`` are split into
    numbered parts (chapter_001_part1.flac, chapter_001_part2.flac, …).
    This prevents excessively long synthesis calls and memory issues.
    """
    chapters = get_chapters(manifest, chapter_filter)
    total = len(chapters)

    if total == 0:
        print("No chapters to synthesize.")
        return

    book_title = manifest.get("book_title", manifest_path.parent.name)
    _print_header(book_title, chapters, "http://localhost:8188")

    progress = _make_progress()
    done = 0

    def _synthesize_chapter(chapter: dict[str, Any]) -> None:
        """Synthesize one chapter, splitting into parts if needed."""
        ch_idx = chapter.get("chapter_index", 0)
        ch_num = ch_idx + 1
        title = chapter.get("title", f"Chapter {ch_num}")
        chunks = [c for c in chapter.get("chunks", []) if c.get("text", "").strip()]

        if not chunks:
            print(f"  WARNING: Chapter {ch_num} has no text — skipping.")
            chapter["synthesized"] = True
            return

        batches = split_into_batches(chunks, max_lines_per_call)
        n_batches = len(batches)
        part_paths: list[Path] = []

        for part_idx, batch in enumerate(batches):
            part_label = f" part {part_idx + 1}/{n_batches}" if n_batches > 1 else ""
            n_lines = len(batch)

            if progress:
                progress.update(
                    task_id,
                    description=(
                        f"Ch.{ch_num:02d}/{total}{part_label} — {title[:30]}"
                        f" ({n_lines} lines)"
                    ),
                )
            else:
                print(
                    f"\n[Ch.{ch_num:02d}/{total}{part_label}] "
                    f"{title}  {n_lines} строк"
                )

            if n_batches > 1:
                output_path = out_dir / f"chapter_{ch_num:03d}_part{part_idx + 1}.flac"
                output_filename = f"chapter_{ch_num:03d}_part{part_idx + 1}"
            else:
                output_path = out_dir / f"chapter_{ch_num:03d}.flac"
                output_filename = f"chapter_{ch_num:03d}"

            script = build_chapter_script(batch)
            workflow = builder.build_dialogue(
                script=script,
                narrator_speaker=speaker_map["narrator"],
                men_speaker=speaker_map["men"],
                women_speaker=speaker_map["women"],
                output_filename=output_filename,
            )

            t_start = time.monotonic()
            try:
                client.synthesize_chunk(workflow, output_path, timeout=chapter_timeout)
                part_paths.append(output_path)
            except ComfyUIError as exc:
                print(f"  ERROR synthesizing chapter {ch_num}{part_label}: {exc}")
                print("  Will retry on next run.")
                return  # Leave synthesized=False so entire chapter retries.

            elapsed = time.monotonic() - t_start
            _print_chapter_result(
                ch_num, title, n_lines, output_path, elapsed, success=True
            )

        chapter["synthesized"] = True
        chapter["audio_files"] = [str(p) for p in part_paths]
        if len(part_paths) == 1:
            chapter["audio_file"] = str(part_paths[0])

    def _run() -> None:
        nonlocal done
        for chapter in chapters:
            if chapter.get("synthesized", False):
                done += 1
                if progress:
                    progress.advance(task_id)
                print(f"PROGRESS {done}/{total}")
                continue

            _synthesize_chapter(chapter)
            done += 1
            if progress:
                progress.advance(task_id)
            print(f"PROGRESS {done}/{total}")
            save_manifest(manifest_path, manifest)

    if progress:
        with progress:
            task_id = progress.add_task("Starting...", total=total)
            _run()
    else:
        _run()

    synthesized = sum(1 for ch in chapters if ch.get("synthesized"))
    print(f"\nDone: {synthesized}/{total} chapters synthesized.")
    if synthesized == total:
        print(f"Output: {out_dir}/chapter_NNN.flac")


# ── Entry point ────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Synthesize audiobook chapters via ComfyUI FB_Qwen3TTSDialogueInference.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--chunks-json", required=True,
        help="Path to chunks_manifest_v2.json.",
    )
    parser.add_argument(
        "--out", required=True,
        help="Output directory for chapter audio files.",
    )
    parser.add_argument(
        "--workflow", default=_DEFAULT_WORKFLOW,
        help="Path to qwen3_dialogue_template.json (default: built-in).",
    )
    parser.add_argument(
        "--narrator-speaker", default="narrator",
        help="Saved speaker name for the narrator role (default: narrator).",
    )
    parser.add_argument(
        "--men-speaker", default="men",
        help="Saved speaker name for the male character role (default: men).",
    )
    parser.add_argument(
        "--women-speaker", default="women",
        help="Saved speaker name for the female character role (default: women).",
    )
    parser.add_argument(
        "--comfyui-url", default="http://localhost:8188",
        help="ComfyUI server URL (default: http://localhost:8188).",
    )
    parser.add_argument(
        "--chapter", type=int, default=None,
        help="Synthesize only this chapter (1-based). Omit for all chapters.",
    )
    parser.add_argument(
        "--chapter-timeout", type=float, default=_DEFAULT_CHAPTER_TIMEOUT,
        help=f"Max seconds to wait per ComfyUI call (default: {_DEFAULT_CHAPTER_TIMEOUT}).",
    )
    parser.add_argument(
        "--max-lines", type=int, default=200,
        help=(
            "Max dialogue lines per ComfyUI call (default: 200). "
            "Chapters with more chunks are split into numbered parts. "
            "Lower values reduce VRAM usage and ComfyUI timeout risk."
        ),
    )
    args = parser.parse_args()

    manifest_path = Path(args.chunks_json)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(manifest_path)
    print(f"Book: {manifest.get('book_title', manifest_path.parent.name)}")
    print(f"Manifest: v{manifest.get('version', '?')}, chunker={manifest.get('chunker', '?')}")

    client = ComfyUIClient(args.comfyui_url)
    if not client.is_reachable():
        print(f"ERROR: ComfyUI not reachable at {args.comfyui_url}")
        sys.exit(1)

    # Warn if speakers are not yet saved.
    saved = client.list_saved_speakers()
    speaker_map = {
        "narrator": args.narrator_speaker,
        "men": args.men_speaker,
        "women": args.women_speaker,
    }
    missing = [name for name in speaker_map.values() if name not in saved]
    if missing:
        print(
            f"WARNING: Speaker(s) not found in ComfyUI: {', '.join(missing)}\n"
            f"Saved speakers: {saved or ['(none)']}\n"
            f"Run  python scripts/save_voice.py --audio <file.wav> --name <name>  first.\n"
            f"Continuing anyway — ComfyUI will error if the speaker file is missing."
        )

    try:
        builder = WorkflowBuilder(args.workflow)
    except WorkflowBuilderError as exc:
        print(f"ERROR loading workflow template: {exc}")
        sys.exit(1)
    print(f"Workflow: {args.workflow}")
    print(
        f"Speakers: narrator={args.narrator_speaker}, "
        f"men={args.men_speaker}, women={args.women_speaker}"
    )

    synthesize_all(
        manifest=manifest,
        manifest_path=manifest_path,
        client=client,
        builder=builder,
        out_dir=out_dir,
        chapter_filter=args.chapter,
        speaker_map=speaker_map,
        chapter_timeout=args.chapter_timeout,
        max_lines_per_call=args.max_lines,
    )


if __name__ == "__main__":
    main()
