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
    "source_preview",
    "output_preview",
    "before_text",
    "after_text",
    "first_paragraph",
    "last_paragraph",
    "prompt",
    "paragraphs",
    "content",
}
TEXT_KEY_SUFFIXES = ("_text", "_preview")
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
REDACTED_SECRET = "<REDACTED_SECRET>"

ALLOWED_ROOT_FILE_NAMES = {
    "anomaly_report.txt",
    "artifact_qa_report.json",
    "asr_qa_report.json",
    "audio_qa_report.json",
    "audiobook_package_report.json",
    "audit_report.json",
    "casting_plan.json",
    "chapter_sanity_report.txt",
    "chunks_manifest_v2.json",
    "debug.log",
    "director_score.json",
    "final_readiness_report.json",
    "llm_voice_review_report.json",
    "live_tts_smoke_report.json",
    "mastering_report.json",
    "missing_headings.txt",
    "package_qa_report.json",
    "production_qa_report.json",
    "production_run_report.json",
    "quality_report.json",
    "random_sample_review.txt",
    "report.json",
    "roles_manifest.json",
    "run.log",
    "run_contract.json",
    "segments_manifest.json",
    "stats_before_after.json",
    "suspicious_changes.json",
    "synthesis_manifest.json",
    "test_manifest.json",
    "voice_overrides.json",
}
ALLOWED_DIR_FILE_NAMES = {
    "audiobook_package": {
        "audiobook_package_report.json",
        "package_qa_report.json",
        "checksums.sha256",
        "chapters.concat.txt",
        "chapters.ffmetadata",
    },
    "logs": {"*.jsonl"},
    "reports": {"*_report.json"},
}
SECRET_EXACT_KEYS = {
    "authorization",
    "api_key",
    "api-key",
    "apikey",
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
}
SECRET_TOKEN_KEYS = {
    "access_token",
    "auth_token",
    "bearer_token",
    "client_token",
    "id_token",
    "refresh_token",
    "session_token",
}
NON_SECRET_TOKEN_KEYS = {
    "completion_tokens",
    "generated_tokens",
    "input_tokens",
    "max_new_tokens",
    "max_tokens",
    "min_new_tokens",
    "output_tokens",
    "prompt_tokens",
    "token_count",
    "tokens_per_second",
    "total_tokens",
}
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(authorization|api[_-]?key|access[_-]?token|auth[_-]?token|bearer[_-]?token|client[_-]?secret|"
    r"client[_-]?token|id[_-]?token|refresh[_-]?token|session[_-]?token|password|passwd|pwd|secret|token)\b"
    r"(\s*[:=]\s*)(?:Bearer\s+)?[^\s\"',;]+"
)
BEARER_TOKEN_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")


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
            if _is_secret_key(normalized_key):
                redacted[key] = REDACTED_SECRET
            elif _is_book_text_key(normalized_key):
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


def _is_book_text_key(normalized_key: str) -> bool:
    return normalized_key in TEXT_KEYS or normalized_key.endswith(TEXT_KEY_SUFFIXES)


def _is_secret_key(normalized_key: str) -> bool:
    key = normalized_key.strip()
    compact = re.sub(r"[^a-z0-9]+", "_", key).strip("_")
    collapsed = compact.replace("_", "")
    if key in SECRET_EXACT_KEYS or compact in SECRET_EXACT_KEYS or collapsed in SECRET_EXACT_KEYS:
        return True
    if compact in NON_SECRET_TOKEN_KEYS:
        return False
    if compact in SECRET_TOKEN_KEYS:
        return True
    return "secret" in compact or "password" in compact or compact.endswith("_token")


def redact_text(value: str, *, root: Path | None = None) -> str:
    """Redact secrets, absolute paths, and project-private paths from plain text."""
    redacted = _redact_secret_text(value)
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


def _redact_secret_text(value: str) -> str:
    redacted = SECRET_ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}{match.group(2)}{REDACTED_SECRET}", value)
    return BEARER_TOKEN_RE.sub(f"Bearer {REDACTED_SECRET}", redacted)


def _candidate_files(source_dir: Path, *, include_logs: bool, include_json: bool) -> list[Path]:
    found: dict[Path, None] = {}
    for path in _safe_walk(source_dir):
        if (
            path.is_file()
            and DEFAULT_SUPPORT_BUNDLE_NAME not in path.name
            and _is_allowed_candidate(path, source_dir, include_logs=include_logs, include_json=include_json)
        ):
            found[path] = None
    return sorted(found)


def _safe_walk(root: Path) -> list[Path]:
    pending = [root]
    found: list[Path] = []
    while pending:
        directory = pending.pop()
        try:
            children = sorted(directory.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_symlink():
                continue
            if child.is_dir():
                if child.name.lower() not in PRIVATE_DIR_NAMES:
                    pending.append(child)
                continue
            found.append(child)
    return found


def _is_allowed_candidate(path: Path, root: Path, *, include_logs: bool, include_json: bool) -> bool:
    if not _suffix_enabled(path, include_logs=include_logs, include_json=include_json):
        return False
    rel = path.relative_to(root)
    if len(rel.parts) == 1:
        return path.name in ALLOWED_ROOT_FILE_NAMES
    parent = rel.parts[0]
    allowed_names = ALLOWED_DIR_FILE_NAMES.get(parent)
    if allowed_names is None:
        return False
    return any(path.match(pattern) for pattern in allowed_names)


def _suffix_enabled(path: Path, *, include_logs: bool, include_json: bool) -> bool:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return include_json
    if suffix in {".log", ".txt", ".jsonl", ".sha256", ".ffmetadata"}:
        return include_logs
    return False


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
        "were replaced before packaging. Plain .txt files are not included because they can contain "
        "book extracts. Do not add original books, audio output, data folders, model caches, or .env "
        "files to support requests.\n"
    )
