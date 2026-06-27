from __future__ import annotations

from book_normalizer.tts.engines import (
    DEFAULT_TTS_ENGINE_ID,
    get_tts_engine,
    tts_engine_choices,
    unsupported_tts_engine_message,
)


def test_tts_engine_choices_include_requested_engines() -> None:
    choices = dict(tts_engine_choices())

    assert choices["Qwen3 CustomVoice 1.7B (recommended)"] == DEFAULT_TTS_ENGINE_ID
    assert choices["Fish Speech v1.5"] == "fish-speech-1.5"
    assert choices["F5-TTS"] == "f5-tts"
    assert choices["XTTS v2"] == "xtts-v2"
    assert choices["CosyVoice 3"] == "cosyvoice-3"


def test_recommended_engine_is_currently_runnable() -> None:
    engine = get_tts_engine(DEFAULT_TTS_ENGINE_ID)

    assert engine is not None
    assert engine.recommended is True
    assert engine.runnable is True
    assert unsupported_tts_engine_message(DEFAULT_TTS_ENGINE_ID) is None


def test_alternative_engines_are_downloadable_but_not_runnable_yet() -> None:
    message = unsupported_tts_engine_message("f5-tts")

    assert message is not None
    assert "F5-TTS models can be downloaded" in message
    assert "Missing backend: f5-tts" in message

