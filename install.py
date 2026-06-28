#!/usr/bin/env python3
"""Cross-platform installer for Books to Audio."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

MIN_PYTHON = (3, 10)
DEFAULT_EXTRAS = {"audio", "gui", "llm", "ocr", "perceptual"}
DEFAULT_OLLAMA_ENDPOINT = "http://localhost:11434"
DEFAULT_COMFYUI_URL = "http://localhost:8188"
DEFAULT_COMFYUI_REPO = "https://github.com/comfy-org/ComfyUI.git"
DEFAULT_COMFYUI_QWEN_NODE_REPO = "https://github.com/flybirdxx/ComfyUI-Qwen-TTS.git"
DEFAULT_OLLAMA_MODELS = (
    "hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M",
    "hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M",
)
DEFAULT_TESSDATA_LANGS = ("eng", "rus", "chi_sim", "kaz", "uzb", "osd")
TESSDATA_FAST_BASE_URL = "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main"
DEFAULT_TTS_HASH_MODEL_IDS = (
    "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    "Qwen/Qwen3-TTS-Tokenizer-12Hz",
)
DEFAULT_TTS_MODEL_SELECTIONS = DEFAULT_TTS_HASH_MODEL_IDS
TTS_MODEL_SELECTIONS = {
    "default": DEFAULT_TTS_MODEL_SELECTIONS,
    "recommended": DEFAULT_TTS_MODEL_SELECTIONS,
    "qwen3-customvoice-1.7b": (
        "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        "Qwen/Qwen3-TTS-Tokenizer-12Hz",
    ),
    "qwen3-customvoice-0.6b": (
        "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
        "Qwen/Qwen3-TTS-Tokenizer-12Hz",
    ),
    "fish-speech-1.5": ("fish-speech-1.5",),
    "f5-tts": ("f5-tts",),
    "xtts-v2": ("xtts-v2",),
    "cosyvoice-3": ("cosyvoice-3",),
    "all": (
        "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
        "Qwen/Qwen3-TTS-Tokenizer-12Hz",
        "fish-speech-1.5",
        "f5-tts",
        "xtts-v2",
        "cosyvoice-3",
    ),
}
DEFAULT_AUDIO_QA_MODEL_SELECTIONS = ("production",)
AUDIO_QA_MODEL_SELECTIONS = {
    "omni": ("omni",),
    "production": ("production",),
    "all": ("all",),
}
INSTALL_TOOL_PACKAGES = ("pip", "setuptools", "wheel", "build")
LOG_PATH = Path("install.log")
LOG_PATH_ENV = "BOOKS_TO_AUDIO_INSTALL_LOG"
RUNTIME_CONFIG_PATH = Path("data/local_runtime_paths.json")
HASH_MANIFEST_PATH = Path("data/install_hashes.json")
TESSDATA_HASH_LABEL = "tessdata"
TTS_HASH_LABEL = "tts_models"
AUDIO_QA_HASH_LABEL = "audio_qa_models"
OLLAMA_HASH_LABEL = "ollama_models"
OLLAMA_RUNTIME_HASH_LABEL = "ollama_runtime"
COMFYUI_RUNTIME_HASH_LABEL = "comfyui_runtime"
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
VERIFY_MODULES = {
    "core": [
        "build",
        "book_normalizer",
        "click",
        "docx",
        "ebooklib",
        "fitz",
        "huggingface_hub",
        "lxml",
        "num2words",
        "peyo",
        "pydantic",
        "pymorphy3",
        "razdel",
        "rich",
    ],
    "audio": ["pydub", "soundfile"],
    "audio-qa-runtime": ["accelerate", "qwen_omni_utils", "transformers", "vllm"],
    "asr": ["faster_whisper", "jiwer", "rapidfuzz"],
    "dev": ["pytest", "ruff"],
    "gui": ["PyQt6"],
    "llm": ["httpx"],
    "ocr": ["PIL", "pytesseract"],
    "perceptual": ["librosa", "requests", "torch", "torchmetrics"],
    "stress": ["silero_stress"],
    "tts": ["numpy", "qwen_tts", "soundfile", "torch"],
    "tts-sage": ["numpy", "qwen_tts", "sageattention", "soundfile", "torch"],
}


@dataclass
class InstallPaths:
    """Installer-selected local paths."""

    install_root: Path
    venv_dir: Path
    models_dir: Path
    hf_cache_dir: Path
    ollama_endpoint: str
    ollama_bin: str
    tesseract_cmd: str
    ffmpeg_bin: str
    ollama_models_dir: Path = Path("ollama-models")
    tessdata_dir: Path | None = None
    comfyui_root: Path = Path("ComfyUI")
    comfyui_url: str = DEFAULT_COMFYUI_URL
    comfyui_custom_node_repo: str = DEFAULT_COMFYUI_QWEN_NODE_REPO


class _TeeStream:
    """Mirror terminal output to an overwritten install log."""

    def __init__(self, stream: TextIO, log_file: TextIO) -> None:
        self._stream = stream
        self._log_file = log_file

    def write(self, data: str) -> int:
        written = self._stream.write(data)
        self._log_file.write(ANSI_RE.sub("", data))
        self._log_file.flush()
        return written

    def flush(self) -> None:
        self._stream.flush()
        self._log_file.flush()

    def isatty(self) -> bool:
        return self._stream.isatty()


def main() -> int:
    args = _parse_args()
    project_root = Path(__file__).resolve().parent
    os.chdir(project_root)
    log_path = _resolve_log_path(args.log_path, project_root)
    _configure_console(log_path)

    _ensure_python_version()
    extras = _resolve_extras(args)
    paths = _resolve_install_paths(args, project_root)
    _resolve_optional_downloads(args)
    if args.download_tessdata and paths.tessdata_dir is None:
        paths.tessdata_dir = paths.install_root / "data" / "tessdata"
    venv_python = _venv_python(paths.venv_dir)

    _say("Books to Audio installer", "Установщик Books to Audio", "title")
    _print_install_summary(project_root, paths, extras, log_path=log_path)

    if args.system_check:
        _print_system_dependency_notes(extras, paths)

    if args.install_system_tools:
        _install_system_tools(extras)

    if args.dry_run:
        _write_runtime_config(paths, project_root)
        _say(
            "Dry run: venv and dependencies were not changed; runtime paths/log were refreshed.",
            "Пробный запуск: venv и зависимости не изменялись; runtime-пути и лог обновлены.",
            "warn",
        )
        editable_flag = "" if args.no_editable else "-e "
        print(f"Would run: {venv_python} -m pip install {editable_flag}{_project_spec(extras)}")
        print(f"Would write runtime config: {(project_root / RUNTIME_CONFIG_PATH).resolve()}")
        return 0

    if args.recreate and _same_path(Path(sys.executable), venv_python):
        raise SystemExit(
            "--recreate cannot run from the virtual environment being deleted. "
            "Run install.py with a system Python instead."
        )

    if args.recreate and paths.venv_dir.exists():
        _say(
            f"Removing existing virtual environment: {paths.venv_dir}",
            f"Удаляю существующее виртуальное окружение: {paths.venv_dir}",
            "warn",
        )
        shutil.rmtree(paths.venv_dir)

    if not venv_python.exists():
        _say("Creating virtual environment...", "Создаю виртуальное окружение...", "info")
        _run([sys.executable, "-m", "venv", str(paths.venv_dir)], paths)
    else:
        _say("Virtual environment already exists.", "Виртуальное окружение уже существует.", "ok")

    if not venv_python.exists():
        raise SystemExit(f"Virtual environment Python was not created: {venv_python}")

    _write_runtime_config(paths, project_root)

    _say("Upgrading pip/build tools...", "Обновляю pip и build-инструменты...", "info")
    _run([str(venv_python), "-m", "pip", "install", "--upgrade", *INSTALL_TOOL_PACKAGES], paths)

    install_cmd = [str(venv_python), "-m", "pip", "install"]
    if args.upgrade:
        install_cmd.append("--upgrade")
    if args.no_editable:
        install_cmd.append(_project_spec(extras))
    else:
        install_cmd.extend(["-e", _project_spec(extras)])

    _say("Installing project dependencies...", "Устанавливаю зависимости проекта...", "info")
    _run(install_cmd, paths)

    _say("Verifying imports...", "Проверяю импорты...", "info")
    _verify_imports(venv_python, extras, paths)

    if args.download_tessdata:
        _download_tessdata(paths, args.verify_hashes)

    if args.install_ollama:
        _install_ollama(paths, args.verify_hashes)

    if args.download_ollama_models:
        _pull_ollama_models(paths, args.verify_hashes)

    if args.download_tts_models:
        _install_tts_models(
            venv_python,
            paths,
            args.verify_hashes,
            _selected_tts_model_ids(args.tts_model),
        )

    if args.download_perceptual_models:
        _install_perceptual_models(venv_python, paths)

    if args.download_audio_qa_models:
        _install_audio_qa_models(
            venv_python,
            paths,
            args.verify_hashes,
            _selected_audio_qa_models(args.audio_qa_model),
        )

    if args.install_comfyui:
        _install_comfyui(paths, args.comfyui_repo, args.verify_hashes)

    print()
    _say("Installation complete.", "Установка завершена.", "ok")
    _print_next_steps(paths.venv_dir)
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create .venv and install Books to Audio dependencies for Windows, Linux, and macOS.",
    )
    parser.add_argument("--venv", default=".venv", help="Virtual environment directory. Default: .venv")
    parser.add_argument(
        "--log-path",
        default=os.environ.get(LOG_PATH_ENV, ""),
        help=f"Installer log path. Default: {LOG_PATH} or {LOG_PATH_ENV}.",
    )
    parser.add_argument("--interactive", action="store_true", help="Ask for install locations and optional downloads.")
    parser.add_argument("--yes", action="store_true", help="Use defaults/non-interactive answers for prompts.")
    parser.add_argument(
        "--install-root",
        default="",
        help="Base folder for installer-managed data. Default: project folder.",
    )
    parser.add_argument("--models-dir", default="", help="Shared TTS/ComfyUI models folder.")
    parser.add_argument("--hf-cache-dir", default="", help="Hugging Face cache folder.")
    parser.add_argument(
        "--ollama-models-dir",
        default="",
        help="Ollama model storage folder used via OLLAMA_MODELS.",
    )
    parser.add_argument("--ollama-endpoint", default="", help="Local Ollama endpoint. Default: http://localhost:11434")
    parser.add_argument("--ollama-bin", default="", help="Path or command name for Ollama. Default: ollama")
    parser.add_argument(
        "--install-ollama",
        action="store_true",
        help="Install native Ollama if it is not already available.",
    )
    parser.add_argument("--comfyui-root", default="", help="Local ComfyUI root folder.")
    parser.add_argument("--comfyui-url", default="", help="Local ComfyUI endpoint. Default: http://localhost:8188")
    parser.add_argument(
        "--comfyui-repo",
        default=DEFAULT_COMFYUI_REPO,
        help=f"ComfyUI git repository. Default: {DEFAULT_COMFYUI_REPO}",
    )
    parser.add_argument(
        "--comfyui-custom-node-repo",
        default=DEFAULT_COMFYUI_QWEN_NODE_REPO,
        help=f"Qwen3-TTS ComfyUI custom node git repository. Default: {DEFAULT_COMFYUI_QWEN_NODE_REPO}",
    )
    parser.add_argument(
        "--install-comfyui",
        action="store_true",
        help="Install or prepare a local ComfyUI checkout plus Qwen3-TTS custom nodes.",
    )
    parser.add_argument("--tesseract-bin", default="", help="Path or command name for Tesseract OCR.")
    parser.add_argument("--tessdata-dir", default="", help="Optional Tesseract tessdata language-pack folder.")
    parser.add_argument("--ffmpeg-bin", default="", help="Path or command name for FFmpeg.")
    parser.add_argument(
        "--install-system-tools",
        action="store_true",
        help="Run the suggested native package-manager command for missing OCR/audio/GUI tools.",
    )
    parser.add_argument(
        "--download-ollama-models",
        action="store_true",
        help="Pull recommended local Qwen GGUF models with Ollama.",
    )
    parser.add_argument(
        "--download-tessdata",
        action="store_true",
        help="Download Tesseract OCR language packs for ru/en/zh/kk/uz into --tessdata-dir or data/tessdata.",
    )
    parser.add_argument(
        "--download-tts-models",
        action="store_true",
        help="Download selected TTS models into --models-dir.",
    )
    parser.add_argument(
        "--download-perceptual-models",
        action="store_true",
        help="Pre-download/prewarm NISQA v2 perceptual QA weights after installing dependencies.",
    )
    parser.add_argument(
        "--download-audio-qa-models",
        action="store_true",
        help="Download local Hugging Face audio QA models for LLM/ASR/forced-alignment checks.",
    )
    parser.add_argument(
        "--tts-model",
        action="append",
        choices=tuple(TTS_MODEL_SELECTIONS),
        default=[],
        help=(
            "TTS model set to download with --download-tts-models. "
            "Repeatable. Default/recommended: qwen3-customvoice-1.7b. "
            "Also: qwen3-customvoice-0.6b, fish-speech-1.5, f5-tts, xtts-v2, cosyvoice-3, all."
        ),
    )
    parser.add_argument(
        "--audio-qa-model",
        action="append",
        choices=tuple(AUDIO_QA_MODEL_SELECTIONS),
        default=[],
        help=(
            "Audio QA model set to download with --download-audio-qa-models. "
            "Default: production. Also: omni, all."
        ),
    )
    parser.add_argument(
        "--verify-hashes",
        action="store_true",
        help="Write/compare SHA-256 manifests for installer-managed folders.",
    )
    parser.add_argument("--minimal", action="store_true", help="Install only core package dependencies.")
    parser.add_argument("--without-gui", action="store_true", help="Skip PyQt6 GUI dependencies.")
    parser.add_argument("--without-llm", action="store_true", help="Skip httpx/Ollama-compatible LLM dependencies.")
    parser.add_argument("--without-ocr", action="store_true", help="Skip pytesseract/Pillow OCR dependencies.")
    parser.add_argument("--without-audio", action="store_true", help="Skip pydub/soundfile audio helper dependencies.")
    parser.add_argument("--without-perceptual", action="store_true", help="Skip NISQA v2 perceptual QA dependencies.")
    parser.add_argument("--with-dev", action="store_true", help="Install pytest and ruff.")
    parser.add_argument("--with-asr", action="store_true", help="Install faster-whisper ASR QA dependencies.")
    parser.add_argument(
        "--with-audio-qa-runtime",
        action="store_true",
        help="Install local Omni audio QA runtime dependencies such as vLLM and qwen-omni-utils.",
    )
    parser.add_argument("--with-stress", action="store_true", help="Install optional silero-stress model support.")
    parser.add_argument(
        "--with-tts",
        action="store_true",
        help="Install direct Qwen-TTS runner dependencies. Heavy; CUDA/Linux is recommended.",
    )
    parser.add_argument(
        "--with-sage",
        action="store_true",
        help="Install Qwen-TTS plus SageAttention from GitHub. CUDA/Linux only in practice.",
    )
    parser.add_argument("--upgrade", action="store_true", help="Ask pip to upgrade already installed packages.")
    parser.add_argument("--recreate", action="store_true", help="Delete and recreate the selected virtual environment.")
    parser.add_argument(
        "--no-editable",
        action="store_true",
        help="Install as a normal package instead of editable mode.",
    )
    parser.add_argument(
        "--no-system-check",
        dest="system_check",
        action="store_false",
        help="Skip system dependency notes.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print what would be installed without changing files.")
    parser.set_defaults(system_check=True)
    return parser.parse_args()


def _configure_console(log_path: Path) -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("w", encoding="utf-8")
    sys.stdout = _TeeStream(sys.stdout, log_file)  # type: ignore[assignment]
    sys.stderr = _TeeStream(sys.stderr, log_file)  # type: ignore[assignment]


def _resolve_log_path(provided: str, project_root: Path) -> Path:
    value = (provided or "").strip()
    if not value:
        return project_root / LOG_PATH
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def _supports_color() -> bool:
    return bool(getattr(sys.stdout, "isatty", lambda: False)())


def _paint(text: str, code: str) -> str:
    if not _supports_color():
        return text
    return f"\x1b[{code}m{text}\x1b[0m"


def _say(en: str, ru: str = "", level: str = "info") -> None:
    colors = {"title": "1;36", "ok": "32", "warn": "33", "error": "31", "info": "36"}
    prefix = {"title": "==", "ok": "OK", "warn": "!!", "error": "!!", "info": "--"}[level]
    print(_paint(f"{prefix} {en}", colors[level]))
    if ru:
        print(_paint(f"   {ru}", colors[level]))


def _print_install_summary(
    project_root: Path,
    paths: InstallPaths,
    extras: set[str],
    *,
    log_path: Path | None = None,
) -> None:
    """Print a bilingual, log-friendly installation summary."""
    rows = [
        ("Project", "Проект", str(project_root)),
        ("Python", "Python", f"{sys.version.split()[0]} ({sys.executable})"),
        ("OS", "ОС", f"{platform.system()} {platform.release()}"),
        ("Virtual environment", "Виртуальное окружение", str(paths.venv_dir)),
        ("Models folder", "Папка моделей", str(paths.models_dir)),
        ("Hugging Face cache", "Кэш Hugging Face", str(paths.hf_cache_dir)),
        ("Ollama models folder", "Папка моделей Ollama", str(paths.ollama_models_dir)),
        ("Ollama endpoint/bin", "Ollama адрес/команда", f"{paths.ollama_endpoint} ({paths.ollama_bin})"),
        ("ComfyUI root/url", "ComfyUI папка/адрес", f"{paths.comfyui_root} ({paths.comfyui_url})"),
        ("ComfyUI Qwen nodes", "ComfyUI Qwen nodes", paths.comfyui_custom_node_repo),
        ("Tesseract OCR", "Tesseract OCR", paths.tesseract_cmd),
        ("Tesseract tessdata", "Языковые данные Tesseract", str(paths.tessdata_dir or "auto / авто")),
        ("FFmpeg", "FFmpeg", paths.ffmpeg_bin),
        ("Log file", "Лог", str((log_path or project_root / LOG_PATH).resolve())),
        ("Install extras", "Опции установки", ", ".join(sorted(extras)) if extras else "core only / только ядро"),
    ]
    width = max(len(en) for en, _ru, _value in rows)
    for en, ru, value in rows:
        label = _paint(f"{en:<{width}}", "1;34")
        print(f"{label} / {ru}: {value}")
    print()


def _resolve_install_paths(args: argparse.Namespace, project_root: Path) -> InstallPaths:
    interactive = _should_prompt(args)
    install_root = _prompt_path(
        "Install/data root",
        "Папка установки/данных",
        args.install_root,
        project_root,
        interactive,
    )
    venv_default = (project_root / args.venv).resolve()
    venv_arg = "" if interactive and args.venv == ".venv" else args.venv
    venv_dir = _prompt_path(
        "Python virtual environment",
        "Python virtualenv",
        venv_arg,
        venv_default,
        interactive,
    )
    models_dir = _prompt_path(
        "TTS/Hugging Face models folder",
        "Папка моделей TTS/Hugging Face",
        args.models_dir,
        _default_models_dir(),
        interactive,
    )
    hf_cache_dir = _prompt_path(
        "Hugging Face cache folder",
        "Кэш Hugging Face",
        args.hf_cache_dir,
        install_root / "hf-cache",
        interactive,
    )
    ollama_models_dir = _prompt_path(
        "Ollama models folder",
        "Папка моделей Ollama",
        args.ollama_models_dir,
        install_root / "ollama-models",
        interactive,
    )
    ollama_endpoint = _prompt_text(
        "Ollama endpoint",
        "Адрес Ollama",
        args.ollama_endpoint,
        DEFAULT_OLLAMA_ENDPOINT,
        interactive,
    )
    ollama_bin = _prompt_text(
        "Ollama command/path",
        "Команда/путь Ollama",
        args.ollama_bin,
        _default_ollama_bin(),
        interactive,
    )
    comfyui_root = _prompt_path(
        "ComfyUI root folder",
        "Папка ComfyUI",
        getattr(args, "comfyui_root", ""),
        install_root / "ComfyUI",
        interactive,
    )
    comfyui_url = _prompt_text(
        "ComfyUI endpoint",
        "Адрес ComfyUI",
        getattr(args, "comfyui_url", ""),
        DEFAULT_COMFYUI_URL,
        interactive,
    )
    tesseract_cmd = _prompt_text(
        "Tesseract command/path",
        "Команда/путь Tesseract",
        args.tesseract_bin,
        _default_command("tesseract"),
        interactive,
    )
    tessdata_dir = _prompt_optional_path(
        "Tesseract tessdata folder",
        "Папка языковых данных Tesseract",
        args.tessdata_dir,
        interactive,
    )
    ffmpeg_bin = _prompt_text(
        "FFmpeg command/path",
        "Команда/путь FFmpeg",
        args.ffmpeg_bin,
        _default_command("ffmpeg"),
        interactive,
    )
    return InstallPaths(
        install_root=install_root,
        venv_dir=venv_dir,
        models_dir=models_dir,
        hf_cache_dir=hf_cache_dir,
        ollama_endpoint=ollama_endpoint,
        ollama_bin=ollama_bin,
        tesseract_cmd=tesseract_cmd,
        tessdata_dir=tessdata_dir,
        ffmpeg_bin=ffmpeg_bin,
        ollama_models_dir=ollama_models_dir,
        comfyui_root=comfyui_root,
        comfyui_url=comfyui_url,
        comfyui_custom_node_repo=getattr(args, "comfyui_custom_node_repo", DEFAULT_COMFYUI_QWEN_NODE_REPO),
    )


def _should_prompt(args: argparse.Namespace) -> bool:
    if args.yes:
        return False
    return bool(args.interactive or (sys.stdin.isatty() and sys.stdout.isatty()))


def _prompt_path(
    en: str,
    ru: str,
    provided: str,
    default: Path,
    interactive: bool,
) -> Path:
    if provided:
        return Path(provided).expanduser().resolve()
    if not interactive:
        return default.expanduser().resolve()
    answer = input(f"{en} / {ru}\n[{default}]: ").strip()
    return Path(answer or default).expanduser().resolve()


def _prompt_optional_path(
    en: str,
    ru: str,
    provided: str,
    interactive: bool,
) -> Path | None:
    """Return an optional user-provided path, leaving blank values automatic."""
    if provided:
        return Path(provided).expanduser().resolve()
    if not interactive:
        return None
    answer = input(f"{en} / {ru}\n[auto / авто]: ").strip()
    return Path(answer).expanduser().resolve() if answer else None


def _prompt_text(
    en: str,
    ru: str,
    provided: str,
    default: str,
    interactive: bool,
) -> str:
    if provided:
        return provided.strip()
    if not interactive:
        return default
    answer = input(f"{en} / {ru}\n[{default}]: ").strip()
    return answer or default


def _resolve_optional_downloads(args: argparse.Namespace) -> None:
    if not _should_prompt(args):
        return
    args.install_ollama = getattr(args, "install_ollama", False) or _prompt_yes_no(
        "Install native Ollama if missing?",
        "Установить нативную Ollama, если она не найдена?",
        default=False,
    )
    args.download_tessdata = args.download_tessdata or _prompt_yes_no(
        "Download local Tesseract language packs for ru/en/zh/kk/uz? This avoids sudo for OCR languages.",
        (
            "Скачать локальные языковые пакеты Tesseract для ru/en/zh/kk/uz? "
            "Это позволяет обойтись без sudo для OCR-языков."
        ),
        default=False,
    )
    args.download_ollama_models = args.download_ollama_models or _prompt_yes_no(
        "Pull Qwen3 Ollama 8B/4B models now? This is several GB.",
        "Скачать Qwen3 Ollama 8B/4B сейчас? Это несколько ГБ.",
        default=False,
    )
    args.download_tts_models = args.download_tts_models or _prompt_yes_no(
        "Download default Qwen3-TTS model now?",
        "Скачать стандартную Qwen3-TTS модель сейчас?",
        default=False,
    )
    args.download_perceptual_models = args.download_perceptual_models or _prompt_yes_no(
        "Pre-download NISQA v2 perceptual QA weights now?",
        "Pre-download NISQA v2 perceptual QA weights now?",
        default=False,
    )
    args.download_audio_qa_models = args.download_audio_qa_models or _prompt_yes_no(
        "Download local audio QA models now? The Omni reviewer is very large.",
        "Скачать локальные audio QA модели сейчас? Omni-рецензент очень большой.",
        default=False,
    )
    args.install_comfyui = getattr(args, "install_comfyui", False) or _prompt_yes_no(
        "Install or prepare local ComfyUI plus Qwen3-TTS custom nodes?",
        "Установить или подготовить локальный ComfyUI плюс Qwen3-TTS custom nodes?",
        default=False,
    )
    args.verify_hashes = args.verify_hashes or _prompt_yes_no(
        "Compute SHA-256 manifests for installer-managed downloads?",
        "Посчитать SHA-256 манифесты для скачанных установщиком файлов?",
        default=False,
    )


def _prompt_yes_no(en: str, ru: str, *, default: bool) -> bool:
    suffix = "Y/n" if default else "y/N"
    answer = input(f"{en}\n{ru}\n[{suffix}]: ").strip().lower()
    if not answer:
        return default
    return answer in {"y", "yes", "д", "да"}


def _default_models_dir() -> Path:
    if platform.system() == "Windows":
        return Path("D:/ComfyUI-external/models")
    return Path.home() / "books-to-audio-models"


def _default_ollama_bin() -> str:
    found = shutil.which("ollama")
    if found:
        return found
    if platform.system() == "Windows":
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            candidate = Path(local_appdata) / "Programs" / "Ollama" / "ollama.exe"
            if candidate.exists():
                return str(candidate)
        return "ollama"
    return "ollama"


def _default_command(command: str) -> str:
    return shutil.which(command) or command


def _ensure_python_version() -> None:
    if sys.version_info < MIN_PYTHON:
        required = ".".join(str(part) for part in MIN_PYTHON)
        current = ".".join(str(part) for part in sys.version_info[:3])
        raise SystemExit(f"Python {required}+ is required; current version is {current}.")


def _resolve_extras(args: argparse.Namespace) -> set[str]:
    extras: set[str] = set()
    if not args.minimal:
        extras.update(DEFAULT_EXTRAS)

    if args.with_dev:
        extras.add("dev")
    if args.with_asr:
        extras.add("asr")
    if args.with_audio_qa_runtime:
        extras.add("audio-qa-runtime")
    if args.with_stress:
        extras.add("stress")
    if args.with_sage:
        extras.add("tts-sage")
        extras.discard("tts")
    elif args.with_tts:
        extras.add("tts")

    if args.without_gui:
        extras.discard("gui")
    if args.without_llm:
        extras.discard("llm")
    if args.without_ocr:
        extras.discard("ocr")
    if args.without_audio:
        extras.discard("audio")
    if args.without_perceptual:
        extras.discard("perceptual")

    return extras


def _venv_python(venv_dir: Path) -> Path:
    if platform.system() == "Windows":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return left.absolute() == right.absolute()


def _project_spec(extras: set[str]) -> str:
    if not extras:
        return "."
    return f".[{','.join(sorted(extras))}]"


def _run(cmd: list[str], paths: InstallPaths) -> None:
    print("+ " + " ".join(_quote(part) for part in cmd))
    subprocess.run(cmd, check=True, env=_installer_env(paths))


def _quote(value: str) -> str:
    if any(ch.isspace() for ch in value):
        return f'"{value}"'
    return value


def _verify_imports(venv_python: Path, extras: set[str], paths: InstallPaths) -> None:
    modules = list(VERIFY_MODULES["core"])
    for extra in sorted(extras):
        modules.extend(VERIFY_MODULES.get(extra, []))
    unique_modules = sorted(set(modules))
    code = (
        "import importlib.util, sys\n"
        f"mods = {unique_modules!r}\n"
        "missing = [m for m in mods if importlib.util.find_spec(m) is None]\n"
        "print('checked modules:', ', '.join(mods))\n"
        "raise SystemExit('Missing modules: ' + ', '.join(missing) if missing else 0)\n"
    )
    _run([str(venv_python), "-c", code], paths)


def _write_runtime_config(paths: InstallPaths, project_root: Path) -> None:
    """Persist installer-selected paths for GUI/runtime defaults."""
    paths.install_root.mkdir(parents=True, exist_ok=True)
    paths.models_dir.mkdir(parents=True, exist_ok=True)
    paths.hf_cache_dir.mkdir(parents=True, exist_ok=True)
    paths.ollama_models_dir.mkdir(parents=True, exist_ok=True)
    config_path = project_root / RUNTIME_CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "install_root": str(paths.install_root),
        "venv_dir": str(paths.venv_dir),
        "models_dir": str(paths.models_dir),
        "hf_cache_dir": str(paths.hf_cache_dir),
        "ollama_models_dir": str(paths.ollama_models_dir),
        "ollama_endpoint": paths.ollama_endpoint,
        "ollama_bin": paths.ollama_bin,
        "comfyui_root": str(paths.comfyui_root),
        "comfyui_url": paths.comfyui_url,
        "comfyui_custom_node_repo": paths.comfyui_custom_node_repo,
        "tesseract_cmd": paths.tesseract_cmd,
        "tessdata_dir": str(paths.tessdata_dir) if paths.tessdata_dir else "",
        "ffmpeg_bin": paths.ffmpeg_bin,
    }
    config_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    env_path = config_path.with_suffix(".env")
    env_path.write_text(
        "\n".join(
            [
                _env_assignment("BOOKS_TO_AUDIO_RUNTIME_CONFIG", config_path.resolve()),
                _env_assignment("BOOKS_TO_AUDIO_MODELS_DIR", paths.models_dir),
                _env_assignment("COMFYUI_MODELS_DIR", paths.models_dir),
                _env_assignment("HF_HOME", paths.hf_cache_dir),
                _env_assignment("BOOKS_TO_AUDIO_OLLAMA_MODELS_DIR", paths.ollama_models_dir),
                _env_assignment("OLLAMA_MODELS", paths.ollama_models_dir),
                _env_assignment("BOOKS_TO_AUDIO_OLLAMA_ENDPOINT", paths.ollama_endpoint),
                _env_assignment("BOOKS_TO_AUDIO_OLLAMA_BIN", paths.ollama_bin),
                _env_assignment("BOOKS_TO_AUDIO_COMFYUI_ROOT", paths.comfyui_root),
                _env_assignment("COMFYUI_ROOT", paths.comfyui_root),
                _env_assignment("BOOKS_TO_AUDIO_COMFYUI_URL", paths.comfyui_url),
                _env_assignment("BOOKS_TO_AUDIO_TESSERACT_CMD", paths.tesseract_cmd),
                *(
                    [
                        _env_assignment("BOOKS_TO_AUDIO_TESSDATA_DIR", paths.tessdata_dir),
                        _env_assignment("TESSDATA_PREFIX", paths.tessdata_dir),
                    ]
                    if paths.tessdata_dir
                    else []
                ),
                _env_assignment("BOOKS_TO_AUDIO_FFMPEG_BIN", paths.ffmpeg_bin),
                "",
            ]
        ),
        encoding="utf-8",
    )
    _say(
        f"Runtime paths saved: {config_path}",
        f"Пути runtime сохранены: {config_path}",
        "ok",
    )


def _env_assignment(key: str, value: object) -> str:
    """Return a shell/dotenv-safe assignment, preserving paths with spaces."""
    text = str(value)
    if re.fullmatch(r"[A-Za-z0-9_./:@%+=,\\-]+", text):
        return f"{key}={text}"
    escaped = text.replace("'", "'\\''")
    return f"{key}='{escaped}'"


def _install_ollama(paths: InstallPaths, verify_hashes: bool) -> None:
    """Install native Ollama when the configured executable is not available."""
    if _command_available(paths.ollama_bin):
        _say(
            f"Ollama is already installed: {paths.ollama_bin}",
            f"Ollama уже установлена: {paths.ollama_bin}",
            "ok",
        )
        _verify_runtime_file_hash(OLLAMA_RUNTIME_HASH_LABEL, paths.ollama_bin, verify_hashes)
        return

    _say("Installing native Ollama...", "Устанавливаю нативную Ollama...", "info")
    system = platform.system()
    if system == "Windows":
        _run_native_install_command(
            [
                "winget",
                "install",
                "-e",
                "--silent",
                "--disable-interactivity",
                "--accept-package-agreements",
                "--accept-source-agreements",
                "--id",
                "Ollama.Ollama",
            ]
        )
    elif system == "Darwin":
        _run_native_install_command(["brew", "install", "ollama"])
    elif system == "Linux":
        _install_ollama_linux()
    else:
        raise SystemExit(f"Automatic Ollama install is not supported on {system}. Install Ollama manually.")

    resolved = _default_ollama_bin()
    if not _command_available(resolved):
        raise SystemExit(
            "Ollama install command finished, but the executable was not found. "
            "Set it explicitly with --ollama-bin."
        )
    paths.ollama_bin = resolved
    _say(f"Ollama installed: {paths.ollama_bin}", f"Ollama установлена: {paths.ollama_bin}", "ok")
    _verify_runtime_file_hash(OLLAMA_RUNTIME_HASH_LABEL, paths.ollama_bin, verify_hashes)


def _install_ollama_linux() -> None:
    """Install Ollama on Linux using the vendor install script."""
    with tempfile.TemporaryDirectory(prefix="books-to-audio-ollama-") as temp_dir:
        script_path = Path(temp_dir) / "install_ollama.sh"
        urllib.request.urlretrieve("https://ollama.com/install.sh", script_path)
        subprocess.run(["sh", str(script_path)], check=True)


def _run_native_install_command(command: list[str]) -> None:
    print("+ " + " ".join(_quote(part) for part in command))
    subprocess.run(command, check=True)


def _verify_runtime_file_hash(label: str, command: str, verify_hashes: bool) -> None:
    if not verify_hashes:
        return
    executable = _resolve_command_path(command)
    if executable is None:
        _say(
            f"Cannot hash runtime executable because it was not found: {command}",
            f"Не могу посчитать хэш executable, файл не найден: {command}",
            "warn",
        )
        return
    _verify_or_write_hash(label, executable, metadata={"executable": str(executable)})


def _resolve_command_path(command: str) -> Path | None:
    path = Path(command).expanduser()
    if path.is_absolute() or path.parent != Path("."):
        return path if path.exists() else None
    found = shutil.which(command)
    return Path(found) if found else None


def _install_comfyui(paths: InstallPaths, comfyui_repo: str, verify_hashes: bool) -> None:
    """Install or prepare a source-layout ComfyUI checkout with Qwen3-TTS nodes."""
    root = paths.comfyui_root
    if _looks_like_comfyui_root(root):
        _say(f"ComfyUI is already installed: {root}", f"ComfyUI уже установлен: {root}", "ok")
    else:
        if not _command_available("git"):
            raise SystemExit("Git is required to install ComfyUI. Install Git or provide an existing --comfyui-root.")
        root.parent.mkdir(parents=True, exist_ok=True)
        _say(f"Cloning ComfyUI into {root}...", f"Клонирую ComfyUI в {root}...", "info")
        _run_git(["clone", comfyui_repo, str(root)])

    comfy_python = _ensure_comfyui_python(root)
    requirements = _comfyui_requirements_path(root)
    if requirements.exists():
        _run([str(comfy_python), "-m", "pip", "install", "-r", str(requirements)], paths)

    _install_comfyui_custom_nodes(root, comfy_python, paths)
    _write_comfyui_extra_model_paths(root, paths.models_dir)

    if verify_hashes:
        _verify_or_write_hash(
            COMFYUI_RUNTIME_HASH_LABEL,
            root,
            metadata={
                "comfyui_repo": comfyui_repo,
                "custom_node_repo": paths.comfyui_custom_node_repo,
            },
        )


def _install_comfyui_custom_nodes(root: Path, comfy_python: Path, paths: InstallPaths) -> None:
    custom_nodes = _comfyui_custom_nodes_dir(root)
    custom_nodes.mkdir(parents=True, exist_ok=True)
    repo_name = _repo_folder_name(paths.comfyui_custom_node_repo)
    node_dir = custom_nodes / repo_name
    if node_dir.exists():
        _say(
            f"Qwen3-TTS custom nodes already installed: {node_dir}",
            f"Qwen3-TTS custom nodes уже установлены: {node_dir}",
            "ok",
        )
    else:
        if not _command_available("git"):
            raise SystemExit("Git is required to install ComfyUI custom nodes.")
        _say(
            f"Cloning Qwen3-TTS custom nodes into {node_dir}...",
            f"Клонирую Qwen3-TTS custom nodes в {node_dir}...",
            "info",
        )
        _run_git(["clone", paths.comfyui_custom_node_repo, str(node_dir)])

    requirements = node_dir / "requirements.txt"
    if requirements.exists():
        _run([str(comfy_python), "-m", "pip", "install", "-r", str(requirements), "--no-cache-dir"], paths)


def _ensure_comfyui_python(root: Path) -> Path:
    embedded = root / "python_embeded" / "python.exe"
    if embedded.exists():
        return embedded

    venv_dir = root / ".venv"
    python = _venv_python(venv_dir)
    if not python.exists():
        _say(
            f"Creating ComfyUI virtual environment: {venv_dir}",
            f"Создаю virtualenv для ComfyUI: {venv_dir}",
            "info",
        )
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    subprocess.run([str(python), "-m", "pip", "install", "--upgrade", *INSTALL_TOOL_PACKAGES], check=True)
    return python


def _looks_like_comfyui_root(root: Path) -> bool:
    return (
        (root / "python_embeded" / "python.exe").exists()
        and (root / "ComfyUI" / "main.py").exists()
    ) or (root / "main.py").exists()


def _comfyui_requirements_path(root: Path) -> Path:
    portable = root / "ComfyUI" / "requirements.txt"
    if portable.exists():
        return portable
    return root / "requirements.txt"


def _comfyui_custom_nodes_dir(root: Path) -> Path:
    portable = root / "ComfyUI" / "custom_nodes"
    if (root / "ComfyUI" / "main.py").exists():
        return portable
    return root / "custom_nodes"


def _write_comfyui_extra_model_paths(root: Path, models_dir: Path) -> None:
    target = root / "extra_model_paths.yaml"
    text = (
        "books_to_audio:\n"
        f"  base_path: {models_dir.as_posix()}\n"
        "  audio_encoders: audio_encoders\n"
        "  tts: audio_encoders\n"
        "  qwen-tts: audio_encoders\n"
    )
    target.write_text(text, encoding="utf-8")
    _say(
        f"ComfyUI model path config written: {target}",
        f"Конфиг путей моделей ComfyUI записан: {target}",
        "ok",
    )


def _repo_folder_name(repo_url: str) -> str:
    name = repo_url.rstrip("/").rsplit("/", 1)[-1]
    return name[:-4] if name.endswith(".git") else name


def _run_git(args: list[str]) -> None:
    command = ["git", *args]
    print("+ " + " ".join(_quote(part) for part in command))
    subprocess.run(command, check=True)


def _pull_ollama_models(paths: InstallPaths, verify_hashes: bool) -> None:
    paths.ollama_models_dir.mkdir(parents=True, exist_ok=True)
    hash_metadata = {
        "models": list(DEFAULT_OLLAMA_MODELS),
        "ollama_models_dir": str(paths.ollama_models_dir),
    }
    if verify_hashes and _verified_hash_matches(
        OLLAMA_HASH_LABEL,
        paths.ollama_models_dir,
        metadata=hash_metadata,
    ):
        _say(
            "Ollama models already verified by SHA-256; skipping pull.",
            "Модели Ollama уже проверены по SHA-256; скачивание пропущено.",
            "ok",
        )
        return

    _say("Pulling Ollama language models...", "Скачиваю модели Ollama...", "info")
    for model in DEFAULT_OLLAMA_MODELS:
        if _ollama_model_is_present(paths, model):
            _say(
                f"Ollama model already present: {model}",
                f"Модель Ollama уже есть: {model}",
                "ok",
            )
            continue
        _run([paths.ollama_bin, "pull", model], paths)
        if not _ollama_model_file_is_present(paths, model):
            _say(
                (
                    f"Ollama reported pull complete, but {model} was not found under "
                    f"{paths.ollama_models_dir}. If Ollama Desktop was already running, "
                    "restart it with OLLAMA_MODELS pointing to this folder."
                ),
                (
                    f"Ollama завершил pull, но {model} не найден в {paths.ollama_models_dir}. "
                    "Если Ollama Desktop уже был запущен, перезапустите его с OLLAMA_MODELS, "
                    "указывающим на эту папку."
                ),
                "warn",
            )
    if verify_hashes:
        _verify_or_write_hash(OLLAMA_HASH_LABEL, paths.ollama_models_dir, metadata=hash_metadata)


def _download_tessdata(paths: InstallPaths, verify_hashes: bool) -> None:
    """Download supported Tesseract language data into a local tessdata folder."""
    tessdata_dir = paths.tessdata_dir or (paths.install_root / "data" / "tessdata")
    paths.tessdata_dir = tessdata_dir
    tessdata_dir.mkdir(parents=True, exist_ok=True)
    hash_metadata = {
        "languages": list(DEFAULT_TESSDATA_LANGS),
        "source": TESSDATA_FAST_BASE_URL,
        "tessdata_dir": str(tessdata_dir),
    }
    if verify_hashes and _verified_hash_matches(
        TESSDATA_HASH_LABEL,
        tessdata_dir,
        metadata=hash_metadata,
    ):
        _say(
            "Tesseract language data already verified by SHA-256; skipping download.",
            "Языковые данные Tesseract уже проверены по SHA-256; скачивание пропущено.",
            "ok",
        )
        return

    _say(
        f"Downloading Tesseract language data to {tessdata_dir}...",
        f"Скачиваю языковые данные Tesseract в {tessdata_dir}...",
        "info",
    )
    for lang in DEFAULT_TESSDATA_LANGS:
        target = tessdata_dir / f"{lang}.traineddata"
        if target.exists() and target.stat().st_size > 0:
            _say(
                f"Tesseract language already present: {lang}",
                f"Язык Tesseract уже есть: {lang}",
                "ok",
            )
            continue
        url = f"{TESSDATA_FAST_BASE_URL}/{lang}.traineddata"
        tmp_target = target.with_suffix(".traineddata.tmp")
        try:
            urllib.request.urlretrieve(url, str(tmp_target))  # noqa: S310
            if tmp_target.stat().st_size <= 0:
                raise RuntimeError(f"Downloaded empty Tesseract language file: {lang}")
            tmp_target.replace(target)
        finally:
            tmp_target.unlink(missing_ok=True)
    if verify_hashes:
        _verify_or_write_hash(TESSDATA_HASH_LABEL, tessdata_dir, metadata=hash_metadata)


def _ollama_model_is_present(paths: InstallPaths, model: str) -> bool:
    """Return True when Ollama already has the requested model locally."""
    if _ollama_model_file_is_present(paths, model):
        return True
    if not _same_path(paths.ollama_models_dir, _native_ollama_default_models_dir()):
        return False
    result = subprocess.run(
        [paths.ollama_bin, "show", model],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=_installer_env(paths),
    )
    return result.returncode == 0


def _ollama_model_file_is_present(paths: InstallPaths, model: str) -> bool:
    """Return True when the configured Ollama storage folder has a model manifest."""
    manifest_path = _ollama_manifest_path(paths.ollama_models_dir, model)
    if manifest_path.exists():
        return True
    manifests_root = paths.ollama_models_dir / "models" / "manifests"
    if not manifests_root.exists():
        return False
    safe_tail = model.replace("/", "_").replace(":", "_")
    return any(path.is_file() and safe_tail in path.name for path in manifests_root.rglob("*"))


def _ollama_manifest_path(models_dir: Path, model: str) -> Path:
    """Return the native Ollama manifest path for a model reference."""
    name, tag = _split_ollama_model_tag(model)
    parts = name.split("/")
    if len(parts) == 1:
        parts = ["registry.ollama.ai", "library", parts[0]]
    return models_dir / "models" / "manifests" / Path(*parts) / tag


def _split_ollama_model_tag(model: str) -> tuple[str, str]:
    """Split an Ollama model reference into name and tag."""
    last_slash = model.rfind("/")
    last_colon = model.rfind(":")
    if last_colon > last_slash:
        return model[:last_colon], model[last_colon + 1 :]
    return model, "latest"


def _native_ollama_default_models_dir() -> Path:
    """Return Ollama's native default model directory for the host user."""
    return Path.home() / ".ollama" / "models"


