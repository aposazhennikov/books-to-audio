#!/usr/bin/env python3
"""Run a lightweight multilingual quality benchmark.

Default mode is offline and fast: it checks synthetic multilingual samples and
any local books under ``books/`` without calling Ollama. Set
``RUN_OLLAMA_TESTS=1`` or pass ``--run-ollama`` to exercise the local WSL
Ollama stack and write reviewable reports under ``output/quality_reports``.
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
from book_normalizer.languages import SUPPORTED_LANGUAGE_CODES  # noqa: E402
from book_normalizer.llm.model_router import PRIMARY_QWEN3_MODEL, model_plan_for_language  # noqa: E402
from book_normalizer.loaders.factory import LoaderFactory  # noqa: E402
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
    args = parser.parse_args()

    run_ollama = args.run_ollama or os.environ.get("RUN_OLLAMA_TESTS") == "1"
    report = run_benchmark(
        books_dir=Path(args.books_dir),
        run_ollama=run_ollama,
        limit_books=args.limit_books,
    )
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"quality_report_{stamp}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Quality report written: {out_path}")


def run_benchmark(*, books_dir: Path, run_ollama: bool, limit_books: int = 5) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for language in SUPPORTED_LANGUAGE_CODES:
        cases.append(_run_case(_synthetic_book(language), source="synthetic", run_ollama=run_ollama))

    if books_dir.exists():
        for path in _iter_book_paths(books_dir)[:limit_books]:
            try:
                book = LoaderFactory.default().load(path)
                cases.append(_run_case(book, source=str(path), run_ollama=run_ollama))
            except Exception as exc:  # noqa: BLE001
                cases.append({
                    "source": str(path),
                    "status": "error",
                    "error": f"{type(exc).__name__}: {exc}",
                })

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_ollama": run_ollama,
        "primary_model": PRIMARY_QWEN3_MODEL,
        "cases": cases,
    }


def _run_case(book: Book, *, source: str, run_ollama: bool) -> dict[str, Any]:
    language = book.metadata.language
    before = book.normalized_text or book.raw_text
    record: dict[str, Any] = {
        "source": source,
        "language": language,
        "chapters": len(book.chapters),
        "paragraphs": sum(len(ch.paragraphs) for ch in book.chapters),
        "chars_before": len(before),
        "model_candidates": list(model_plan_for_language(language).candidates),
    }

    if run_ollama:
        try:
            normalizer = LlmNormalizer(language=language)
            accepted, rejected = normalizer.normalize_book(book)
            segmenter = LlmVoiceSegmenter(language=language)
            segments = segmenter.segment_book(book)
            after = book.normalized_text or book.raw_text
            record.update({
                "status": "ok",
                "llm_accepted": accepted,
                "llm_rejected": rejected,
                "segments": len(segments),
                "chunks": len(chunk_text(after, 600)),
                "text_preserved": _canonical(before) == _canonical(after),
            })
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


def _canonical(text: str) -> str:
    return "".join((text or "").split())


if __name__ == "__main__":
    main()
