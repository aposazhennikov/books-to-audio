from __future__ import annotations

import json
from pathlib import Path

import pytest

from book_normalizer.gui.role_cache import (
    CachedRoleExtraction,
    RoleCacheSettings,
    cache_path_for,
    cached_role_entry_from_output_dir,
    find_any_cached_roles,
    find_cached_roles,
    restore_role_cache,
    save_role_cache,
)
from book_normalizer.models.book import Book, Chapter, Metadata, Paragraph


def _settings(**overrides: object) -> RoleCacheSettings:
    values = {
        "book_language": "ru",
        "speaker_mode": "llm",
        "llm_endpoint": "http://localhost:11434/v1",
        "llm_model": "hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M",
        "stress_mode": "double_vowel",
    }
    values.update(overrides)
    return RoleCacheSettings(**values)


def _book(*, text: str = "Normalized text.", language: str = "ru") -> Book:
    return Book(
        metadata=Metadata(language=language),
        chapters=[
            Chapter(
                title="Chapter",
                index=0,
                paragraphs=[
                    Paragraph(
                        raw_text="Raw text.",
                        normalized_text=text,
                        index_in_chapter=0,
                    ),
                ],
            ),
        ],
    )


def _write_manifests(path: Path) -> tuple[Path, Path]:
    segments_path = path / "segments_manifest.json"
    roles_path = path / "roles_manifest.json"
    segments_path.write_text(
        json.dumps(
            [
                {
                    "segment_index": 0,
                    "chapter_index": 0,
                    "speaker": "Alice",
                    "text": "Hello.",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    roles_path.write_text(
        json.dumps(
            {
                "roles": [
                    {
                        "display_name": "Alice",
                        "segment_count": 1,
                        "direct_speech_count": 1,
                    }
                ],
                "total_segments": 1,
                "total_direct_speech": 1,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return segments_path, roles_path


def test_role_cache_round_trips_manifests_and_review_report(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    segments_path, roles_path = _write_manifests(source_dir)
    review_path = source_dir / "llm_voice_review_report.json"
    review_path.write_text('{"requires_human_review": true}', encoding="utf-8")
    cache_root = tmp_path / "cache"

    entry = save_role_cache(
        _book(),
        _settings(),
        segments_path,
        roles_path,
        review_report_path=review_path,
        cache_root=cache_root,
    )
    found = find_cached_roles(_book(), _settings(), cache_root=cache_root)
    output_dir = tmp_path / "restored"
    restored_segments, restored_roles = restore_role_cache(found, output_dir)

    assert found == entry
    assert restored_segments == output_dir / "segments_manifest.json"
    assert restored_roles == output_dir / "roles_manifest.json"
    assert json.loads(restored_segments.read_text(encoding="utf-8"))[0]["speaker"] == "Alice"
    assert json.loads(restored_roles.read_text(encoding="utf-8"))["roles"][0]["display_name"] == "Alice"
    assert (output_dir / "llm_voice_review_report.json").exists()


def test_role_cache_key_uses_normalized_book_text_and_settings(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    segments_path, roles_path = _write_manifests(source_dir)
    cache_root = tmp_path / "cache"

    save_role_cache(
        _book(text="Same normalized text."),
        _settings(book_language="ru"),
        segments_path,
        roles_path,
        cache_root=cache_root,
    )

    assert find_cached_roles(
        _book(text="Same normalized text."),
        _settings(book_language="ru"),
        cache_root=cache_root,
    ) is not None
    assert find_cached_roles(
        _book(text="Changed normalized text."),
        _settings(book_language="ru"),
        cache_root=cache_root,
    ) is None
    assert find_cached_roles(
        _book(text="Same normalized text."),
        _settings(book_language="en"),
        cache_root=cache_root,
    ) is None


def test_role_cache_can_find_book_entry_ignoring_settings(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    segments_path, roles_path = _write_manifests(source_dir)
    cache_root = tmp_path / "cache"
    book = _book(text="Same normalized text.")
    entry = save_role_cache(
        book,
        _settings(book_language="ru"),
        segments_path,
        roles_path,
        cache_root=cache_root,
    )

    assert find_cached_roles(
        book,
        _settings(book_language="en"),
        cache_root=cache_root,
    ) is None
    assert find_any_cached_roles(book, cache_root=cache_root) == entry


def test_role_cache_normalizes_llm_endpoint_suffix(tmp_path: Path) -> None:
    with_v1 = cache_path_for(
        _book(),
        _settings(llm_endpoint="http://localhost:11434/v1"),
        cache_root=tmp_path,
    )
    without_v1 = cache_path_for(
        _book(),
        _settings(llm_endpoint="http://localhost:11434"),
        cache_root=tmp_path,
    )

    assert with_v1 == without_v1


def test_role_cache_finds_compatible_legacy_entry(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    segments_path, roles_path = _write_manifests(source_dir)
    cache_root = tmp_path / "cache"
    entry = save_role_cache(
        _book(),
        _settings(),
        segments_path,
        roles_path,
        cache_root=cache_root,
    )
    legacy_path = cache_root / "legacy-role-cache-key"
    entry.path.rename(legacy_path)

    found = find_cached_roles(_book(), _settings(), cache_root=cache_root)

    assert found == CachedRoleExtraction(key=entry.key, path=legacy_path)


def test_role_cache_detects_completed_output_manifests(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    _write_manifests(output_dir)

    entry = cached_role_entry_from_output_dir(output_dir)

    assert entry == CachedRoleExtraction(key=output_dir.name, path=output_dir)


def test_role_cache_restores_absent_review_report_by_removing_stale_file(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    segments_path, roles_path = _write_manifests(source_dir)
    cache_root = tmp_path / "cache"
    entry = save_role_cache(
        _book(),
        _settings(),
        segments_path,
        roles_path,
        cache_root=cache_root,
    )
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    stale_report = output_dir / "llm_voice_review_report.json"
    stale_report.write_text('{"stale": true}', encoding="utf-8")

    restore_role_cache(entry, output_dir)

    assert not stale_report.exists()


def test_role_cache_rejects_corrupt_cached_manifests(tmp_path: Path) -> None:
    cache_dir = tmp_path / "bad"
    cache_dir.mkdir()
    (cache_dir / "segments_manifest.json").write_text('{"not": "a list"}', encoding="utf-8")
    (cache_dir / "roles_manifest.json").write_text('{"roles": []}', encoding="utf-8")

    with pytest.raises(ValueError, match="segments"):
        restore_role_cache(CachedRoleExtraction(key="bad", path=cache_dir), tmp_path / "out")