def _selected_tts_model_ids(selections: list[str] | tuple[str, ...] | None) -> list[str]:
    """Expand installer TTS selection aliases into engine/model identifiers."""
    requested = selections or ["default"]
    expanded: list[str] = []
    for selection in requested:
        for model_id in TTS_MODEL_SELECTIONS.get(selection, (selection,)):
            if model_id not in expanded:
                expanded.append(model_id)
    return expanded


def _selected_audio_qa_models(selections: list[str] | tuple[str, ...] | None) -> list[str]:
    """Expand installer audio QA selections into model-set aliases."""
    requested = selections or list(DEFAULT_AUDIO_QA_MODEL_SELECTIONS)
    expanded: list[str] = []
    for selection in requested:
        for model_id in AUDIO_QA_MODEL_SELECTIONS.get(selection, (selection,)):
            if model_id not in expanded:
                expanded.append(model_id)
    return expanded


def _install_tts_models(
    venv_python: Path,
    paths: InstallPaths,
    verify_hashes: bool,
    model_ids: list[str] | tuple[str, ...] | None = None,
) -> None:
    selected_model_ids = _selected_tts_model_ids(model_ids)
    hash_metadata = {"models": selected_model_ids}
    if verify_hashes and _verified_hash_matches(
        TTS_HASH_LABEL,
        paths.models_dir,
        metadata=hash_metadata,
    ):
        _say(
            "TTS models already verified by SHA-256; skipping download.",
            "TTS-модели уже проверены по SHA-256; скачивание пропущено.",
            "ok",
        )
        return

    selected_label = ", ".join(selected_model_ids)
    _say(
        f"Installing selected TTS models: {selected_label}",
        f"Устанавливаю выбранные TTS-модели: {selected_label}",
        "info",
    )
    code = (
        "from pathlib import Path\n"
        "from book_normalizer.tts.model_download import install_tts_models\n"
        f"models_dir = Path({str(paths.models_dir)!r})\n"
        f"install_tts_models({json.dumps(selected_model_ids)}, models_dir, progress=print)\n"
    )
    _run([str(venv_python), "-c", code], paths)
    if verify_hashes:
        _verify_or_write_hash(TTS_HASH_LABEL, paths.models_dir, metadata=hash_metadata)


