from __future__ import annotations

from typing import Any

import pytest

from book_normalizer.llm.ollama_client import OllamaChatClient, OllamaChatError


class _Response:
    def __init__(self, body: dict[str, Any]) -> None:
        self._body = body

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._body


def test_native_chat_payload_strips_openai_suffix(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_post(url: str, **kwargs: Any) -> _Response:
        calls.append({"url": url, **kwargs})
        return _Response({"message": {"content": '{"text":"ok"}'}})

    monkeypatch.setattr("httpx.post", fake_post)
    client = OllamaChatClient(endpoint="http://localhost:11434/v1", keep_alive="7m")

    result = client.chat_json_with_fallback(
        models=["model-a"],
        messages=[{"role": "user", "content": "Hello"}],
        schema={"type": "object", "properties": {"text": {"type": "string"}}},
        temperature=0.2,
    )

    assert result.data == {"text": "ok"}
    assert calls[0]["url"] == "http://localhost:11434/api/chat"
    payload = calls[0]["json"]
    assert payload["model"] == "model-a"
    assert payload["stream"] is False
    assert payload["think"] is False
    assert payload["keep_alive"] == "7m"
    assert payload["options"] == {
        "temperature": 0.2,
        "num_ctx": 4096,
        "num_parallel": 1,
    }
    assert payload["format"]["type"] == "object"


def test_chat_json_falls_back_and_unloads_failed_model(monkeypatch: pytest.MonkeyPatch) -> None:
    chat_models: list[str] = []
    unloaded: list[str] = []

    def fake_post(url: str, **kwargs: Any) -> _Response:
        if url.endswith("/api/generate"):
            unloaded.append(kwargs["json"]["model"])
            return _Response({"done": True})

        model = kwargs["json"]["model"]
        chat_models.append(model)
        if model == "primary":
            return _Response({"message": {"content": "not json"}})
        return _Response({"message": {"content": '{"segments":[]}'}})

    monkeypatch.setattr("httpx.post", fake_post)
    client = OllamaChatClient()

    result = client.chat_json_with_fallback(
        models=["primary", "fallback"],
        messages=[{"role": "user", "content": "x"}],
        schema={"type": "object"},
    )

    assert chat_models == ["primary", "fallback"]
    assert unloaded == ["primary"]
    assert result.model == "fallback"
    assert result.data == {"segments": []}


def test_chat_json_raises_when_all_models_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, **kwargs: Any) -> _Response:
        if url.endswith("/api/generate"):
            return _Response({"done": True})
        return _Response({"message": {"content": "not json"}})

    monkeypatch.setattr("httpx.post", fake_post)
    client = OllamaChatClient()

    with pytest.raises(OllamaChatError):
        client.chat_json_with_fallback(
            models=["a", "b"],
            messages=[{"role": "user", "content": "x"}],
            schema={"type": "object"},
        )
