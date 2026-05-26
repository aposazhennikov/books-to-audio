"""Persistent cache for completed GUI normalization runs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha1
from pathlib import Path
from typing import Any

from book_normalizer.models.book import Book

CACHE_SCHEMA_VERSION = 1
CACHE_ROOT = Path("data") / "user_memory" / "normalization_cache"


@dataclass(frozen=True)
class NormalizationCacheSettings:
    """Settings that affect the normalized book produced by the GUI pipeline."""

    source_format: str
    book_language: str
    ocr_mode: str
    ocr_dpi: int
    ocr_psm: int
    llm_normalize: bool
    llm_endpoint: str
    llm_model: str
    tesseract_available: bool | None = None
    tesseract_language_available: bool | None = None

    def to_key_record(self) -> dict[str, Any]:
        """Return a normalized settings record suitable for cache keys."""
        llm_endpoint = _normalize_endpoint(self.llm_endpoint) if self.llm_normalize else ""
        llm_model = self.llm_model.strip() if self.llm_normalize else ""
        return {
            "source_format": self.source_format.lower().strip("."),
            "book_language": self.book_language,
            "ocr_mode": self.ocr_mode,
            "ocr_dpi": int(self.ocr_dpi),
            "ocr_psm": int(self.ocr_psm),
            "llm_normalize": bool(self.llm_normalize),
            "llm_endpoint": llm_endpoint,
            "llm_model": llm_model,
            "tesseract_available": self.tesseract_available,
            "tesseract_language_available": self.tesseract_language_available,
        }


@dataclass(frozen=True)
class CachedNormalization:
    """A completed normalization cache entry found on disk."""

    key: str
    path: Path


def find_cached_normalization(
    source_path: Path,
    settings: NormalizationCacheSettings,
    *,
    cache_root: Path | None = None,
) -> CachedNormalization | None:
    """Return a cache entry for the source/settings pair when one exists."""
    path = cache_path_for(source_path, settings, cache_root=cache_root)
    if not path.exists():
        return None
    return CachedNormalization(key=path.stem, path=path)


def cache_path_for(
    source_path: Path,
    settings: NormalizationCacheSettings,
    *,
    cache_root: Path | None = None,
) -> Path:
    """Return the JSON path for a source/settings pair."""
    key = cache_key_for(source_path, settings)
    return (cache_root or CACHE_ROOT) / f"{key}.json"


def cache_key_for(source_path: Path, settings: NormalizationCacheSettings) -> str:
    """Return a stable cache key based on file contents and normalization settings."""
    payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "source_sha1": _file_sha1(source_path),
        "settings": settings.to_key_record(),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha1(encoded.encode("utf-8")).hexdigest()[:24]


def load_cached_book(entry: CachedNormalization) -> Book:
    """Load a cached book and validate the cache envelope."""
    payload = json.loads(entry.path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != CACHE_SCHEMA_VERSION:
        raise ValueError("Unsupported normalization cache schema")
    if payload.get("cache_key") != entry.key:
        raise ValueError("Normalization cache key mismatch")
    book_payload = payload.get("book")
    if not isinstance(book_payload, dict):
        raise ValueError("Normalization cache does not contain a book")
    return Book.model_validate(book_payload)


def save_cached_book(
    book: Book,
    source_path: Path,
    settings: NormalizationCacheSettings,
    *,
    cache_root: Path | None = None,
) -> CachedNormalization:
    """Persist a completed normalized book and return the written cache entry."""
    root = cache_root or CACHE_ROOT
    key = cache_key_for(source_path, settings)
    path = root / f"{key}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    source = Path(source_path)
    stat = source.stat()
    payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "cache_key": key,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "name": source.name,
            "suffix": source.suffix.lower(),
            "size": stat.st_size,
            "sha1": _file_sha1(source),
        },
        "settings": asdict(settings),
        "book": book.model_dump(mode="json"),
    }
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_path.replace(path)
    return CachedNormalization(key=key, path=path)


def _file_sha1(path: Path) -> str:
    digest = sha1()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_endpoint(endpoint: str) -> str:
    value = (endpoint or "").strip().rstrip("/")
    if value.endswith("/v1"):
        value = value[:-3].rstrip("/")
    return value
