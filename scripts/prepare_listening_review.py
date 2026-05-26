#!/usr/bin/env python3
"""Prepare the post-filter TTS smoke sample for human listening review."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare manual listening review.")
    parser.add_argument(
        "--readiness-report",
        type=Path,
        default=Path("output/final_readiness_report.json"),
    )
    parser.add_argument(
        "--checklist",
        type=Path,
        default=Path("output/manual_listening_checklist.md"),
    )
    parser.add_argument("--open", action="store_true", help="Open audio and checklist with OS defaults.")
    args = parser.parse_args(argv)

    try:
        review = build_review_payload(args.readiness_report, args.checklist)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Listening review is not ready: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(review, ensure_ascii=False, indent=2))
    if args.open:
        open_for_review(Path(review["audio_path"]), Path(review["checklist"]))
    return 0


def build_review_payload(readiness_report: Path, checklist: Path) -> dict[str, Any]:
    """Return the exact human-review inputs and next verdict command."""
    readiness = json.loads(readiness_report.read_text(encoding="utf-8"))
    if readiness.get("automated_gates_ok") is not True:
        raise ValueError("automated gates are not ok")
    if readiness.get("manual_verdict_status") not in {"missing", "review", "fail"}:
        raise ValueError(f"unexpected manual verdict status: {readiness.get('manual_verdict_status')!r}")
    audio_path = Path(readiness["tts_smoke_audit"]["wav"]["path"])
    if not audio_path.exists():
        raise FileNotFoundError(audio_path)
    if not checklist.exists():
        raise FileNotFoundError(checklist)

    return {
        "ready_for_human_listening": True,
        "audio_path": str(audio_path),
        "checklist": str(checklist),
        "duration_seconds": readiness["tts_smoke_audit"]["wav"].get("duration_seconds"),
        "estimated_completion_percent": readiness.get("estimated_completion_percent"),
        "remaining_percent": readiness.get("remaining_percent"),
        "record_pass_command": (
            "python scripts/record_listening_verdict.py --verdict pass "
            '--notes "Accepted post-filter narrator smoke sample."'
        ),
        "record_review_command": (
            "python scripts/record_listening_verdict.py --verdict review "
            '--notes "Describe what needs adjustment."'
        ),
        "record_fail_command": (
            "python scripts/record_listening_verdict.py --verdict fail "
            '--notes "Describe the blocking audio/text issue."'
        ),
    }


def open_for_review(audio_path: Path, checklist: Path) -> None:
    """Open the audio and checklist using the current OS defaults."""
    for path in (audio_path, checklist):
        _open_path(path)


def _open_path(path: Path) -> None:
    system = platform.system()
    if system == "Windows":
        subprocess.Popen(["cmd", "/c", "start", "", str(path)])
    elif system == "Darwin":
        subprocess.Popen(["open", str(path)])
    elif _running_on_linux_windows_host():
        subprocess.Popen(["cmd.exe", "/c", "start", "", _windows_path(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def _running_on_linux_windows_host() -> bool:
    try:
        return "microsoft" in Path("/proc/sys/kernel/osrelease").read_text(encoding="utf-8").lower()
    except OSError:
        return False


def _windows_path(path: Path) -> str:
    text = str(path.resolve())
    if text.startswith("/mnt/") and len(text) >= 7:
        drive = text[5].upper()
        rest = text[7:].replace("/", "\\")
        return f"{drive}:\\" + rest
    return text.replace("/", "\\")


if __name__ == "__main__":
    raise SystemExit(main())
