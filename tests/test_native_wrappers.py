"""Checks for native OS launch/install wrappers."""

from __future__ import annotations

from pathlib import Path

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
