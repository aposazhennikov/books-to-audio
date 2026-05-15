"""Tests for GUI manifest compatibility helpers."""

from __future__ import annotations

import json
from pathlib import Path

from book_normalizer.gui.pages.synthesis_page import _iter_manifest_chunks
from book_normalizer.gui.workers.tts_worker import (
    TTSSynthesisWorker,
    _flatten_manifest_chunks,
)


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


def test_tts_worker_converts_models_dir_to_wsl_path() -> None:
    assert (
        TTSSynthesisWorker._wsl_path_text(r"D:\ComfyUI-external\models")
        == "/mnt/d/ComfyUI-external/models"
    )


def test_tts_worker_converts_sample_audio_path_inside_clone_config(tmp_path: Path) -> None:
    cfg_path = tmp_path / "clone.json"
    cfg_path.write_text(
        json.dumps(
            {
                "__all__": {
                    "ref_audio": r"D:\samples\narrator.wav",
                    "ref_text": "Sample transcript.",
                }
            }
        ),
        encoding="utf-8",
    )

    worker = TTSSynthesisWorker(
        manifest_path=tmp_path / "manifest.json",
        output_dir=tmp_path,
        clone_config=str(cfg_path),
    )

    converted_path = worker._prepare_clone_config()

    assert converted_path is not None
    converted = json.loads(converted_path.read_text(encoding="utf-8"))
    assert converted["__all__"]["ref_audio"] == "/mnt/d/samples/narrator.wav"
