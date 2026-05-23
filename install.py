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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

MIN_PYTHON = (3, 10)
DEFAULT_EXTRAS = {"audio", "gui", "llm", "ocr"}
DEFAULT_OLLAMA_ENDPOINT = "http://localhost:11434"
DEFAULT_OLLAMA_MODELS = (
    "hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M",
    "hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M",
)
INSTALL_TOOL_PACKAGES = ("pip", "setuptools", "wheel", "build")
LOG_PATH = Path("install.log")
RUNTIME_CONFIG_PATH = Path("data/local_runtime_paths.json")
HASH_MANIFEST_PATH = Path("data/install_hashes.json")
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
    "dev": ["pytest", "ruff"],
    "gui": ["PyQt6"],
    "llm": ["httpx"],
    "ocr": ["PIL", "pytesseract"],
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
    _configure_console(project_root / LOG_PATH)

    _ensure_python_version()
    extras = _resolve_extras(args)
    paths = _resolve_install_paths(args, project_root)
    _resolve_optional_downloads(args)
    venv_python = _venv_python(paths.venv_dir)

    _say("Books to Audio installer", "Установщик Books to Audio", "title")
    print(f"Project: {project_root}")
    print(f"Python:  {sys.version.split()[0]} ({sys.executable})")
    print(f"OS:      {platform.system()} {platform.release()}")
    print(f"Venv:    {paths.venv_dir}")
    print(f"Models:  {paths.models_dir}")
    print(f"HF_HOME: {paths.hf_cache_dir}")
    print(f"Ollama:  {paths.ollama_endpoint} ({paths.ollama_bin})")
    print(f"OCR:     {paths.tesseract_cmd}")
    print(f"FFmpeg:  {paths.ffmpeg_bin}")
    print(f"Log:     {(project_root / LOG_PATH).resolve()}")
    print(f"Extras:  {', '.join(sorted(extras)) if extras else 'core only'}")
    print()

    if args.system_check:
        _print_system_dependency_notes(extras, paths)

    if args.install_system_tools:
        _install_system_tools(extras)

    if args.dry_run:
        _say("Dry run only; no files were changed.", "Пробный запуск: файлы не изменялись.", "warn")
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

    if args.download_ollama_models:
        _pull_ollama_models(paths, args.verify_hashes)

    if args.download_tts_models:
        _install_tts_models(venv_python, paths, args.verify_hashes)

    print()
    _say("Installation complete.", "Установка завершена.", "ok")
    _print_next_steps(paths.venv_dir)
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create .venv and install Books to Audio dependencies for Windows, Linux, and macOS.",
    )
    parser.add_argument("--venv", default=".venv", help="Virtual environment directory. Default: .venv")
    parser.add_argument("--interactive", action="store_true", help="Ask for install locations and optional downloads.")
    parser.add_argument("--yes", action="store_true", help="Use defaults/non-interactive answers for prompts.")
    parser.add_argument(
        "--install-root",
        default="",
        help="Base folder for installer-managed data. Default: project folder.",
    )
    parser.add_argument("--models-dir", default="", help="Shared TTS/ComfyUI models folder.")
    parser.add_argument("--hf-cache-dir", default="", help="Hugging Face cache folder.")
    parser.add_argument("--ollama-endpoint", default="", help="Local Ollama endpoint. Default: http://localhost:11434")
    parser.add_argument("--ollama-bin", default="", help="Path or command name for Ollama. Default: ollama")
    parser.add_argument("--tesseract-bin", default="", help="Path or command name for Tesseract OCR.")
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
        "--download-tts-models",
        action="store_true",
        help="Download default Qwen3-TTS models into --models-dir.",
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
    parser.add_argument("--with-dev", action="store_true", help="Install pytest and ruff.")
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
    venv_dir = _prompt_path(
        "Python virtual environment",
        "Python virtualenv",
        args.venv,
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
        "ollama",
        interactive,
    )
    tesseract_cmd = _prompt_text(
        "Tesseract command/path",
        "Команда/путь Tesseract",
        args.tesseract_bin,
        _default_command("tesseract"),
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
        ffmpeg_bin=ffmpeg_bin,
    )


