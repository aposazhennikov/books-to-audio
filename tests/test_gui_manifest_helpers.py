"""Tests for GUI manifest compatibility helpers."""

from __future__ import annotations

import json
from pathlib import Path

from book_normalizer.chunking.manifest import chunks_to_v2_manifest
from book_normalizer.gui.pages.synthesis_page import (
    _build_test_manifest_chunks,
    _iter_manifest_chunks,
    _shorten_test_fragment,
)
from book_normalizer.gui.workers.tts_worker import (
    ExportSegmentsWorker,
    TTSSynthesisWorker,
    _flatten_manifest_chunks,
)
from book_normalizer.models.book import Book, Chapter, Paragraph


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


def test_build_test_manifest_uses_selected_chapter_and_trims_text() -> None:
    long_text = " ".join(["Sentence"] * 90) + ". Final tail that should not be used."
    manifest = {
        "version": 2,
        "chapters": [
            {
                "chapter_index": 0,
                "chunks": [
                    {
                        "chunk_index": 4,
                        "voice_id": "female_warm",
                        "text": "First chapter text.",
                    },
                ],
            },
            {
                "chapter_index": 1,
                "chunks": [
                    {
                        "chunk_index": 9,
                        "voice_id": "male_young",
                        "text": long_text,
                    },
                ],
            },
        ],
    }

    preview = _build_test_manifest_chunks(manifest, chapter=2)

    assert len(preview) == 1
    assert preview[0]["chapter_index"] == 1
    assert preview[0]["chunk_index"] == 0
    assert preview[0]["voice_id"] == "male_young"
    assert len(preview[0]["text"]) <= 420


def test_shorten_test_fragment_prefers_sentence_boundary() -> None:
    text = "A" * 140 + ". " + "B" * 500

    shortened = _shorten_test_fragment(text, max_chars=300)

    assert shortened == "A" * 140 + "."


def test_v2_manifest_prefers_assigned_voice_id_over_stale_role() -> None:
    manifest = chunks_to_v2_manifest(
        [
            {
                "chapter_index": 0,
                "chunk_index": 0,
                "role": "narrator",
                "voice_id": "male_young",
                "text": "Manual voice assignment.",
            },
        ],
        book_title="book",
    )

    chunk = manifest["chapters"][0]["chunks"][0]
    assert chunk["voice_label"] == "men"
    assert chunk["voice"] == "male"
    assert chunk["men"] == "Manual voice assignment."


def test_export_segments_manual_mode_does_not_call_terminal_attributor(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import book_normalizer.dialogue.attribution as attribution

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("manual GUI mode must not call terminal attributor")

    monkeypatch.setattr(attribution, "create_attributor", fail_if_called)

    book = Book(
        chapters=[
            Chapter(
                title="Ch",
                index=0,
                paragraphs=[
                    Paragraph(
                        raw_text="\u2014 \u0414\u0430.",
                        normalized_text="\u2014 \u0414\u0430.",
                        index_in_chapter=0,
                    ),
                ],
            ),
        ],
    )
    worker = ExportSegmentsWorker(book=book, output_dir=tmp_path, speaker_mode="manual")
    finished: list[str] = []
    errors: list[str] = []
    worker.finished.connect(finished.append)
    worker.error.connect(errors.append)

    worker.run()

    assert errors == []
    assert finished
    data = json.loads(Path(finished[0]).read_text(encoding="utf-8"))
    assert data[0]["is_dialogue"] is True
    assert data[0]["role"] == "unknown"
