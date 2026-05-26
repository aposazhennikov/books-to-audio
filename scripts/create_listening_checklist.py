#!/usr/bin/env python3
"""Create a human listening checklist for the final TTS smoke sample."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a manual listening checklist.")
    parser.add_argument(
        "--smoke-dir",
        type=Path,
        default=Path("output/live_tts_real_book_smoke_after_filter"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("output/manual_listening_checklist.md"),
    )
    args = parser.parse_args(argv)

    checklist = build_listening_checklist(args.smoke_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(checklist, encoding="utf-8")
    print(f"Listening checklist: {args.out}")
    return 0


def build_listening_checklist(smoke_dir: Path) -> str:
    """Return a markdown checklist for human sign-off."""
    audit = _load_optional_json(smoke_dir / "audit_report.json")
    manifest = _load_optional_json(smoke_dir / "chunks_manifest_v2.json")
    chunks = manifest.get("chapters", [{}])[0].get("chunks", []) if manifest else []
    audio_path = smoke_dir / "chapter_001.wav"
    duration = audit.get("wav", {}).get("duration_seconds", "unknown")
    bad_terms = audit.get("bad_front_matter_terms", [])
    chunk_lines = [
        f"{index}. {str(chunk.get('text', '')).strip()[:220]}"
        for index, chunk in enumerate(chunks, start=1)
    ]
    chunk_preview = "\n".join(chunk_lines) if chunk_lines else "- No manifest chunks found."
    bad_terms_text = ", ".join(bad_terms) if bad_terms else "none detected"

    return f"""# Manual Listening Checklist

Audio file: `{audio_path}`
Duration: `{duration}` seconds
Automated front-matter terms: `{bad_terms_text}`

## Expected Text

{chunk_preview}

## Listen-Through Criteria

- [ ] The sample starts with useful book content, not library or publisher front matter.
- [ ] The spoken words match the manifest text closely enough for audiobook use.
- [ ] No obvious clipping, harsh distortion, repeated loops, or long accidental silence.
- [ ] Chapter/title/narration pacing is understandable and not rushed.
- [ ] Pauses between the two smoke chunks sound acceptable.
- [ ] The voice is acceptable for a narrator smoke test.

## Verdict

- [ ] PASS: ready to use this path for a longer acceptance run.
- [ ] REVIEW: keep the pipeline, but adjust voice/settings before a full book.
- [ ] FAIL: fix synthesis, chunking, or text cleanup before continuing.

Notes:

"""


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