def _install_audio_qa_models(
    venv_python: Path,
    paths: InstallPaths,
    verify_hashes: bool,
    model_sets: list[str] | tuple[str, ...] | None = None,
) -> None:
    selected = _selected_audio_qa_models(model_sets)
    hash_metadata = {"models": selected}
    if verify_hashes and _verified_hash_matches(
        AUDIO_QA_HASH_LABEL,
        paths.models_dir,
        metadata=hash_metadata,
    ):
        _say(
            "Audio QA models already verified by SHA-256; skipping download.",
            "Audio QA модели уже проверены по SHA-256; скачивание пропущено.",
            "ok",
        )
        return

    selected_label = ", ".join(selected)
    _say(
        f"Installing selected audio QA models: {selected_label}",
        f"Устанавливаю выбранные audio QA модели: {selected_label}",
        "info",
    )
    code = (
        "from pathlib import Path\n"
        "from book_normalizer.tts.audio_qa_model_download import install_audio_qa_models\n"
        f"models_dir = Path({str(paths.models_dir)!r})\n"
        f"install_audio_qa_models({json.dumps(selected)}, models_dir, progress=print)\n"
    )
    _run([str(venv_python), "-c", code], paths)
    if verify_hashes:
        _verify_or_write_hash(AUDIO_QA_HASH_LABEL, paths.models_dir, metadata=hash_metadata)


