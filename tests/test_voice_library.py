"""Tests for reusable saved voice prompt metadata."""

from __future__ import annotations

import json
import sys
from types import SimpleNamespace

from book_normalizer.tts.voice_library import (
    VOICE_FILE_SUFFIX,
    UnsafeVoicePromptError,
    default_voice_library_dir,
    list_saved_voices,
    load_voice_prompt,
    normalize_voice_library_dir,
    resolve_saved_voice_path,
    sanitize_voice_id,
    save_comfyui_voice_metadata,
    save_voice_prompt,
    voice_paths,
)


def test_sanitize_voice_id_is_filesystem_safe() -> None:
    assert sanitize_voice_id(" Ilya Isaev! ") == "ilya_isaev"
    assert sanitize_voice_id("Дикторский голос мужской 1 медленный") == (
        "дикторский_голос_мужской_1_медленный"
    )
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
                "speech_rate": 0.9,
            },
        ),
        encoding="utf-8",
    )

    voices = list_saved_voices(tmp_path)

    assert len(voices) == 1
    assert voices[0].voice_id == "ilya_isaev"
    assert voices[0].name == "Ilya Isaev"
    assert voices[0].speech_rate == 0.9
    assert resolve_saved_voice_path("ilya_isaev", tmp_path) == prompt_path
    assert resolve_saved_voice_path("Ilya Isaev", tmp_path) == prompt_path


def test_default_voice_library_dir_is_project_local_absolute() -> None:
    library_dir = default_voice_library_dir()

    assert library_dir.is_absolute()
    assert library_dir.name == "voices"
    assert library_dir.parent.name == "output"


def test_normalize_voice_library_dir_handles_relative_paths() -> None:
    library_dir = normalize_voice_library_dir("output/voices")

    assert library_dir == default_voice_library_dir()


def test_list_saved_voices_falls_back_to_sidecar_prompt(tmp_path) -> None:  # noqa: ANN001
    metadata_path = tmp_path / "actual.voice.json"
    prompt_path = tmp_path / f"actual{VOICE_FILE_SUFFIX}"
    prompt_path.write_bytes(b"fake prompt")
    metadata_path.write_text(
        json.dumps(
            {
                "id": "broken",
                "name": "Actual",
                "prompt_file": "missing.voice.pt",
                "model": "Qwen/Base",
            },
        ),
        encoding="utf-8",
    )

    voices = list_saved_voices(tmp_path)

    assert len(voices) == 1
    assert voices[0].voice_id == "actual"
    assert voices[0].prompt_path == prompt_path


def test_comfyui_saved_voice_metadata_is_listed_without_prompt_file(tmp_path) -> None:  # noqa: ANN001
    ref_audio = tmp_path / "sample.wav"
    ref_audio.write_bytes(b"fake wav")

    saved = save_comfyui_voice_metadata(
        library_dir=tmp_path,
        name="Margarita Sad",
        ref_audio=str(ref_audio),
        ref_text="Exact reference transcript.",
        speech_rate=0.92,
    )
    voices = list_saved_voices(tmp_path)

    assert saved.voice_id == "margarita_sad"
    assert len(voices) == 1
    assert voices[0].source == "comfyui"
    assert voices[0].preview_audio == str(ref_audio)
    assert voices[0].ref_text == "Exact reference transcript."
    assert voices[0].speech_rate == 0.92


def test_load_voice_prompt_uses_weights_only(monkeypatch, tmp_path) -> None:  # noqa: ANN001
    calls = []
    prompt_path = tmp_path / "sample.voice.pt"
    prompt_path.write_bytes(b"fake prompt")

    def fake_load(path, *, map_location=None, weights_only=False):  # noqa: ANN001, ANN202
        calls.append(
            {
                "path": path,
                "map_location": map_location,
                "weights_only": weights_only,
            }
        )
        return {"ok": True}

    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(load=fake_load))

    assert load_voice_prompt(prompt_path, map_location="cpu") == {"ok": True}
    assert calls == [
        {
            "path": prompt_path,
            "map_location": "cpu",
            "weights_only": True,
        }
    ]


def test_load_voice_prompt_rejects_torch_without_weights_only(monkeypatch, tmp_path) -> None:  # noqa: ANN001
    prompt_path = tmp_path / "sample.voice.pt"
    prompt_path.write_bytes(b"fake prompt")

    def legacy_load(path, *, map_location=None):  # noqa: ANN001, ANN202, ARG001
        return {"unsafe": True}

    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(load=legacy_load))

    try:
        load_voice_prompt(prompt_path)
    except UnsafeVoicePromptError as exc:
        assert "weights_only" in str(exc)
    else:
        raise AssertionError("Expected unsafe legacy torch.load to be rejected.")


def test_save_voice_prompt_records_prompt_hash(monkeypatch, tmp_path) -> None:  # noqa: ANN001
    def fake_save(prompt, path) -> None:  # noqa: ANN001
        path.write_bytes(prompt)

    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(save=fake_save))

    saved = save_voice_prompt(
        b"fake prompt",
        library_dir=tmp_path,
        name="Ilya Isaev",
        ref_audio="missing.wav",
        ref_text="Exact reference transcript.",
        model="Qwen/Base",
    )
    metadata = json.loads(saved.metadata_path.read_text(encoding="utf-8"))

    assert metadata["prompt_sha256"] == "f5b75fb3abfafdb8ad9e977f254084eabd38286c425e2db9cc329606bfa1becb"


def test_load_voice_prompt_rejects_sidecar_hash_mismatch(monkeypatch, tmp_path) -> None:  # noqa: ANN001
    load_was_called = False
    prompt_path = tmp_path / "sample.voice.pt"
    metadata_path = tmp_path / "sample.voice.json"
    prompt_path.write_bytes(b"tampered prompt")
    metadata_path.write_text(
        json.dumps({"prompt_sha256": "0" * 64}),
        encoding="utf-8",
    )

    def fake_load(path, *, map_location=None, weights_only=False):  # noqa: ANN001, ANN202, ARG001
        nonlocal load_was_called
        load_was_called = True
        return {"unsafe": True}

    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(load=fake_load))

    try:
        load_voice_prompt(prompt_path)
    except UnsafeVoicePromptError as exc:
        assert "hash mismatch" in str(exc)
    else:
        raise AssertionError("Expected tampered saved voice prompt to be rejected.")
    assert load_was_called is False
