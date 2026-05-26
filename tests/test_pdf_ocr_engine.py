"""Tests for PDF OCR runtime helpers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

from book_normalizer.loaders import pdf_ocr_engine
from book_normalizer.loaders.pdf_ocr_engine import tesseract_available
from book_normalizer.runtime_paths import reset_runtime_path_cache


def _isolate_runtime_config(monkeypatch, tmp_path: Path) -> None:
    """Keep OCR runtime tests independent from a developer's local install."""
    monkeypatch.setenv("BOOKS_TO_AUDIO_RUNTIME_CONFIG", str(tmp_path / "missing-runtime.json"))
    monkeypatch.delenv("BOOKS_TO_AUDIO_TESSERACT_CMD", raising=False)
    monkeypatch.delenv("BOOKS_TO_AUDIO_TESSDATA_DIR", raising=False)
    monkeypatch.delenv("TESSDATA_PREFIX", raising=False)
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


def test_tesseract_available_ignores_stale_wsl_config_on_windows(
    monkeypatch,
    tmp_path,
) -> None:
    """Windows GUI must not get stuck on a runtime config written by WSL."""
    _isolate_runtime_config(monkeypatch, tmp_path)
    config_path = tmp_path / "local_runtime_paths.json"
    config_path.write_text(
        json.dumps(
            {
                "tesseract_cmd": "/usr/bin/tesseract",
                "tessdata_dir": "/mnt/c/Users/LENOVO/project/data/tessdata",
            }
        ),
        encoding="utf-8",
    )
    native = tmp_path / "Program Files" / "Tesseract-OCR" / "tesseract.exe"
    calls: list[list[str]] = []

    def fake_import(name, *args, **kwargs):  # noqa: ANN001
        if name == "pytesseract":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    def fake_run(args, *_args, **_kwargs):  # noqa: ANN001
        calls.append(args)
        return subprocess.CompletedProcess(args, 0)

    real_import = __import__
    monkeypatch.setenv("BOOKS_TO_AUDIO_RUNTIME_CONFIG", str(config_path))
    monkeypatch.setattr(pdf_ocr_engine.platform, "system", lambda: "Windows")
    monkeypatch.setattr("builtins.__import__", fake_import)
    monkeypatch.setattr(pdf_ocr_engine.shutil, "which", lambda name: str(native))
    monkeypatch.setattr(pdf_ocr_engine.subprocess, "run", fake_run)
    reset_runtime_path_cache()

    assert tesseract_available() is True
    assert calls == [[str(native), "--version"]]
    reset_runtime_path_cache()


