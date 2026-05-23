"""Helpers for invoking TTS tooling through the current native OS."""

from __future__ import annotations

import json
import subprocess
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
    code = (
        "import importlib.util, json, sys; "
        f"required={REQUIRED_TTS_MODULES!r}; "
        "missing=[name for name in required if importlib.util.find_spec(name) is None]; "
        "print(json.dumps({'executable': sys.executable, 'missing': missing}))"
    )
    try:
        result = subprocess.run(
            [exe, "-c", code],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except Exception as exc:
        return False, f"Could not inspect Python runtime {exe}: {exc}"
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        return False, detail or f"{exe} exited with code {result.returncode}"
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False, result.stdout.strip() or "Python runtime returned non-JSON output."
    missing = payload.get("missing") or []
    executable = str(payload.get("executable") or exe)
    if missing:
        return False, f"{executable}; missing Python packages: {', '.join(missing)}"
    return True, executable
