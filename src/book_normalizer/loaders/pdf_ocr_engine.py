"""Tesseract runtime helpers for PDF OCR extraction."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


def tesseract_available() -> bool:
    """Check if Tesseract OCR is installed in the current OS environment."""
    try:
        import pytesseract  # noqa: F401

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return tesseract_cli_available()


def tesseract_cli_available() -> bool:
    """Check if the Tesseract command-line binary is available locally."""
    if shutil.which("tesseract") is None:
        return False
    try:
        result = subprocess.run(
            ["tesseract", "--version"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def ocr_image_via_tesseract_cli(img_bytes: bytes, lang: str, psm: int = 6) -> str:
    """Run Tesseract OCR on image bytes through the local CLI binary."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(img_bytes)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [
                "tesseract",
                tmp_path,
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
