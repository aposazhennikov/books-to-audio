"""Language-aware model routing for local Ollama processing."""

from __future__ import annotations

from dataclasses import dataclass

from book_normalizer.languages import SUPPORTED_LANGUAGE_CODES, normalize_book_language

PRIMARY_QWEN3_MODEL = "hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M"
FALLBACK_QWEN3_MODEL = "hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M"

LEGACY_LOCAL_MODEL_DEFAULTS = {
    "",
    "auto",
    "gemma3:4b",
    "qwen3:8b",
}


@dataclass(frozen=True)
class OllamaModelPlan:
    """Resolved local model sequence for one book language."""

    language: str
    primary_model: str
    fallback_model: str
    candidates: tuple[str, ...]
    num_ctx: int = 4096
    num_parallel: int = 1
    keep_alive: str = "5m"
    think: bool = False


def model_plan_for_language(
    language: str | None,
    *,
    preferred_model: str = "",
    lightweight: bool = False,
    allow_fallback: bool = True,
) -> OllamaModelPlan:
    """Return the Ollama model plan for a supported book language.

    Qwen3-8B is the default for every supported language because it is the
    best quality model that should fit in the target 8 GB VRAM setup. Qwen3-4B
    is kept as a fallback for memory or timeout failures.
    """

    normalized_language = normalize_book_language(language)
    if normalized_language not in SUPPORTED_LANGUAGE_CODES:
        normalized_language = normalize_book_language("")

    primary = FALLBACK_QWEN3_MODEL if lightweight else PRIMARY_QWEN3_MODEL
    fallback = FALLBACK_QWEN3_MODEL

    preferred = (preferred_model or "").strip()
    if preferred and preferred.lower() not in LEGACY_LOCAL_MODEL_DEFAULTS:
        primary = preferred

    candidates: list[str] = [primary]
    if allow_fallback and fallback not in candidates:
        candidates.append(fallback)

    return OllamaModelPlan(
        language=normalized_language,
        primary_model=primary,
        fallback_model=fallback,
        candidates=tuple(candidates),
    )
