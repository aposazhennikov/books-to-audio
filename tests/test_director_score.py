from __future__ import annotations

import json

from click.testing import CliRunner

import book_normalizer.cli as cli
from book_normalizer.production.director import (
    apply_director_score_to_manifest,
    build_director_score,
)


def _manifest() -> dict:
    return {
        "version": 2,
        "book_title": "Director Test",
        "language": "en",
        "chapters": [
            {
                "chapter_index": 0,
                "chapter_title": "Chapter 1",
                "chunks": [
                    {
                        "chapter_index": 0,
                        "chunk_index": 0,
                        "voice_label": "women",
                        "speaker": "Alice",
                        "emotion": "angry",
                        "section_kind": "dialogue",
                        "voice_tone": "neutral",
                        "text": "Leave me alone!",
                    },
                    {
                        "chapter_index": 0,
                        "chunk_index": 1,
                        "voice_label": "men",
                        "speaker": "Bob",
                        "emotion": "sad",
                        "section_kind": "dialogue",
                        "voice_tone": "neutral",
                        "text": "I cannot.",
                    },
                    {
                        "chapter_index": 0,
                        "chunk_index": 2,
                        "voice_label": "narrator",
                        "section_kind": "narration",
                        "voice_tone": "neutral",
                        "pause_after_ms": 1500,
                        "boundary_after": "scene",
                        "text": "The room fell silent...",
                    },
                ],
            }
        ],
    }


def test_director_score_adds_performance_metadata_and_pauses() -> None:
    score = build_director_score(_manifest())
    first = score["chunks"][0]
    second = score["chunks"][1]

    assert score["summary"]["high_tension_chunks"] == 1
    assert first["director"]["tension"] == "high"
    assert first["director"]["volume"] == "firm but not clipped"
    assert first["director"]["pause"] == "clear speaker handoff beat"
    assert first["pause_after_ms"] >= 650
    assert "controlled" in first["director"]["pace"]
    assert second["director"]["delivery"] == "subdued, emotionally present, no melodrama"


def test_director_score_manifest_annotation_preserves_existing_longer_pause() -> None:
    manifest = _manifest()
    manifest["chapters"][0]["chunks"][0]["pause_after_ms"] = 900
    score = build_director_score(manifest)

    annotated = apply_director_score_to_manifest(manifest, score)
    first = annotated["chapters"][0]["chunks"][0]

    assert first["director"]["tension"] == "high"
    assert first["pause_after_ms"] == 900
    assert "angry; high;" in first["voice_tone"]


def test_score_director_cli_writes_score_and_manifest(tmp_path) -> None:  # noqa: ANN001
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")

    result = CliRunner().invoke(
        cli.main,
        ["score-director", str(manifest_path), "--write-manifest"],
    )

    assert result.exit_code == 0, result.output
    score = json.loads((tmp_path / "director_score.json").read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert score["summary"]["scenes"] == 1
    assert manifest["chapters"][0]["chunks"][0]["director"]["tension"] == "high"
