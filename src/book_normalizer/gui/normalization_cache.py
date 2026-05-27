"""Persistent cache for completed GUI normalization runs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha1
from pathlib import Path
from typing import Any

from book_normalizer.models.book import Book

CACHE_SCHEMA_VERSION = 2
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
    pdf_text_variant: str | None = None

    def to_key_record(self) -> dict[str, Any]:
        """Return a normalized settings record suitable for cache keys."""
        source_format = self.source_format.lower().strip(".")
        ocr_mode = self.ocr_mode
        ocr_dpi = int(self.ocr_dpi)
        ocr_psm = int(self.ocr_psm)
        pdf_text_variant = (self.pdf_text_variant or "").strip().lower()
        if source_format == "pdf" and pdf_text_variant == "native":
            ocr_dpi = 0
            ocr_psm = 0
        llm_endpoint = _normalize_endpoint(self.llm_endpoint) if self.llm_normalize else ""
        llm_model = self.llm_model.strip() if self.llm_normalize else ""
        record = {
            "source_format": source_format,
            "book_language": self.book_language,
            "ocr_mode": ocr_mode,
            "ocr_dpi": ocr_dpi,
            "ocr_psm": ocr_psm,
            "llm_normalize": bool(self.llm_normalize),
            "llm_endpoint": llm_endpoint,
            "llm_model": llm_model,
        }
        if source_format == "pdf":
            record["pdf_text_variant"] = pdf_text_variant
        return record


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
    if path.exists() and _cache_envelope_matches(path, path.stem):
        return CachedNormalization(key=path.stem, path=path)
    return _find_compatible_cached_normalization(
        source_path,
        settings,
        cache_root=cache_root,
    )


def find_any_cached_normalization(
    source_path: Path,
    *,
    cache_root: Path | None = None,
) -> CachedNormalization | None:
    """Return the newest completed cache entry for the source file."""
    root = cache_root or CACHE_ROOT
    if not root.exists():
        return None

    source_digest = _file_sha1(source_path)
    for candidate in sorted(root.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("schema_version") != CACHE_SCHEMA_VERSION:
            continue
        source = payload.get("source")
        if not isinstance(source, dict) or source.get("sha1") != source_digest:
            continue
        cache_key = payload.get("cache_key")
        if not isinstance(cache_key, str) or not cache_key:
            continue
        return CachedNormalization(key=cache_key, path=candidate)
    return None


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


def _cache_envelope_matches(path: Path, expected_key: str) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        payload.get("schema_version") == CACHE_SCHEMA_VERSION
        and payload.get("cache_key") == expected_key
    )


def _find_compatible_cached_normalization(
    source_path: Path,
    settings: NormalizationCacheSettings,
    *,
    cache_root: Path | None = None,
) -> CachedNormalization | None:
    """Find compatible legacy cache entries that used older key material."""
    root = cache_root or CACHE_ROOT
    if not root.exists():
        return None

    source_digest = _file_sha1(source_path)
    settings_record = settings.to_key_record()
    for candidate in sorted(root.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("schema_version") != CACHE_SCHEMA_VERSION:
            continue
        source = payload.get("source")
        if not isinstance(source, dict) or source.get("sha1") != source_digest:
            continue
        payload_settings = _payload_settings_record(payload.get("settings"))
        if payload_settings is None or not _settings_records_compatible(
            payload_settings,
            settings_record,
        ):
            continue
        cache_key = payload.get("cache_key")
        if not isinstance(cache_key, str) or not cache_key:
            continue
        return CachedNormalization(key=cache_key, path=candidate)
    return None


def _payload_settings_record(raw_settings: object) -> dict[str, Any] | None:
    """Normalize persisted settings for compatibility checks."""
    if not isinstance(raw_settings, dict):
        return None
    try:
        return NormalizationCacheSettings(
            source_format=str(raw_settings.get("source_format", "")),
            book_language=str(raw_settings.get("book_language", "")),
            ocr_mode=str(raw_settings.get("ocr_mode", "")),
            ocr_dpi=int(raw_settings.get("ocr_dpi") or 0),
            ocr_psm=int(raw_settings.get("ocr_psm") or 0),
            llm_normalize=bool(raw_settings.get("llm_normalize")),
            llm_endpoint=str(raw_settings.get("llm_endpoint", "")),
            llm_model=str(raw_settings.get("llm_model", "")),
            pdf_text_variant=str(raw_settings.get("pdf_text_variant") or ""),
        ).to_key_record()
    except (TypeError, ValueError):
        return None


def _settings_records_compatible(
    cached_record: dict[str, Any],
    current_record: dict[str, Any],
) -> bool:
    """Return true when records produce the same normalized text."""
    if cached_record == current_record:
        return True

    if (
        cached_record.get("source_format") == "pdf"
        and current_record.get("source_format") == "pdf"
        and cached_record.get("pdf_text_variant")
        and not current_record.get("pdf_text_variant")
    ):
        cached_without_variant = dict(cached_record)
        cached_without_variant["pdf_text_variant"] = ""
        if cached_without_variant == current_record:
            return True

    if (
        cached_record.get("source_format") == "pdf"
        and current_record.get("source_format") == "pdf"
        and cached_record.get("pdf_text_variant") == "native"
    ):
        cached_neutral = dict(cached_record)
        current_neutral = dict(current_record)
        for record in (cached_neutral, current_neutral):
            record["ocr_dpi"] = 0
            record["ocr_psm"] = 0
            record["pdf_text_variant"] = "native"
        return cached_neutral == current_neutral

    return False


def _normalize_endpoint(endpoint: str) -> str:
    value = (endpoint or "").strip().rstrip("/")
    if value.endswith("/v1"):
        value = value[:-3].rstrip("/")
    return value
