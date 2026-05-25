#!/usr/bin/env python3
"""Fetch a small public multilingual corpus for local quality benchmarks."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


@dataclass(frozen=True)
class PublicCorpusSource:
    """One fetchable public text used for benchmark smoke tests."""

    language: str
    subdir: str
    filename: str
    title: str
    url: str
    source_type: str
    license_note: str


PUBLIC_CORPUS_SOURCES = (
    PublicCorpusSource(
        language="en",
        subdir="english",
        filename="pride_and_prejudice.txt",
        title="Pride and Prejudice",
        url="https://www.gutenberg.org/ebooks/1342.txt.utf-8",
        source_type="gutenberg_txt",
        license_note="Project Gutenberg public-domain text in the USA.",
    ),
    PublicCorpusSource(
        language="zh",
        subdir="chinese",
        filename="gui_tian_lu.txt",
        title="歸田錄",
        url="https://www.gutenberg.org/ebooks/25431.txt.utf-8",
        source_type="gutenberg_txt",
        license_note="Project Gutenberg public-domain text in the USA.",
    ),
    PublicCorpusSource(
        language="kk",
        subdir="kazakh",
        filename="abylai_khan.txt",
        title="Абылай хан",
        url="https://wikisource.org/wiki/%D0%90%D0%B1%D1%8B%D0%BB%D0%B0%D0%B9_%D1%85%D0%B0%D0%BD?action=raw",
        source_type="wikisource_raw",
        license_note="Wikisource text page; check page metadata before redistribution.",
    ),
    PublicCorpusSource(
        language="uz",
        subdir="uzbek",
        filename="xalq.txt",
        title="Xalq",
        url="https://wikisource.org/wiki/Xalq?action=raw",
        source_type="wikisource_raw",
        license_note="Wikisource page states public domain in Uzbekistan; check page metadata before redistribution.",
    ),
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download public multilingual benchmark texts.")
    parser.add_argument(
        "--out-dir",
        default="output/public_quality_corpus",
        help="Destination folder. Default: output/public_quality_corpus.",
    )
    parser.add_argument("--force", action="store_true", help="Re-download even when files already exist.")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds.")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    fetch_public_corpus(out_dir=out_dir, force=args.force, timeout=args.timeout)
    print(f"Public quality corpus ready: {out_dir}")
    print(f"Language map: {out_dir / 'languages.json'}")
    return 0


def fetch_public_corpus(
    *,
    out_dir: Path,
    force: bool = False,
    timeout: float = 30.0,
) -> list[Path]:
    """Fetch public corpus files and return written text paths."""

    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    language_map: dict[str, str] = {}
    source_records: list[dict[str, str]] = []

    for source in PUBLIC_CORPUS_SOURCES:
        destination = out_dir / source.subdir / source.filename
        language_map[f"{source.subdir}/*.txt"] = source.language
        source_records.append({
            "language": source.language,
            "title": source.title,
            "url": source.url,
            "path": str(destination.relative_to(out_dir)),
            "license_note": source.license_note,
        })
        if destination.exists() and not force and destination.stat().st_size > 0:
            written.append(destination)
            continue

        raw = _download_text(source.url, timeout=timeout)
        cleaned = clean_downloaded_text(raw, source.source_type)
        if len(cleaned) < 80:
            raise RuntimeError(f"Downloaded text is too short for {source.url}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(cleaned.rstrip() + "\n", encoding="utf-8")
        written.append(destination)

    (out_dir / "languages.json").write_text(
        json.dumps(language_map, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out_dir / "sources.json").write_text(
        json.dumps(source_records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return written


def clean_downloaded_text(text: str, source_type: str) -> str:
    """Strip transport/project boilerplate while keeping the book text."""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if source_type == "gutenberg_txt":
        normalized = _strip_gutenberg_boilerplate(normalized)
    elif source_type == "wikisource_raw":
        normalized = _strip_wikisource_markup(normalized)
    return _squash_blank_lines(normalized)


def _download_text(url: str, *, timeout: float) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "books-to-audio-quality-benchmark/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        content_type = response.headers.get_content_charset() or "utf-8"
        data = response.read()
    return data.decode(content_type, errors="replace")


def _strip_gutenberg_boilerplate(text: str) -> str:
    start_patterns = (
        r"\*\*\* START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK .*?\*\*\*",
        r"\*\*\*START OF THE PROJECT GUTENBERG EBOOK.*?\*\*\*",
    )
    end_patterns = (
        r"\*\*\* END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK .*?\*\*\*",
        r"\*\*\*END OF THE PROJECT GUTENBERG EBOOK.*?\*\*\*",
    )
    stripped = text
    for pattern in start_patterns:
        match = re.search(pattern, stripped, flags=re.IGNORECASE | re.DOTALL)
        if match:
            stripped = stripped[match.end():]
            break
    for pattern in end_patterns:
        match = re.search(pattern, stripped, flags=re.IGNORECASE | re.DOTALL)
        if match:
            stripped = stripped[:match.start()]
            break
    return stripped.strip()


def _strip_wikisource_markup(text: str) -> str:
    stripped = re.sub(r"\{\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}\}", "\n", text)
    stripped = re.sub(r"<ref\b[^>]*>.*?</ref>", "", stripped, flags=re.IGNORECASE | re.DOTALL)
    stripped = re.sub(r"<[^>]+>", "", stripped)
    stripped = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", stripped)
    stripped = re.sub(r"\[[a-z]+:[^\]]+\]", "", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"^=+\s*(.*?)\s*=+$", r"\1", stripped, flags=re.MULTILINE)
    stripped = re.sub(r"^\s*(?:Category|File|Image):.*$", "", stripped, flags=re.MULTILINE)
    return stripped.strip()


def _squash_blank_lines(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    squashed = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", squashed).strip()


if __name__ == "__main__":
    raise SystemExit(main())
