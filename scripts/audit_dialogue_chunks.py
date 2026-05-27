#!/usr/bin/env python3
"""Audit v2 chunk manifests for likely dialogue/narration boundary leaks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from book_normalizer.chunking.dialogue_invariants import (  # noqa: E402
    audit_dialogue_chunk_boundaries,
    audit_dialogue_speaker_assignments,
    format_dialogue_chunk_issues,
    format_dialogue_speaker_issues,
)
from book_normalizer.chunking.manifest_v2 import flatten_manifest, load_manifest  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check a v2 chunks manifest for mixed dialogue/narration chunks."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--language", default="")
    parser.add_argument(
        "--include-speaker-warnings",
        action="store_true",
        help="Also print non-fatal dialogue speaker/voice assignment warnings.",
    )
    parser.add_argument(
        "--fail-on-speaker-warnings",
        action="store_true",
        help="Return a non-zero exit code when speaker warnings are found.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable issues.")
    args = parser.parse_args(argv)

    manifest = load_manifest(args.manifest)
    language = args.language or manifest.language
    chunks = flatten_manifest(manifest)
    issues = audit_dialogue_chunk_boundaries(chunks, language=language)
    speaker_warnings = (
        audit_dialogue_speaker_assignments(chunks, language=language)
        if args.include_speaker_warnings or args.fail_on_speaker_warnings
        else []
    )

    if args.json:
        print(json.dumps(
            {
                "boundary_issues": [issue.__dict__ for issue in issues],
                "speaker_warnings": [warning.__dict__ for warning in speaker_warnings],
            },
            ensure_ascii=False,
            indent=2,
        ))
    elif issues:
        print(format_dialogue_chunk_issues(issues))
    else:
        print("Dialogue chunk boundary audit passed.")
    if not args.json and speaker_warnings:
        print(format_dialogue_speaker_issues(speaker_warnings))

    return 1 if issues or (speaker_warnings and args.fail_on_speaker_warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