def test_tesseract_available_finds_standard_windows_install_when_path_is_stale(
    monkeypatch,
    tmp_path,
) -> None:
    _isolate_runtime_config(monkeypatch, tmp_path)
    program_files = tmp_path / "Program Files"
    native = program_files / "Tesseract-OCR" / "tesseract.exe"
    native.parent.mkdir(parents=True)
    native.write_text("", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_import(name, *args, **kwargs):  # noqa: ANN001
        if name == "pytesseract":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    def fake_run(args, *_args, **_kwargs):  # noqa: ANN001
        calls.append(args)
        return subprocess.CompletedProcess(args, 0)

    real_import = __import__
    monkeypatch.setattr(pdf_ocr_engine.platform, "system", lambda: "Windows")
    monkeypatch.setenv("ProgramFiles", str(program_files))
    monkeypatch.delenv("ProgramFiles(x86)", raising=False)
    monkeypatch.setattr("builtins.__import__", fake_import)
    monkeypatch.setattr(pdf_ocr_engine.shutil, "which", lambda name: None)
    monkeypatch.setattr(pdf_ocr_engine.subprocess, "run", fake_run)

    assert tesseract_available() is True
    assert calls == [[str(native), "--version"]]
    reset_runtime_path_cache()


def test_tesseract_available_finds_project_local_windows_binary(
    monkeypatch,
    tmp_path,
) -> None:
    _isolate_runtime_config(monkeypatch, tmp_path)
    project = tmp_path / "project"
    native = project / "tools" / "Tesseract-OCR" / "tesseract.exe"
    native.parent.mkdir(parents=True)
    native.write_text("", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_import(name, *args, **kwargs):  # noqa: ANN001
        if name == "pytesseract":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    def fake_run(args, *_args, **_kwargs):  # noqa: ANN001
        calls.append(args)
        return subprocess.CompletedProcess(args, 0)

    real_import = __import__
    monkeypatch.setattr(pdf_ocr_engine.platform, "system", lambda: "Windows")
    monkeypatch.delenv("ProgramFiles", raising=False)
    monkeypatch.delenv("ProgramFiles(x86)", raising=False)
    monkeypatch.setattr("builtins.__import__", fake_import)
    monkeypatch.setattr(pdf_ocr_engine.shutil, "which", lambda name: None)
    monkeypatch.setattr(pdf_ocr_engine, "project_root", lambda: project)
    monkeypatch.setattr(pdf_ocr_engine.subprocess, "run", fake_run)

    assert tesseract_available() is True
    assert calls == [[str(native), "--version"]]
    reset_runtime_path_cache()


def test_tesseract_available_sets_configured_pytesseract_paths(monkeypatch, tmp_path) -> None:
    _isolate_runtime_config(monkeypatch, tmp_path)
    configured = tmp_path / "Tesseract-OCR" / "tesseract.exe"
    tessdata = tmp_path / "Tesseract-OCR" / "tessdata"
    configured.parent.mkdir()
    tessdata.mkdir()
    configured.write_text("", encoding="utf-8")
    fake_pytesseract = SimpleNamespace(
        pytesseract=SimpleNamespace(tesseract_cmd=""),
        get_tesseract_version=lambda: "5.3.0",
    )

    def fake_import(name, *args, **kwargs):  # noqa: ANN001
        if name == "pytesseract":
            return fake_pytesseract
        return real_import(name, *args, **kwargs)

    real_import = __import__
    monkeypatch.setenv("BOOKS_TO_AUDIO_TESSERACT_CMD", str(configured))
    monkeypatch.setenv("BOOKS_TO_AUDIO_TESSDATA_DIR", str(tessdata))
    monkeypatch.setattr("builtins.__import__", fake_import)

    assert tesseract_available() is True
    assert fake_pytesseract.pytesseract.tesseract_cmd == str(configured)
    assert pdf_ocr_engine.os.environ["TESSDATA_PREFIX"] == str(tessdata)


def test_tesseract_cli_receives_configured_tessdata_prefix(monkeypatch, tmp_path) -> None:
    _isolate_runtime_config(monkeypatch, tmp_path)
    configured = tmp_path / "Tesseract-OCR" / "tesseract.exe"
    tessdata = tmp_path / "Tesseract-OCR" / "tessdata"
    configured.parent.mkdir()
    tessdata.mkdir()
    configured.write_text("", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_run(args, **kwargs):  # noqa: ANN001
        captured["args"] = args
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(args, 0, stdout=b"Recognized text", stderr=b"")

    monkeypatch.setenv("BOOKS_TO_AUDIO_TESSERACT_CMD", str(configured))
    monkeypatch.setenv("BOOKS_TO_AUDIO_TESSDATA_DIR", str(tessdata))
    monkeypatch.setattr(pdf_ocr_engine.subprocess, "run", fake_run)

    text = pdf_ocr_engine.ocr_image_via_tesseract_cli(b"png", "rus+eng", psm=6)

    assert text == "Recognized text"
    assert captured["args"][:3] == [str(configured), captured["args"][1], "stdout"]
    assert captured["env"]["TESSDATA_PREFIX"] == str(tessdata)


def test_available_tesseract_languages_uses_native_cli_and_tessdata_prefix(
    monkeypatch,
    tmp_path,
) -> None:
    _isolate_runtime_config(monkeypatch, tmp_path)
    configured = tmp_path / "Tesseract-OCR" / "tesseract.exe"
    tessdata = tmp_path / "Tesseract-OCR" / "tessdata"
    configured.parent.mkdir()
    tessdata.mkdir()
    configured.write_text("", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_run(args, **kwargs):  # noqa: ANN001
        captured["args"] = args
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(
            args,
            0,
            stdout="List of available languages in tessdata (5):\neng\nrus\nchi_sim\nkaz\nuzb\n",
            stderr="",
        )

    monkeypatch.setenv("BOOKS_TO_AUDIO_TESSERACT_CMD", str(configured))
    monkeypatch.setenv("BOOKS_TO_AUDIO_TESSDATA_DIR", str(tessdata))
    monkeypatch.setattr(pdf_ocr_engine.subprocess, "run", fake_run)

    languages = pdf_ocr_engine.available_tesseract_languages()

    assert languages == {"eng", "rus", "chi_sim", "kaz", "uzb"}
    assert captured["args"] == [str(configured), "--list-langs"]
    assert captured["env"]["TESSDATA_PREFIX"] == str(tessdata)


def test_available_tesseract_languages_does_not_probe_wsl_when_native_missing(
    monkeypatch,
    tmp_path,
) -> None:
    _isolate_runtime_config(monkeypatch, tmp_path)

    def fake_run(*_args, **_kwargs):  # noqa: ANN001
        raise AssertionError("language scan must not run without a native binary")

    monkeypatch.setattr(pdf_ocr_engine.shutil, "which", lambda name: None)
    monkeypatch.setattr(pdf_ocr_engine.subprocess, "run", fake_run)

    assert pdf_ocr_engine.available_tesseract_languages() == set()


def test_tesseract_language_available_requires_every_requested_pack(monkeypatch) -> None:
    monkeypatch.setattr(
        pdf_ocr_engine,
        "available_tesseract_languages",
        lambda: {"eng", "rus", "chi_sim"},
    )

    assert pdf_ocr_engine.tesseract_language_available("rus") is True
    assert pdf_ocr_engine.tesseract_language_available("rus+eng") is True
    assert pdf_ocr_engine.tesseract_language_available("kaz") is False
    assert pdf_ocr_engine.tesseract_language_available("rus+kaz") is False
    assert pdf_ocr_engine.tesseract_language_available("") is False
    assert pdf_ocr_engine.tesseract_book_language_available("zh") is True
