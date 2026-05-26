from __future__ import annotations

import json

from click.testing import CliRunner

import book_normalizer.cli as cli
from book_normalizer.production.character_bible import (
    apply_character_bible_to_manifest,
    build_character_bible,
)


def test_character_bible_groups_named_speakers_and_reports_unresolved() -> None:
    bible = build_character_bible(
        [
            {
                "chapter_index": 0,
                "role": "female",
                "speaker": "Маргарита",
                "character_description": "Резкая и смелая.",
                "emotion": "angry",
                "is_dialogue": True,
                "text": "Я здесь!",
            },
            {
                "chapter_index": 2,
                "role": "female",
                "speaker": "Маргарита",
                "emotion": "fearful",
                "is_dialogue": True,
                "text": "Что это?",
            },
            {
                "chapter_index": 0,
                "role": "male",
                "speaker": "",
                "is_dialogue": True,
                "text": "Кто здесь?",
            },
            {
                "chapter_index": 0,
                "role": "narrator",
                "text": "Авторский текст.",
            },
        ],
        book_title="Book",
        language="ru",
    )

    names = [item["display_name"] for item in bible["characters"]]
    margarita = next(item for item in bible["characters"] if item["display_name"] == "Маргарита")

    assert "Маргарита" in names
    assert "Narrator" in names
    assert margarita["direct_speech_count"] == 2
    assert margarita["chapter_indexes"] == [0, 2]
    assert margarita["emotions"] == [
        {"emotion": "angry", "count": 1},
        {"emotion": "fearful", "count": 1},
    ]
    assert bible["summary"]["unresolved_dialogue"] == 1


def test_character_bible_can_annotate_v2_manifest() -> None:
    manifest = {
        "version": 2,
        "language": "ru",
        "chapters": [
            {
                "chapter_index": 0,
                "chunks": [
                    {
                        "chapter_index": 0,
                        "chunk_index": 0,
                        "voice_label": "women",
                        "speaker": "Маргарита",
                        "text": "Я здесь.",
                    }
                ],
            }
        ],
    }
    bible = build_character_bible(
        [{"chapter_index": 0, "role": "female", "speaker": "Маргарита", "is_dialogue": True, "text": "Я здесь."}],
    )

    annotated = apply_character_bible_to_manifest(manifest, bible)
    chunk = annotated["chapters"][0]["chunks"][0]

    assert chunk["canonical_speaker"] == "Маргарита"
    assert chunk["character_id"].startswith("char_")
    assert chunk["character_confidence"] > 0


def test_analyze_characters_cli_writes_bible_and_manifest(tmp_path) -> None:  # noqa: ANN001
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": 2,
                "language": "ru",
                "chapters": [
                    {
                        "chapter_index": 0,
                        "chunks": [
                            {
                                "chapter_index": 0,
                                "chunk_index": 0,
                                "voice_label": "men",
                                "speaker": "Воланд",
                                "text": "Никогда и ничего не просите.",
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli.main,
        ["analyze-characters", str(manifest_path), "--write-manifest"],
    )

    assert result.exit_code == 0, result.output
    bible = json.loads((tmp_path / "character_bible.json").read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert bible["characters"][0]["display_name"] == "Воланд"
    assert manifest["chapters"][0]["chunks"][0]["canonical_speaker"] == "Воланд"