def _should_prompt(args: argparse.Namespace) -> bool:
    if args.dry_run or args.yes:
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
    config_path = project_root / RUNTIME_CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "install_root": str(paths.install_root),
        "venv_dir": str(paths.venv_dir),
        "models_dir": str(paths.models_dir),
        "hf_cache_dir": str(paths.hf_cache_dir),
        "ollama_endpoint": paths.ollama_endpoint,
        "ollama_bin": paths.ollama_bin,
        "tesseract_cmd": paths.tesseract_cmd,
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
                f"BOOKS_TO_AUDIO_RUNTIME_CONFIG={config_path.resolve()}",
                f"BOOKS_TO_AUDIO_MODELS_DIR={paths.models_dir}",
                f"COMFYUI_MODELS_DIR={paths.models_dir}",
                f"HF_HOME={paths.hf_cache_dir}",
                f"BOOKS_TO_AUDIO_OLLAMA_ENDPOINT={paths.ollama_endpoint}",
                f"BOOKS_TO_AUDIO_TESSERACT_CMD={paths.tesseract_cmd}",
                f"BOOKS_TO_AUDIO_FFMPEG_BIN={paths.ffmpeg_bin}",
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


def _pull_ollama_models(paths: InstallPaths, verify_hashes: bool) -> None:
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
    if verify_hashes:
        _record_command_hash("ollama_models", [paths.ollama_bin, "list"], paths)


def _ollama_model_is_present(paths: InstallPaths, model: str) -> bool:
    """Return True when Ollama already has the requested model locally."""
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


def _install_tts_models(venv_python: Path, paths: InstallPaths, verify_hashes: bool) -> None:
    _say("Installing default Qwen3-TTS models...", "Устанавливаю стандартные Qwen3-TTS модели...", "info")
    code = (
        "from pathlib import Path\n"
        "from book_normalizer.tts.model_download import DEFAULT_TTS_MODEL_ID, install_tts_models\n"
        f"models_dir = Path({str(paths.models_dir)!r})\n"
        "install_tts_models([DEFAULT_TTS_MODEL_ID], models_dir, progress=print)\n"
    )
    _run([str(venv_python), "-c", code], paths)
    if verify_hashes:
        _verify_or_write_hash("models_dir", paths.models_dir)


def _record_command_hash(label: str, cmd: list[str], paths: InstallPaths) -> None:
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=_installer_env(paths),
    )
    digest = hashlib.sha256(result.stdout.encode("utf-8", errors="replace")).hexdigest()
    _write_hash_manifest_entry(label, {"sha256": digest, "source": " ".join(cmd)})


def _verify_or_write_hash(label: str, path: Path) -> None:
    _say(f"Hashing {path}...", f"Считаю SHA-256 для {path}...", "info")
    current = _hash_tree(path)
    manifest = _read_hash_manifest()
    previous = manifest.get(label)
    if previous and previous.get("sha256") != current["sha256"]:
        raise SystemExit(
            f"Hash mismatch for {label}: expected {previous.get('sha256')}, got {current['sha256']}"
        )
    _write_hash_manifest_entry(label, current)
    _say(f"Hash verified: {label}", f"Хэш проверен: {label}", "ok")


def _hash_tree(path: Path) -> dict[str, object]:
    if not path.exists():
        raise SystemExit(f"Cannot hash missing path: {path}")
    digest = hashlib.sha256()
    files = [p for p in path.rglob("*") if p.is_file()]
    for file_path in sorted(files):
        rel = file_path.relative_to(path).as_posix()
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
    env["BOOKS_TO_AUDIO_OLLAMA_ENDPOINT"] = paths.ollama_endpoint
    env["BOOKS_TO_AUDIO_TESSERACT_CMD"] = paths.tesseract_cmd
    env["BOOKS_TO_AUDIO_FFMPEG_BIN"] = paths.ffmpeg_bin
    return env


