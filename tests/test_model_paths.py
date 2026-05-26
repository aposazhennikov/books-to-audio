from __future__ import annotations

import json
from pathlib import Path

from book_normalizer.runtime_paths import reset_runtime_path_cache
from book_normalizer.tts import model_paths
from book_normalizer.tts.model_paths import (
    QWEN3_TTS_REQUIRED_DIRS,
    default_comfyui_models_dir,
    describe_model_resolution,
    effective_comfyui_models_dir,
    resolve_model_path,
)


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


def test_resolve_model_path_accepts_tokenizer_marker(tmp_path: Path) -> None:
    tokenizer_dir = tmp_path / "audio_encoders" / "Qwen3-TTS-Tokenizer-12Hz"
    tokenizer_dir.mkdir(parents=True)
    (tokenizer_dir / "tokenizer_config.json").write_text("{}", encoding="utf-8")

    resolved = resolve_model_path(
        "Qwen/Qwen3-TTS-Tokenizer-12Hz",
        models_dir=tmp_path,
    )

    assert resolved == str(tokenizer_dir)


def test_effective_models_dir_falls_back_from_stale_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    stale_config_root = tmp_path / "empty-config-models"
    stale_config_root.mkdir()
    platform_root = tmp_path / "platform-models"
    _write_required_qwen3_tts_markers(platform_root)
    config_path = tmp_path / "runtime.json"
    config_path.write_text(json.dumps({"models_dir": str(stale_config_root)}), encoding="utf-8")

    monkeypatch.setenv("BOOKS_TO_AUDIO_RUNTIME_CONFIG", str(config_path))
    monkeypatch.delenv("BOOKS_TO_AUDIO_MODELS_DIR", raising=False)
    monkeypatch.setattr(model_paths, "_platform_default_comfyui_models_dir", lambda: platform_root)
    reset_runtime_path_cache()

    assert default_comfyui_models_dir() == stale_config_root
    assert effective_comfyui_models_dir() == platform_root
    assert (
        resolve_model_path("Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice")
        == str(platform_root / "audio_encoders" / "Qwen3-TTS-12Hz-1.7B-CustomVoice")
    )

    reset_runtime_path_cache()


def test_effective_models_dir_keeps_config_when_models_exist(
    tmp_path: Path,
    monkeypatch,
) -> None:
    configured_root = tmp_path / "configured-models"
    platform_root = tmp_path / "platform-models"
    _write_required_qwen3_tts_markers(configured_root)
    _write_required_qwen3_tts_markers(platform_root)
    config_path = tmp_path / "runtime.json"
    config_path.write_text(json.dumps({"models_dir": str(configured_root)}), encoding="utf-8")

    monkeypatch.setenv("BOOKS_TO_AUDIO_RUNTIME_CONFIG", str(config_path))
    monkeypatch.delenv("BOOKS_TO_AUDIO_MODELS_DIR", raising=False)
    monkeypatch.setattr(model_paths, "_platform_default_comfyui_models_dir", lambda: platform_root)
    reset_runtime_path_cache()

    assert effective_comfyui_models_dir() == configured_root

    reset_runtime_path_cache()


def _write_required_qwen3_tts_markers(root: Path) -> None:
    for name in QWEN3_TTS_REQUIRED_DIRS:
        model_dir = root / "audio_encoders" / name
        model_dir.mkdir(parents=True)
        (model_dir / "config.json").write_text("{}", encoding="utf-8")
