"""Tests for the cross-platform installer helpers."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from install import (
    DEFAULT_OLLAMA_MODELS,
    HASH_MANIFEST_PATH,
    INSTALL_TOOL_PACKAGES,
    RUNTIME_CONFIG_PATH,
    InstallPaths,
    _command_available,
    _hash_tree,
    _pull_ollama_models,
    _resolve_install_paths,
    _write_hash_manifest_entry,
    _write_runtime_config,
)


def test_installer_always_installs_packaging_build_tool() -> None:
    assert "build" in INSTALL_TOOL_PACKAGES


def test_installer_entrypoints_do_not_contain_mojibake() -> None:
    markers = ("РЈ", "Рџ", "СЃ", "вЂ", "К»")
    for path in (Path("install.py"), Path("install.bat"), Path("install.sh")):
        text = path.read_text(encoding="utf-8")
        assert not any(marker in text for marker in markers), path


def test_installer_dry_run_overwrites_bilingual_log(tmp_path: Path) -> None:
    log_path = Path("install.log")
    log_path.write_text("OLD INSTALL LOG", encoding="utf-8")
    config_path = Path(RUNTIME_CONFIG_PATH)
    env_path = RUNTIME_CONFIG_PATH.with_suffix(".env")
    previous_config = config_path.read_text(encoding="utf-8") if config_path.exists() else None
    previous_env = env_path.read_text(encoding="utf-8") if env_path.exists() else None

    models_dir = tmp_path / "models"
    hf_cache_dir = tmp_path / "hf-cache"
    try:
        result = subprocess.run(
            [
                sys.executable,
                "install.py",
                "--dry-run",
                "--yes",
                "--no-system-check",
                "--venv",
                str(tmp_path / ".venv"),
                "--install-root",
                str(tmp_path / "install-root"),
                "--models-dir",
                str(models_dir),
                "--hf-cache-dir",
                str(hf_cache_dir),
                "--tesseract-bin",
                str(tmp_path / "tools" / "tesseract.exe"),
                "--ffmpeg-bin",
                str(tmp_path / "tools" / "ffmpeg.exe"),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )

        log_text = log_path.read_text(encoding="utf-8")
        runtime_config = json.loads(Path(RUNTIME_CONFIG_PATH).read_text(encoding="utf-8"))
        assert "OLD INSTALL LOG" not in log_text
        assert "Books to Audio installer" in result.stdout
        assert "Установщик Books to Audio" in result.stdout
        assert "Пробный запуск" in log_text
        assert str(models_dir) in log_text
        assert str(hf_cache_dir) in log_text
        assert runtime_config["models_dir"] == str(models_dir)
        assert runtime_config["hf_cache_dir"] == str(hf_cache_dir)
        assert runtime_config["tesseract_cmd"] == str(tmp_path / "tools" / "tesseract.exe")
        assert "BOOKS_TO_AUDIO_RUNTIME_CONFIG" in env_path.read_text(encoding="utf-8")
    finally:
        if previous_config is None:
            config_path.unlink(missing_ok=True)
        else:
            config_path.write_text(previous_config, encoding="utf-8")
        if previous_env is None:
            env_path.unlink(missing_ok=True)
        else:
            env_path.write_text(previous_env, encoding="utf-8")


def test_write_runtime_config_persists_selected_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    paths = InstallPaths(
        install_root=tmp_path / "install-root",
        venv_dir=tmp_path / ".venv",
        models_dir=tmp_path / "models",
        hf_cache_dir=tmp_path / "hf-cache",
        ollama_endpoint="http://127.0.0.1:11435",
        ollama_bin="ollama",
        tesseract_cmd=str(tmp_path / "tools" / "tesseract.exe"),
        ffmpeg_bin=str(tmp_path / "tools" / "ffmpeg.exe"),
    )

    _write_runtime_config(paths, tmp_path)

    payload = json.loads((tmp_path / RUNTIME_CONFIG_PATH).read_text(encoding="utf-8"))
    assert payload["models_dir"] == str(paths.models_dir)
    assert payload["hf_cache_dir"] == str(paths.hf_cache_dir)
    assert payload["ollama_endpoint"] == "http://127.0.0.1:11435"
    assert payload["tesseract_cmd"] == str(paths.tesseract_cmd)
    assert payload["ffmpeg_bin"] == str(paths.ffmpeg_bin)
    env_text = (tmp_path / RUNTIME_CONFIG_PATH).with_suffix(".env").read_text(encoding="utf-8")
    assert "BOOKS_TO_AUDIO_MODELS_DIR=" in env_text
    assert "BOOKS_TO_AUDIO_OLLAMA_ENDPOINT=http://127.0.0.1:11435" in env_text
    assert "BOOKS_TO_AUDIO_TESSERACT_CMD=" in env_text
    assert "BOOKS_TO_AUDIO_FFMPEG_BIN=" in env_text


def test_interactive_installer_prompts_for_all_runtime_paths(
    tmp_path: Path,
    monkeypatch,
) -> None:
    answers = iter([
        str(tmp_path / "install-root"),
        str(tmp_path / "venv"),
        str(tmp_path / "models"),
        str(tmp_path / "hf-cache"),
        "http://127.0.0.1:11435",
        str(tmp_path / "ollama.exe"),
        str(tmp_path / "tesseract.exe"),
        str(tmp_path / "ffmpeg.exe"),
    ])
    args = SimpleNamespace(
        dry_run=False,
        yes=False,
        interactive=True,
        install_root="",
        venv=".venv",
        models_dir="",
        hf_cache_dir="",
        ollama_endpoint="",
        ollama_bin="",
        tesseract_bin="",
        ffmpeg_bin="",
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    paths = _resolve_install_paths(args, tmp_path)

    assert paths.install_root == tmp_path / "install-root"
    assert paths.venv_dir == tmp_path / "venv"
    assert paths.models_dir == tmp_path / "models"
    assert paths.hf_cache_dir == tmp_path / "hf-cache"
    assert paths.ollama_endpoint == "http://127.0.0.1:11435"
    assert paths.ollama_bin == str(tmp_path / "ollama.exe")
    assert paths.tesseract_cmd == str(tmp_path / "tesseract.exe")
    assert paths.ffmpeg_bin == str(tmp_path / "ffmpeg.exe")


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
        tesseract_cmd="tesseract",
        ffmpeg_bin="ffmpeg",
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


def test_command_available_accepts_explicit_tool_path(tmp_path: Path) -> None:
    tool = tmp_path / "tools" / "tesseract.exe"
    tool.parent.mkdir()
    tool.write_text("", encoding="utf-8")

    assert _command_available(str(tool))
    assert not _command_available(str(tmp_path / "missing.exe"))


def test_system_dependency_notes_are_bilingual(tmp_path: Path, capsys) -> None:
    from install import _print_system_dependency_notes

    paths = InstallPaths(
        install_root=tmp_path,
        venv_dir=tmp_path / ".venv",
        models_dir=tmp_path / "models",
        hf_cache_dir=tmp_path / "hf-cache",
        ollama_endpoint="http://localhost:11434",
        ollama_bin="ollama",
        tesseract_cmd=str(tmp_path / "missing-tesseract"),
        ffmpeg_bin=str(tmp_path / "missing-ffmpeg"),
    )

    _print_system_dependency_notes({"ocr", "audio"}, paths)

    out = capsys.readouterr().out
    assert "System dependency notes / Системные зависимости" in out
    assert "Tesseract was not found" in out
    assert "Tesseract не найден" in out
    assert "FFmpeg was not found" in out
    assert "FFmpeg не найден" in out
