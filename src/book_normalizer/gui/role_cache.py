"""Persistent cache for completed GUI role extraction runs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha1
from pathlib import Path
from typing import Any

CACHE_SCHEMA_VERSION = 1
CACHE_ROOT = Path("data") / "user_memory" / "role_cache"
REVIEW_REPORT_NAME = "llm_voice_review_report.json"
ROLES_MANIFEST_NAME = "roles_manifest.json"
SEGMENTS_MANIFEST_NAME = "segments_manifest.json"


@dataclass(frozen=True)
class RoleCacheSettings:
    """Settings that affect GUI role extraction output."""

    book_language: str
    speaker_mode: str
    llm_endpoint: str
    llm_model: str
    stress_mode: str

    def to_key_record(self) -> dict[str, Any]:
        """Return normalized settings suitable for a cache key."""
        return {
            "book_language": self.book_language,
            "speaker_mode": self.speaker_mode,
            "llm_endpoint": _normalize_endpoint(self.llm_endpoint),
            "llm_model": self.llm_model.strip(),
            "stress_mode": self.stress_mode,
        }


@dataclass(frozen=True)
class CachedRoleExtraction:
    """A completed role extraction cache entry found on disk."""

    key: str
    path: Path

    @property
    def segments_path(self) -> Path:
        return self.path / SEGMENTS_MANIFEST_NAME

    @property
    def roles_path(self) -> Path:
        return self.path / ROLES_MANIFEST_NAME

    @property
    def review_report_path(self) -> Path:
        return self.path / REVIEW_REPORT_NAME


def find_cached_roles(
    book: object,
    settings: RoleCacheSettings,
    *,
    cache_root: Path | None = None,
) -> CachedRoleExtraction | None:
    """Return a cache entry for the book/settings pair when one exists."""
    path = cache_path_for(book, settings, cache_root=cache_root)
    entry = CachedRoleExtraction(key=path.name, path=path)
    if entry.segments_path.exists() and entry.roles_path.exists():
        return entry
    return None


def cache_path_for(
    book: object,
    settings: RoleCacheSettings,
    *,
    cache_root: Path | None = None,
) -> Path:
    """Return the cache directory for a book/settings pair."""
    return (cache_root or CACHE_ROOT) / cache_key_for(book, settings)


def cache_key_for(book: object, settings: RoleCacheSettings) -> str:
    """Return a stable cache key based on normalized book text and role settings."""
    payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "book_sha1": _book_sha1(book),
        "settings": settings.to_key_record(),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha1(encoded.encode("utf-8")).hexdigest()[:24]


def save_role_cache(
    book: object,
    settings: RoleCacheSettings,
    segments_path: Path,
    roles_path: Path,
    *,
    review_report_path: Path | None = None,
    cache_root: Path | None = None,
) -> CachedRoleExtraction:
    """Persist completed role extraction manifests."""
    segments = _load_json(segments_path)
    roles = _load_json(roles_path)
    if not isinstance(segments, list):
        raise ValueError("segments manifest must be a JSON array")
    if not isinstance(roles, dict):
        raise ValueError("roles manifest must be a JSON object")

    root = cache_root or CACHE_ROOT
    key = cache_key_for(book, settings)
    path = root / key
    path.mkdir(parents=True, exist_ok=True)
    (path / SEGMENTS_MANIFEST_NAME).write_text(
        json.dumps(segments, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (path / ROLES_MANIFEST_NAME).write_text(
        json.dumps(roles, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    cached_review = path / REVIEW_REPORT_NAME
    if review_report_path is not None and review_report_path.exists():
        report = _load_json(review_report_path)
        cached_review.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        cached_review.unlink(missing_ok=True)
    metadata = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "cache_key": key,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "settings": asdict(settings),
        "book_sha1": _book_sha1(book),
    }
    (path / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return CachedRoleExtraction(key=key, path=path)


def restore_role_cache(
    entry: CachedRoleExtraction,
    output_dir: Path,
) -> tuple[Path, Path]:
    """Copy cached role manifests into the current output directory."""
    segments = _load_json(entry.segments_path)
    roles = _load_json(entry.roles_path)
    if not isinstance(segments, list):
        raise ValueError("cached segments manifest must be a JSON array")
    if not isinstance(roles, dict):
        raise ValueError("cached roles manifest must be a JSON object")

    output_dir.mkdir(parents=True, exist_ok=True)
    segments_path = output_dir / SEGMENTS_MANIFEST_NAME
    roles_path = output_dir / ROLES_MANIFEST_NAME
    segments_path.write_text(
        json.dumps(segments, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    roles_path.write_text(
        json.dumps(roles, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    target_review = output_dir / REVIEW_REPORT_NAME
    if entry.review_report_path.exists():
        report = _load_json(entry.review_report_path)
        target_review.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        target_review.unlink(missing_ok=True)
    return segments_path, roles_path


def _book_sha1(book: object) -> str:
    metadata = getattr(book, "metadata", None)
    language = str(getattr(metadata, "language", "") or "")
    chapters_payload: list[dict[str, Any]] = []
    for chapter in getattr(book, "chapters", []):
        paragraphs = [
            {
                "index": getattr(para, "index_in_chapter", 0),
                "text": getattr(para, "normalized_text", "") or getattr(para, "raw_text", ""),
            }
            for para in getattr(chapter, "paragraphs", [])
        ]
        chapters_payload.append(
            {
                "index": getattr(chapter, "index", 0),
                "title": getattr(chapter, "title", ""),
                "paragraphs": paragraphs,
            }
        )
    payload = {"language": language, "chapters": chapters_payload}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha1(encoded.encode("utf-8")).hexdigest()


def _load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _normalize_endpoint(endpoint: str) -> str:
    value = (endpoint or "").strip().rstrip("/")
    if value.endswith("/v1"):
        value = value[:-3].rstrip("/")
    return value
