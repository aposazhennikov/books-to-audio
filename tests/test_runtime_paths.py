"""Tests for installer-written runtime path configuration."""

from __future__ import annotations

import json
from pathlib import Path

from book_normalizer.llm.ollama_client import _normalise_endpoint
from book_normalizer.runtime_paths import (
    configured_models_dir,
    configured_ollama_endpoint,
    reset_runtime_path_cache,
)
from book_normalizer.tts.model_paths import default_comfyui_models_dir


def test_runtime_config_drives_models_and_ollama_defaults(
    tmp_path: Path,
    monkeypatch,
) -> None:
    models_dir = tmp_path / "models"
    config_path = tmp_path / "local_runtime_paths.json"
    config_path.write_text(
        json.dumps(
            {
                "models_dir": str(models_dir),
                "ollama_endpoint": "http://127.0.0.1:11435",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("BOOKS_TO_AUDIO_RUNTIME_CONFIG", str(config_path))
    monkeypatch.delenv("BOOKS_TO_AUDIO_MODELS_DIR", raising=False)
    monkeypatch.delenv("BOOKS_TO_AUDIO_OLLAMA_ENDPOINT", raising=False)
    reset_runtime_path_cache()

    assert configured_models_dir() == models_dir
    assert default_comfyui_models_dir() == models_dir
    assert configured_ollama_endpoint() == "http://127.0.0.1:11435"
    assert _normalise_endpoint(None) == "http://127.0.0.1:11435"

    reset_runtime_path_cache()


def test_runtime_env_overrides_config(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "local_runtime_paths.json"
    config_path.write_text(
        json.dumps(
            {
                "models_dir": str(tmp_path / "config-models"),
                "ollama_endpoint": "http://127.0.0.1:11435",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("BOOKS_TO_AUDIO_RUNTIME_CONFIG", str(config_path))
    monkeypatch.setenv("BOOKS_TO_AUDIO_MODELS_DIR", str(tmp_path / "env-models"))
    monkeypatch.setenv("BOOKS_TO_AUDIO_OLLAMA_ENDPOINT", "http://localhost:11500/v1")
    reset_runtime_path_cache()

    assert configured_models_dir() == tmp_path / "env-models"
    assert _normalise_endpoint(None) == "http://localhost:11500"

    reset_runtime_path_cache()
