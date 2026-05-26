"""V2-only chunk manifest facade.

New code should import from :mod:`book_normalizer.chunking.manifest_v2`.
This module keeps established import paths while rejecting v1 list manifests.
"""

from __future__ import annotations

from typing import Any

from book_normalizer.chunking.manifest_v2 import (
    DEFAULT_MANIFEST_NAME,
    MANIFEST_VERSION,
    VOICE_BY_LABEL,
    VOICE_ID_BY_LABEL,
    VOICE_LABEL_BY_ROLE,
    ManifestChapterV2,
    ManifestChunkV2,
    ManifestV2,
    ManifestV2Error,
    chunk_is_excluded,
    chunks_to_manifest,
    ensure_v2_manifest,
    flatten_manifest,
    load_manifest,
    merge_chunk_with_next,
    role_for_voice_id,
    role_to_voice_label,
    save_manifest,
    split_chunk_text,
    update_chunk_text,
)

__all__ = [
    "DEFAULT_MANIFEST_NAME",
    "MANIFEST_VERSION",
    "VOICE_BY_LABEL",
    "VOICE_ID_BY_LABEL",
    "VOICE_LABEL_BY_ROLE",
    "ManifestChapterV2",
    "ManifestChunkV2",
    "ManifestV2",
    "ManifestV2Error",
    "chunk_is_excluded",
    "chunks_to_manifest",
    "chunks_to_v2_manifest",
    "ensure_v2_manifest",
    "flatten_manifest",
    "flatten_v2_manifest",
    "load_manifest",
    "merge_chunk_with_next",
    "role_for_voice_id",
    "role_to_voice_label",
    "save_manifest",
    "split_chunk_text",
    "update_chunk_text",
]


def chunks_to_v2_manifest(
    chunks: list[dict[str, Any]],
    *,
    book_title: str,
    language: str = "ru",
    chunker: str = "gui",
    model: str = "",
    max_chunk_chars: int | None = None,
) -> dict[str, Any]:
    """Build a v2 manifest JSON object from flat chunk dictionaries."""
    return chunks_to_manifest(
        chunks,
        book_title=book_title,
        language=language,
        chunker=chunker,
        model=model,
        max_chunk_chars=max_chunk_chars,
    ).to_record()


def flatten_v2_manifest(data: object) -> list[dict[str, Any]]:
    """Return flat v2 chunks, rejecting removed v1 list manifests."""
    return flatten_manifest(ensure_v2_manifest(data))
