#!/usr/bin/env python3
"""Run a lightweight multilingual quality benchmark.

Default mode is offline and fast: it checks synthetic multilingual samples and
any local books under ``books/`` without calling Ollama. Set
``RUN_OLLAMA_TESTS=1`` or pass ``--run-ollama`` to exercise the local Ollama
stack and write reviewable reports under ``output/quality_reports``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from book_normalizer.chunking.llm_segmenter import LlmSegmentationError, LlmVoiceSegmenter  # noqa: E402
from book_normalizer.chunking.splitter import chunk_text  # noqa: E402
from book_normalizer.chunking.voice_splitter import build_chunks_from_segments  # noqa: E402
from book_normalizer.config import OcrMode  # noqa: E402
from book_normalizer.languages import (  # noqa: E402
    SUPPORTED_LANGUAGE_CODES,
    normalize_book_language,
    tesseract_language,
)
from book_normalizer.llm.model_router import PRIMARY_QWEN3_MODEL, model_plan_for_language  # noqa: E402
from book_normalizer.loaders.factory import LoaderFactory  # noqa: E402
from book_normalizer.loaders.pdf_loader import (  # noqa: E402
    PdfLoader,
    extract_pdf_with_ocr_mode,
    select_pdf_text_for_mode,
)
from book_normalizer.models.book import Book, Chapter, Metadata, Paragraph  # noqa: E402
from book_normalizer.normalization.llm_normalizer import LlmNormalizer  # noqa: E402

SYNTHETIC_SAMPLES = {
    "ru": "Сергей открыл дверь.\n\n— Кто там? — спросил он.",
    "en": "Sergey opened the door.\n\n\"Who is there?\" he asked.",
    "zh": "谢尔盖打开了门。\n\n“谁在那里？”他问。",
    "kk": "Сергей есікті ашты.\n\n— Онда кім бар? — деді ол.",
    "uz": "Sergey eshikni ochdi.\n\n\"U yerda kim bor?\" deb so'radi u.",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Multilingual extraction and LLM quality benchmark.")
    parser.add_argument("--books-dir", default="books", help="Optional local books directory.")
    parser.add_argument("--out-dir", default="output/quality_reports", help="Report output directory.")
    parser.add_argument("--run-ollama", action="store_true", help="Call local Ollama for each benchmark case.")
    parser.add_argument("--limit-books", type=int, default=5, help="Maximum local books to inspect.")
    parser.add_argument(
        "--max-chars",
        type=int,
        default=1200,
        help="Maximum characters per real-book LLM excerpt. Keeps 8 GB VRAM / 16 GB RAM machines responsive.",
    )
    args = parser.parse_args()

    run_ollama = args.run_ollama or os.environ.get("RUN_OLLAMA_TESTS") == "1"
    report = run_benchmark(
        books_dir=Path(args.books_dir),
        run_ollama=run_ollama,
        limit_books=args.limit_books,
        max_chars=args.max_chars,
    )
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"quality_report_{stamp}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Quality report written: {out_path}")


def run_benchmark(
    *,
    books_dir: Path,
    run_ollama: bool,
    limit_books: int = 5,
    max_chars: int = 1200,
) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for language in SUPPORTED_LANGUAGE_CODES:
        cases.append(_run_case(_synthetic_book(language), source="synthetic", run_ollama=run_ollama))

    if books_dir.exists():
        for path in _iter_book_paths(books_dir)[:limit_books]:
            try:
                book = _load_book_for_benchmark(path)
                excerpt = _excerpt_book(book, max_chars=max_chars)
                cases.append(_run_case(excerpt, source=str(path), run_ollama=run_ollama))
            except Exception as exc:  # noqa: BLE001
                cases.append({
                    "source": str(path),
                    "status": "error",
                    "error": f"{type(exc).__name__}: {exc}",
                })

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_ollama": run_ollama,
        "max_chars": max_chars,
        "primary_model": PRIMARY_QWEN3_MODEL,
        "cases": cases,
    }


def _run_case(book: Book, *, source: str, run_ollama: bool) -> dict[str, Any]:
    language = book.metadata.language
    before = book.normalized_text or book.raw_text
    record: dict[str, Any] = {
        "source": source,
        "language": language,
        "source_format": book.metadata.source_format,
        "chapters": len(book.chapters),
        "paragraphs": sum(len(ch.paragraphs) for ch in book.chapters),
        "chars_before": len(before),
        "model_candidates": list(model_plan_for_language(language).candidates),
    }
    if book.metadata.extra:
        record["metadata_extra"] = book.metadata.extra

    if run_ollama:
        try:
            normalizer = LlmNormalizer(language=language)
            accepted, rejected = normalizer.normalize_book(book)
            segmenter = LlmVoiceSegmenter(language=language)
            segments = segmenter.segment_book(book)
            after = book.normalized_text or book.raw_text
            chunks = build_chunks_from_segments(segments, max_chunk_chars=600)
            segments_preserve_text = _canonical_exact(after) == _canonical_exact(
                " ".join(str(segment.get("text") or "") for segment in segments)
            )
            chunk_text_preserved = _canonical_exact(after) == _canonical_exact(
                " ".join(str(chunk.get("text") or "") for chunk in chunks)
            )
            structure_ok = bool(segments) and bool(chunks) and segments_preserve_text and chunk_text_preserved
            record.update({
                "status": "ok" if structure_ok else "review_required",
                "llm_accepted": accepted,
                "llm_rejected": rejected,
                "segments": len(segments),
                "dialogue_segments": sum(1 for segment in segments if segment.get("role") in {"male", "female"}),
                "chunks": len(chunks),
                "text_preserved": _canonical_content(before) == _canonical_content(after),
                "segments_preserve_text": segments_preserve_text,
                "chunk_text_preserved": chunk_text_preserved,
            })
            if not structure_ok:
                record["error"] = "segment/chunk manifest does not preserve normalized text"
        except (LlmSegmentationError, Exception) as exc:  # noqa: BLE001
            record.update({
                "status": "review_required",
                "error": f"{type(exc).__name__}: {exc}",
            })
    else:
        chunks = chunk_text(before, 600)
        record.update({
            "status": "offline_checked",
            "segments": len(chunks),
            "chunks": len(chunks),
            "text_preserved": True,
        })

    return record


def _load_book_for_benchmark(path: Path, language: str = "ru") -> Book:
    """Load local benchmark books with OCR-aware PDF selection."""
    if path.suffix.lower() != ".pdf":
        book = LoaderFactory.default().load(path)
        book.metadata.language = normalize_book_language(book.metadata.language)
        return book

    language_code = normalize_book_language(language)
    native_compare = extract_pdf_with_ocr_mode(
        path,
        OcrMode.OFF,
        dpi=300,
        psm=6,
        lang=tesseract_language(language_code),
        language_code=language_code,
    )
    chosen, stats = select_pdf_text_for_mode(native_compare, OcrMode.AUTO, language_code=language_code)
    if not stats.get("native_unreadable"):
        stats["reason"] = "benchmark_native_precheck_preferred"
        return _book_from_pdf_variant(path, language_code, chosen, stats)

    compare = extract_pdf_with_ocr_mode(
        path,
        OcrMode.AUTO,
        dpi=300,
        psm=6,
        lang=tesseract_language(language_code),
        language_code=language_code,
    )
    chosen, stats = select_pdf_text_for_mode(compare, OcrMode.AUTO, language_code=language_code)
    if stats.get("native_unreadable") and chosen.kind == "native":
        raise RuntimeError(f"PDF text unreadable and OCR unavailable/unusable: {stats.get('reason')}")

    return _book_from_pdf_variant(path, language_code, chosen, stats)


def _book_from_pdf_variant(
    path: Path,
    language_code: str,
    chosen: Any,
    stats: dict[str, Any],
) -> Book:
    text = chosen.text
    text = text.strip()
    paragraphs = PdfLoader._split_paragraphs(text)
    chapter = Chapter(
        title="Full Text",
        index=0,
        paragraphs=paragraphs,
        source_span_start=0,
        source_span_end=len(text),
    )
    metadata = Metadata(
        title=path.stem,
        language=language_code,
        source_path=str(path.resolve()),
        source_format="pdf",
        extra={
            "pdf_text_variant": chosen.kind,
            "pdf_text_stats": stats,
        },
    )
    book = Book(metadata=metadata, chapters=[chapter])
    book.add_audit(
        "loading",
        "quality_benchmark_pdf",
        f"variant={chosen.kind}, chars={len(text)}, reason={stats.get('reason')}",
    )
    return book


def _excerpt_book(book: Book, *, max_chars: int) -> Book:
    """Return a bounded real-book excerpt for local LLM smoke tests."""
    if max_chars <= 0 or len(book.raw_text) <= max_chars:
        return book

    remaining = max_chars
    excerpt_chapters: list[Chapter] = []
    for chapter in book.chapters:
        excerpt_paragraphs: list[Paragraph] = []
        for paragraph in chapter.paragraphs:
            source = (paragraph.normalized_text or paragraph.raw_text).strip()
            if not source:
                continue
            if excerpt_paragraphs and remaining < 120:
                break
            selected = source
            if len(selected) > remaining:
                selected = _trim_excerpt(selected, remaining)
            if not selected:
                break
            excerpt_paragraphs.append(
                Paragraph(
                    raw_text=selected,
                    normalized_text="",
                    index_in_chapter=len(excerpt_paragraphs),
                )
            )
            remaining -= len(selected) + 2
            if remaining <= 0:
                break
        if excerpt_paragraphs:
            excerpt_chapters.append(
                Chapter(
                    title=chapter.title,
                    index=chapter.index,
                    paragraphs=excerpt_paragraphs,
                    source_span_start=chapter.source_span_start,
                    source_span_end=chapter.source_span_end,
                )
            )
        if remaining <= 0:
            break

    metadata = book.metadata.model_copy(deep=True)
    metadata.extra = {
        **metadata.extra,
        "benchmark_excerpt": True,
        "benchmark_original_chars": len(book.raw_text),
    }
    excerpt = Book(metadata=metadata, chapters=excerpt_chapters)
    metadata.extra["benchmark_excerpt_chars"] = len(excerpt.raw_text)
    return excerpt


def _trim_excerpt(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    clipped = text[:max_chars].rstrip()
    for separator in (". ", "! ", "? ", "। ", "。", " "):
        head, sep, _tail = clipped.rpartition(separator)
        if sep and len(head) >= max(120, max_chars // 3):
            return (head + sep.strip()).strip()
    head, _sep, _tail = clipped.rpartition(" ")
    if head and len(head) >= min(40, max_chars):
        return head.strip()
    return clipped


def _synthetic_book(language: str) -> Book:
    text = SYNTHETIC_SAMPLES[language]
    paragraphs = [
        Paragraph(raw_text=part, normalized_text=part, index_in_chapter=index)
        for index, part in enumerate(text.split("\n\n"))
    ]
    return Book(
        metadata=Metadata(title=f"Synthetic {language}", language=language, source_format="synthetic"),
        chapters=[Chapter(title="Synthetic", index=0, paragraphs=paragraphs)],
    )


def _iter_book_paths(books_dir: Path) -> list[Path]:
    suffixes = {".txt", ".fb2", ".epub", ".docx", ".pdf"}
    return sorted(path for path in books_dir.rglob("*") if path.suffix.lower() in suffixes)


def _canonical_exact(text: str) -> str:
    return "".join((text or "").split())


def _canonical_content(text: str) -> str:
    return "".join(char.casefold() for char in text or "" if char.isalnum())


if __name__ == "__main__":
    main()
