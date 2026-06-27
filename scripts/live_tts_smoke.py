#!/usr/bin/env python3
"""Run a small live ComfyUI/Qwen TTS smoke test.

The smoke keeps the workload intentionally tiny: two short chunks, sequential
synthesis, audio QA, and one assembled chapter. It is meant for final local
sign-off after ComfyUI is already running.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from book_normalizer.chunking.manifest_v2 import chunks_to_manifest  # noqa: E402
from book_normalizer.chunking.splitter import chunk_text  # noqa: E402
from book_normalizer.comfyui.client import ComfyUIClient, ComfyUIError  # noqa: E402
from book_normalizer.comfyui.synthesis import synthesize_manifest  # noqa: E402
from book_normalizer.comfyui.workflow_builder import (  # noqa: E402
    WorkflowBuilder,
    WorkflowBuilderError,
)
from book_normalizer.languages import normalize_book_language  # noqa: E402
from book_normalizer.loaders.factory import LoaderFactory  # noqa: E402
from book_normalizer.normalization.cleanup import (  # noqa: E402
    is_likely_publisher_boilerplate,
    remove_publisher_boilerplate,
)
from book_normalizer.tts.audio_qa import run_audio_qa  # noqa: E402
from book_normalizer.tts.manifest_assembly import assemble_from_manifest  # noqa: E402

DEFAULT_WORKFLOW = Path("comfyui_workflows/qwen3_tts_template.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Live ComfyUI/Qwen TTS smoke test.")
    parser.add_argument("--comfyui-url", default="http://127.0.0.1:8188")
    parser.add_argument("--workflow", default=str(DEFAULT_WORKFLOW))
    parser.add_argument("--out-dir", default="output/live_tts_smoke")
    parser.add_argument("--language", default="ru")
    parser.add_argument("--chunk-timeout", type=float, default=300.0)
    parser.add_argument(
        "--book-path",
        default="",
        help="Optional real book file to use for the smoke instead of built-in text.",
    )
    parser.add_argument(
        "--max-book-chars",
        type=int,
        default=1200,
        help="Maximum real-book characters to include in the smoke manifest.",
    )
    parser.add_argument(
        "--max-smoke-chunks",
        type=int,
        default=2,
        help="Maximum real-book chunks to synthesize.",
    )
    parser.add_argument(
        "--max-chunk-chars",
        type=int,
        default=260,
        help="Maximum characters per real-book TTS smoke chunk.",
    )
    parser.add_argument(
        "--manifest-only",
        action="store_true",
        help="Build the smoke manifest without connecting to ComfyUI or synthesizing audio.",
    )
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    report = run_live_tts_smoke(
        comfyui_url=args.comfyui_url,
        workflow_path=Path(args.workflow),
        out_dir=out_dir,
        language=args.language,
        chunk_timeout=args.chunk_timeout,
        book_path=Path(args.book_path) if args.book_path else None,
        max_book_chars=args.max_book_chars,
        max_smoke_chunks=args.max_smoke_chunks,
        max_chunk_chars=args.max_chunk_chars,
        manifest_only=args.manifest_only,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "live_tts_smoke_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Live TTS smoke report: {report_path}")
    print(f"Status: {report['status']}")
    if report.get("message"):
        print(report["message"])
    if report["status"] == "ok":
        print(f"Assembled chapter: {report.get('assembled_chapter', '')}")
        return 0
    if report["status"] == "manifest_only":
        print(f"Manifest: {report.get('manifest', '')}")
        return 0
    if report["status"] == "unavailable":
        return 2
    return 1


def run_live_tts_smoke(
    *,
    comfyui_url: str,
    workflow_path: Path,
    out_dir: Path,
    language: str = "ru",
    chunk_timeout: float = 300.0,
    book_path: Path | None = None,
    max_book_chars: int = 1200,
    max_smoke_chunks: int = 2,
    max_chunk_chars: int = 260,
    manifest_only: bool = False,
) -> dict[str, Any]:
    """Run the live TTS smoke and return a JSON-serializable report."""
    language = normalize_book_language(language)
    created_at = datetime.now(timezone.utc).isoformat()
    report: dict[str, Any] = {
        "created_at": created_at,
        "status": "unknown",
        "comfyui_url": comfyui_url,
        "workflow": str(workflow_path),
        "out_dir": str(out_dir),
        "language": language,
        "source_book": str(book_path) if book_path else "",
        "max_book_chars": max_book_chars,
        "max_smoke_chunks": max_smoke_chunks,
        "max_chunk_chars": max_chunk_chars,
        "manifest_only": manifest_only,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        manifest = (
            _real_book_smoke_manifest(
                book_path,
                language=language,
                max_book_chars=max_book_chars,
                max_smoke_chunks=max_smoke_chunks,
                max_chunk_chars=max_chunk_chars,
            )
            if book_path
            else _smoke_manifest(language)
        ).to_record()
    except (OSError, ValueError) as exc:
        report.update({"status": "error", "message": str(exc)})
        return report
    manifest_path = out_dir / "chunks_manifest_v2.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    report["manifest"] = str(manifest_path)
    report["manifest_chunks"] = _manifest_chunk_count(manifest)
    if manifest_only:
        report.update({
            "status": "manifest_only",
            "message": "Smoke manifest built without contacting ComfyUI.",
        })
        return report

    client = ComfyUIClient(comfyui_url)
    if not client.is_reachable():
        report.update({
            "status": "unavailable",
            "message": f"ComfyUI is not reachable at {comfyui_url}. Start ComfyUI and rerun.",
        })
        return report

    try:
        builder = WorkflowBuilder(workflow_path)
    except WorkflowBuilderError as exc:
        report.update({"status": "error", "message": str(exc)})
        return report

    progress_lines: list[str] = []
    try:
        summary = synthesize_manifest(
            manifest=manifest,
            manifest_path=manifest_path,
            client=client,
            builder=builder,
            out_dir=out_dir / "audio_chunks",
            chunk_timeout=chunk_timeout,
            progress=progress_lines.append,
        )
        qa = run_audio_qa(
            manifest,
            manifest_path=manifest_path,
            min_seconds_per_100_chars=0.1,
        )
        assembly = assemble_from_manifest(
            manifest,
            out_dir,
            pause_same_voice_ms=250,
            pause_voice_change_ms=500,
            manifest_path=manifest_path,
        )
    except (ComfyUIError, OSError, ValueError) as exc:
        report.update({
            "status": "error",
            "message": f"{type(exc).__name__}: {exc}",
            "progress": progress_lines[-20:],
        })
        return report

    assembled = next((item for item in assembly if item.output_path is not None), None)
    report.update({
        "status": "ok" if qa.ok and assembled is not None else "review_required",
        "synthesis": summary.__dict__,
        "audio_qa": qa.to_dict(),
        "assembled_chapter": str(assembled.output_path) if assembled else "",
        "assembly": [
            {
                "chapter_number": item.chapter_number,
                "output_path": str(item.output_path) if item.output_path else "",
                "chunks": item.chunks,
                "missing": item.missing,
                "skipped": item.skipped,
                "messages": item.messages,
            }
            for item in assembly
        ],
        "progress": progress_lines[-20:],
    })
    if report["status"] != "ok":
        report["message"] = "Live TTS smoke completed but QA or assembly needs review."
    return report


def _real_book_smoke_manifest(
    book_path: Path,
    *,
    language: str,
    max_book_chars: int,
    max_smoke_chunks: int,
    max_chunk_chars: int,
):
    """Build a tiny TTS manifest from the start of a real book file."""
    if max_book_chars <= 0:
        raise ValueError("--max-book-chars must be greater than zero")
    if max_smoke_chunks <= 0:
        raise ValueError("--max-smoke-chunks must be greater than zero")
    if max_chunk_chars <= 0:
        raise ValueError("--max-chunk-chars must be greater than zero")
    if not book_path.exists():
        raise FileNotFoundError(f"Book not found: {book_path}")

    book = LoaderFactory.default().load(book_path)
    if getattr(book, "metadata", None) is not None:
        book.metadata.language = language
    text = _bounded_book_text(book, max_book_chars=max_book_chars)
    chunks = [
        {
            "chapter_index": 0,
            "chunk_index": index,
            "role": "narrator",
            "voice_id": "narrator_calm",
            "intonation": "calm",
            "text": chunk,
            "language": language,
            "pause_after_ms": 250,
            "boundary_after": "paragraph",
        }
        for index, chunk in enumerate(chunk_text(text, max_chunk_chars)[:max_smoke_chunks])
        if chunk.strip()
    ]
    if not chunks:
        raise ValueError(f"Book has no usable text for TTS smoke: {book_path}")
    chunks[-1]["boundary_after"] = "chapter"
    chunks[-1]["pause_after_ms"] = 1500
    return chunks_to_manifest(
        chunks,
        book_title=getattr(book.metadata, "title", "") or book_path.stem,
        language=language,
        chunker="real-book-live-tts-smoke",
        model="ComfyUI/Qwen3-TTS",
        max_chunk_chars=max_chunk_chars,
    )


def _manifest_chunk_count(manifest: dict[str, Any]) -> int:
    """Return the number of chunks in a manifest record."""
    return sum(len(chapter.get("chunks", [])) for chapter in manifest.get("chapters", []))


def _bounded_book_text(book: object, *, max_book_chars: int) -> str:
    """Return a clean leading slice of normalized/raw book text."""
    pieces: list[str] = []
    remaining = max_book_chars
    for chapter in getattr(book, "chapters", []):
        for paragraph in getattr(chapter, "paragraphs", []):
            source = (
                getattr(paragraph, "normalized_text", "")
                or getattr(paragraph, "raw_text", "")
                or ""
            ).strip()
            if not source:
                continue
            source = remove_publisher_boilerplate(source)
            if not source:
                continue
            if is_likely_publisher_boilerplate(source):
                continue
            if len(source) > remaining:
                source = source[:remaining].rsplit(" ", 1)[0].strip() or source[:remaining]
            if source:
                pieces.append(source)
                remaining -= len(source) + 2
            if remaining <= 0:
                break
        if remaining <= 0:
            break
    return "\n\n".join(pieces).strip()


def _smoke_manifest(language: str):
    chunks = [
        {
            "chapter_index": 0,
            "chunk_index": 0,
            "role": "narrator",
            "voice_id": "narrator_calm",
            "intonation": "calm",
            "text": "Глава первая. Короткая проверка синтеза.",
            "language": language,
            "pause_after_ms": 250,
            "boundary_after": "paragraph",
        },
        {
            "chapter_index": 0,
            "chunk_index": 1,
            "role": "female",
            "voice_id": "female_warm",
            "speaker": "Маргарита",
            "character_description": "Теплый женский голос для короткой реплики.",
            "emotion": "calm",
            "intonation": "calm",
            "text": "Здравствуйте. Это тестовая реплика.",
            "language": language,
            "is_dialogue": True,
        },
    ]
    return chunks_to_manifest(
        chunks,
        book_title="Live TTS Smoke",
        language=language,
        chunker="live-tts-smoke",
        model="ComfyUI/Qwen3-TTS",
        max_chunk_chars=120,
    )


if __name__ == "__main__":
    raise SystemExit(main())