def _install_perceptual_models(venv_python: Path, paths: InstallPaths) -> None:
    """Prewarm NISQA v2 so model weights are ready before first QA run."""
    code = (
        "import math, tempfile, wave\n"
        "from pathlib import Path\n"
        "from book_normalizer.tts.perceptual_qa import NisqaV2Backend\n"
        "with tempfile.TemporaryDirectory(prefix='books-to-audio-nisqa-') as td:\n"
        "    wav_path = Path(td) / 'prewarm.wav'\n"
        "    sample_rate = 16000\n"
        "    samples = [int(math.sin(i / 16.0) * 1200) for i in range(sample_rate * 2)]\n"
        "    with wave.open(str(wav_path), 'wb') as wav:\n"
        "        wav.setnchannels(1)\n"
        "        wav.setsampwidth(2)\n"
        "        wav.setframerate(sample_rate)\n"
        "        frames = b''.join(int(s).to_bytes(2, 'little', signed=True) for s in samples)\n"
        "        wav.writeframes(frames)\n"
        "    result = NisqaV2Backend().predict(wav_path)\n"
        "    print('NISQA v2 ready:', result.scores)\n"
    )
    _say(
        "Prewarming NISQA v2 perceptual QA weights...",
        "Prewarming NISQA v2 perceptual QA weights...",
        "info",
    )
    _run([str(venv_python), "-c", code], paths)


