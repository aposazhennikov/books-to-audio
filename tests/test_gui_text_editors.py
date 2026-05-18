"""Tests for manual text and chunk editing helpers in the GUI."""

from __future__ import annotations

import json
import os
from pathlib import Path

from book_normalizer.gui.pages.synthesis_page import (
    SynthesisPage,
    _merge_manifest_chunk_with_next,
    _split_manifest_chunk_text,
    _update_manifest_chunk_text,
)
from book_normalizer.gui.widgets.voice_table import VoiceTableWidget


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_voice_table_segment_editor_updates_selected_text() -> None:
    app = _app()
    _ = app
    table = VoiceTableWidget()
    table.set_segments([
        {
            "segment_index": 0,
            "chapter_index": 0,
            "role": "narrator",
            "voice_id": "narrator_calm",
            "intonation": "neutral",
            "text": "Old text.",
        }
    ])

    table._table.setCurrentCell(0, 3)
    table._segment_editor.setPlainText("Edited text.")

    assert table.get_segments()[0]["text"] == "Edited text."
    assert table._table.item(0, 3).text() == "Edited text."


def test_voice_table_full_text_editor_rebuilds_segments() -> None:
    app = _app()
    _ = app
    table = VoiceTableWidget()
    table.set_segments([
        {
            "segment_index": 0,
            "chapter_index": 0,
            "role": "narrator",
            "voice_id": "narrator_calm",
            "intonation": "neutral",
            "text": "First.",
        },
        {
            "segment_index": 1,
            "chapter_index": 0,
            "role": "male",
            "voice_id": "male_young",
            "intonation": "neutral",
            "text": "Second.",
        },
    ])

    table._full_text_editor.setPlainText("One.\n\nTwo.\n\nThree.")
    table._apply_full_text_to_segments()

    segments = table.get_segments()
    assert [segment["text"] for segment in segments] == ["One.", "Two.", "Three."]
    assert segments[2]["voice_id"] == "male_young"
    assert [segment["segment_index"] for segment in segments] == [0, 1, 2]


def test_manifest_chunk_editor_helpers_update_split_and_merge() -> None:
    manifest = {
        "version": 2,
        "chapters": [
            {
                "chapter_index": 0,
                "chunks": [
                    {
                        "chapter_index": 0,
                        "chunk_index": 0,
                        "voice_label": "narrator",
                        "narrator": "Old.",
                        "text": "Old.",
                        "synthesized": True,
                        "audio_file": "old.wav",
                    },
                    {
                        "chapter_index": 0,
                        "chunk_index": 1,
                        "voice_label": "narrator",
                        "narrator": "Next.",
                        "text": "Next.",
                        "pause_after_ms": 450,
                        "boundary_after": "paragraph",
                    },
                ],
            }
        ],
    }

    assert _update_manifest_chunk_text(manifest, 0, 0, "Alpha beta.")
    chunk = manifest["chapters"][0]["chunks"][0]
    assert chunk["text"] == "Alpha beta."
    assert chunk["narrator"] == "Alpha beta."
    assert chunk["synthesized"] is False
    assert chunk["audio_file"] is None

    assert _split_manifest_chunk_text(manifest, 0, 0, 6)
    chunks = manifest["chapters"][0]["chunks"]
    assert [chunk["chunk_index"] for chunk in chunks] == [0, 1, 2]
    assert [chunk["text"] for chunk in chunks] == ["Alpha", "beta.", "Next."]

    assert _merge_manifest_chunk_with_next(manifest, 0, 1)
    chunks = manifest["chapters"][0]["chunks"]
    assert [chunk["chunk_index"] for chunk in chunks] == [0, 1]
    assert chunks[1]["text"] == "beta. Next."
    assert chunks[1]["pause_after_ms"] == 450


def test_synthesis_page_tests_unsaved_chunk_editor_text(tmp_path: Path) -> None:
    app = _app()
    _ = app
    page = SynthesisPage()
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": 2,
                "chapters": [
                    {
                        "chapter_index": 0,
                        "chunks": [
                            {
                                "chunk_index": 0,
                                "voice_id": "narrator_calm",
                                "text": "Original.",
                            }
                        ],
                    }
                ],
            },
        ),
        encoding="utf-8",
    )

    page.set_manifest(manifest_path, tmp_path / "out")
    page._test_chunk_preview.setPlainText("Edited for preview.")

    assert page._build_selected_test_chunks()[0]["text"] == "Edited for preview."
