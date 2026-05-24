"""Tests for the cross-platform installer helpers."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from install import (
    DEFAULT_OLLAMA_MODELS,
    DEFAULT_TTS_HASH_MODEL_IDS,
    HASH_MANIFEST_PATH,
    INSTALL_TOOL_PACKAGES,
    OLLAMA_HASH_LABEL,
    RUNTIME_CONFIG_PATH,
    TTS_HASH_LABEL,
    InstallPaths,
    _command_available,
    _env_assignment,
    _hash_tree,
    _install_system_tools,
    _install_tts_models,
    _paint,
    _print_install_summary,
    _print_next_steps,
    _pull_ollama_models,
    _resolve_install_paths,
    _system_package_commands,
    _system_package_hint,
    _verified_hash_matches,
    _verify_or_write_hash,
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


def test_installer_entrypoints_do_not_route_through_wsl() -> None:
    for path in (Path("install.py"), Path("install.bat"), Path("install.sh")):
        assert "wsl" not in path.read_text(encoding="utf-8").lower(), path


def test_installer_wrappers_pause_without_requiring_enter() -> None:
    shell_text = Path("install.sh").read_text(encoding="utf-8")
    batch_text = Path("install.bat").read_text(encoding="utf-8").lower()

    assert "Press any key to exit terminal" in shell_text
    assert "Нажмите любую кнопку" in shell_text
    assert "BOOKS_TO_AUDIO_FROM_RUN_GUI" in shell_text
    assert "stty raw -echo" in shell_text
    assert "dd bs=1 count=1" in shell_text
    assert "pause >nul" in batch_text


def test_installer_wrappers_bootstrap_python_with_native_package_managers() -> None:
    shell_text = Path("install.sh").read_text(encoding="utf-8")
    batch_text = Path("install.bat").read_text(encoding="utf-8")

    assert "bootstrap_python()" in shell_text
    assert "brew install python@3.12" in shell_text
    assert "apt-get install -y python3 python3-venv python3-pip" in shell_text
    assert "dnf install -y python3 python3-pip" in shell_text
    assert "pacman -S --needed python python-pip" in shell_text
    assert "run_installer_with_python()" in shell_text
    assert "shift" in shell_text
    assert '"$python_cmd" install.py "$@"' in shell_text

    assert "winget install -e --id Python.Python.3.12 --scope user" in batch_text
    assert "--accept-package-agreements --accept-source-agreements" in batch_text
    assert "%LOCALAPPDATA%\\Programs\\Python\\Python312\\python.exe" in batch_text


def test_ci_linux_gui_job_installs_cjk_fonts() -> None:
    workflow_text = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "Install Linux GUI/OCR system packages" in workflow_text
    assert "fonts-noto-cjk" in workflow_text


def test_installer_summary_and_next_steps_are_bilingual(
    tmp_path: Path,
    capsys,
) -> None:
    paths = InstallPaths(
        install_root=tmp_path / "install-root",
        venv_dir=tmp_path / ".venv",
        models_dir=tmp_path / "models",
        hf_cache_dir=tmp_path / "hf-cache",
        ollama_models_dir=tmp_path / "ollama-models",
        ollama_endpoint="http://127.0.0.1:11434",
        ollama_bin="ollama",
        tesseract_cmd="tesseract",
        ffmpeg_bin="ffmpeg",
    )

    _print_install_summary(tmp_path, paths, {"gui", "ocr"})
    _print_next_steps(paths.venv_dir)

    out = capsys.readouterr().out
    assert "Project" in out and "/ Проект:" in out
    assert "Virtual environment" in out and "/ Виртуальное окружение:" in out
    assert "Models folder" in out and "/ Папка моделей:" in out
    assert "Ollama models folder" in out and "/ Папка моделей Ollama:" in out
    assert "Ollama endpoint/bin" in out and "/ Ollama адрес/команда:" in out
    assert "Install extras" in out and "/ Опции установки: gui, ocr" in out
    assert "Next steps / Следующие шаги:" in out
    assert "Activate venv / Активировать venv:" in out
    assert "Run GUI       / Запустить GUI:" in out
    assert "Run checks    / Проверить установку:" in out


def test_installer_paint_adds_ansi_only_for_tty(monkeypatch) -> None:
    monkeypatch.setattr("install._supports_color", lambda: True)
    assert _paint("status", "32") == "\x1b[32mstatus\x1b[0m"

    monkeypatch.setattr("install._supports_color", lambda: False)
    assert _paint("status", "32") == "status"


def test_installer_dry_run_overwrites_bilingual_log(tmp_path: Path) -> None:
    log_path = Path("install.log")
    log_path.write_text("OLD INSTALL LOG", encoding="utf-8")
    config_path = Path(RUNTIME_CONFIG_PATH)
    env_path = RUNTIME_CONFIG_PATH.with_suffix(".env")
    previous_config = config_path.read_text(encoding="utf-8") if config_path.exists() else None
    previous_env = env_path.read_text(encoding="utf-8") if env_path.exists() else None

    models_dir = tmp_path / "models"
    hf_cache_dir = tmp_path / "hf-cache"
    ollama_models_dir = tmp_path / "ollama-models"
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
                "--ollama-models-dir",
                str(ollama_models_dir),
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
        assert str(ollama_models_dir) in log_text
        assert runtime_config["models_dir"] == str(models_dir)
        assert runtime_config["hf_cache_dir"] == str(hf_cache_dir)
        assert runtime_config["ollama_models_dir"] == str(ollama_models_dir)
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
        ollama_models_dir=tmp_path / "ollama-models",
        ollama_endpoint="http://127.0.0.1:11435",
        ollama_bin="ollama",
        tesseract_cmd=str(tmp_path / "tools" / "tesseract.exe"),
        ffmpeg_bin=str(tmp_path / "tools" / "ffmpeg.exe"),
    )

    _write_runtime_config(paths, tmp_path)

    payload = json.loads((tmp_path / RUNTIME_CONFIG_PATH).read_text(encoding="utf-8"))
    assert payload["models_dir"] == str(paths.models_dir)
    assert payload["hf_cache_dir"] == str(paths.hf_cache_dir)
    assert payload["ollama_models_dir"] == str(paths.ollama_models_dir)
    assert payload["ollama_endpoint"] == "http://127.0.0.1:11435"
    assert payload["tesseract_cmd"] == str(paths.tesseract_cmd)
    assert payload["ffmpeg_bin"] == str(paths.ffmpeg_bin)
    env_text = (tmp_path / RUNTIME_CONFIG_PATH).with_suffix(".env").read_text(encoding="utf-8")
    assert "BOOKS_TO_AUDIO_MODELS_DIR=" in env_text
    assert f"BOOKS_TO_AUDIO_OLLAMA_MODELS_DIR={paths.ollama_models_dir}" in env_text
    assert f"OLLAMA_MODELS={paths.ollama_models_dir}" in env_text
    assert "BOOKS_TO_AUDIO_OLLAMA_ENDPOINT=http://127.0.0.1:11435" in env_text
    assert "BOOKS_TO_AUDIO_TESSERACT_CMD=" in env_text
    assert "BOOKS_TO_AUDIO_FFMPEG_BIN=" in env_text


def test_runtime_env_file_quotes_custom_paths_with_spaces(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    paths = InstallPaths(
        install_root=tmp_path / "Install Root",
        venv_dir=tmp_path / "Windows Venv",
        models_dir=tmp_path / "Audio Models",
        hf_cache_dir=tmp_path / "HF Cache",
        ollama_models_dir=tmp_path / "Ollama Models",
        ollama_endpoint="http://127.0.0.1:11434",
        ollama_bin="ollama",
        tesseract_cmd="C:/Program Files/Tesseract-OCR/tesseract.exe",
        ffmpeg_bin="D:/Media Tools/ffmpeg/bin/ffmpeg.exe",
    )

    _write_runtime_config(paths, tmp_path)

    env_text = (tmp_path / RUNTIME_CONFIG_PATH).with_suffix(".env").read_text(encoding="utf-8")
    assert _env_assignment("BOOKS_TO_AUDIO_MODELS_DIR", paths.models_dir) in env_text
    assert f"BOOKS_TO_AUDIO_MODELS_DIR='{paths.models_dir}'" in env_text
    assert "COMFYUI_MODELS_DIR='" in env_text
    assert "HF_HOME='" in env_text
    assert "OLLAMA_MODELS='" in env_text
    assert "BOOKS_TO_AUDIO_TESSERACT_CMD='C:/Program Files/Tesseract-OCR/tesseract.exe'" in env_text
    assert "BOOKS_TO_AUDIO_FFMPEG_BIN='D:/Media Tools/ffmpeg/bin/ffmpeg.exe'" in env_text


def test_interactive_installer_prompts_for_all_runtime_paths(
    tmp_path: Path,
    monkeypatch,
) -> None:
    answers = iter([
        str(tmp_path / "install-root"),
        str(tmp_path / "venv"),
        str(tmp_path / "models"),
        str(tmp_path / "hf-cache"),
        str(tmp_path / "ollama-models"),
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
        ollama_models_dir="",
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
    assert paths.ollama_models_dir == tmp_path / "ollama-models"
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


def test_verify_hash_stores_metadata_and_matches_intact_folder(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "config.json").write_text("{}", encoding="utf-8")
    metadata = {"models": list(DEFAULT_TTS_HASH_MODEL_IDS)}

    _verify_or_write_hash(TTS_HASH_LABEL, models_dir, metadata=metadata)

    manifest = json.loads(HASH_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest[TTS_HASH_LABEL]["metadata"] == metadata
    assert _verified_hash_matches(TTS_HASH_LABEL, models_dir, metadata=metadata) is True


def test_install_tts_models_skips_download_when_hash_manifest_matches(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "config.json").write_text("{}", encoding="utf-8")
    metadata = {"models": list(DEFAULT_TTS_HASH_MODEL_IDS)}
    _verify_or_write_hash(TTS_HASH_LABEL, models_dir, metadata=metadata)
    paths = InstallPaths(
        install_root=tmp_path,
        venv_dir=tmp_path / ".venv",
        models_dir=models_dir,
        hf_cache_dir=tmp_path / "hf-cache",
        ollama_models_dir=tmp_path / "ollama-models",
        ollama_endpoint="http://127.0.0.1:11434",
        ollama_bin="ollama",
        tesseract_cmd="tesseract",
        ffmpeg_bin="ffmpeg",
    )

    def fail_run(*_args, **_kwargs):  # noqa: ANN002
        raise AssertionError("download step should be skipped")

    monkeypatch.setattr("install._run", fail_run)

    _install_tts_models(tmp_path / ".venv" / "bin" / "python", paths, verify_hashes=True)


def test_install_tts_models_rejects_hash_mismatch_before_download(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    model_file = models_dir / "config.json"
    model_file.write_text("{}", encoding="utf-8")
    metadata = {"models": list(DEFAULT_TTS_HASH_MODEL_IDS)}
    _verify_or_write_hash(TTS_HASH_LABEL, models_dir, metadata=metadata)
    model_file.write_text('{"corrupt": true}', encoding="utf-8")
    paths = InstallPaths(
        install_root=tmp_path,
        venv_dir=tmp_path / ".venv",
        models_dir=models_dir,
        hf_cache_dir=tmp_path / "hf-cache",
        ollama_models_dir=tmp_path / "ollama-models",
        ollama_endpoint="http://127.0.0.1:11434",
        ollama_bin="ollama",
        tesseract_cmd="tesseract",
        ffmpeg_bin="ffmpeg",
    )

    with pytest.raises(SystemExit, match="Hash mismatch"):
        _install_tts_models(tmp_path / ".venv" / "bin" / "python", paths, verify_hashes=True)


def test_pull_ollama_models_skips_already_present_model(tmp_path: Path, monkeypatch) -> None:
    paths = InstallPaths(
        install_root=tmp_path,
        venv_dir=tmp_path / ".venv",
        models_dir=tmp_path / "models",
        hf_cache_dir=tmp_path / "hf-cache",
        ollama_models_dir=tmp_path / "ollama-models",
        ollama_endpoint="http://127.0.0.1:11434",
        ollama_bin="ollama",
        tesseract_cmd="tesseract",
        ffmpeg_bin="ffmpeg",
    )
    pulled: list[list[str]] = []

    def fake_subprocess_run(cmd, **kwargs):  # noqa: ANN001
        assert kwargs["env"]["OLLAMA_MODELS"] == str(paths.ollama_models_dir)
        assert kwargs["env"]["BOOKS_TO_AUDIO_OLLAMA_MODELS_DIR"] == str(paths.ollama_models_dir)
        if cmd[:2] == ["ollama", "show"]:
            return SimpleNamespace(returncode=0 if cmd[2] == DEFAULT_OLLAMA_MODELS[0] else 1)
        return SimpleNamespace(returncode=0, stdout="")

    monkeypatch.setattr("install.subprocess.run", fake_subprocess_run)
    monkeypatch.setattr("install._run", lambda cmd, _paths: pulled.append(cmd))

    _pull_ollama_models(paths, verify_hashes=False)

    assert pulled == [["ollama", "pull", DEFAULT_OLLAMA_MODELS[1]]]


def test_pull_ollama_models_skips_when_command_hash_matches(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = InstallPaths(
        install_root=tmp_path,
        venv_dir=tmp_path / ".venv",
        models_dir=tmp_path / "models",
        hf_cache_dir=tmp_path / "hf-cache",
        ollama_models_dir=tmp_path / "ollama-models",
        ollama_endpoint="http://127.0.0.1:11434",
        ollama_bin="ollama",
        tesseract_cmd="tesseract",
        ffmpeg_bin="ffmpeg",
    )
    list_output = "\n".join(DEFAULT_OLLAMA_MODELS)
    metadata = {
        "models": list(DEFAULT_OLLAMA_MODELS),
        "ollama_models_dir": str(paths.ollama_models_dir),
    }
    _write_hash_manifest_entry(
        OLLAMA_HASH_LABEL,
        {
            "sha256": hashlib.sha256(list_output.encode("utf-8")).hexdigest(),
            "source": "ollama list",
            "metadata": metadata,
        },
    )
    calls: list[list[str]] = []

    def fake_subprocess_run(cmd, **_kwargs):  # noqa: ANN001
        calls.append(cmd)
        assert cmd == ["ollama", "list"]
        return SimpleNamespace(returncode=0, stdout=list_output, stderr="")

    def fail_run(*_args, **_kwargs):  # noqa: ANN002
        raise AssertionError("pull step should be skipped when Ollama hash matches")

    monkeypatch.setattr("install.subprocess.run", fake_subprocess_run)
    monkeypatch.setattr("install._run", fail_run)

    _pull_ollama_models(paths, verify_hashes=True)

    assert calls == [["ollama", "list"]]


def test_pull_ollama_models_records_hash_metadata_after_pull(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = InstallPaths(
        install_root=tmp_path,
        venv_dir=tmp_path / ".venv",
        models_dir=tmp_path / "models",
        hf_cache_dir=tmp_path / "hf-cache",
        ollama_models_dir=tmp_path / "ollama-models",
        ollama_endpoint="http://127.0.0.1:11434",
        ollama_bin="ollama",
        tesseract_cmd="tesseract",
        ffmpeg_bin="ffmpeg",
    )
    list_output = "\n".join(DEFAULT_OLLAMA_MODELS)
    pulled: list[list[str]] = []

    def fake_subprocess_run(cmd, **_kwargs):  # noqa: ANN001
        if cmd[:2] == ["ollama", "show"]:
            return SimpleNamespace(returncode=1, stdout="", stderr="")
        if cmd == ["ollama", "list"]:
            return SimpleNamespace(returncode=0, stdout=list_output, stderr="")
        raise AssertionError(cmd)

    monkeypatch.setattr("install.subprocess.run", fake_subprocess_run)
    monkeypatch.setattr("install._run", lambda cmd, _paths: pulled.append(cmd))

    _pull_ollama_models(paths, verify_hashes=True)

    manifest = json.loads(HASH_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert pulled == [["ollama", "pull", model] for model in DEFAULT_OLLAMA_MODELS]
    assert manifest[OLLAMA_HASH_LABEL]["metadata"] == {
        "models": list(DEFAULT_OLLAMA_MODELS),
        "ollama_models_dir": str(paths.ollama_models_dir),
    }
    assert manifest[OLLAMA_HASH_LABEL]["source"] == "ollama list"


def test_pull_ollama_models_rejects_hash_mismatch_before_pull(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = InstallPaths(
        install_root=tmp_path,
        venv_dir=tmp_path / ".venv",
        models_dir=tmp_path / "models",
        hf_cache_dir=tmp_path / "hf-cache",
        ollama_models_dir=tmp_path / "ollama-models",
        ollama_endpoint="http://127.0.0.1:11434",
        ollama_bin="ollama",
        tesseract_cmd="tesseract",
        ffmpeg_bin="ffmpeg",
    )
    _write_hash_manifest_entry(
        OLLAMA_HASH_LABEL,
        {
            "sha256": "not-current",
            "source": "ollama list",
            "metadata": {
                "models": list(DEFAULT_OLLAMA_MODELS),
                "ollama_models_dir": str(paths.ollama_models_dir),
            },
        },
    )

    def fake_subprocess_run(cmd, **_kwargs):  # noqa: ANN001
        assert cmd == ["ollama", "list"]
        return SimpleNamespace(returncode=0, stdout="\n".join(DEFAULT_OLLAMA_MODELS), stderr="")

    def fail_run(*_args, **_kwargs):  # noqa: ANN002
        raise AssertionError("pull step should not run after hash mismatch")

    monkeypatch.setattr("install.subprocess.run", fake_subprocess_run)
    monkeypatch.setattr("install._run", fail_run)

    with pytest.raises(SystemExit, match="Hash mismatch"):
        _pull_ollama_models(paths, verify_hashes=True)


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
        ollama_models_dir=tmp_path / "ollama-models",
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


def test_system_package_hints_are_derived_from_native_command_argv(monkeypatch) -> None:
    monkeypatch.setattr("install.platform.system", lambda: "Linux")
    monkeypatch.setattr("install._linux_id_like", lambda: {"linux", "ubuntu"})

    commands = _system_package_commands({"ocr", "audio", "gui"})
    hint = _system_package_hint({"ocr", "audio", "gui"})

    assert commands[0] == ["sudo", "apt-get", "update"]
    assert commands[1][:5] == ["sudo", "apt-get", "install", "-y", "tesseract-ocr"]
    assert "&&" in hint
    assert {
        "tesseract-ocr-eng",
        "tesseract-ocr-rus",
        "tesseract-ocr-chi-sim",
        "tesseract-ocr-kaz",
        "tesseract-ocr-uzb",
    }.issubset(commands[1])
    assert "libxcb-cursor0" in commands[1]
    assert "fonts-noto-cjk" in commands[1]


@pytest.mark.parametrize(
    ("distro", "expected"),
    [
        (
            {"linux", "fedora"},
            {
                "tesseract-langpack-eng",
                "tesseract-langpack-rus",
                "tesseract-langpack-chi_sim",
                "tesseract-langpack-kaz",
                "tesseract-langpack-uzb",
            },
        ),
        (
            {"linux", "arch"},
            {
                "tesseract-data-eng",
                "tesseract-data-rus",
                "tesseract-data-chi_sim",
                "tesseract-data-kaz",
                "tesseract-data-uzb",
            },
        ),
    ],
)
def test_linux_install_includes_all_supported_tesseract_languages(
    monkeypatch,
    distro: set[str],
    expected: set[str],
) -> None:
    monkeypatch.setattr("install.platform.system", lambda: "Linux")
    monkeypatch.setattr("install._linux_id_like", lambda: distro)

    commands = _system_package_commands({"ocr"})
    flattened = {part for command in commands for part in command}

    assert expected.issubset(flattened)


def test_install_system_tools_runs_native_commands_without_shell(monkeypatch) -> None:
    monkeypatch.setattr("install.platform.system", lambda: "Windows")
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(command, **kwargs):  # noqa: ANN001
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("install.subprocess.run", fake_run)

    _install_system_tools({"ocr", "audio"})

    assert [call[0] for call in calls] == [
        ["winget", "install", "UB-Mannheim.TesseractOCR"],
        ["winget", "install", "Gyan.FFmpeg"],
    ]
    assert all(call[1] == {"check": True} for call in calls)
