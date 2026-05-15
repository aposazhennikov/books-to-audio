"""ComfyUI synthesis loop for v2 chunk manifests."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from book_normalizer.comfyui.client import ComfyUIClient, ComfyUIError
from book_normalizer.comfyui.workflow_builder import WorkflowBuilder

ProgressCallback = Callable[[str], None]


@dataclass(frozen=True)
class SynthesisSummary:
    """Final counters from a ComfyUI synthesis run."""

    total: int
    synthesized: int
    skipped: int
    failed: int


def load_manifest(path: Path) -> dict[str, Any]:
    """Load and validate a v2 manifest JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("ComfyUI synthesis requires a v2 manifest object.")
    if data.get("version", 1) == 1:
        raise ValueError(
            "This synthesis path requires chunks_manifest_v2.json. "
            "Generate it with export_chunks.py --mode llm or the GUI Voices tab."
        )
    return data


def save_manifest(path: Path, data: dict[str, Any]) -> None:
    """Atomically write manifest data back to disk."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def iter_manifest_chunks(
    manifest: dict[str, Any],
    chapter_filter: int | None = None,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Return ``(chapter, chunk)`` pairs matching an optional 1-based chapter."""
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for chapter in manifest.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter_index = int(chapter.get("chapter_index", 0))
        if chapter_filter is not None and chapter_index != chapter_filter - 1:
            continue
        for chunk in chapter.get("chunks", []):
            if isinstance(chunk, dict):
                pairs.append((chapter, chunk))
    return pairs


def collect_pending_chunks(
    manifest: dict[str, Any],
    chapter_filter: int | None = None,
    *,
    failed_only: bool = False,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Return chunk pairs that should be synthesized."""
    pending: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for chapter, chunk in iter_manifest_chunks(manifest, chapter_filter):
        if chunk.get("synthesized", False):
            continue
        if failed_only and not chunk.get("failed", False):
            continue
        pending.append((chapter, chunk))
    return pending


def count_done_chunks(manifest: dict[str, Any], chapter_filter: int | None = None) -> int:
    """Count synthesized chunks matching an optional chapter filter."""
    return sum(
        1
        for _chapter, chunk in iter_manifest_chunks(manifest, chapter_filter)
        if chunk.get("synthesized", False)
    )


def build_output_path(
    out_dir: Path,
    chapter_index: int,
    chunk_index: int,
    voice_label: str,
) -> Path:
    """Return the local WAV path for a chunk."""
    chapter_dir = out_dir / f"chapter_{chapter_index + 1:03d}"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    safe_voice = "".join(ch for ch in voice_label if ch.isalnum() or ch in ("_", "-")) or "voice"
    return chapter_dir / f"chunk_{chunk_index + 1:03d}_{safe_voice}.wav"


def synthesize_manifest(
    *,
    manifest: dict[str, Any],
    manifest_path: Path,
    client: ComfyUIClient,
    builder: WorkflowBuilder,
    out_dir: Path,
    chapter_filter: int | None = None,
    chunk_timeout: float = 300.0,
    failed_only: bool = False,
    progress: ProgressCallback | None = None,
) -> SynthesisSummary:
    """Synthesize all pending chunks and update the manifest after each chunk."""
    out_dir.mkdir(parents=True, exist_ok=True)
    all_pairs = iter_manifest_chunks(manifest, chapter_filter)
    pending = collect_pending_chunks(manifest, chapter_filter, failed_only=failed_only)
    total = len(all_pairs)
    done_start = count_done_chunks(manifest, chapter_filter)
    skipped = done_start
    failed = 0

    def emit(line: str) -> None:
        if progress:
            progress(line)

    if not pending:
        emit(f"All {total} chunks already synthesized. Nothing to do.")
        return SynthesisSummary(total=total, synthesized=0, skipped=skipped, failed=0)

    emit(f"Chunks: {total} total, {done_start} already done, {len(pending)} to synthesize.")
    done = done_start
    synthesized_now = 0

    for chapter_entry, chunk in pending:
        chapter_index = int(chapter_entry.get("chapter_index", 0))
        chunk_index = int(chunk.get("chunk_index", 0))
        voice_label = str(chunk.get("voice_label") or "narrator")
        voice_tone = str(chunk.get("voice_tone") or "calm")
        text = str(chunk.get("text") or chunk.get(voice_label) or "")

        chunk["failed"] = False
        chunk["error"] = ""

        if not text.strip():
            emit(f"  Skipping empty chunk ch{chapter_index + 1:03d}/chunk{chunk_index + 1:03d}")
            chunk["synthesized"] = True
            chunk["audio_file"] = ""
            done += 1
            skipped += 1
            emit(f"PROGRESS {done}/{total}")
            save_manifest(manifest_path, manifest)
            continue

        output_path = build_output_path(out_dir, chapter_index, chunk_index, voice_label)
        output_filename = output_path.with_suffix("").name
        emit(
            f"  Synthesizing ch{chapter_index + 1:03d}/chunk{chunk_index + 1:03d} "
            f"[{voice_label}/{voice_tone}] {len(text)} chars -> {output_path.name}"
        )

        started = time.monotonic()
        try:
            workflow = builder.build(
                text=text,
                voice_label=voice_label,
                voice_tone=voice_tone,
                output_filename=output_filename,
            )
            client.synthesize_chunk(workflow, output_path, timeout=chunk_timeout)
        except ComfyUIError as exc:
            failed += 1
            chunk["failed"] = True
            chunk["error"] = str(exc)
            emit(f"  ERROR: {exc}")
            save_manifest(manifest_path, manifest)
            continue

        elapsed = time.monotonic() - started
        size_kb = output_path.stat().st_size // 1024 if output_path.exists() else 0
        emit(f"    Done in {elapsed:.1f}s -> {size_kb} KB")

        chunk["synthesized"] = True
        chunk["failed"] = False
        chunk["error"] = ""
        chunk["audio_file"] = str(output_path)
        done += 1
        synthesized_now += 1
        emit(f"PROGRESS {done}/{total}")
        save_manifest(manifest_path, manifest)

    emit(
        f"Synthesis complete: {synthesized_now} new chunks synthesized "
        f"({done}/{total} total done, {failed} failed)."
    )
    return SynthesisSummary(
        total=total,
        synthesized=synthesized_now,
        skipped=skipped,
        failed=failed,
    )
