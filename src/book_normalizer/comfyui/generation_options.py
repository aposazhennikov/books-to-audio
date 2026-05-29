"""Generation option handling for ComfyUI Qwen TTS workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DEFAULT_TEMPERATURE = 0.55
DEFAULT_TOP_P = 0.65
DEFAULT_TOP_K = 12
DEFAULT_REPETITION_PENALTY = 1.08
DEFAULT_MAX_NEW_TOKENS = 2048
DEFAULT_SEED = 42
DEFAULT_SPEECH_RATE = 1.0


@dataclass(frozen=True)
class GenerationOptions:
    """Stable synthesis knobs that can be injected into workflow nodes."""

    batch_size: int = 1
    temperature: float = DEFAULT_TEMPERATURE
    top_p: float = DEFAULT_TOP_P
    top_k: int = DEFAULT_TOP_K
    repetition_penalty: float = DEFAULT_REPETITION_PENALTY
    max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS
    seed: int = DEFAULT_SEED
    speech_rate: float = DEFAULT_SPEECH_RATE
    output_format: str = "both"

    def for_attempt(
        self,
        attempt: int,
        *,
        chapter_index: int = 0,
        chunk_index: int = 0,
    ) -> dict[str, Any]:
        """Return deterministic retry options for one chunk attempt.

        Attempt 0 keeps user settings. Attempt 1 changes the seed. Attempt 2+
        also lowers temperature and raises repetition penalty to reduce
        stutter/repetition risk.
        """
        attempt = max(0, int(attempt))
        seed = int(self.seed)
        if attempt > 0:
            base_seed = seed if seed >= 0 else 1_000_003
            seed = (
                base_seed
                + (chapter_index + 1) * 10_007
                + (chunk_index + 1) * 101
                + attempt * 7_919
            ) % 2_147_483_647

        temperature = float(self.temperature)
        repetition_penalty = float(self.repetition_penalty)
        if attempt >= 2:
            temperature = max(0.35, temperature * 0.75)
            repetition_penalty = min(2.0, repetition_penalty + 0.15)

        return {
            "batch_size": max(1, int(self.batch_size)),
            "temperature": temperature,
            "top_p": float(self.top_p),
            "top_k": int(self.top_k),
            "repetition_penalty": repetition_penalty,
            "max_new_tokens": int(self.max_new_tokens),
            "seed": seed,
            "speech_rate": float(self.speech_rate),
            "output_format": str(self.output_format or "both"),
        }


def generation_options_from_mapping(value: GenerationOptions | dict[str, Any] | None) -> GenerationOptions:
    """Build ``GenerationOptions`` from GUI/CLI mapping values."""
    if isinstance(value, GenerationOptions):
        return value
    if not value:
        return GenerationOptions()
    return GenerationOptions(
        batch_size=_int_value(value.get("batch_size"), 1),
        temperature=_float_value(value.get("temperature"), DEFAULT_TEMPERATURE),
        top_p=_float_value(value.get("top_p"), DEFAULT_TOP_P),
        top_k=_int_value(value.get("top_k"), DEFAULT_TOP_K),
        repetition_penalty=_float_value(value.get("repetition_penalty"), DEFAULT_REPETITION_PENALTY),
        max_new_tokens=_int_value(value.get("max_new_tokens"), DEFAULT_MAX_NEW_TOKENS),
        seed=_int_value(value.get("seed"), DEFAULT_SEED),
        speech_rate=_float_value(value.get("speech_rate"), DEFAULT_SPEECH_RATE),
        output_format=str(value.get("output_format") or "both"),
    )


def _float_value(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int_value(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
