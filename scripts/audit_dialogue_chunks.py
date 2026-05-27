#!/usr/bin/env python3
"""Audit v2 chunk manifests for likely dialogue/narration boundary leaks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from book_normalizer.chunking.dialogue_invariants import audit_dialogue_chunk_boundaries  # noqa: E402
from book_normalizer.chunking.manifest_v2 import flatten_manifest, load_manifest  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check a v2 chunks manifest for mixed dialogue/narration chunks."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--language", default="")
    parser.add_argument("--json", action="store_true", help="Print machine-readable issues.")
    args = parser.parse_args(argv)

    manifest = load_manifest(args.manifest)
    language = args.language or manifest.language
    issues = audit_dialogue_chunk_boundaries(
        flatten_manifest(manifest),
        language=language,
    )

    if args.json:
        print(json.dumps([issue.__dict__ for issue in issues], ensure_ascii=False, indent=2))
    elif issues:
        for issue in issues:
            print(
                f"{issue.kind}: chapter={issue.chapter_index + 1} "
                f"chunk={issue.chunk_index + 1} role={issue.role} text={issue.text!r}"
            )
    else:
        print("Dialogue chunk boundary audit passed.")

    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
