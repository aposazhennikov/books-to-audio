from __future__ import annotations

import json

from click.testing import CliRunner

import book_normalizer.cli as cli
from book_normalizer.production.casting import (
    apply_casting_plan_to_manifest,
    build_casting_plan,
    casting_voice_overrides,
)


def _bible() -> dict:
    return {
        "version": 1,
        "book_title": "Test Book",
        "language": "en",
        "characters": [
            {
                "character_id": "char_narrator",
                "display_name": "Narrator",
                "role": "narrator",
                "aliases": ["Narrator"],
                "direct_speech_count": 0,
                "emotions": [],
                "sample_lines": ["The street was quiet."],
            },
            {
                "character_id": "char_alice",
                "display_name": "Alice",
                "role": "female",
                "aliases": ["Alice"],
                "description": "A tired but brave woman.",
                "direct_speech_count": 4,
                "emotions": [{"emotion": "sad", "count": 3}],
                "sample_lines": ["I cannot go back.", "Please listen to me."],
            },
            {
                "character_id": "char_bob",
                "display_name": "Bob",
                "role": "male",
                "aliases": ["Bob"],
                "direct_speech_count": 1,
                "emotions": [{"emotion": "angry", "count": 1}],
                "sample_lines": ["Leave now."],
            },
        ],
    }


def test_casting_plan_designs_important_character_and_uses_builtin_fallback() -> None:
    plan = build_casting_plan(_bible(), min_design_lines=3)

    alice = next(item for item in plan["characters"] if item["display_name"] == "Alice")
    bob = next(item for item in plan["characters"] if item["display_name"] == "Bob")

    assert alice["voice_strategy"] == "designed"
    assert alice["selected_voice_id"] == "design:char_alice"
    assert alice["fallback_voice_id"] == "female_gentle"
    assert alice["requires_voice_generation"] is True
    assert "A tired but brave woman" in alice["voice_design_prompt"]
    assert bob["voice_strategy"] == "builtin"
    assert bob["selected_voice_id"] == "male_confident"
    assert plan["summary"]["designed"] == 1
    assert plan["summary"]["builtin"] == 2


def test_saved_voice_match_wins_over_design(tmp_path) -> None:  # noqa: ANN001
    prompt_path = tmp_path / "alice.voice.pt"
    prompt_path.write_bytes(b"prompt")
    (tmp_path / "alice.voice.json").write_text(
        json.dumps(
            {
                "id": "alice",
                "name": "Alice",
                "prompt_file": prompt_path.name,
                "speech_rate": 0.91,
            }
        ),
        encoding="utf-8",
    )

    plan = build_casting_plan(_bible(), voice_library_dir=tmp_path, min_design_lines=3)
    alice = next(item for item in plan["characters"] if item["display_name"] == "Alice")

    assert alice["voice_strategy"] == "saved"
    assert alice["selected_voice_id"] == "alice"
    assert alice["speech_rate"] == 0.91
    assert plan["summary"]["saved"] == 1


def test_casting_plan_overrides_and_manifest_annotation() -> None:
    plan = build_casting_plan(_bible(), min_design_lines=3)
    overrides = casting_voice_overrides(plan)
    manifest = {
        "version": 2,
        "language": "en",
        "chapters": [
            {
                "chapter_index": 0,
                "chunks": [
                    {
                        "chapter_index": 0,
                        "chunk_index": 0,
                        "voice_label": "women",
                        "speaker": "Alice",
                        "character_id": "char_alice",
                        "text": "I cannot go back.",
                    }
                ],
            }
        ],
    }

    annotated = apply_casting_plan_to_manifest(manifest, plan)
    chunk = annotated["chapters"][0]["chunks"][0]

    assert overrides["speaker:Alice"]["strategy"] == "designed"
    assert overrides["speaker:Alice"]["speaker"] == "Sohee"
    assert chunk["cast_voice_id"] == "design:char_alice"
    assert chunk["voice_strategy"] == "designed"
    assert chunk["voice_id"] == "female_gentle"
    assert chunk["canonical_speaker"] == "Alice"


def test_cast_voices_cli_writes_plan_overrides_and_manifest(tmp_path) -> None:  # noqa: ANN001
    bible_path = tmp_path / "character_bible.json"
    bible_path.write_text(json.dumps(_bible()), encoding="utf-8")
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": 2,
                "language": "en",
                "chapters": [
                    {
                        "chapter_index": 0,
                        "chunks": [
                            {
                                "chapter_index": 0,
                                "chunk_index": 0,
                                "voice_label": "women",
                                "speaker": "Alice",
                                "character_id": "char_alice",
                                "text": "I cannot go back.",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli.main,
        ["cast-voices", str(bible_path), "--manifest", str(manifest_path)],
    )

    assert result.exit_code == 0, result.output
    plan = json.loads((tmp_path / "casting_plan.json").read_text(encoding="utf-8"))
    overrides = json.loads((tmp_path / "voice_overrides.json").read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert plan["summary"]["designed"] == 1
    assert overrides["speaker:Alice"]["voice_design_prompt"]
    assert manifest["chapters"][0]["chunks"][0]["cast_voice_id"] == "design:char_alice"
