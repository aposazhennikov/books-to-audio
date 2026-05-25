"""Tests for installer-written runtime path configuration."""

from __future__ import annotations

import json
from pathlib import Path

from book_normalizer.llm.ollama_client import _normalise_endpoint
from book_normalizer.runtime_paths import (
    configured_ffmpeg_bin,
    configured_models_dir,
    configured_ollama_bin,
    configured_ollama_endpoint,
    configured_ollama_models_dir,
    configured_tessdata_dir,
    configured_tesseract_cmd,
    reset_runtime_path_cache,
)
from book_normalizer.tts.model_paths import default_comfyui_models_dir


def test_runtime_config_drives_models_and_ollama_defaults(
    tmp_path: Path,
    monkeypatch,
) -> None:
    models_dir = tmp_path / "models"
    ollama_models_dir = tmp_path / "ollama-models"
    config_path = tmp_path / "local_runtime_paths.json"
    config_path.write_text(
        json.dumps(
            {
                "models_dir": str(models_dir),
                "ollama_models_dir": str(ollama_models_dir),
                "ollama_endpoint": "http://127.0.0.1:11435",
                "ollama_bin": str(tmp_path / "tools" / "ollama.exe"),
                "tesseract_cmd": str(tmp_path / "tools" / "tesseract.exe"),
                "tessdata_dir": str(tmp_path / "Tesseract-OCR" / "tessdata"),
                "ffmpeg_bin": str(tmp_path / "tools" / "ffmpeg.exe"),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("BOOKS_TO_AUDIO_RUNTIME_CONFIG", str(config_path))
    monkeypatch.delenv("BOOKS_TO_AUDIO_MODELS_DIR", raising=False)
    monkeypatch.delenv("BOOKS_TO_AUDIO_OLLAMA_MODELS_DIR", raising=False)
    monkeypatch.delenv("OLLAMA_MODELS", raising=False)
    monkeypatch.delenv("BOOKS_TO_AUDIO_OLLAMA_ENDPOINT", raising=False)
    monkeypatch.delenv("BOOKS_TO_AUDIO_OLLAMA_BIN", raising=False)
    monkeypatch.delenv("BOOKS_TO_AUDIO_TESSERACT_CMD", raising=False)
    monkeypatch.delenv("BOOKS_TO_AUDIO_TESSDATA_DIR", raising=False)
    monkeypatch.delenv("TESSDATA_PREFIX", raising=False)
    monkeypatch.delenv("BOOKS_TO_AUDIO_FFMPEG_BIN", raising=False)
    reset_runtime_path_cache()

    assert configured_models_dir() == models_dir
    assert configured_ollama_models_dir() == ollama_models_dir
    assert default_comfyui_models_dir() == models_dir
    assert configured_ollama_endpoint() == "http://127.0.0.1:11435"
    assert configured_ollama_bin() == str(tmp_path / "tools" / "ollama.exe")
    assert configured_tesseract_cmd() == tmp_path / "tools" / "tesseract.exe"
    assert configured_tessdata_dir() == tmp_path / "Tesseract-OCR" / "tessdata"
    assert configured_ffmpeg_bin() == tmp_path / "tools" / "ffmpeg.exe"
    assert _normalise_endpoint(None) == "http://127.0.0.1:11435"

    reset_runtime_path_cache()


def test_runtime_env_overrides_config(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "local_runtime_paths.json"
    config_path.write_text(
        json.dumps(
            {
                "models_dir": str(tmp_path / "config-models"),
                "ollama_models_dir": str(tmp_path / "config-ollama-models"),
                "ollama_endpoint": "http://127.0.0.1:11435",
                "ollama_bin": str(tmp_path / "config-ollama"),
                "tesseract_cmd": str(tmp_path / "config-tesseract"),
                "tessdata_dir": str(tmp_path / "config-tessdata"),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("BOOKS_TO_AUDIO_RUNTIME_CONFIG", str(config_path))
    monkeypatch.setenv("BOOKS_TO_AUDIO_MODELS_DIR", str(tmp_path / "env-models"))
    monkeypatch.setenv("OLLAMA_MODELS", str(tmp_path / "env-ollama-models"))
    monkeypatch.setenv("BOOKS_TO_AUDIO_OLLAMA_ENDPOINT", "http://localhost:11500/v1")
    monkeypatch.setenv("BOOKS_TO_AUDIO_OLLAMA_BIN", str(tmp_path / "env-ollama"))
    monkeypatch.setenv("BOOKS_TO_AUDIO_TESSERACT_CMD", str(tmp_path / "env-tesseract"))
    monkeypatch.setenv("BOOKS_TO_AUDIO_TESSDATA_DIR", str(tmp_path / "env-tessdata"))
    reset_runtime_path_cache()

    assert configured_models_dir() == tmp_path / "env-models"
    assert configured_ollama_models_dir() == tmp_path / "env-ollama-models"
    assert configured_ollama_bin() == str(tmp_path / "env-ollama")
    assert configured_tesseract_cmd() == tmp_path / "env-tesseract"
    assert configured_tessdata_dir() == tmp_path / "env-tessdata"
    assert _normalise_endpoint(None) == "http://localhost:11500"

    reset_runtime_path_cache()
