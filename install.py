#!/usr/bin/env python3
"""Cross-platform installer for Books to Audio."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

MIN_PYTHON = (3, 10)
DEFAULT_EXTRAS = {"audio", "gui", "llm", "ocr"}
VERIFY_MODULES = {
    "core": [
        "book_normalizer",
        "click",
        "docx",
        "ebooklib",
        "fitz",
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


def main() -> int:
    _configure_console()
    args = _parse_args()
    project_root = Path(__file__).resolve().parent
    os.chdir(project_root)

    _ensure_python_version()
    extras = _resolve_extras(args)
    venv_dir = (project_root / args.venv).resolve()
    venv_python = _venv_python(venv_dir)

    print("Books to Audio installer")
    print(f"Project: {project_root}")
    print(f"Python:  {sys.version.split()[0]} ({sys.executable})")
    print(f"OS:      {platform.system()} {platform.release()}")
    print(f"Venv:    {venv_dir}")
    print(f"Extras:  {', '.join(sorted(extras)) if extras else 'core only'}")
    print()

    if args.system_check:
        _print_system_dependency_notes(extras)

    if args.dry_run:
        print("Dry run only; no files were changed.")
        editable_flag = "" if args.no_editable else "-e "
        print(f"Would run: {venv_python} -m pip install {editable_flag}{_project_spec(extras)}")
        return 0

    if args.recreate and _same_path(Path(sys.executable), venv_python):
        raise SystemExit(
            "--recreate cannot run from the virtual environment being deleted. "
            "Run install.py with a system Python instead."
        )

    if args.recreate and venv_dir.exists():
        print(f"Removing existing virtual environment: {venv_dir}")
        shutil.rmtree(venv_dir)

    if not venv_python.exists():
        print("Creating virtual environment...")
        _run([sys.executable, "-m", "venv", str(venv_dir)])
    else:
        print("Virtual environment already exists.")

    if not venv_python.exists():
        raise SystemExit(f"Virtual environment Python was not created: {venv_python}")

    print("Upgrading pip/build tools...")
    _run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])

    install_cmd = [str(venv_python), "-m", "pip", "install"]
    if args.upgrade:
        install_cmd.append("--upgrade")
    if args.no_editable:
        install_cmd.append(_project_spec(extras))
    else:
        install_cmd.extend(["-e", _project_spec(extras)])

    print("Installing project dependencies...")
    _run(install_cmd)

    print("Verifying imports...")
    _verify_imports(venv_python, extras)

    print()
    print("Installation complete.")
    _print_next_steps(venv_dir)
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create .venv and install Books to Audio dependencies for Windows, Linux, and macOS.",
    )
    parser.add_argument("--venv", default=".venv", help="Virtual environment directory. Default: .venv")
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


def _configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


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


def _run(cmd: list[str]) -> None:
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    print("+ " + " ".join(_quote(part) for part in cmd))
    subprocess.run(cmd, check=True, env=env)


def _quote(value: str) -> str:
    if any(ch.isspace() for ch in value):
        return f'"{value}"'
    return value


def _verify_imports(venv_python: Path, extras: set[str]) -> None:
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
    _run([str(venv_python), "-c", code])


def _print_system_dependency_notes(extras: set[str]) -> None:
    notes: list[str] = []
    if "ocr" in extras and shutil.which("tesseract") is None:
        notes.append("Tesseract is not on PATH. Scanned PDF OCR will be unavailable until it is installed.")
    if "audio" in extras and shutil.which("ffmpeg") is None:
        notes.append("FFmpeg is not on PATH. WAV output works, but MP3 export via pydub needs FFmpeg.")
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
