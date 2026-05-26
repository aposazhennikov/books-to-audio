from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from book_normalizer.diagnostics import doctor
from book_normalizer.diagnostics.doctor import _check_comfyui, _check_llm_endpoint, _check_tesseract
from book_normalizer.llm.model_router import FALLBACK_QWEN3_MODEL, PRIMARY_QWEN3_MODEL


@dataclass
class _FakeResponse:
    payload: dict[str, Any]
    status_code: int = 200

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict[str, Any]:
        return self.payload


def test_doctor_checks_native_ollama_api(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    calls: list[str] = []

    def fake_get(url: str, **_kwargs: Any) -> _FakeResponse:
        calls.append(url)
        if url.endswith("/api/version"):
            return _FakeResponse({"version": "0.24.0"})
        if url.endswith("/api/tags"):
            return _FakeResponse(
                {
                    "models": [
                        {"name": PRIMARY_QWEN3_MODEL},
                        {"name": FALLBACK_QWEN3_MODEL},
                    ]
                }
            )
        raise AssertionError(f"Unexpected endpoint: {url}")

    monkeypatch.setattr(httpx, "get", fake_get)

    result = _check_llm_endpoint("http://localhost:11434")

    assert result.status == "ok"
    assert "native Ollama 0.24.0" in result.detail
    assert "2 model(s)" in result.detail
    assert calls == [
        "http://localhost:11434/api/version",
        "http://localhost:11434/api/tags",
    ]


def test_doctor_warns_when_default_qwen3_models_are_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import httpx

    def fake_get(url: str, **_kwargs: Any) -> _FakeResponse:
        if url.endswith("/api/version"):
            return _FakeResponse({"version": "0.24.0"})
        if url.endswith("/api/tags"):
            return _FakeResponse({"models": [{"name": "qwen2.5:3b"}]})
        raise AssertionError(f"Unexpected endpoint: {url}")

    monkeypatch.setattr(httpx, "get", fake_get)

    result = _check_llm_endpoint("http://localhost:11434")

    assert result.status == "warn"
    assert "native Ollama 0.24.0" in result.detail
    assert "Missing default Qwen3 model(s)" in result.detail
    assert PRIMARY_QWEN3_MODEL in result.detail
    assert FALLBACK_QWEN3_MODEL in result.detail
    assert "install.bat --interactive --download-ollama-models" in result.detail
    assert "wsl" not in result.detail.lower()


def test_doctor_ollama_warning_points_to_native_start(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    def fake_get(_url: str, **_kwargs: Any) -> _FakeResponse:
        raise TimeoutError("offline")

    monkeypatch.setattr(httpx, "get", fake_get)

    result = _check_llm_endpoint("http://localhost:11434")

    assert result.status == "warn"
    assert "Ollama Desktop on Windows" in result.detail
    assert "native Linux/macOS terminal" in result.detail
    assert "wsl" not in result.detail.lower()


def test_doctor_tesseract_warning_points_to_native_install(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor, "tesseract_available", lambda: False)

    result = _check_tesseract()

    assert result.status == "warn"
    assert "scanned PDFs" in result.detail
    assert "install.bat --interactive --install-system-tools --download-tessdata" in result.detail
    assert "./install.sh --interactive --install-system-tools --download-tessdata" in result.detail


def test_doctor_tesseract_warns_when_multilingual_tessdata_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(doctor, "tesseract_available", lambda: True)
    monkeypatch.setattr(doctor, "available_tesseract_languages", lambda: {"eng", "rus"})

    result = _check_tesseract()

    assert result.status == "warn"
    assert "missing OCR language data" in result.detail
    assert "chi_sim" in result.detail
    assert "kaz" in result.detail
    assert "uzb" in result.detail


def test_doctor_tesseract_accepts_required_book_languages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor, "tesseract_available", lambda: True)
    monkeypatch.setattr(
        doctor,
        "available_tesseract_languages",
        lambda: {"eng", "rus", "chi_sim", "kaz", "uzb", "osd"},
    )

    result = _check_tesseract()

    assert result.status == "ok"
    assert "eng, rus, chi_sim, kaz, uzb" in result.detail


def test_doctor_comfyui_warning_includes_live_tts_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeComfyClient:
        def __init__(self, url: str) -> None:
            self.url = url

        def is_reachable(self) -> bool:
            return False

    monkeypatch.setattr(doctor, "ComfyUIClient", _FakeComfyClient)
    monkeypatch.setattr(doctor, "_windows_host_url_reachable", lambda _url: False)

    [result] = _check_comfyui("http://127.0.0.1:8188")

    assert result.status == "warn"
    assert "scripts/live_tts_smoke.py" in result.detail
    assert "--comfyui-url http://127.0.0.1:8188" in result.detail
    assert "qwen3_tts_template.json" in result.detail


def test_doctor_comfyui_accepts_windows_host_reachability(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeComfyClient:
        def __init__(self, url: str) -> None:
            self.url = url

        def is_reachable(self) -> bool:
            return False

    monkeypatch.setattr(doctor, "ComfyUIClient", _FakeComfyClient)
    monkeypatch.setattr(doctor, "_windows_host_url_reachable", lambda _url: True)

    [result] = _check_comfyui("http://127.0.0.1:8188")

    assert result.status == "ok"
    assert "reachable from the Windows host" in result.detail
    assert ".venv-windows/Scripts/python.exe" in result.detail
