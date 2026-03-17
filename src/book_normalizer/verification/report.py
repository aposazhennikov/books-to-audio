"""Verification statistics and report generation for before/after books."""

from __future__ import annotations

import json
import math
import random
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, Sequence

from book_normalizer.models.book import Book, Chapter, Paragraph


RE_HEADING_CANDIDATE = re.compile(
    r"^\s*(?:глава|часть|пролог|эпилог|введение|заключение|предисловие|послесловие)\b",
    re.IGNORECASE,
)


RE_NUMERIC_HEADING = re.compile(
    r"^\s*(\d+(\.\d+)*)\s+[^\d]{3,}",
    re.IGNORECASE,
)


RE_SUSPICIOUS_TOKEN = re.compile(r"[^\w\s«»…—\-.,;:?!]", re.UNICODE)


RE_WORD = re.compile(r"\w+", re.UNICODE)


RE_REPLACEMENT_CHAR = re.compile("�")


@dataclass
class BookStats:
    """Aggregate statistics for a book representation."""

    character_count: int
    word_count: int
    paragraph_count: int
    chapter_count: int
    heading_count: int
    em_dash_count: int
    angle_quote_count: int
    ellipsis_char_count: int
    ellipsis_three_dots_count: int
    replacement_char_count: int


@dataclass
class HeadingReport:
    """Heading preservation summary."""

    preserved: list[str]
    missing: list[str]
    added: list[str]


@dataclass
class SuspiciousChange:
    """Single suspicious change signal."""

    kind: str
    severity: str
    message: str


@dataclass
class VerificationSamples:
    """Random and suspicious fragments for manual spot-check."""

    random_paragraphs: list[dict]
    chapter_boundaries: list[dict]
    suspicious_fragments: list[dict]


@dataclass
class VerificationConfig:
    """Config for verification heuristics."""

    sample_size: int = 20
    random_seed: int = 42


@dataclass
class VerificationResult:
    """Full result of verification, including paths to artifacts."""

    stats_before: BookStats
    stats_after: BookStats
    heading_report: HeadingReport
    suspicious_changes: list[SuspiciousChange]
    samples: VerificationSamples
    artifacts: dict[str, str]


def _book_text(book: Book, normalized: bool) -> str:
    return book.normalized_text if normalized else book.raw_text


def _count_words(text: str) -> int:
    return len(RE_WORD.findall(text))


def _collect_all_paragraphs(book: Book, normalized: bool) -> list[Paragraph]:
    paragraphs: list[Paragraph] = []
    for chapter in book.chapters:
        for para in chapter.paragraphs:
            if normalized and not (para.normalized_text or para.raw_text):
                continue
            if not normalized and not para.raw_text:
                continue
            paragraphs.append(para)
    return paragraphs


def _collect_candidate_headings(book: Book, normalized: bool) -> list[str]:
    headings: set[str] = set()

    for ch in book.chapters:
        title = (ch.title or "").strip()
        if title:
            headings.add(title)

    for ch in book.chapters:
        for para in ch.paragraphs:
            text = (para.normalized_text if normalized and para.normalized_text else para.raw_text).strip()
            if not text:
                continue
            if len(text) > 120:
                continue
            if "." in text:
                continue
            if RE_HEADING_CANDIDATE.match(text) or RE_NUMERIC_HEADING.match(text):
                headings.add(text)

    return sorted(headings)


def compute_book_stats(book: Book, normalized: bool) -> BookStats:
    """Compute aggregate statistics for a book."""
    text = _book_text(book, normalized=normalized)
    paragraphs = _collect_all_paragraphs(book, normalized=normalized)
    headings = _collect_candidate_headings(book, normalized=normalized)

    return BookStats(
        character_count=len(text),
        word_count=_count_words(text),
        paragraph_count=len(paragraphs),
        chapter_count=len(book.chapters),
        heading_count=len(headings),
        em_dash_count=text.count("—"),
        angle_quote_count=text.count("«") + text.count("»"),
        ellipsis_char_count=text.count("…"),
        ellipsis_three_dots_count=text.count("..."),
        replacement_char_count=len(RE_REPLACEMENT_CHAR.findall(text)),
    )


def _heading_report(before: Book, after: Book) -> HeadingReport:
    before_headings = set(_collect_candidate_headings(before, normalized=False))
    after_headings = set(_collect_candidate_headings(after, normalized=True))

    preserved = sorted(before_headings & after_headings)
    missing = sorted(before_headings - after_headings)
    added = sorted(after_headings - before_headings)

    return HeadingReport(preserved=preserved, missing=missing, added=added)


def _paragraph_lengths(paragraphs: Iterable[Paragraph], normalized: bool) -> list[int]:
    lengths: list[int] = []
    for p in paragraphs:
        text = p.normalized_text if normalized and p.normalized_text else p.raw_text
        if text:
            lengths.append(len(text))
    return lengths


def _median(values: Sequence[int]) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 1:
        return float(sorted_vals[mid])
    return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0


