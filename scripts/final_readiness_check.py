#!/usr/bin/env python3
"""Create a final readiness report without starting LLM or TTS models."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_tts_smoke import audit_tts_smoke  # noqa: E402

REQUIRED_QUALITY_MARKERS = (
    "885 passed, 9 skipped",
    "Live real-book TTS smoke passed",
    "Qwen3-8B-GGUF:Q4_K_M",
    "Qwen3-4B-GGUF:Q4_K_M",
    "ComfyUI was stopped",
    "`ollama ps` was empty",
)

MANUAL_REMAINING = (
    "Human listen-through of output/live_tts_real_book_smoke_after_filter/chapter_001.wav.",
    "Optional full-length real-book LLM+TTS acceptance run in an explicit long-running window.",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a final readiness report.")
    parser.add_argument(
        "--smoke-dir",
        type=Path,
        default=Path("output/live_tts_real_book_smoke_after_filter"),
    )
    parser.add_argument("--quality-doc", type=Path, default=Path("docs/quality-status.md"))
    parser.add_argument("--write-report", type=Path, default=Path("output/final_readiness_report.json"))
    args = parser.parse_args(argv)

    report = build_readiness_report(args.smoke_dir, args.quality_doc)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(payload)
    args.write_report.parent.mkdir(parents=True, exist_ok=True)
    args.write_report.write_text(payload + "\n", encoding="utf-8")
    return 0 if report["automated_gates_ok"] else 1


def build_readiness_report(smoke_dir: Path, quality_doc: Path) -> dict[str, Any]:
    """Return an automated readiness report and explicit remaining manual work."""
    tts_audit = audit_tts_smoke(smoke_dir)
    quality_text = quality_doc.read_text(encoding="utf-8")
    missing_quality_markers = [
        marker for marker in REQUIRED_QUALITY_MARKERS if marker not in quality_text
    ]
    automated_gates_ok = tts_audit["ok"] and not missing_quality_markers
    return {
        "automated_gates_ok": automated_gates_ok,
        "complete_without_human_review": False,
        "tts_smoke_audit": tts_audit,
        "quality_doc": str(quality_doc),
        "missing_quality_markers": missing_quality_markers,
        "manual_remaining": list(MANUAL_REMAINING),
    }


if __name__ == "__main__":
    raise SystemExit(main())
