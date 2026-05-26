#!/usr/bin/env python3
"""Record the human verdict for a manual listening checklist."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

Verdict = Literal["pass", "review", "fail"]
VALID_VERDICTS = {"pass", "review", "fail"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record a human listening verdict.")
    parser.add_argument("--verdict", required=True, choices=sorted(VALID_VERDICTS))
    parser.add_argument("--notes", default="")
    parser.add_argument(
        "--checklist",
        type=Path,
        default=Path("output/manual_listening_checklist.md"),
    )
    parser.add_argument(
        "--readiness-report",
        type=Path,
        default=Path("output/final_readiness_report.json"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("output/manual_listening_verdict.json"),
    )
    parser.add_argument(
        "--refresh-readiness",
        action="store_true",
        help="Rebuild the final readiness report after writing the verdict.",
    )
    args = parser.parse_args(argv)

    record = build_verdict_record(
        verdict=args.verdict,
        notes=args.notes,
        checklist=args.checklist,
        readiness_report=args.readiness_report,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Listening verdict: {args.out}")
    if args.refresh_readiness:
        report = refresh_readiness_report(args.readiness_report, verdict_report=args.out)
        print(
            "Final readiness: "
            f"{report.get('estimated_completion_percent')}% "
            f"(manual={report.get('manual_verdict_status')})"
        )
    return 0 if args.verdict == "pass" else 1


def build_verdict_record(
    *,
    verdict: Verdict,
    notes: str,
    checklist: Path,
    readiness_report: Path,
) -> dict[str, Any]:
    """Build a machine-readable human listening verdict."""
    if verdict not in VALID_VERDICTS:
        raise ValueError(f"Unknown verdict: {verdict}")
    readiness = _load_optional_json(readiness_report)
    audio_path = (
        readiness.get("tts_smoke_audit", {})
        .get("wav", {})
        .get("path", "output/live_tts_real_book_smoke_after_filter/chapter_001.wav")
    )
    return {
        "verdict": verdict,
        "passed": verdict == "pass",
        "requires_review": verdict == "review",
        "failed": verdict == "fail",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "audio_path": audio_path,
        "checklist": str(checklist),
        "readiness_report": str(readiness_report),
        "automated_gates_ok": readiness.get("automated_gates_ok"),
        "notes": notes,
    }


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def refresh_readiness_report(readiness_report: Path, *, verdict_report: Path) -> dict[str, Any]:
    """Regenerate the final readiness report with the freshly written verdict."""
    script_dir = Path(__file__).resolve().parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    from final_readiness_check import build_readiness_report  # noqa: PLC0415

    report = build_readiness_report(
        Path("output/live_tts_real_book_smoke_after_filter"),
        Path("docs/quality-status.md"),
        verdict_report,
    )
    readiness_report.parent.mkdir(parents=True, exist_ok=True)
    readiness_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    raise SystemExit(main())
