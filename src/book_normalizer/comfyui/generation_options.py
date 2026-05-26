"""Generation option handling for ComfyUI Qwen TTS workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GenerationOptions:
    """Stable synthesis knobs that can be injected into workflow nodes."""

    batch_size: int = 1
    temperature: float = 1.0
    top_p: float = 0.8
    top_k: int = 20
    repetition_penalty: float = 1.05
    max_new_tokens: int = 2048
    seed: int = -1
    speech_rate: float = 1.0
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
        temperature=_float_value(value.get("temperature"), 1.0),
        top_p=_float_value(value.get("top_p"), 0.8),
        top_k=_int_value(value.get("top_k"), 20),
        repetition_penalty=_float_value(value.get("repetition_penalty"), 1.05),
        max_new_tokens=_int_value(value.get("max_new_tokens"), 2048),
        seed=_int_value(value.get("seed"), -1),
        speech_rate=_float_value(value.get("speech_rate"), 1.0),
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
