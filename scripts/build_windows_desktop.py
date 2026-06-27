#!/usr/bin/env python3
"""Build a portable Windows desktop bundle with PyInstaller."""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "BooksToAudio"
CLI_NAME = "NormalizeBook"
DISPLAY_NAME = "Books to Audio"
DEFAULT_DIST = ROOT / "dist" / "windows"
GUI_ENTRYPOINT = ROOT / "src" / "book_normalizer" / "gui" / "app.py"
CLI_ENTRYPOINT = ROOT / "src" / "book_normalizer" / "cli.py"
ICON = ROOT / "src" / "book_normalizer" / "gui" / "assets" / "icon.ico"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Books to Audio portable Windows desktop bundle.")
    parser.add_argument("--dist-dir", type=Path, default=DEFAULT_DIST)
    parser.add_argument("--no-zip", action="store_true", help="Leave the bundle directory without creating a zip.")
    parser.add_argument(
        "--allow-non-windows",
        action="store_true",
        help="Allow command generation on non-Windows hosts. The resulting executable is still Windows-only.",
    )
    args = parser.parse_args(argv)

    if platform.system() != "Windows" and not args.allow_non_windows:
        print("Windows desktop bundles must be built on Windows, or pass --allow-non-windows for CI command checks.")
        return 1

    bundle_dir = build_pyinstaller_bundle(args.dist_dir)
    write_portable_layout(bundle_dir)
    archive = None if args.no_zip else create_zip(bundle_dir)
    print(f"Portable bundle: {bundle_dir}")
    if archive is not None:
        print(f"Zip artifact: {archive}")
    return 0


def pyinstaller_command(
    dist_dir: Path,
    *,
    name: str,
    entrypoint: Path,
    windowed: bool,
    onefile: bool = False,
) -> list[str]:
    mode = "--windowed" if windowed else "--console"
    layout = "--onefile" if onefile else "--onedir"
    return [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        mode,
        layout,
        "--name",
        name,
        "--icon",
        str(ICON),
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(ROOT / "build" / "pyinstaller"),
        "--specpath",
        str(ROOT / "build" / "pyinstaller"),
        "--add-data",
        f"{ROOT / 'src' / 'book_normalizer' / 'gui' / 'assets'};book_normalizer/gui/assets",
        str(entrypoint),
    ]


def build_pyinstaller_bundle(dist_dir: Path) -> Path:
    dist_dir.mkdir(parents=True, exist_ok=True)
    _run_pyinstaller(pyinstaller_command(dist_dir, name=APP_NAME, entrypoint=GUI_ENTRYPOINT, windowed=True))
    _run_pyinstaller(
        pyinstaller_command(dist_dir, name=CLI_NAME, entrypoint=CLI_ENTRYPOINT, windowed=False, onefile=True)
    )
    bundle_dir = dist_dir / APP_NAME
    if not bundle_dir.exists():
        raise SystemExit(f"PyInstaller did not create {bundle_dir}")
    cli_exe = dist_dir / f"{CLI_NAME}.exe"
    if not cli_exe.exists():
        raise SystemExit(f"PyInstaller did not create {cli_exe}")
    merge_cli_bundle(bundle_dir, cli_exe)
    return bundle_dir


def _run_pyinstaller(command: list[str]) -> None:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.stdout + result.stderr)


def merge_cli_bundle(bundle_dir: Path, cli_exe: Path) -> None:
    shutil.copy2(cli_exe, bundle_dir / cli_exe.name)
    cli_exe.unlink()


def write_portable_layout(bundle_dir: Path) -> None:
    for folder in ("models", "data", "output"):
        (bundle_dir / folder).mkdir(parents=True, exist_ok=True)

    (bundle_dir / "Books to Audio.bat").write_text(
        "@echo off\r\n"
        "setlocal\r\n"
        "set BOOKS_TO_AUDIO_MODELS_DIR=%~dp0models\r\n"
        "set HF_HOME=%~dp0models\\hf-cache\r\n"
        "set BOOKS_TO_AUDIO_DATA_DIR=%~dp0data\r\n"
        f"start \"{DISPLAY_NAME}\" \"%~dp0{APP_NAME}.exe\"\r\n",
        encoding="utf-8",
    )
    (bundle_dir / "Normalize Book CLI.bat").write_text(
        "@echo off\r\n"
        "setlocal\r\n"
        "set BOOKS_TO_AUDIO_MODELS_DIR=%~dp0models\r\n"
        "set HF_HOME=%~dp0models\\hf-cache\r\n"
        "set BOOKS_TO_AUDIO_DATA_DIR=%~dp0data\r\n"
        f"\"%~dp0{CLI_NAME}.exe\" %*\r\n",
        encoding="utf-8",
    )
    (bundle_dir / "README.txt").write_text(
        "Books to Audio portable bundle\r\n"
        "\r\n"
        "Run Books to Audio.bat to launch the desktop app.\r\n"
        "Keep model files under models\\, local state under data\\, and generated audio under output\\.\r\n"
        "These folders are intentionally local and should not be committed to git.\r\n",
        encoding="utf-8",
    )
    write_windows_shortcut_script(bundle_dir)


def write_windows_shortcut_script(bundle_dir: Path) -> None:
    script = bundle_dir / "Create Desktop Shortcut.ps1"
    script.write_text(
        "$Shell = New-Object -ComObject WScript.Shell\r\n"
        "$Desktop = [Environment]::GetFolderPath('Desktop')\r\n"
        f"$Shortcut = $Shell.CreateShortcut((Join-Path $Desktop '{DISPLAY_NAME}.lnk'))\r\n"
        "$Root = Split-Path -Parent $MyInvocation.MyCommand.Path\r\n"
        "$Shortcut.TargetPath = Join-Path $Root 'Books to Audio.bat'\r\n"
        "$Shortcut.WorkingDirectory = $Root\r\n"
        f"$Shortcut.IconLocation = Join-Path $Root '{APP_NAME}.exe'\r\n"
        "$Shortcut.Save()\r\n",
        encoding="utf-8",
    )


def create_zip(bundle_dir: Path) -> Path:
    archive_base = bundle_dir.parent / bundle_dir.name
    archive = Path(shutil.make_archive(str(archive_base), "zip", bundle_dir.parent, bundle_dir.name))
    return archive


if __name__ == "__main__":
    raise SystemExit(main())
