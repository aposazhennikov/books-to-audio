"""Checks for native OS launch/install wrappers."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_PATHS = (
    ROOT / "src",
    ROOT / "scripts",
    ROOT / "install.py",
    ROOT / "install.bat",
    ROOT / "install.sh",
    ROOT / "run_gui.bat",
    ROOT / "run_gui.sh",
)


def test_windows_wrappers_use_utf8_and_do_not_delegate_to_wsl() -> None:
    for name in ("install.bat", "run_gui.bat"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "chcp 65001" in text
        assert "PYTHONUTF8=1" in text
        assert "wsl" not in text.lower()


def test_gui_wrappers_prefer_current_source_tree() -> None:
    """Launching the GUI should not show a stale installed package from an old venv."""
    batch_text = (ROOT / "run_gui.bat").read_text(encoding="utf-8")
    shell_text = (ROOT / "run_gui.sh").read_text(encoding="utf-8")

    assert 'set "PYTHONPATH=%CD%\\src;%PYTHONPATH%"' in batch_text
    assert 'export PYTHONPATH="$SCRIPT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"' in shell_text
    assert "--check" in batch_text
    assert "--check" in shell_text


def test_posix_gui_wrapper_supports_web_browser_mode() -> None:
    shell_text = (ROOT / "run_gui.sh").read_text(encoding="utf-8")

    assert "--web" in shell_text
    assert "Xvfb" in shell_text
    assert "x11vnc" in shell_text
    assert "websockify" in shell_text
    assert "WAYLAND_DISPLAY" in shell_text
    assert "vnc.html?autoconnect=1&resize=scale" in shell_text
    assert "ssh -L" in shell_text


def test_linux_system_tool_hints_include_web_gui_dependencies() -> None:
    installer_text = (ROOT / "install.py").read_text(encoding="utf-8")

    assert "xvfb" in installer_text.lower()
    assert "x11vnc" in installer_text
    assert "novnc" in installer_text
    assert "websockify" in installer_text


def test_run_gui_batch_keeps_windows_line_endings() -> None:
    batch_bytes = (ROOT / "run_gui.bat").read_bytes()

    assert batch_bytes.count(b"\n") == batch_bytes.count(b"\r\n")


def test_posix_gui_wrapper_check_smoke_uses_native_venv() -> None:
    """The POSIX GUI wrapper must be callable without starting the window."""
    if sys.platform == "win32" or not (ROOT / ".venv" / "bin" / "python").exists():
        pytest.skip("POSIX native venv is not available in this checkout")
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")

    result = subprocess.run(
        ["sh", "run_gui.sh", "--check"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )

    combined = f"{result.stdout}\n{result.stderr}"
    assert result.returncode == 0, combined
    assert "Native POSIX GUI environment OK." in combined
    assert "wsl" not in combined.lower()


def test_windows_gui_wrapper_check_smoke_uses_native_venv() -> None:
    """The Windows GUI wrapper must be callable without starting the window."""
    if sys.platform != "win32" or not (ROOT / ".venv-windows" / "Scripts" / "python.exe").exists():
        pytest.skip("Windows native venv is not available in this checkout")
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")

    result = subprocess.run(
        ["cmd", "/c", "run_gui.bat", "--check"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )

    combined = f"{result.stdout}\n{result.stderr}"
    assert result.returncode == 0, combined
    assert "Native Windows GUI environment OK." in combined
    assert "Нативная Windows-среда GUI готова." in combined
    assert "Рќ" not in combined
    assert "Р " not in combined
    assert "wsl" not in combined.lower()


def test_posix_wrappers_use_native_python_and_do_not_delegate_to_wsl() -> None:
    for name in ("install.sh", "run_gui.sh"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "PYTHONUTF8=1" in text
        assert "wsl" not in text.lower()


def test_production_sources_do_not_reference_wsl_launch_paths() -> None:
    """Application/runtime code must stay native on Windows, Linux, and macOS."""
    forbidden = ("wsl", "wsl.exe", "bash -lc", "ubuntu-24.04", "/mnt/c")
    for root in PRODUCTION_PATHS:
        paths = root.rglob("*") if root.is_dir() else (root,)
        for path in paths:
            if "__pycache__" in path.parts:
                continue
            if path.suffix.lower() in {
                ".png",
                ".jpg",
                ".jpeg",
                ".webp",
                ".wav",
                ".flac",
                ".pyc",
            }:
                continue
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            assert not any(token in text for token in forbidden), path
