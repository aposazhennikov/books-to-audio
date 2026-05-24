"""Tests for PDF OCR runtime helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

from book_normalizer.loaders import pdf_ocr_engine
from book_normalizer.loaders.pdf_ocr_engine import tesseract_available
from book_normalizer.runtime_paths import reset_runtime_path_cache


def _isolate_runtime_config(monkeypatch, tmp_path: Path) -> None:
    """Keep OCR runtime tests independent from a developer's local install."""
    monkeypatch.setenv("BOOKS_TO_AUDIO_RUNTIME_CONFIG", str(tmp_path / "missing-runtime.json"))
    monkeypatch.delenv("BOOKS_TO_AUDIO_TESSERACT_CMD", raising=False)
    reset_runtime_path_cache()


def test_tesseract_available_uses_local_cli_when_pytesseract_missing(monkeypatch, tmp_path) -> None:
    _isolate_runtime_config(monkeypatch, tmp_path)

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


def test_tesseract_available_does_not_probe_wsl_when_native_missing(monkeypatch, tmp_path) -> None:
    _isolate_runtime_config(monkeypatch, tmp_path)

    def fake_import(name, *args, **kwargs):  # noqa: ANN001
        if name == "pytesseract":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    def fake_run(args, *_args, **_kwargs):  # noqa: ANN001
        calls.append(args)
        return subprocess.CompletedProcess(args, 1)

    real_import = __import__
    calls: list[list[str]] = []
    monkeypatch.setattr("builtins.__import__", fake_import)
    monkeypatch.setattr(pdf_ocr_engine.shutil, "which", lambda name: None)
    monkeypatch.setattr(pdf_ocr_engine.subprocess, "run", fake_run)

    assert tesseract_available() is False
    assert calls == []


def test_tesseract_available_uses_configured_native_binary(monkeypatch, tmp_path) -> None:
    _isolate_runtime_config(monkeypatch, tmp_path)

    configured = tmp_path / "Tesseract-OCR" / "tesseract.exe"
    configured.parent.mkdir()
    configured.write_text("", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_import(name, *args, **kwargs):  # noqa: ANN001
        if name == "pytesseract":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    def fake_run(args, *_args, **_kwargs):  # noqa: ANN001
        calls.append(args)
        return subprocess.CompletedProcess(args, 0)

    real_import = __import__
    monkeypatch.setenv("BOOKS_TO_AUDIO_TESSERACT_CMD", str(configured))
    monkeypatch.setattr("builtins.__import__", fake_import)
    monkeypatch.setattr(pdf_ocr_engine.shutil, "which", lambda name: None)
    monkeypatch.setattr(pdf_ocr_engine.subprocess, "run", fake_run)

    assert tesseract_available() is True
    assert calls == [[str(configured), "--version"]]
