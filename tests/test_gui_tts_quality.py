"""Tests for GUI TTS quality metadata."""

from __future__ import annotations

import json
from pathlib import Path

from book_normalizer.chunking.manifest import chunks_to_v2_manifest
from book_normalizer.gui.workers.tts_worker import ExportSegmentsWorker
from book_normalizer.models.book import Book, Chapter, Metadata, Paragraph, Segment


def test_export_segments_renders_stress_hints_for_tts_manifest(
    tmp_path: Path,
) -> None:
    paragraph = Paragraph(
        raw_text="\u041e\u043d \u043e\u0442\u043a\u0440\u044b\u043b \u0437\u0430\u043c\u043e\u043a.",
        normalized_text="\u041e\u043d \u043e\u0442\u043a\u0440\u044b\u043b \u0437\u0430\u043c\u043e\u043a.",
        index_in_chapter=0,
        segments=[
            Segment(text="\u041e\u043d"),
            Segment(text=" "),
            Segment(
                text="\u043e\u0442\u043a\u0440\u044b\u043b",
                stress_form="\u043e\u0442\u043a\u0440\u044b\u0301\u043b",
            ),
            Segment(text=" "),
            Segment(
                text="\u0437\u0430\u043c\u043e\u043a",
                stress_form="\u0437\u0430\u043c\u043e\u0301\u043a",
            ),
            Segment(text="."),
        ],
    )
    book = Book(
        chapters=[
            Chapter(title="Ch", index=0, paragraphs=[paragraph]),
        ],
    )
    worker = ExportSegmentsWorker(
        book=book,
        output_dir=tmp_path,
        speaker_mode="manual",
        stress_mode="double_vowel",
    )
    finished: list[str] = []
    errors: list[str] = []
    worker.finished.connect(finished.append)
    worker.error.connect(errors.append)

    worker.run()

    assert errors == []
    assert finished
    data = json.loads(Path(finished[0]).read_text(encoding="utf-8"))
    text = " ".join(segment["text"] for segment in data)
    assert "\u0437\u0430\u043c\u043e\u043e\u043a" in text
    assert "\u0437\u0430\u043c\u043e\u0301\u043a" not in text
    assert data[-1]["boundary_after"] == "chapter"
    assert data[-1]["pause_after_ms"] == 1500


def test_chunks_to_v2_manifest_preserves_pause_metadata() -> None:
    manifest = chunks_to_v2_manifest(
        [
            {
                "chapter_index": 0,
                "chunk_index": 0,
                "role": "narrator",
                "voice_id": "narrator_calm",
                "intonation": "neutral",
                "text": "First paragraph.",
                "pause_after_ms": 450,
                "boundary_after": "paragraph",
            },
        ],
        book_title="book",
    )

    chunk = manifest["chapters"][0]["chunks"][0]
    assert chunk["pause_after_ms"] == 450
    assert chunk["boundary_after"] == "paragraph"


def test_export_segments_persists_selected_book_language(tmp_path: Path) -> None:
    book = Book(
        metadata=Metadata(language="en"),
        chapters=[
            Chapter(
                title="Ch",
                index=0,
                paragraphs=[
                    Paragraph(
                        raw_text="Hello there.",
                        normalized_text="Hello there.",
                        index_in_chapter=0,
                    ),
                ],
            ),
        ],
    )
    worker = ExportSegmentsWorker(
        book=book,
        output_dir=tmp_path,
        speaker_mode="manual",
    )
    finished: list[str] = []
    errors: list[str] = []
    worker.finished.connect(finished.append)
    worker.error.connect(errors.append)

    worker.run()

    assert errors == []
    data = json.loads(Path(finished[0]).read_text(encoding="utf-8"))
    assert data[0]["language"] == "en"


def test_chunks_to_v2_manifest_persists_language_for_synthesis() -> None:
    manifest = chunks_to_v2_manifest(
        [
            {
                "chapter_index": 0,
                "chunk_index": 0,
                "role": "narrator",
                "voice_id": "narrator_calm",
                "language": "zh",
                "text": "\u4f60\u597d\u3002",
            },
        ],
        book_title="book",
    )

    assert manifest["language"] == "zh"
    assert manifest["tts_language"] == "Chinese"
