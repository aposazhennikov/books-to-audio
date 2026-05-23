"""Runtime path configuration written by the cross-platform installer."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

DEFAULT_OLLAMA_ENDPOINT = "http://localhost:11434"
RUNTIME_CONFIG_ENV = "BOOKS_TO_AUDIO_RUNTIME_CONFIG"
OLLAMA_ENDPOINT_ENV = "BOOKS_TO_AUDIO_OLLAMA_ENDPOINT"
MODELS_DIR_ENV = "BOOKS_TO_AUDIO_MODELS_DIR"
HF_HOME_ENV = "HF_HOME"


def project_root() -> Path:
    """Return the editable checkout root when running from this repository."""
    return Path(__file__).resolve().parents[2]


def runtime_config_path() -> Path:
    """Return the local runtime config path."""
    configured = os.environ.get(RUNTIME_CONFIG_ENV)
    if configured:
        return Path(configured).expanduser()
    return project_root() / "data" / "local_runtime_paths.json"


@lru_cache(maxsize=1)
def load_runtime_paths() -> dict[str, Any]:
    """Load installer-written runtime path configuration if present."""
    path = runtime_config_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def reset_runtime_path_cache() -> None:
    """Clear cached runtime paths for tests or after rewriting config."""
    load_runtime_paths.cache_clear()


def configured_path(key: str, env_var: str | None = None) -> Path | None:
    """Return a configured path from env first, then installer config."""
    if env_var:
        value = os.environ.get(env_var)
        if value:
            return Path(value).expanduser()
    value = load_runtime_paths().get(key)
    if not value:
        return None
    return Path(str(value)).expanduser()


def configured_models_dir() -> Path | None:
    """Return configured shared TTS/ComfyUI models directory if set."""
    return configured_path("models_dir", MODELS_DIR_ENV)


def configured_hf_cache_dir() -> Path | None:
    """Return configured Hugging Face cache directory if set."""
    return configured_path("hf_cache_dir", HF_HOME_ENV)


def configured_ollama_endpoint(default: str = DEFAULT_OLLAMA_ENDPOINT) -> str:
    """Return configured Ollama endpoint from env, config, or default."""
    value = os.environ.get(OLLAMA_ENDPOINT_ENV) or load_runtime_paths().get("ollama_endpoint")
    return str(value or default).strip() or default
