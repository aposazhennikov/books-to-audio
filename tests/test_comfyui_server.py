from __future__ import annotations

from pathlib import Path

import pytest

from book_normalizer.comfyui import server


def _portable_root(tmp_path: Path) -> Path:
    root = tmp_path / "ComfyUI"
    (root / "python_embeded").mkdir(parents=True)
    (root / "ComfyUI").mkdir()
    (root / "python_embeded" / "python.exe").write_text("", encoding="utf-8")
    (root / "ComfyUI" / "main.py").write_text("", encoding="utf-8")
    return root


def test_ensure_local_comfyui_starts_portable_when_unreachable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _portable_root(tmp_path)
    started: dict[str, object] = {}

    monkeypatch.setattr(server, "probe_url", lambda _url: False)
    monkeypatch.setattr(server, "wait_for_api", lambda _url, *, timeout: True)

    def fake_start_comfyui(**kwargs):  # noqa: ANN001, ANN202
        started.update(kwargs)

    monkeypatch.setattr(server, "start_comfyui", fake_start_comfyui)

    result = server.ensure_local_comfyui(
        "http://localhost:8189",
        wait_seconds=1,
        log_dir=tmp_path / "logs",
        root=str(root),
    )

    assert result.started is True
    assert result.root == root
    assert result.api_url == "http://localhost:8189/system_stats"
    assert started["root"] == root
    assert started["host"] == "127.0.0.1"
    assert started["port"] == 8189


def test_ensure_local_comfyui_rejects_remote_urls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(server, "probe_url", lambda _url: False)

    with pytest.raises(server.ComfyUIStartError, match="localhost"):
        server.ensure_local_comfyui("http://192.168.1.55:8188", log_dir=tmp_path)
