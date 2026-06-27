"""Redacted support bundle generation."""

from __future__ import annotations

import json
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TEXT_KEYS = {
    "text",
    "raw_text",
    "normalized_text",
    "original_text",
    "ref_text",
    "prompt",
    "paragraphs",
    "content",
}
PATH_KEYS = {
    "path",
    "source_path",
    "audio_file",
    "output_path",
    "report_path",
    "manifest_path",
    "cache_dir",
    "models_dir",
}
PRIVATE_DIR_NAMES = {"books", "output", "data"}
DEFAULT_SUPPORT_BUNDLE_NAME = "support_bundle_redacted.zip"


@dataclass(frozen=True)
class SupportBundleResult:
    """Support bundle output."""

    bundle_path: Path
    files: list[str] = field(default_factory=list)


def create_support_bundle(
    source_dir: Path,
    *,
    output_path: Path | None = None,
    include_logs: bool = True,
    include_json: bool = True,
) -> SupportBundleResult:
    """Create a zip with redacted diagnostics from a run directory."""
    source_dir = source_dir.resolve()
    target = output_path or source_dir / DEFAULT_SUPPORT_BUNDLE_NAME
    files = _candidate_files(source_dir, include_logs=include_logs, include_json=include_json)
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_dir": "<PRIVATE_PATH>",
        "redaction": {
            "book_text_fields": sorted(TEXT_KEYS),
            "private_dirs": sorted(PRIVATE_DIR_NAMES),
            "private_paths": "replaced with <PRIVATE_PATH>",
        },
        "files": [str(path.relative_to(source_dir)).replace("\\", "/") for path in files],
    }

    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.txt", _bundle_readme())
        archive.writestr("support_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for path in files:
            rel = str(path.relative_to(source_dir)).replace("\\", "/")
            archive.writestr(rel, _redacted_file_bytes(path, source_dir))
    return SupportBundleResult(bundle_path=target, files=manifest["files"])


def redact_payload(value: Any, *, root: Path | None = None) -> Any:
    """Redact book text and private paths from JSON-compatible data."""
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = str(key).lower()
            if normalized_key in TEXT_KEYS:
                redacted[key] = "<REDACTED_BOOK_TEXT>"
            elif normalized_key in PATH_KEYS:
                redacted[key] = redact_text(str(item), root=root)
            else:
                redacted[key] = redact_payload(item, root=root)
        return redacted
    if isinstance(value, list):
        return [redact_payload(item, root=root) for item in value]
    if isinstance(value, str):
        return redact_text(value, root=root)
    return value


def redact_text(value: str, *, root: Path | None = None) -> str:
    """Redact absolute and project-private paths from plain text."""
    redacted = value
    candidates = [Path.home()]
    if root is not None:
        candidates.append(root)
    for candidate in candidates:
        try:
            text = str(candidate.resolve())
        except OSError:
            text = str(candidate)
        if text:
            redacted = redacted.replace(text, "<PRIVATE_PATH>")
            redacted = redacted.replace(text.replace("\\", "/"), "<PRIVATE_PATH>")
    redacted = re.sub(
        r"(?i)([A-Z]:)?[\\/][^\s\"']*(?:books|output|data)[\\/][^\s\"']+",
        "<PRIVATE_PATH>",
        redacted,
    )
    redacted = re.sub(
        r"(?i)(?:^|[\\/])(?:books|output|data)[\\/][^\s\"']+",
        "<PRIVATE_PATH>",
        redacted,
    )
    return redacted


def _candidate_files(source_dir: Path, *, include_logs: bool, include_json: bool) -> list[Path]:
    patterns: list[str] = []
    if include_json:
        patterns.extend(
            [
                "*.json",
                "*report*.json",
                "*manifest*.json",
            ]
        )
    if include_logs:
        patterns.extend(["*.log", "*.txt"])
    found: dict[Path, None] = {}
    for pattern in patterns:
        for path in source_dir.rglob(pattern):
            if path.is_file() and DEFAULT_SUPPORT_BUNDLE_NAME not in path.name:
                found[path] = None
    return sorted(found)


def _redacted_file_bytes(path: Path, root: Path) -> bytes:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return redact_text(raw, root=root).encode("utf-8")
        return json.dumps(redact_payload(payload, root=root), ensure_ascii=False, indent=2).encode("utf-8")
    return redact_text(raw, root=root).encode("utf-8")


def _bundle_readme() -> str:
    return (
        "Redacted Books to Audio support bundle.\n\n"
        "This archive is intended for diagnostics only. Book text fields and private local paths "
        "were replaced before packaging. Do not add original books, audio output, data folders, "
        "model caches, or .env files to support requests.\n"
    )
