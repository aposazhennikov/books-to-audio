"""Tests for PDF OCR runtime helpers."""

from __future__ import annotations

import subprocess

from book_normalizer.loaders import pdf_ocr_engine
from book_normalizer.loaders.pdf_ocr_engine import tesseract_available, win_to_wsl_path


def test_win_to_wsl_path_converts_drive_path() -> None:
    assert win_to_wsl_path(r"D:\books\scan.png") == "/mnt/d/books/scan.png"


def test_win_to_wsl_path_leaves_unix_path_unchanged() -> None:
    assert win_to_wsl_path("/tmp/scan.png") == "/tmp/scan.png"


def test_tesseract_available_uses_local_cli_when_pytesseract_missing(monkeypatch) -> None:
    def fake_import(name, *args, **kwargs):  # noqa: ANN001
        if name == "pytesseract":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    def fake_run(*_args, **_kwargs):  # noqa: ANN001
        return subprocess.CompletedProcess(["tesseract"], 0)

    real_import = __import__
    monkeypatch.setattr("builtins.__import__", fake_import)
    monkeypatch.setattr(pdf_ocr_engine.shutil, "which", lambda name: "/usr/bin/tesseract")
    monkeypatch.setattr(pdf_ocr_engine.subprocess, "run", fake_run)

    assert tesseract_available() is True