def _verified_hash_matches(
    label: str,
    path: Path,
    *,
    metadata: dict[str, object] | None = None,
) -> bool:
    """Return True when an existing hash manifest proves this folder is intact."""
    manifest = _read_hash_manifest()
    previous = manifest.get(label)
    if not previous:
        return False
    if metadata is not None and previous.get("metadata") != metadata:
        return False
    current = _hash_tree(path)
    if previous.get("sha256") != current["sha256"]:
        raise SystemExit(
            f"Hash mismatch for {label}: expected {previous.get('sha256')}, got {current['sha256']}"
        )
    return True


def _verify_or_write_hash(
    label: str,
    path: Path,
    *,
    metadata: dict[str, object] | None = None,
) -> None:
    _say(f"Hashing {path}...", f"Считаю SHA-256 для {path}...", "info")
    current = _hash_tree(path)
    if metadata is not None:
        current["metadata"] = metadata
    manifest = _read_hash_manifest()
    previous = manifest.get(label)
    comparable_metadata = previous is not None and (
        metadata is None or previous.get("metadata") == metadata
    )
    if previous and comparable_metadata and previous.get("sha256") != current["sha256"]:
        raise SystemExit(
            f"Hash mismatch for {label}: expected {previous.get('sha256')}, got {current['sha256']}"
        )
    _write_hash_manifest_entry(label, current)
    _say(f"Hash verified: {label}", f"Хэш проверен: {label}", "ok")