def _detect_suspicious_changes(before: Book, after: Book) -> list[SuspiciousChange]:
    """Heuristic detection of suspicious structural and punctuation changes."""
    changes: list[SuspiciousChange] = []

    before_paras = _collect_all_paragraphs(before, normalized=False)
    after_paras = _collect_all_paragraphs(after, normalized=True)

    before_lens = _paragraph_lengths(before_paras, normalized=False)
    after_lens = _paragraph_lengths(after_paras, normalized=True)

    if before_lens and after_lens:
        before_med = _median(before_lens)
        after_med = _median(after_lens)

        if before_med > 0 and after_med > 0:
            ratio = after_med / before_med
            if ratio > 2.5:
                changes.append(
                    SuspiciousChange(
                        kind="paragraph_merge",
                        severity="medium",
                        message=f"Median paragraph length increased significantly (ratio={ratio:.2f}).",
                    )
                )
            elif ratio < 0.4:
                changes.append(
                    SuspiciousChange(
                        kind="paragraph_split",
                        severity="medium",
                        message=f"Median paragraph length decreased significantly (ratio={ratio:.2f}).",
                    )
                )

        very_long_after = [l for l in after_lens if l > max(2000, 4 * after_med)]
        if very_long_after:
            changes.append(
                SuspiciousChange(
                    kind="long_paragraphs",
                    severity="high",
                    message=f"{len(very_long_after)} paragraphs are unusually long after normalization.",
                )
            )

        very_short_after = [l for l in after_lens if l < min(10, 0.25 * after_med)]
        if very_short_after and len(very_short_after) > len(after_lens) * 0.3:
            changes.append(
                SuspiciousChange(
                    kind="many_short_paragraphs",
                    severity="medium",
                    message="Large fraction of paragraphs are very short after normalization.",
                )
            )

    if len(after_paras) > len(before_paras) * 3 or len(after_paras) < len(before_paras) * 0.3:
        changes.append(
            SuspiciousChange(
                kind="paragraph_count_change",
                severity="high",
                message=(
                    f"Paragraph count changed significantly: before={len(before_paras)}, "
                    f"after={len(after_paras)}."
                ),
            )
        )

    before_text = before.raw_text
    after_text = after.normalized_text
    before_punct = sum(before_text.count(ch) for ch in ".,!?;:")
    after_punct = sum(after_text.count(ch) for ch in ".,!?;:")
    if before_punct > 0:
        punct_ratio = after_punct / before_punct
        if punct_ratio < 0.7:
            changes.append(
                SuspiciousChange(
                    kind="punctuation_loss",
                    severity="high",
                    message=f"Punctuation density dropped (ratio={punct_ratio:.2f}).",
                )
            )

    before_repr = {p.raw_text.strip()[:80] for p in before_paras if p.raw_text.strip()}
    after_repr = {
        (p.normalized_text or p.raw_text).strip()[:80] for p in after_paras if (p.normalized_text or p.raw_text).strip()
    }
    missing_like = before_repr - after_repr
    if missing_like:
        sample = list(sorted(missing_like))[:5]
        changes.append(
            SuspiciousChange(
                kind="potential_missing_paragraphs",
                severity="medium",
                message=f"Some paragraphs seem missing after normalization (examples: {sample}).",
            )
        )

    before_suspicious = len(RE_SUSPICIOUS_TOKEN.findall(before_text))
    after_suspicious = len(RE_SUSPICIOUS_TOKEN.findall(after_text))
    if after_suspicious > before_suspicious * 1.5 and after_suspicious > 10:
        changes.append(
            SuspiciousChange(
                kind="garbage_tokens",
                severity="medium",
                message="Suspicious symbol count increased after normalization.",
            )
        )

    if after_text.count("�") > before_text.count("�"):
        changes.append(
            SuspiciousChange(
                kind="replacement_chars",
                severity="high",
                message="Replacement character '�' appears more frequently after normalization.",
            )
        )

    return changes


def _sample_paragraph_pairs(
    before: Book,
    after: Book,
    config: VerificationConfig,
) -> list[dict]:
    before_paras = _collect_all_paragraphs(before, normalized=False)
    after_paras = _collect_all_paragraphs(after, normalized=True)

    if not before_paras or not after_paras:
        return []

    rng = random.Random(config.random_seed)
    indices = list(range(len(before_paras)))
    rng.shuffle(indices)
    indices = indices[: config.sample_size]

    samples: list[dict] = []
    for idx in sorted(indices):
        before_para = before_paras[idx]
        j = min(idx, len(after_paras) - 1)
        after_para = after_paras[j]

        samples.append(
            {
                "before_index": idx,
                "after_index": j,
                "before_text": before_para.raw_text,
                "after_text": after_para.normalized_text or after_para.raw_text,
            }
        )

    return samples


