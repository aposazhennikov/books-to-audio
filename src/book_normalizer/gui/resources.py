"""Shared GUI resource helpers."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtGui import QIcon

WINDOWS_APP_USER_MODEL_ID = "books-to-audio.app"


def asset_path(name: str) -> Path:
    """Return an absolute path to a bundled GUI asset."""
    return Path(__file__).resolve().parent / "assets" / name


def application_icon() -> QIcon:
    """Load the canonical application/window icon."""
    if sys.platform == "win32":
        return QIcon(str(asset_path("icon.ico")))
    return QIcon(str(asset_path("icon.svg")))


def install_windows_app_user_model_id(
    app_id: str = WINDOWS_APP_USER_MODEL_ID,
) -> None:
    """Bind the process to our taskbar identity before QApplication starts."""
    if sys.platform != "win32":
        return

    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except OSError:
        return
