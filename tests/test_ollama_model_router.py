from __future__ import annotations

import pytest

from book_normalizer.languages import SUPPORTED_LANGUAGE_CODES
from book_normalizer.llm.model_router import (
    FALLBACK_QWEN3_MODEL,
    PRIMARY_QWEN3_MODEL,
    model_plan_for_language,
)


@pytest.mark.parametrize("language", SUPPORTED_LANGUAGE_CODES)
def test_supported_languages_route_to_qwen3_8b_with_4b_fallback(language: str) -> None:
    plan = model_plan_for_language(language)

    assert plan.language == language
    assert plan.primary_model == PRIMARY_QWEN3_MODEL
    assert plan.fallback_model == FALLBACK_QWEN3_MODEL
    assert plan.candidates == (PRIMARY_QWEN3_MODEL, FALLBACK_QWEN3_MODEL)
    assert plan.num_ctx == 4096
    assert plan.num_parallel == 1
    assert plan.keep_alive == "5m"
    assert plan.think is False


@pytest.mark.parametrize("legacy", ["", "auto", "gemma3:4b", "qwen3:8b"])
def test_legacy_defaults_do_not_override_safe_router(legacy: str) -> None:
    plan = model_plan_for_language("ru", preferred_model=legacy)

    assert plan.candidates == (PRIMARY_QWEN3_MODEL, FALLBACK_QWEN3_MODEL)


def test_primary_default_keeps_4b_fallback() -> None:
    plan = model_plan_for_language("ru", preferred_model=PRIMARY_QWEN3_MODEL)

    assert plan.candidates == (PRIMARY_QWEN3_MODEL, FALLBACK_QWEN3_MODEL)


def test_lightweight_mode_uses_4b_only() -> None:
    plan = model_plan_for_language("en", lightweight=True)

    assert plan.primary_model == FALLBACK_QWEN3_MODEL
    assert plan.candidates == (FALLBACK_QWEN3_MODEL,)


def test_custom_model_disables_implicit_4b_fallback() -> None:
    plan = model_plan_for_language("zh", preferred_model="custom:q4")

    assert plan.primary_model == "custom:q4"
    assert plan.candidates == ("custom:q4",)
