"""Mocked tests for the ComfyUI HTTP client."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from book_normalizer.comfyui.client import ComfyUIClient


class _Response:
    def __init__(self, data: dict[str, Any] | None = None, content: bytes = b"") -> None:
        self._data = data or {}
        self._content = content
        self.status_code = 200
        self.text = ""

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._data

    def iter_bytes(self, chunk_size: int = 65536):  # noqa: ANN202
        yield self._content or b"abc"

    def __enter__(self):  # noqa: ANN204
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_queue_prompt_returns_prompt_id(monkeypatch) -> None:  # noqa: ANN001
    def fake_post(url: str, json: dict, timeout: float) -> _Response:  # noqa: A002
        assert url == "http://localhost:8188/prompt"
        assert json == {"prompt": {"1": {}}}
        assert timeout == 30.0
        return _Response({"prompt_id": "abc"})

    import httpx

    monkeypatch.setattr(httpx, "post", fake_post)

    assert ComfyUIClient().queue_prompt({"1": {}}) == "abc"


def test_wait_for_completion_reads_audio_output(monkeypatch) -> None:  # noqa: ANN001
    client = ComfyUIClient()
    calls = {"n": 0}

    def fake_history(prompt_id: str) -> dict[str, Any]:
        calls["n"] += 1
        if calls["n"] == 1:
            return {}
        return {
            "status": {"status_str": "success"},
            "outputs": {"2": {"audio": [{"filename": "out.wav", "subfolder": "x", "type": "output"}]}},
        }

    monkeypatch.setattr(client, "get_history", fake_history)
    monkeypatch.setattr("time.sleep", lambda _seconds: None)

    assert client.wait_for_completion("abc", timeout=1) == {
        "filename": "out.wav",
        "subfolder": "x",
        "type": "output",
    }


def test_download_audio_streams_to_file(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    def fake_stream(method: str, url: str, params: dict, timeout: float) -> _Response:
        assert method == "GET"
        assert url == "http://localhost:8188/view"
        assert params["filename"] == "out.wav"
        return _Response(content=b"wav-bytes")

    import httpx

    monkeypatch.setattr(httpx, "stream", fake_stream)
    out = ComfyUIClient().download_audio("out.wav", "", tmp_path / "out.wav")

    assert out.read_bytes() == b"wav-bytes"


def test_upload_audio_uses_comfyui_upload_endpoint(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    audio = tmp_path / "voice.wav"
    audio.write_bytes(b"data")

    def fake_post(url: str, files: dict, data: dict, timeout: float) -> _Response:
        assert url == "http://localhost:8188/upload/image"
        assert data == {"type": "input", "overwrite": "true"}
        assert "image" in files
        return _Response({"name": "voice.wav"})

    import httpx

    monkeypatch.setattr(httpx, "post", fake_post)

    assert ComfyUIClient().upload_audio(audio) == "voice.wav"


def test_list_saved_speakers_reads_object_info(monkeypatch) -> None:  # noqa: ANN001
    def fake_get(url: str, timeout: float) -> _Response:
        assert url == "http://localhost:8188/object_info"
        return _Response(
            {
                "FB_Qwen3TTSLoadSpeaker": {
                    "input": {"required": {"filename": [["None", "narrator", "men"]]}}
                }
            }
        )

    import httpx

    monkeypatch.setattr(httpx, "get", fake_get)

    assert ComfyUIClient().list_saved_speakers() == ["narrator", "men"]
