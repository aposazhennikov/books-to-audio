from __future__ import annotations

import json
from pathlib import Path

import pytest

from book_normalizer.gui.normalization_cache import (
    CachedNormalization,
    NormalizationCacheSettings,
    cache_path_for,
    find_any_cached_normalization,
    find_cached_normalization,
    load_cached_book,
    save_cached_book,
)
from book_normalizer.models.book import Book, Chapter, Metadata, Paragraph


def _settings(**overrides: object) -> NormalizationCacheSettings:
    values = {
        "source_format": "txt",
        "book_language": "ru",
        "ocr_mode": "off",
        "ocr_dpi": 0,
        "ocr_psm": 0,
        "llm_normalize": True,
        "llm_endpoint": "http://localhost:11434/v1",
        "llm_model": "hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M",
    }
    values.update(overrides)
    return NormalizationCacheSettings(**values)


def _book() -> Book:
    return Book(
        metadata=Metadata(title="Cached", language="ru", source_format="txt"),
        chapters=[
            Chapter(
                title="Chapter",
                index=0,
                paragraphs=[
                    Paragraph(
                        raw_text="Исходный текст.",
                        normalized_text="Нормализованный текст.",
                        index_in_chapter=0,
                    ),
                ],
            ),
        ],
    )


def test_normalization_cache_round_trips_completed_book(tmp_path: Path) -> None:
    source = tmp_path / "book.txt"
    source.write_text("source text", encoding="utf-8")
    cache_root = tmp_path / "cache"

    entry = save_cached_book(_book(), source, _settings(), cache_root=cache_root)
    found = find_cached_normalization(source, _settings(), cache_root=cache_root)
    restored = load_cached_book(found)

    assert found == entry
    assert restored.metadata.title == "Cached"
    assert restored.chapters[0].paragraphs[0].normalized_text == "Нормализованный текст."


def test_normalization_cache_key_uses_file_contents_not_path(tmp_path: Path) -> None:
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("same content", encoding="utf-8")
    second.write_text("same content", encoding="utf-8")
    cache_root = tmp_path / "cache"

    save_cached_book(_book(), first, _settings(), cache_root=cache_root)

    assert find_cached_normalization(second, _settings(), cache_root=cache_root) is not None


def test_normalization_cache_misses_when_settings_change(tmp_path: Path) -> None:
    source = tmp_path / "book.txt"
    source.write_text("source text", encoding="utf-8")
    cache_root = tmp_path / "cache"

    save_cached_book(_book(), source, _settings(book_language="ru"), cache_root=cache_root)

    assert find_cached_normalization(source, _settings(book_language="en"), cache_root=cache_root) is None


def test_normalization_cache_can_find_source_entry_ignoring_settings(tmp_path: Path) -> None:
    source = tmp_path / "book.txt"
    source.write_text("source text", encoding="utf-8")
    cache_root = tmp_path / "cache"
    entry = save_cached_book(
        _book(),
        source,
        _settings(book_language="ru"),
        cache_root=cache_root,
    )

    assert find_cached_normalization(source, _settings(book_language="en"), cache_root=cache_root) is None
    assert find_any_cached_normalization(source, cache_root=cache_root) == entry


def test_normalization_cache_normalizes_llm_endpoint_suffix(tmp_path: Path) -> None:
    source = tmp_path / "book.txt"
    source.write_text("source text", encoding="utf-8")
    cache_root = tmp_path / "cache"

    path_with_v1 = cache_path_for(source, _settings(llm_endpoint="http://localhost:11434/v1"), cache_root=cache_root)
    path_without_v1 = cache_path_for(source, _settings(llm_endpoint="http://localhost:11434"), cache_root=cache_root)

    assert path_with_v1 == path_without_v1


def test_normalization_cache_ignores_host_ocr_availability_in_key(tmp_path: Path) -> None:
    source = tmp_path / "book.pdf"
    source.write_text("source text", encoding="utf-8")
    cache_root = tmp_path / "cache"

    available = cache_path_for(
        source,
        _settings(
            source_format="pdf",
            ocr_mode="auto",
            ocr_dpi=600,
            ocr_psm=3,
            tesseract_available=True,
            tesseract_language_available=True,
        ),
        cache_root=cache_root,
    )
    unchecked = cache_path_for(
        source,
        _settings(
            source_format="pdf",
            ocr_mode="auto",
            ocr_dpi=600,
            ocr_psm=3,
            tesseract_available=None,
            tesseract_language_available=None,
        ),
        cache_root=cache_root,
    )

    assert available == unchecked


def test_normalization_cache_finds_legacy_entry_with_compatible_settings(
    tmp_path: Path,
) -> None:
    source = tmp_path / "book.pdf"
    source.write_text("source text", encoding="utf-8")
    cache_root = tmp_path / "cache"
    settings = _settings(
        source_format="pdf",
        ocr_mode="auto",
        ocr_dpi=600,
        ocr_psm=3,
        tesseract_available=True,
        tesseract_language_available=True,
    )
    entry = save_cached_book(_book(), source, settings, cache_root=cache_root)
    legacy_path = cache_root / "legacy-environment-sensitive-key.json"
    entry.path.rename(legacy_path)

    found = find_cached_normalization(
        source,
        _settings(
            source_format="pdf",
            ocr_mode="auto",
            ocr_dpi=600,
            ocr_psm=3,
            tesseract_available=False,
            tesseract_language_available=False,
        ),
        cache_root=cache_root,
    )

    assert found == CachedNormalization(key=entry.key, path=legacy_path)
    assert load_cached_book(found).metadata.title == "Cached"


def test_normalization_cache_rejects_corrupt_envelope(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"schema_version": 999, "cache_key": "bad"}), encoding="utf-8")

    with pytest.raises(ValueError, match="schema"):
        load_cached_book(CachedNormalization(key="bad", path=path))
