"""Tests for the cross-platform installer helpers."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from install import (
    DEFAULT_OLLAMA_MODELS,
    HASH_MANIFEST_PATH,
    RUNTIME_CONFIG_PATH,
    InstallPaths,
    _hash_tree,
    _pull_ollama_models,
    _write_hash_manifest_entry,
    _write_runtime_config,
)


def test_write_runtime_config_persists_selected_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    paths = InstallPaths(
        install_root=tmp_path / "install-root",
        venv_dir=tmp_path / ".venv",
        models_dir=tmp_path / "models",
        hf_cache_dir=tmp_path / "hf-cache",
        ollama_endpoint="http://127.0.0.1:11435",
        ollama_bin="ollama",
    )

    _write_runtime_config(paths, tmp_path)

    payload = json.loads((tmp_path / RUNTIME_CONFIG_PATH).read_text(encoding="utf-8"))
    assert payload["models_dir"] == str(paths.models_dir)
    assert payload["hf_cache_dir"] == str(paths.hf_cache_dir)
    assert payload["ollama_endpoint"] == "http://127.0.0.1:11435"
    env_text = (tmp_path / RUNTIME_CONFIG_PATH).with_suffix(".env").read_text(encoding="utf-8")
    assert "BOOKS_TO_AUDIO_MODELS_DIR=" in env_text
    assert "BOOKS_TO_AUDIO_OLLAMA_ENDPOINT=http://127.0.0.1:11435" in env_text


def test_hash_tree_changes_when_file_changes(tmp_path: Path) -> None:
    folder = tmp_path / "models"
    folder.mkdir()
    model_file = folder / "config.json"
    model_file.write_text("{}", encoding="utf-8")
    first = _hash_tree(folder)

    model_file.write_text('{"changed": true}', encoding="utf-8")
    second = _hash_tree(folder)

    assert first["sha256"] != second["sha256"]
    assert second["files"] == 1


def test_write_hash_manifest_entry_overwrites_selected_label(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_hash_manifest_entry("models_dir", {"sha256": "one"})
    _write_hash_manifest_entry("models_dir", {"sha256": "two"})

    payload = json.loads(HASH_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert payload == {"models_dir": {"sha256": "two"}}


def test_pull_ollama_models_skips_already_present_model(tmp_path: Path, monkeypatch) -> None:
    paths = InstallPaths(
        install_root=tmp_path,
        venv_dir=tmp_path / ".venv",
        models_dir=tmp_path / "models",
        hf_cache_dir=tmp_path / "hf-cache",
        ollama_endpoint="http://127.0.0.1:11434",
        ollama_bin="ollama",
    )
    pulled: list[list[str]] = []

    def fake_subprocess_run(cmd, **_kwargs):  # noqa: ANN001
        if cmd[:2] == ["ollama", "show"]:
            return SimpleNamespace(returncode=0 if cmd[2] == DEFAULT_OLLAMA_MODELS[0] else 1)
        return SimpleNamespace(returncode=0, stdout="")

    monkeypatch.setattr("install.subprocess.run", fake_subprocess_run)
    monkeypatch.setattr("install._run", lambda cmd, _paths: pulled.append(cmd))

    _pull_ollama_models(paths, verify_hashes=False)

    assert pulled == [["ollama", "pull", DEFAULT_OLLAMA_MODELS[1]]]
