"""Checks for native OS launch/install wrappers."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
