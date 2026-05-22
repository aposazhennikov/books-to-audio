"""Local LLM helpers for Ollama-backed book processing."""

from book_normalizer.llm.model_router import (
    FALLBACK_QWEN3_MODEL,
    PRIMARY_QWEN3_MODEL,
    OllamaModelPlan,
    model_plan_for_language,
)
from book_normalizer.llm.ollama_client import OllamaChatClient, OllamaChatError

__all__ = [
    "FALLBACK_QWEN3_MODEL",
    "PRIMARY_QWEN3_MODEL",
    "OllamaChatClient",
    "OllamaChatError",
    "OllamaModelPlan",
    "model_plan_for_language",
]
