"""Tests for GUI manifest compatibility helpers."""

from __future__ import annotations

from book_normalizer.gui.pages.synthesis_page import _iter_manifest_chunks
from book_normalizer.gui.workers.tts_worker import _flatten_manifest_chunks


def _v2_manifest() -> dict:
    return {
        "version": 2,
        "chapters": [
            {
                "chapter_index": 3,
                "chunks": [
                    {
                        "chunk_index": 0,
                        "voice_id": "narrator_calm",
                        "text": "Hello",
                    },
                ],
            },
        ],
    }


def test_synthesis_page_reads_v2_manifest_chunks() -> None:
    chunks = _iter_manifest_chunks(_v2_manifest())

    assert chunks == [
        {
            "chapter_index": 3,
            "chunk_index": 0,
            "voice_id": "narrator_calm",
            "text": "Hello",
        },
    ]


def test_tts_worker_flattens_v2_manifest_for_legacy_runner() -> None:
    chunks = _flatten_manifest_chunks(_v2_manifest())

    assert chunks == [
        {
            "chapter_index": 3,
            "chunk_index": 0,
            "voice_id": "narrator_calm",
            "text": "Hello",
        },
    ]