def _print_system_dependency_notes(extras: set[str], paths: InstallPaths) -> None:
    notes: list[str] = []
    if "ocr" in extras and not _command_available(paths.tesseract_cmd):
        notes.append(
            f"Tesseract was not found at '{paths.tesseract_cmd}'. "
            "Scanned PDF OCR will be unavailable until it is installed or the path is corrected."
        )
    if "audio" in extras and not _command_available(paths.ffmpeg_bin):
        notes.append(
            f"FFmpeg was not found at '{paths.ffmpeg_bin}'. "
            "WAV output works, but MP3 export via pydub needs FFmpeg."
        )
    if "tts-sage" in extras and shutil.which("git") is None:
        notes.append("Git is not on PATH. Direct Git dependencies such as SageAttention need Git.")

    command = _system_package_hint(extras)
    if notes:
        print("System dependency notes:")
        for note in notes:
            print(f"- {note}")
        if command:
            print("Suggested system packages:")
            print(f"  {command}")
        print()
    elif command:
        print("System dependency notes: required command-line tools look available.")
        print()


def _install_system_tools(extras: set[str]) -> None:
    command = _system_package_hint(extras)
    if not command:
        _say(
            "No native system tools are required for the selected extras.",
            "Для выбранных опций системные утилиты не требуются.",
            "ok",
        )
        return
    _say("Installing native system tools...", "Устанавливаю системные утилиты нативным менеджером пакетов...", "info")
    print("+ " + command)
    subprocess.run(command, shell=True, check=True)


def _command_available(command: str) -> bool:
    path = Path(command).expanduser()
    if path.is_absolute() or path.parent != Path("."):
        return path.exists()
    return shutil.which(command) is not None


def _system_package_hint(extras: set[str]) -> str:
    needs_ocr = "ocr" in extras
    needs_audio = "audio" in extras
    needs_gui = "gui" in extras
    if not (needs_ocr or needs_audio or needs_gui):
        return ""

    system = platform.system()
    if system == "Darwin":
        packages = []
        if needs_ocr:
            packages.extend(["tesseract", "tesseract-lang"])
        if needs_audio:
            packages.append("ffmpeg")
        if packages:
            return "brew install " + " ".join(dict.fromkeys(packages))
        return ""

    if system == "Windows":
        commands = []
        if needs_ocr:
            commands.append("winget install UB-Mannheim.TesseractOCR")
        if needs_audio:
            commands.append("winget install Gyan.FFmpeg")
        return " && ".join(commands)

    if system == "Linux":
        distro = _linux_id_like()
        if any(name in distro for name in ("debian", "ubuntu")):
            packages = []
            if needs_ocr:
                packages.extend(["tesseract-ocr", "tesseract-ocr-rus"])
            if needs_audio:
                packages.append("ffmpeg")
            if needs_gui:
                packages.extend(["libegl1", "libgl1", "libxcb-cursor0", "libxkbcommon-x11-0"])
            return "sudo apt-get update && sudo apt-get install -y " + " ".join(dict.fromkeys(packages))
        if any(name in distro for name in ("fedora", "rhel", "centos")):
            packages = []
            if needs_ocr:
                packages.extend(["tesseract", "tesseract-langpack-rus"])
            if needs_audio:
                packages.append("ffmpeg")
            if needs_gui:
                packages.extend(["libglvnd-glx", "libxkbcommon-x11", "xcb-util-cursor"])
            return "sudo dnf install " + " ".join(dict.fromkeys(packages))
        if "arch" in distro:
            packages = []
            if needs_ocr:
                packages.extend(["tesseract", "tesseract-data-rus"])
            if needs_audio:
                packages.append("ffmpeg")
            if needs_gui:
                packages.extend(["libgl", "libxkbcommon-x11", "xcb-util-cursor"])
            return "sudo pacman -S " + " ".join(dict.fromkeys(packages))
    return ""


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

    print("Next steps:")
    print(f"  Activate venv: {activate}")
    print(f"  Run GUI:       {gui_cmd}")
    print(f"  Run checks:    {cli_cmd}")


if __name__ == "__main__":
    raise SystemExit(main())
