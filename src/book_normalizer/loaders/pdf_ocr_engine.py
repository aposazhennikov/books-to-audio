"""Tesseract runtime helpers for PDF OCR extraction."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from book_normalizer.runtime_paths import configured_tesseract_cmd


def tesseract_available() -> bool:
    """Check if Tesseract OCR is installed in the current OS environment."""
    try:
        import pytesseract  # noqa: F401

        cmd = _tesseract_command()
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = str(cmd)
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return tesseract_cli_available()


def tesseract_cli_available() -> bool:
    """Check if the Tesseract command-line binary is available locally."""
    command = _tesseract_command()
    if not command:
        return False
    try:
        result = subprocess.run(
            [str(command), "--version"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _tesseract_command() -> Path | str | None:
    configured = configured_tesseract_cmd()
    if configured:
        return configured
    return shutil.which("tesseract")


def ocr_image_via_tesseract_cli(img_bytes: bytes, lang: str, psm: int = 6) -> str:
    """Run Tesseract OCR on image bytes through the local CLI binary."""
    command = _tesseract_command()
    if not command:
        raise RuntimeError("Tesseract is not installed in the current OS environment.")
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(img_bytes)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [
                str(command),
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
