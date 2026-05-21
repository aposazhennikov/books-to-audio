"""Tesseract runtime helpers for PDF OCR extraction."""

from __future__ import annotations

import platform
import subprocess
import tempfile
from pathlib import Path


def wsl_tesseract_available() -> bool:
    """Check if Tesseract is available inside WSL."""
    if platform.system() != "Windows":
        return False
    try:
        result = subprocess.run(
            ["wsl", "tesseract", "--version"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def tesseract_available() -> bool:
    """Check if Tesseract OCR is installed and accessible natively or through WSL."""
    try:
        import pytesseract  # noqa: F401

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return wsl_tesseract_available()


def win_to_wsl_path(win_path: str) -> str:
    """Convert a Windows path like C:\\Users\\... to /mnt/c/Users/..."""
    path = win_path.replace("\\", "/")
    if len(path) >= 2 and path[1] == ":":
        drive = path[0].lower()
        path = f"/mnt/{drive}{path[2:]}"
    return path


def ocr_image_via_wsl(img_bytes: bytes, lang: str, psm: int = 6) -> str:
    """Run Tesseract OCR on image bytes through WSL."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(img_bytes)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [
                "wsl",
                "tesseract",
                win_to_wsl_path(tmp_path),
                "stdout",
                "-l",
                lang,
                "--psm",
                str(psm),
            ],
            capture_output=True,
            timeout=120,
        )
        return result.stdout.decode("utf-8", errors="replace")
    finally:
        Path(tmp_path).unlink(missing_ok=True)
