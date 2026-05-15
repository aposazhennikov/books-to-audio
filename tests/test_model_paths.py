from __future__ import annotations

from pathlib import Path

from book_normalizer.tts.model_paths import describe_model_resolution, resolve_model_path


def test_resolve_model_path_prefers_audio_encoders(tmp_path: Path) -> None:
    model_dir = (
        tmp_path
        / "audio_encoders"
        / "Qwen3-TTS-12Hz-1.7B-CustomVoice"
    )
    model_dir.mkdir(parents=True)
    (model_dir / "config.json").write_text("{}", encoding="utf-8")

    resolved = resolve_model_path(
        "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        models_dir=tmp_path,
    )

    assert resolved == str(model_dir)


def test_resolve_model_path_returns_original_when_missing(tmp_path: Path) -> None:
    model_name = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"

    assert resolve_model_path(model_name, models_dir=tmp_path) == model_name


def test_resolve_model_path_accepts_direct_local_model_dir(tmp_path: Path) -> None:
    model_dir = tmp_path / "direct-model"
    model_dir.mkdir()
    (model_dir / "config.json").write_text("{}", encoding="utf-8")

    assert resolve_model_path(str(model_dir)) == str(model_dir)


def test_describe_model_resolution_marks_direct_path_as_local(tmp_path: Path) -> None:
    model_dir = tmp_path / "direct-model"
    model_dir.mkdir()
    (model_dir / "config.json").write_text("{}", encoding="utf-8")

    assert describe_model_resolution(str(model_dir)) == (str(model_dir), True)