def _hash_tree(path: Path) -> dict[str, object]:
    if not path.exists():
        raise SystemExit(f"Cannot hash missing path: {path}")
    digest = hashlib.sha256()
    files = [path] if path.is_file() else [p for p in path.rglob("*") if p.is_file()]
    for file_path in sorted(files):
        rel = file_path.name if path.is_file() else file_path.relative_to(path).as_posix()
        digest.update(rel.encode("utf-8"))
        with file_path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
    return {
        "path": str(path),
        "files": len(files),
        "sha256": digest.hexdigest(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _read_hash_manifest() -> dict[str, dict[str, object]]:
    if not HASH_MANIFEST_PATH.exists():
        return {}
    try:
        data = json.loads(HASH_MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_hash_manifest_entry(label: str, value: dict[str, object]) -> None:
    manifest = _read_hash_manifest()
    HASH_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    manifest[label] = value
    HASH_MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _installer_env(paths: InstallPaths) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    env["BOOKS_TO_AUDIO_MODELS_DIR"] = str(paths.models_dir)
    env["COMFYUI_MODELS_DIR"] = str(paths.models_dir)
    env["HF_HOME"] = str(paths.hf_cache_dir)
    env["BOOKS_TO_AUDIO_OLLAMA_MODELS_DIR"] = str(paths.ollama_models_dir)
    env["OLLAMA_MODELS"] = str(paths.ollama_models_dir)
    env["BOOKS_TO_AUDIO_OLLAMA_ENDPOINT"] = paths.ollama_endpoint
    env["BOOKS_TO_AUDIO_OLLAMA_BIN"] = paths.ollama_bin
    env["BOOKS_TO_AUDIO_COMFYUI_ROOT"] = str(paths.comfyui_root)
    env["COMFYUI_ROOT"] = str(paths.comfyui_root)
    env["BOOKS_TO_AUDIO_COMFYUI_URL"] = paths.comfyui_url
    env["BOOKS_TO_AUDIO_TESSERACT_CMD"] = paths.tesseract_cmd
    if paths.tessdata_dir:
        env["BOOKS_TO_AUDIO_TESSDATA_DIR"] = str(paths.tessdata_dir)
        env["TESSDATA_PREFIX"] = str(paths.tessdata_dir)
    env["BOOKS_TO_AUDIO_FFMPEG_BIN"] = paths.ffmpeg_bin
    return env


def _print_system_dependency_notes(extras: set[str], paths: InstallPaths) -> None:
    notes: list[str] = []
    if "ocr" in extras and not _command_available(paths.tesseract_cmd):
        notes.append(_bilingual_line(
            f"Tesseract was not found at '{paths.tesseract_cmd}'. "
            "Scanned PDF OCR will be unavailable until it is installed or the path is corrected.",
            f"Tesseract не найден по пути '{paths.tesseract_cmd}'. "
            "OCR сканированных PDF будет недоступен, пока Tesseract не установлен или путь не исправлен.",
        ))
    if "audio" in extras and not _command_available(paths.ffmpeg_bin):
        notes.append(_bilingual_line(
            f"FFmpeg was not found at '{paths.ffmpeg_bin}'. "
            "WAV output works, but MP3 export via pydub needs FFmpeg.",
            f"FFmpeg не найден по пути '{paths.ffmpeg_bin}'. "
            "WAV будет работать, но экспорт MP3 через pydub требует FFmpeg.",
        ))
    command = _system_package_hint(extras)
    if notes:
        print("System dependency notes / Системные зависимости:")
        for note in notes:
            print(f"- {note}")
        if command:
            print("Suggested system packages / Рекомендуемые системные пакеты:")
            print(f"  {command}")
        print()
    elif command:
        print(
            "System dependency notes: required command-line tools look available. / "
            "Системные зависимости: нужные CLI-утилиты выглядят доступными."
        )
        print()


def _bilingual_line(en: str, ru: str) -> str:
    """Return a compact English/Russian terminal line."""
    return f"{en} / {ru}"


def _install_system_tools(extras: set[str]) -> None:
    commands = _system_package_commands(extras)
    if not commands:
        _say(
            "No native system tools are required for the selected extras.",
            "Для выбранных опций системные утилиты не требуются.",
            "ok",
        )
        return
    _say("Installing native system tools...", "Устанавливаю системные утилиты нативным менеджером пакетов...", "info")
    for command in commands:
        print("+ " + _format_command(command))
        subprocess.run(command, check=True)


def _command_available(command: str) -> bool:
    path = Path(command).expanduser()
    if path.is_absolute() or path.parent != Path("."):
        return path.exists()
    return shutil.which(command) is not None


def _system_package_hint(extras: set[str]) -> str:
    commands = _system_package_commands(extras)
    return " && ".join(_format_command(command) for command in commands)


def _system_package_commands(extras: set[str]) -> list[list[str]]:
    needs_ocr = "ocr" in extras
    needs_audio = "audio" in extras
    needs_gui = "gui" in extras
    if not (needs_ocr or needs_audio or needs_gui):
        return []

    system = platform.system()
    if system == "Darwin":
        packages = []
        if needs_ocr:
            packages.extend(["tesseract", "tesseract-lang"])
        if needs_audio:
            packages.append("ffmpeg")
        if packages:
            return [["brew", "install", *dict.fromkeys(packages)]]
        return []

    if system == "Windows":
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
        commands = []
        if needs_ocr:
            commands.append([*winget_install, "UB-Mannheim.TesseractOCR"])
        if needs_audio:
            commands.append([*winget_install, "Gyan.FFmpeg"])
        return commands

    if system == "Linux":
        distro = _linux_id_like()
        if any(name in distro for name in ("debian", "ubuntu")):
            packages = []
            if needs_ocr:
                packages.extend([
                    "tesseract-ocr",
                    "tesseract-ocr-eng",
                    "tesseract-ocr-rus",
                    "tesseract-ocr-chi-sim",
                    "tesseract-ocr-kaz",
                    "tesseract-ocr-uzb",
                ])
            if needs_audio:
                packages.append("ffmpeg")
            if needs_gui:
                packages.extend([
                    "libegl1",
                    "libgl1",
                    "libxcb-cursor0",
                    "libxcb-icccm4",
                    "libxcb-keysyms1",
                    "libxcb-xinerama0",
                    "libxkbcommon-x11-0",
                    "fonts-noto-cjk",
                    "xvfb",
                    "x11vnc",
                    "novnc",
                    "websockify",
                ])
            return [
                ["sudo", "apt-get", "update"],
                ["sudo", "apt-get", "install", "-y", *dict.fromkeys(packages)],
            ]
        if any(name in distro for name in ("fedora", "rhel", "centos")):
            packages = []
            if needs_ocr:
                packages.extend([
                    "tesseract",
                    "tesseract-langpack-eng",
                    "tesseract-langpack-rus",
                    "tesseract-langpack-chi_sim",
                    "tesseract-langpack-kaz",
                    "tesseract-langpack-uzb",
                ])
            if needs_audio:
                packages.append("ffmpeg")
            if needs_gui:
                packages.extend([
                    "libglvnd-glx",
                    "libxkbcommon-x11",
                    "xcb-util-cursor",
                    "google-noto-sans-cjk-fonts",
                    "xorg-x11-server-Xvfb",
                    "x11vnc",
                    "novnc",
                    "python3-websockify",
                ])
            return [["sudo", "dnf", "install", *dict.fromkeys(packages)]]
        if "arch" in distro:
            packages = []
            if needs_ocr:
                packages.extend([
                    "tesseract",
                    "tesseract-data-eng",
                    "tesseract-data-rus",
                    "tesseract-data-chi_sim",
                    "tesseract-data-kaz",
                    "tesseract-data-uzb",
                ])
            if needs_audio:
                packages.append("ffmpeg")
            if needs_gui:
                packages.extend([
                    "libgl",
                    "libxkbcommon-x11",
                    "xcb-util-cursor",
                    "noto-fonts-cjk",
                    "xorg-server-xvfb",
                    "x11vnc",
                    "novnc",
                    "python-websockify",
                ])
            return [["sudo", "pacman", "-S", *dict.fromkeys(packages)]]
    return []


def _format_command(command: list[str]) -> str:
    return " ".join(_quote(part) for part in command)


def _linux_id_like() -> set[str]:
    values: set[str] = {"linux"}
    path = Path("/etc/os-release")
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith(("ID=", "ID_LIKE=")):
            _, raw_value = line.split("=", 1)
            values.update(raw_value.strip().strip('"').lower().split())
    return values


def _print_next_steps(venv_dir: Path) -> None:
    if platform.system() == "Windows":
        activate = venv_dir / "Scripts" / "activate"
        gui_cmd = f"{venv_dir}\\Scripts\\python.exe -m book_normalizer.gui.app"
        cli_cmd = f"{venv_dir}\\Scripts\\normalize-book.exe doctor --skip-network"
    else:
        activate = venv_dir / "bin" / "activate"
        gui_cmd = f"{venv_dir}/bin/python -m book_normalizer.gui.app"
        cli_cmd = f"{venv_dir}/bin/normalize-book doctor --skip-network"

    print(_paint("Next steps / Следующие шаги:", "1;36"))
    print(f"  Activate venv / Активировать venv: {activate}")
    print(f"  Run GUI       / Запустить GUI:      {gui_cmd}")
    print(f"  Run checks    / Проверить установку: {cli_cmd}")


if __name__ == "__main__":
    raise SystemExit(main())
