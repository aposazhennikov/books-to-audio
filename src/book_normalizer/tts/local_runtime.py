"""Helpers for invoking TTS tooling through the current native OS."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REQUIRED_TTS_MODULES = ("qwen_tts", "torch", "soundfile", "numpy")


def build_tts_preview_command(
    *,
    script_path: Path,
    out_dir: Path,
    text: str,
    voice_ids: list[str],
    model: str,
    models_dir: Path,
    python_executable: str | None = None,
) -> list[str]:
    """Build a native OS command for preview synthesis."""
    return [
        python_executable or sys.executable,
        "-u",
        str(script_path),
        "--out",
        str(out_dir),
        "--model",
        model,
        "--models-dir",
        str(models_dir),
        "--ids",
        ",".join(voice_ids),
        "--text",
        text,
    ]


def check_tts_python(
    python_executable: str | None = None,
    *,
    timeout: float = 20.0,
) -> tuple[bool, str]:
    """Return whether the Python runtime has the local TTS dependencies."""
    exe = python_executable or sys.executable
    _ = timeout
    if Path(exe) != Path(sys.executable):
        return (
            False,
            "Voice preview generation runs inside the current native app Python: "
            f"{sys.executable}. Activate or install dependencies there instead of {exe}.",
        )
    missing = [
        name for name in REQUIRED_TTS_MODULES
        if importlib.util.find_spec(name) is None
    ]
    if missing:
        return False, f"{sys.executable}; missing Python packages: {', '.join(missing)}"
    return True, sys.executable
