"""Tesseract runtime helpers for PDF OCR extraction."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

from book_normalizer.languages import tesseract_language
from book_normalizer.runtime_paths import configured_tessdata_dir, configured_tesseract_cmd, project_root


def tesseract_available() -> bool:
    """Check if Tesseract OCR is installed in the current OS environment."""
    try:
        import pytesseract  # noqa: F401

        cmd = _tesseract_command()
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = str(cmd)
        tessdata_dir = configured_tessdata_dir()
        if tessdata_dir:
            os.environ["TESSDATA_PREFIX"] = str(tessdata_dir)
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
            env=_tesseract_env(),
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def available_tesseract_languages() -> set[str]:
    """Return installed Tesseract language data codes for the native binary."""
    command = _tesseract_command()
    if not command:
        return set()
    try:
        result = subprocess.run(
            [str(command), "--list-langs"],
            capture_output=True,
            timeout=10,
            env=_tesseract_env(),
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    if result.returncode != 0:
        return set()

    languages: set[str] = set()
    for line in (result.stdout or "").splitlines():
        value = line.strip()
        if not value or value.lower().startswith("list of available languages"):
            continue
        languages.add(value)
    return languages


def tesseract_language_available(lang: str) -> bool:
    """Return true when every requested Tesseract language pack is installed."""
    requested = {part.strip() for part in lang.split("+") if part.strip()}
    if not requested:
        return False
    available = available_tesseract_languages()
    return requested.issubset(available)


def tesseract_book_language_available(language: str | None) -> bool:
    """Return true when the configured book language can be OCRed locally."""
    return tesseract_language_available(tesseract_language(language))


def _tesseract_command() -> Path | str | None:
    configured = configured_tesseract_cmd()
    if configured and _native_command_path_exists(configured):
        return configured
    discovered = shutil.which("tesseract")
    if discovered:
        return discovered
    for candidate in _project_local_windows_tesseract_paths():
        if candidate.exists():
            return candidate
    for candidate in _common_windows_tesseract_paths():
        if candidate.exists():
            return candidate
    return None


def _native_command_path_exists(path: Path) -> bool:
    """Return true only for paths usable by the current native OS."""
    text = str(path)
    if platform.system() == "Windows" and text.startswith("/") and not text.startswith("//"):
        return False
    return path.exists()


def _common_windows_tesseract_paths() -> tuple[Path, ...]:
    """Return standard Windows install locations when PATH is stale."""
    if platform.system() != "Windows":
        return ()

    roots = (
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
    )
    paths: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        if not root:
            continue
        candidate = Path(root) / "Tesseract-OCR" / "tesseract.exe"
        key = str(candidate).lower()
        if key in seen:
            continue
        paths.append(candidate)
        seen.add(key)
    return tuple(paths)


def _project_local_windows_tesseract_paths() -> tuple[Path, ...]:
    """Return portable/project-local Windows Tesseract install locations."""
    if platform.system() != "Windows":
        return ()
    return (
        project_root() / "tools" / "Tesseract-OCR" / "tesseract.exe",
    )


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
            env=_tesseract_env(),
        )
        return result.stdout.decode("utf-8", errors="replace")
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _tesseract_env() -> dict[str, str] | None:
    """Return an environment with TESSDATA_PREFIX when installer configured it."""
    tessdata_dir = configured_tessdata_dir()
    if not tessdata_dir:
        return None

    env = os.environ.copy()
    env["TESSDATA_PREFIX"] = str(tessdata_dir)
    return env
