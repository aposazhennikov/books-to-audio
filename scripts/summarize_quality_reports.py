#!/usr/bin/env python3
"""Summarize multiple quality benchmark JSON reports for human review."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a combined quality benchmark summary.")
    parser.add_argument("reports", nargs="+", help="quality_report_*.json files to include.")
    parser.add_argument(
        "--out",
        default="output/quality_reports_current_summary.md",
        help="Markdown output path.",
    )
    args = parser.parse_args()

    reports = [Path(value) for value in args.reports]
    markdown = summarize_reports(reports)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")
    print(f"Quality summary written: {out_path}")
    return 0


def summarize_reports(paths: list[Path]) -> str:
    """Return one Markdown summary from benchmark report JSON files."""
    loaded = [_load_report(path) for path in paths]
    totals = _totals(loaded)
    lines = [
        "# Current Quality Verification",
        "",
        f"- Reports: {len(loaded)}",
        f"- Cases: {totals['cases']}",
        f"- OK/offline checked: {totals['ok']}",
        f"- Review required/errors: {totals['review']}",
        f"- Text preserved: {totals['text_preserved']}/{totals['cases']}",
        "",
        "| Report | Model | LLM | Langs | Cases | OK | Review | Text Preserved |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]
    for path, report in loaded:
        report_totals = _totals([(path, report)])
        model = str(report.get("primary_model") or "")
        llm = "yes" if report.get("run_ollama") else "no"
        languages = ", ".join(str(lang) for lang in report.get("languages", []))
        lines.append(
            f"| {path.as_posix()} | {model} | {llm} | {languages} | "
            f"{report_totals['cases']} | {report_totals['ok']} | "
            f"{report_totals['review']} | {report_totals['text_preserved']} |"
        )

    lines.extend([
        "",
        "## Case Details",
        "",
        "| # | Status | Lang | Source | Chars | Segments | Chunks | Text OK | Notes |",
        "|---:|---|---|---|---:|---:|---:|---|---|",
    ])
    case_index = 1
    for path, report in loaded:
        for case in report.get("cases", []):
            if not isinstance(case, dict):
                continue
            text_ok = _case_text_ok(case)
            lines.append(
                f"| {case_index} | {case.get('status', 'unknown')} | "
                f"{case.get('language', '')} | {_short_source(str(case.get('source', path)))} | "
                f"{case.get('chars_before', '')} | {case.get('segments', '')} | "
                f"{case.get('chunks', '')} | {'yes' if text_ok else 'no'} | "
                f"{_notes(case)} |"
            )
            case_index += 1
    return "\n".join(lines) + "\n"


def _load_report(path: Path) -> tuple[Path, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Quality report must be a JSON object: {path}")
    return path, data


def _totals(reports: list[tuple[Path, dict[str, Any]]]) -> dict[str, int]:
    cases = [
        case
        for _path, report in reports
        for case in report.get("cases", [])
        if isinstance(case, dict)
    ]
    ok_statuses = {"ok", "offline_checked"}
    return {
        "cases": len(cases),
        "ok": sum(1 for case in cases if case.get("status") in ok_statuses),
        "review": sum(1 for case in cases if case.get("status") not in ok_statuses),
        "text_preserved": sum(1 for case in cases if _case_text_ok(case)),
    }


def _case_text_ok(case: dict[str, Any]) -> bool:
    return bool(
        case.get("text_preserved", False)
        and case.get("segments_preserve_text", case.get("text_preserved", False))
        and case.get("chunk_text_preserved", case.get("text_preserved", False))
    )


def _notes(case: dict[str, Any]) -> str:
    notes = []
    if case.get("llm_rejected"):
        notes.append(f"LLM rejected {case['llm_rejected']}")
    if case.get("error"):
        notes.append(str(case["error"]))
    if case.get("metadata_extra", {}).get("pdf_text_variant"):
        notes.append(f"PDF: {case['metadata_extra']['pdf_text_variant']}")
    return "; ".join(note.replace("|", "/") for note in notes)


def _short_source(source: str, max_len: int = 56) -> str:
    cleaned = source.replace("|", "/")
    if len(cleaned) <= max_len:
        return cleaned
    return "..." + cleaned[-(max_len - 3):]


if __name__ == "__main__":
    raise SystemExit(main())
