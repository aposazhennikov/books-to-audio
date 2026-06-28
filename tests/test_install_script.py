"""Tests for the cross-platform installer helpers."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from install import (
    DEFAULT_EXTRAS,
    DEFAULT_OLLAMA_MODELS,
    DEFAULT_TESSDATA_LANGS,
    DEFAULT_TTS_HASH_MODEL_IDS,
    HASH_MANIFEST_PATH,
    INSTALL_TOOL_PACKAGES,
    OLLAMA_HASH_LABEL,
    RUNTIME_CONFIG_PATH,
    TESSDATA_FAST_BASE_URL,
    TESSDATA_HASH_LABEL,
    TTS_HASH_LABEL,
    InstallPaths,
    _command_available,
    _download_tessdata,
    _env_assignment,
    _hash_tree,
    _install_system_tools,
    _install_tts_models,
    _ollama_manifest_path,
    _paint,
    _parse_args,
    _print_install_summary,
    _print_next_steps,
    _pull_ollama_models,
    _resolve_install_paths,
    _resolve_log_path,
    _selected_tts_model_ids,
    _system_package_commands,
    _system_package_hint,
    _verified_hash_matches,
    _verify_or_write_hash,
    _write_hash_manifest_entry,
    _write_runtime_config,
)


def test_installer_always_installs_packaging_build_tool() -> None:
    assert "build" in INSTALL_TOOL_PACKAGES


def test_installer_exposes_asr_extra_flag(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["install.py", "--with-asr", "--minimal"])
    args = _parse_args()
    from install import _resolve_extras

    assert _resolve_extras(args) == {"asr"}


def test_installer_exposes_audio_qa_runtime_extra_flag(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["install.py", "--with-audio-qa-runtime", "--minimal"])
    args = _parse_args()
    from install import VERIFY_MODULES, _resolve_extras

    assert _resolve_extras(args) == {"audio-qa-runtime"}
    assert VERIFY_MODULES["audio-qa-runtime"] == [
        "accelerate",
        "qwen_omni_utils",
        "transformers",
        "vllm",
    ]


def test_installer_default_profile_includes_perceptual_qa() -> None:
    assert "perceptual" in DEFAULT_EXTRAS


def test_installer_can_skip_perceptual_extra(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["install.py", "--without-perceptual"])
    args = _parse_args()
    from install import _resolve_extras

    extras = _resolve_extras(args)

    assert "perceptual" not in extras
    assert {"audio", "gui", "llm", "ocr"}.issubset(extras)


def test_installer_exposes_perceptual_model_download_flag(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["install.py", "--download-perceptual-models"])
    args = _parse_args()

    assert args.download_perceptual_models is True


def test_installer_tts_model_selection_defaults_to_recommended_qwen() -> None:
    assert _selected_tts_model_ids([]) == list(DEFAULT_TTS_HASH_MODEL_IDS)


def test_installer_tts_model_selection_supports_requested_alternatives() -> None:
    assert _selected_tts_model_ids(["fish-speech-1.5", "f5-tts", "xtts-v2", "cosyvoice-3"]) == [
        "fish-speech-1.5",
        "f5-tts",
        "xtts-v2",
        "cosyvoice-3",
    ]


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
    assert "say info \\" in shell_text
    assert "BOOKS_TO_AUDIO_FROM_RUN_GUI" in shell_text
    assert "stty raw -echo" in shell_text
    assert "dd bs=1 count=1" in shell_text
    assert "color %c_info%" in batch_text
    assert "pause >nul" in batch_text


def test_install_wrappers_use_native_line_endings() -> None:
    batch_bytes = Path("install.bat").read_bytes()
    shell_bytes = Path("install.sh").read_bytes()

    assert batch_bytes.count(b"\n") == batch_bytes.count(b"\r\n")
    assert shell_bytes.count(b"\r\n") == 0


def test_installer_wrappers_use_colored_bilingual_status_helpers() -> None:
    shell_text = Path("install.sh").read_text(encoding="utf-8")
    batch_text = Path("install.bat").read_text(encoding="utf-8")

    assert "C_INFO=$(printf '\\033[36m')" in shell_text
    assert "say()" in shell_text
    assert "say info \\" in shell_text
    assert "say err \\" in shell_text
    assert "Trying to install Python 3 with the native system package manager" in shell_text
    assert "Пробую установить Python 3 нативным менеджером пакетов системы" in shell_text

    assert "set \"C_INFO=0B\"" in batch_text
    assert "color %C_INFO%" in batch_text
    assert "color %C_ERR%" in batch_text
    assert "Installing Python 3.12 with native Windows winget" in batch_text
    assert "Устанавливаю Python 3.12 через нативный Windows winget" in batch_text


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
        tessdata_dir=tmp_path / "tessdata",
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
    assert "Tesseract tessdata" in out and "/ Языковые данные Tesseract:" in out
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
                "--tessdata-dir",
                str(tmp_path / "tools" / "tessdata"),
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
        assert str(tmp_path / "tools" / "tessdata") in log_text
        assert runtime_config["models_dir"] == str(models_dir)
        assert runtime_config["hf_cache_dir"] == str(hf_cache_dir)
        assert runtime_config["ollama_models_dir"] == str(ollama_models_dir)
        assert runtime_config["tesseract_cmd"] == str(tmp_path / "tools" / "tesseract.exe")
        assert runtime_config["tessdata_dir"] == str(tmp_path / "tools" / "tessdata")
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


@pytest.mark.skipif(sys.platform != "win32", reason="Windows batch wrapper smoke")
def test_windows_install_wrapper_dry_run_has_no_argument_fallthrough(tmp_path: Path) -> None:
    config_path = Path(RUNTIME_CONFIG_PATH)
    env_path = RUNTIME_CONFIG_PATH.with_suffix(".env")
    previous_config = config_path.read_text(encoding="utf-8") if config_path.exists() else None
    previous_env = env_path.read_text(encoding="utf-8") if env_path.exists() else None
    env = os.environ.copy()
    env["BOOKS_TO_AUDIO_FROM_RUN_GUI"] = "1"

    try:
        result = subprocess.run(
            [
                "cmd",
                "/c",
                "install.bat",
                "--dry-run",
                "--yes",
                "--no-system-check",
                "--log-path",
                str(tmp_path / "wrapper.log"),
                "--install-root",
                str(tmp_path / "install-root"),
                "--venv",
                str(tmp_path / "wrapper-venv"),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            check=True,
        )

        combined = f"{result.stdout}\n{result.stderr}"
        assert "Books to Audio installer" in combined
        assert "Would run:" in combined
        assert "not recognized as an internal or external command" not in combined
        assert "The AT command has been deprecated" not in combined
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
        tessdata_dir=tmp_path / "tools" / "tessdata",
        ffmpeg_bin=str(tmp_path / "tools" / "ffmpeg.exe"),
    )

    _write_runtime_config(paths, tmp_path)

    payload = json.loads((tmp_path / RUNTIME_CONFIG_PATH).read_text(encoding="utf-8"))
    assert payload["models_dir"] == str(paths.models_dir)
    assert payload["hf_cache_dir"] == str(paths.hf_cache_dir)
    assert payload["ollama_models_dir"] == str(paths.ollama_models_dir)
    assert payload["ollama_endpoint"] == "http://127.0.0.1:11435"
    assert payload["tesseract_cmd"] == str(paths.tesseract_cmd)
    assert payload["tessdata_dir"] == str(paths.tessdata_dir)
    assert payload["ffmpeg_bin"] == str(paths.ffmpeg_bin)
    env_text = (tmp_path / RUNTIME_CONFIG_PATH).with_suffix(".env").read_text(encoding="utf-8")
    assert "BOOKS_TO_AUDIO_MODELS_DIR=" in env_text
    assert f"BOOKS_TO_AUDIO_OLLAMA_MODELS_DIR={paths.ollama_models_dir}" in env_text
    assert f"OLLAMA_MODELS={paths.ollama_models_dir}" in env_text
    assert "BOOKS_TO_AUDIO_OLLAMA_ENDPOINT=http://127.0.0.1:11435" in env_text
    assert "BOOKS_TO_AUDIO_TESSERACT_CMD=" in env_text
    assert f"BOOKS_TO_AUDIO_TESSDATA_DIR={paths.tessdata_dir}" in env_text
    assert f"TESSDATA_PREFIX={paths.tessdata_dir}" in env_text
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
        tessdata_dir=tmp_path / "Tesseract Data",
        ffmpeg_bin="D:/Media Tools/ffmpeg/bin/ffmpeg.exe",
    )

    _write_runtime_config(paths, tmp_path)

    env_text = (tmp_path / RUNTIME_CONFIG_PATH).with_suffix(".env").read_text(encoding="utf-8")
    assert _env_assignment("BOOKS_TO_AUDIO_MODELS_DIR", paths.models_dir) in env_text
    assert f"BOOKS_TO_AUDIO_MODELS_DIR='{paths.models_dir}'" in env_text
    assert "COMFYUI_MODELS_DIR='" in env_text
    assert "HF_HOME='" in env_text
    assert "OLLAMA_MODELS='" in env_text
    assert "BOOKS_TO_AUDIO_OLLAMA_BIN=ollama" in env_text
    assert "BOOKS_TO_AUDIO_TESSERACT_CMD='C:/Program Files/Tesseract-OCR/tesseract.exe'" in env_text
    assert f"BOOKS_TO_AUDIO_TESSDATA_DIR='{tmp_path / 'Tesseract Data'}'" in env_text
    assert f"TESSDATA_PREFIX='{tmp_path / 'Tesseract Data'}'" in env_text
    assert "BOOKS_TO_AUDIO_FFMPEG_BIN='D:/Media Tools/ffmpeg/bin/ffmpeg.exe'" in env_text


def test_resolve_log_path_accepts_custom_absolute_and_relative_paths(tmp_path: Path) -> None:
    absolute = tmp_path / "logs" / "install.log"

    assert _resolve_log_path("", tmp_path) == tmp_path / "install.log"
    assert _resolve_log_path("logs/custom.log", tmp_path) == (tmp_path / "logs" / "custom.log").resolve()
    assert _resolve_log_path(str(absolute), tmp_path) == absolute.resolve()


def test_installer_dry_run_can_write_custom_log_path(tmp_path: Path) -> None:
    custom_log = tmp_path / "logs" / "custom-install.log"
    custom_log.parent.mkdir()
    custom_log.write_text("OLD CUSTOM LOG", encoding="utf-8")
    config_path = Path(RUNTIME_CONFIG_PATH)
    env_path = RUNTIME_CONFIG_PATH.with_suffix(".env")
    previous_config = config_path.read_text(encoding="utf-8") if config_path.exists() else None
    previous_env = env_path.read_text(encoding="utf-8") if env_path.exists() else None

    try:
        subprocess.run(
            [
                sys.executable,
                "install.py",
                "--dry-run",
                "--yes",
                "--no-system-check",
                "--log-path",
                str(custom_log),
                "--venv",
                str(tmp_path / ".venv"),
                "--install-root",
                str(tmp_path / "install-root"),
                "--ollama-bin",
                str(tmp_path / "tools" / "ollama.exe"),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )

        log_text = custom_log.read_text(encoding="utf-8")
        env_text = env_path.read_text(encoding="utf-8")
        assert "OLD CUSTOM LOG" not in log_text
        assert "Books to Audio installer" in log_text
        assert str(custom_log) in log_text
        assert f"BOOKS_TO_AUDIO_OLLAMA_BIN={tmp_path / 'tools' / 'ollama.exe'}" in env_text
    finally:
        if previous_config is None:
            config_path.unlink(missing_ok=True)
        else:
            config_path.write_text(previous_config, encoding="utf-8")
        if previous_env is None:
            env_path.unlink(missing_ok=True)
        else:
            env_path.write_text(previous_env, encoding="utf-8")


def test_interactive_dry_run_prompts_paths_and_writes_runtime_config(tmp_path: Path) -> None:
    log_path = tmp_path / "interactive-install.log"
    config_path = Path(RUNTIME_CONFIG_PATH)
    env_path = RUNTIME_CONFIG_PATH.with_suffix(".env")
    previous_config = config_path.read_text(encoding="utf-8") if config_path.exists() else None
    previous_env = env_path.read_text(encoding="utf-8") if env_path.exists() else None
    answers = "\n".join(
        [
            str(tmp_path / "install-root"),
            str(tmp_path / "venv"),
            str(tmp_path / "models"),
            str(tmp_path / "hf-cache"),
            str(tmp_path / "ollama-models"),
            "http://127.0.0.1:11436",
            str(tmp_path / "tools" / "ollama.exe"),
            str(tmp_path / "ComfyUI"),
            "http://127.0.0.1:8189",
            str(tmp_path / "tools" / "tesseract.exe"),
            str(tmp_path / "tools" / "tessdata"),
            str(tmp_path / "tools" / "ffmpeg.exe"),
            "n",
            "n",
            "n",
                "n",
                "n",
                "n",
                "n",
                "n",
            ]
        ) + "\n"

    try:
        result = subprocess.run(
            [
                sys.executable,
                "install.py",
                "--interactive",
                "--dry-run",
                "--no-system-check",
                "--log-path",
                str(log_path),
            ],
            input=answers,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )

        stdout = result.stdout
        log_text = log_path.read_text(encoding="utf-8")
        runtime_config = json.loads(config_path.read_text(encoding="utf-8"))
        assert "Install/data root / Папка установки/данных" in stdout
        assert "Ollama models folder / Папка моделей Ollama" in stdout
        assert "ComfyUI root folder / Папка ComfyUI" in stdout
        assert "Tesseract tessdata folder / Папка языковых данных Tesseract" in stdout
        assert "Install native Ollama if missing?" in stdout
        assert "Pull Qwen3 Ollama 8B/4B models now?" in stdout
        assert "Install or prepare local ComfyUI plus Qwen3-TTS custom nodes?" in stdout
        assert "Would run:" in stdout
        assert "wsl.exe" not in stdout.lower()
        assert "bash -lc" not in stdout.lower()
        assert "Пробный запуск" in log_text
        assert runtime_config["install_root"] == str(tmp_path / "install-root")
        assert runtime_config["venv_dir"] == str(tmp_path / "venv")
        assert runtime_config["models_dir"] == str(tmp_path / "models")
        assert runtime_config["hf_cache_dir"] == str(tmp_path / "hf-cache")
        assert runtime_config["ollama_models_dir"] == str(tmp_path / "ollama-models")
        assert runtime_config["ollama_endpoint"] == "http://127.0.0.1:11436"
        assert runtime_config["ollama_bin"] == str(tmp_path / "tools" / "ollama.exe")
        assert runtime_config["comfyui_root"] == str(tmp_path / "ComfyUI")
        assert runtime_config["comfyui_url"] == "http://127.0.0.1:8189"
        assert runtime_config["tesseract_cmd"] == str(tmp_path / "tools" / "tesseract.exe")
        assert runtime_config["tessdata_dir"] == str(tmp_path / "tools" / "tessdata")
        assert runtime_config["ffmpeg_bin"] == str(tmp_path / "tools" / "ffmpeg.exe")
    finally:
        if previous_config is None:
            config_path.unlink(missing_ok=True)
        else:
            config_path.write_text(previous_config, encoding="utf-8")
        if previous_env is None:
            env_path.unlink(missing_ok=True)
        else:
            env_path.write_text(previous_env, encoding="utf-8")


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
        str(tmp_path / "ComfyUI"),
        "http://127.0.0.1:8189",
        str(tmp_path / "tesseract.exe"),
        str(tmp_path / "tessdata"),
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
        tessdata_dir="",
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
    assert paths.comfyui_root == tmp_path / "ComfyUI"
    assert paths.comfyui_url == "http://127.0.0.1:8189"
    assert paths.tesseract_cmd == str(tmp_path / "tesseract.exe")
    assert paths.tessdata_dir == tmp_path / "tessdata"
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
    first_manifest = _ollama_manifest_path(paths.ollama_models_dir, DEFAULT_OLLAMA_MODELS[0])
    first_manifest.parent.mkdir(parents=True)
    first_manifest.write_text("{}", encoding="utf-8")

    def fake_subprocess_run(cmd, **kwargs):  # noqa: ANN001
        assert kwargs["env"]["OLLAMA_MODELS"] == str(paths.ollama_models_dir)
        assert kwargs["env"]["BOOKS_TO_AUDIO_OLLAMA_MODELS_DIR"] == str(paths.ollama_models_dir)
        return SimpleNamespace(returncode=0, stdout="")

    monkeypatch.setattr("install.subprocess.run", fake_subprocess_run)

    def fake_run(cmd, _paths):  # noqa: ANN001
        pulled.append(cmd)
        manifest = _ollama_manifest_path(paths.ollama_models_dir, cmd[-1])
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text("{}", encoding="utf-8")

    monkeypatch.setattr("install._run", fake_run)

    _pull_ollama_models(paths, verify_hashes=False)

    assert pulled == [["ollama", "pull", DEFAULT_OLLAMA_MODELS[1]]]


def test_pull_ollama_models_does_not_trust_global_server_for_custom_folder(
    tmp_path: Path,
    monkeypatch,
) -> None:
    paths = InstallPaths(
        install_root=tmp_path,
        venv_dir=tmp_path / ".venv",
        models_dir=tmp_path / "models",
        hf_cache_dir=tmp_path / "hf-cache",
        ollama_models_dir=tmp_path / "custom-ollama-models",
        ollama_endpoint="http://127.0.0.1:11434",
        ollama_bin="ollama",
        tesseract_cmd="tesseract",
        ffmpeg_bin="ffmpeg",
    )
    pulled: list[list[str]] = []

    def fake_subprocess_run(*_args, **_kwargs):  # noqa: ANN002
        raise AssertionError("Custom model folders must be checked by files, not global ollama show")

    def fake_run(cmd, _paths):  # noqa: ANN001
        pulled.append(cmd)
        manifest = _ollama_manifest_path(paths.ollama_models_dir, cmd[-1])
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text("{}", encoding="utf-8")

    monkeypatch.setattr("install.subprocess.run", fake_subprocess_run)
    monkeypatch.setattr("install._run", fake_run)

    _pull_ollama_models(paths, verify_hashes=False)

    assert pulled == [["ollama", "pull", model] for model in DEFAULT_OLLAMA_MODELS]


def test_pull_ollama_models_skips_when_file_hash_matches(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    ollama_models_dir = tmp_path / "ollama-models"
    ollama_models_dir.mkdir()
    (ollama_models_dir / "models" / "manifests").mkdir(parents=True)
    (ollama_models_dir / "models" / "manifests" / "qwen3-8b.json").write_text(
        "{}",
        encoding="utf-8",
    )
    paths = InstallPaths(
        install_root=tmp_path,
        venv_dir=tmp_path / ".venv",
        models_dir=tmp_path / "models",
        hf_cache_dir=tmp_path / "hf-cache",
        ollama_models_dir=ollama_models_dir,
        ollama_endpoint="http://127.0.0.1:11434",
        ollama_bin="ollama",
        tesseract_cmd="tesseract",
        ffmpeg_bin="ffmpeg",
    )
    metadata = {
        "models": list(DEFAULT_OLLAMA_MODELS),
        "ollama_models_dir": str(paths.ollama_models_dir),
    }
    _verify_or_write_hash(OLLAMA_HASH_LABEL, paths.ollama_models_dir, metadata=metadata)

    def fail_run(*_args, **_kwargs):  # noqa: ANN002
        raise AssertionError("Ollama should not be called when file hash matches")

    monkeypatch.setattr("install.subprocess.run", fail_run)
    monkeypatch.setattr("install._run", fail_run)

    _pull_ollama_models(paths, verify_hashes=True)


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
    pulled: list[list[str]] = []

    def fake_subprocess_run(cmd, **_kwargs):  # noqa: ANN001
        if cmd[:2] == ["ollama", "show"]:
            return SimpleNamespace(returncode=1, stdout="", stderr="")
        raise AssertionError(cmd)

    def fake_run(cmd, _paths):  # noqa: ANN001
        pulled.append(cmd)
        model_dir = paths.ollama_models_dir / "models" / "manifests"
        model_dir.mkdir(parents=True, exist_ok=True)
        (model_dir / f"{cmd[-1].replace('/', '_').replace(':', '_')}.json").write_text(
            cmd[-1],
            encoding="utf-8",
        )

    monkeypatch.setattr("install.subprocess.run", fake_subprocess_run)
    monkeypatch.setattr("install._run", fake_run)

    _pull_ollama_models(paths, verify_hashes=True)

    manifest = json.loads(HASH_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert pulled == [["ollama", "pull", model] for model in DEFAULT_OLLAMA_MODELS]
    assert manifest[OLLAMA_HASH_LABEL]["metadata"] == {
        "models": list(DEFAULT_OLLAMA_MODELS),
        "ollama_models_dir": str(paths.ollama_models_dir),
    }
    assert manifest[OLLAMA_HASH_LABEL]["path"] == str(paths.ollama_models_dir)
    assert manifest[OLLAMA_HASH_LABEL]["files"] == len(DEFAULT_OLLAMA_MODELS)


def test_pull_ollama_models_rejects_hash_mismatch_before_pull(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    ollama_models_dir = tmp_path / "ollama-models"
    ollama_models_dir.mkdir()
    model_file = ollama_models_dir / "model.blob"
    model_file.write_text("ok", encoding="utf-8")
    paths = InstallPaths(
        install_root=tmp_path,
        venv_dir=tmp_path / ".venv",
        models_dir=tmp_path / "models",
        hf_cache_dir=tmp_path / "hf-cache",
        ollama_models_dir=ollama_models_dir,
        ollama_endpoint="http://127.0.0.1:11434",
        ollama_bin="ollama",
        tesseract_cmd="tesseract",
        ffmpeg_bin="ffmpeg",
    )
    metadata = {
        "models": list(DEFAULT_OLLAMA_MODELS),
        "ollama_models_dir": str(paths.ollama_models_dir),
    }
    _verify_or_write_hash(OLLAMA_HASH_LABEL, paths.ollama_models_dir, metadata=metadata)
    model_file.write_text("corrupt", encoding="utf-8")

    def fail_run(*_args, **_kwargs):  # noqa: ANN002
        raise AssertionError("pull step should not run after hash mismatch")

    monkeypatch.setattr("install.subprocess.run", fail_run)
    monkeypatch.setattr("install._run", fail_run)

    with pytest.raises(SystemExit, match="Hash mismatch"):
        _pull_ollama_models(paths, verify_hashes=True)


def test_download_tessdata_fetches_supported_languages_to_local_folder(
    tmp_path: Path,
    monkeypatch,
) -> None:
    paths = InstallPaths(
        install_root=tmp_path,
        venv_dir=tmp_path / ".venv",
        models_dir=tmp_path / "models",
        hf_cache_dir=tmp_path / "hf-cache",
        ollama_models_dir=tmp_path / "ollama-models",
        ollama_endpoint="http://127.0.0.1:11434",
        ollama_bin="ollama",
        tesseract_cmd="tesseract",
        tessdata_dir=tmp_path / "custom-tessdata",
        ffmpeg_bin="ffmpeg",
    )
    downloads: list[tuple[str, Path]] = []

    def fake_urlretrieve(url: str, filename: str) -> tuple[str, None]:
        target = Path(filename)
        downloads.append((url, target))
        target.write_bytes(b"traineddata")
        return filename, None

    monkeypatch.setattr("install.urllib.request.urlretrieve", fake_urlretrieve)

    _download_tessdata(paths, verify_hashes=False)

    assert downloads == [
        (
            f"{TESSDATA_FAST_BASE_URL}/{lang}.traineddata",
            tmp_path / "custom-tessdata" / f"{lang}.traineddata.tmp",
        )
        for lang in DEFAULT_TESSDATA_LANGS
    ]
    assert {
        path.name for path in (tmp_path / "custom-tessdata").glob("*.traineddata")
    } == {f"{lang}.traineddata" for lang in DEFAULT_TESSDATA_LANGS}


def test_download_tessdata_uses_install_root_default_and_hash_manifest(
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

    def fake_urlretrieve(_url: str, filename: str) -> tuple[str, None]:
        Path(filename).write_bytes(b"traineddata")
        return filename, None

    monkeypatch.setattr("install.urllib.request.urlretrieve", fake_urlretrieve)

    _download_tessdata(paths, verify_hashes=True)

    assert paths.tessdata_dir == tmp_path / "data" / "tessdata"
    manifest = json.loads(HASH_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert manifest[TESSDATA_HASH_LABEL]["metadata"] == {
        "languages": list(DEFAULT_TESSDATA_LANGS),
        "source": TESSDATA_FAST_BASE_URL,
        "tessdata_dir": str(paths.tessdata_dir),
    }


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
    assert {
        "libxcb-cursor0",
        "libxcb-icccm4",
        "libxcb-image0",
        "libxcb-keysyms1",
        "libxcb-randr0",
        "libxcb-render-util0",
        "libxcb-shape0",
        "libxcb-xfixes0",
        "libxcb-xinerama0",
        "libxcb-xkb1",
    }.issubset(commands[1])
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


def test_readme_documents_multilingual_ocr_and_benchmark_language_map() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "tesseract-ocr-chi-sim" in readme
    assert "tesseract-ocr-kaz" in readme
    assert "tesseract-ocr-uzb" in readme
    assert "--install-system-tools" in readme
    assert "--tessdata-dir" in readme
    assert "--install-ollama" in readme
    assert "--install-comfyui" in readme
    assert "--download-ollama-models" in readme
    assert "--download-tts-models" in readme


def test_install_system_tools_runs_native_commands_without_shell(monkeypatch) -> None:
    monkeypatch.setattr("install.platform.system", lambda: "Windows")
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(command, **kwargs):  # noqa: ANN001
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("install.subprocess.run", fake_run)

    _install_system_tools({"ocr", "audio"})

    winget_install = [
        "winget",
        "install",
        "-e",
        "--silent",
        "--disable-interactivity",
        "--accept-package-agreements",
        "--accept-source-agreements",
        "--id",
    ]
    assert [call[0] for call in calls] == [
        [*winget_install, "UB-Mannheim.TesseractOCR"],
        [*winget_install, "Gyan.FFmpeg"],
    ]
    assert all(call[1] == {"check": True} for call in calls)
