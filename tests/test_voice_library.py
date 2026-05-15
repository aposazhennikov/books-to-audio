"""Tests for reusable saved voice prompt metadata."""

from __future__ import annotations

import json

from book_normalizer.tts.voice_library import (
    list_saved_voices,
    resolve_saved_voice_path,
    sanitize_voice_id,
    voice_paths,
)


def test_sanitize_voice_id_is_filesystem_safe() -> None:
    assert sanitize_voice_id(" Ilya Isaev! ") == "ilya_isaev"
    assert sanitize_voice_id("Голос 1") == "1"
    assert sanitize_voice_id("!!!") == "voice"


def test_list_and_resolve_saved_voice(tmp_path) -> None:  # noqa: ANN001
    prompt_path, metadata_path, voice_id = voice_paths(tmp_path, "Ilya Isaev")
    prompt_path.write_bytes(b"fake prompt")
    metadata_path.write_text(
        json.dumps(
            {
                "id": voice_id,
                "name": "Ilya Isaev",
                "prompt_file": prompt_path.name,
                "model": "Qwen/Base",
            },
        ),
        encoding="utf-8",
    )

    voices = list_saved_voices(tmp_path)

    assert len(voices) == 1
    assert voices[0].voice_id == "ilya_isaev"
    assert voices[0].name == "Ilya Isaev"
    assert resolve_saved_voice_path("ilya_isaev", tmp_path) == prompt_path
    assert resolve_saved_voice_path("Ilya Isaev", tmp_path) == prompt_path
