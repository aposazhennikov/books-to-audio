"""Tests for PDF OCR runtime helpers."""

from __future__ import annotations

from book_normalizer.loaders.pdf_ocr_engine import win_to_wsl_path


def test_win_to_wsl_path_converts_drive_path() -> None:
    assert win_to_wsl_path(r"D:\books\scan.png") == "/mnt/d/books/scan.png"


def test_win_to_wsl_path_leaves_unix_path_unchanged() -> None:
    assert win_to_wsl_path("/tmp/scan.png") == "/tmp/scan.png"
