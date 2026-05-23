"""Native Ollama API client with conservative local resource defaults."""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from book_normalizer.runtime_paths import configured_ollama_endpoint

logger = logging.getLogger(__name__)


class OllamaChatError(RuntimeError):
    """Raised when all local Ollama model attempts fail."""


@dataclass(frozen=True)
class OllamaChatAttempt:
    """One successful Ollama response."""

    model: str
    content: str
    data: Any


class OllamaChatClient:
    """Small wrapper around Ollama's native ``/api/chat`` endpoint."""

    def __init__(
        self,
        endpoint: str | None = None,
        *,
        api_key: str = "",
        timeout: float = 300.0,
        num_ctx: int = 4096,
        num_parallel: int = 1,
        keep_alive: str = "5m",
        think: bool = False,
    ) -> None:
        self._endpoint = _normalise_endpoint(endpoint)
        self._api_key = api_key
        self._timeout = timeout
        self._num_ctx = num_ctx
        self._num_parallel = num_parallel
        self._keep_alive = keep_alive
        self._think = think

    @property
    def endpoint(self) -> str:
        return self._endpoint

    def chat_json_with_fallback(
        self,
        *,
        models: Sequence[str],
        messages: list[dict[str, str]],
        schema: dict[str, Any] | None = None,
        temperature: float = 0.1,
    ) -> OllamaChatAttempt:
        """Call models in order and parse a JSON response from the first success."""

        last_error: Exception | None = None
        for model in models:
            try:
                content = self.chat(
                    model=model,
                    messages=messages,
                    schema=schema,
                    temperature=temperature,
                )
                return OllamaChatAttempt(
                    model=model,
                    content=content,
                    data=_parse_json_response(content),
                )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning("Ollama model %s failed: %s", model, exc)
                self.unload_model(model)

        raise OllamaChatError(
            f"All Ollama model attempts failed: {', '.join(models)}; last_error={last_error!r}"
        )

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        schema: dict[str, Any] | None = None,
        temperature: float = 0.1,
    ) -> str:
        """Return raw assistant content from Ollama ``/api/chat``."""

        try:
            import httpx
        except ImportError as exc:  # pragma: no cover - dependency is declared by extras.
            raise OllamaChatError("httpx is required for local Ollama calls") from exc

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "think": self._think,
            "keep_alive": self._keep_alive,
            "options": {
                "temperature": temperature,
                "num_ctx": self._num_ctx,
                "num_parallel": self._num_parallel,
            },
        }
        if schema is not None:
            payload["format"] = schema

        try:
            response = httpx.post(
                f"{self._endpoint}/api/chat",
                json=payload,
                headers=headers,
                timeout=self._timeout,
            )
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            raise OllamaChatError(f"Ollama chat failed for model {model}: {exc}") from exc

        body = response.json()
        message = body.get("message") if isinstance(body, dict) else None
        if not isinstance(message, dict):
            raise OllamaChatError(f"Unexpected Ollama response shape: {body!r}")
        content = str(message.get("content") or "").strip()
        if not content:
            raise OllamaChatError("Ollama returned empty content")
        return content

    def unload_model(self, model: str) -> None:
        """Ask Ollama to unload a model from memory."""

        try:
            import httpx

            httpx.post(
                f"{self._endpoint}/api/generate",
                json={"model": model, "keep_alive": 0, "prompt": ""},
                timeout=15.0,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not unload Ollama model %s: %s", model, exc)

    def unload_models(self, models: Sequence[str]) -> None:
        """Unload every distinct model in order."""

        seen: set[str] = set()
        for model in models:
            if model in seen:
                continue
            seen.add(model)
            self.unload_model(model)


def _normalise_endpoint(endpoint: str | None) -> str:
    value = (endpoint or configured_ollama_endpoint()).strip().rstrip("/")
    if value.endswith("/v1"):
        value = value[:-3].rstrip("/")
    return value or configured_ollama_endpoint()


def _parse_json_response(content: str) -> Any:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start_obj = cleaned.find("{")
        end_obj = cleaned.rfind("}")
        start_arr = cleaned.find("[")
        end_arr = cleaned.rfind("]")
        candidates: list[str] = []
        if start_obj >= 0 and end_obj > start_obj:
            candidates.append(cleaned[start_obj:end_obj + 1])
        if start_arr >= 0 and end_arr > start_arr:
            candidates.append(cleaned[start_arr:end_arr + 1])
        for candidate in candidates:
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
        raise