def _sample_chapter_boundaries(before: Book, after: Book, max_samples: int = 10) -> list[dict]:
    samples: list[dict] = []

    for book in (before, after):
        label = "before" if book is before else "after"
        for ch in book.chapters:
            if not ch.paragraphs:
                continue
            first = ch.paragraphs[0]
            last = ch.paragraphs[-1]
            samples.append(
                {
                    "phase": label,
                    "chapter_index": ch.index,
                    "chapter_title": ch.title,
                    "first_paragraph": first.raw_text or first.normalized_text,
                    "last_paragraph": last.raw_text or last.normalized_text,
                }
            )

    return samples[:max_samples]


def _sample_suspicious_fragments(
    before: Book,
    after: Book,
    suspicious: Sequence[SuspiciousChange],
) -> list[dict]:
    fragments: list[dict] = []

    if not suspicious:
        return fragments

    after_paras = _collect_all_paragraphs(after, normalized=True)
    for p in after_paras:
        text = p.normalized_text or p.raw_text
        if len(text) > 4000:
            fragments.append(
                {
                    "reason": "long_paragraph",
                    "text_start": text[:500],
                }
            )
        if "�" in text:
            fragments.append(
                {
                    "reason": "replacement_char",
                    "text_context": text[:2000],
                }
            )
        if len(fragments) >= 20:
            break

    return fragments


def generate_reports(
    before: Book,
    after: Book,
    output_dir: Path,
    config: VerificationConfig,
) -> VerificationResult:
    """
    Generate verification reports and write them to the output directory.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    stats_before = compute_book_stats(before, normalized=False)
    stats_after = compute_book_stats(after, normalized=True)

    heading_rep = _heading_report(before, after)
    suspicious = _detect_suspicious_changes(before, after)

    samples = VerificationSamples(
        random_paragraphs=_sample_paragraph_pairs(before, after, config),
        chapter_boundaries=_sample_chapter_boundaries(before, after),
        suspicious_fragments=_sample_suspicious_fragments(before, after, suspicious),
    )

    stats_path = output_dir / "stats_before_after.json"
    suspicious_path = output_dir / "suspicious_changes.json"
    headings_path = output_dir / "missing_headings.txt"
    anomaly_path = output_dir / "anomaly_report.txt"
    sample_path = output_dir / "random_sample_review.txt"

    stats_payload = {
        "before": asdict(stats_before),
        "after": asdict(stats_after),
    }
    stats_path.write_text(json.dumps(stats_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    suspicious_payload = [asdict(item) for item in suspicious]
    suspicious_path.write_text(json.dumps(suspicious_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if heading_rep.missing:
        headings_path.write_text("\n".join(heading_rep.missing), encoding="utf-8")
    else:
        headings_path.write_text("# No missing headings detected.\n", encoding="utf-8")

    anomaly_lines: list[str] = []
    anomaly_lines.append("Verification anomaly summary:")
    anomaly_lines.append("")
    for item in suspicious:
        anomaly_lines.append(f"- [{item.severity}] {item.kind}: {item.message}")
    anomaly_path.write_text("\n".join(anomaly_lines), encoding="utf-8")

    sample_lines: list[str] = []
    sample_lines.append("=== RANDOM PARAGRAPH SAMPLES ===")
    for s in samples.random_paragraphs:
        sample_lines.append("")
        sample_lines.append(f"[before idx={s['before_index']}]")
        sample_lines.append(s["before_text"])
        sample_lines.append("")
        sample_lines.append(f"[after idx={s['after_index']}]")
        sample_lines.append(s["after_text"])
        sample_lines.append("\n" + "-" * 40)

    sample_lines.append("\n=== CHAPTER BOUNDARY SAMPLES ===")
    for s in samples.chapter_boundaries:
        sample_lines.append("")
        sample_lines.append(f"[{s['phase']}] Chapter {s['chapter_index']}: {s['chapter_title']}")
        sample_lines.append("FIRST:")
        sample_lines.append(s["first_paragraph"])
        sample_lines.append("LAST:")
        sample_lines.append(s["last_paragraph"])
        sample_lines.append("\n" + "-" * 40)

    sample_lines.append("\n=== SUSPICIOUS FRAGMENTS ===")
    for s in samples.suspicious_fragments:
        sample_lines.append("")
        sample_lines.append(f"Reason: {s['reason']}")
        if "text_start" in s:
            sample_lines.append(s["text_start"])
        if "text_context" in s:
            sample_lines.append(s["text_context"])
        sample_lines.append("\n" + "-" * 40)

    sample_path.write_text("\n".join(sample_lines), encoding="utf-8")

    artifacts = {
        "stats_before_after": str(stats_path),
        "suspicious_changes": str(suspicious_path),
        "missing_headings": str(headings_path),
        "anomaly_report": str(anomaly_path),
        "random_sample_review": str(sample_path),
    }

    return VerificationResult(
        stats_before=stats_before,
        stats_after=stats_after,
        heading_report=heading_rep,
        suspicious_changes=suspicious,
        samples=samples,
        artifacts=artifacts,
    )

