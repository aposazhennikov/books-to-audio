"""Tests for WSL TTS runtime command helpers."""

from __future__ import annotations

from book_normalizer.tts.wsl_runtime import (
    DEFAULT_WSL_TTS_VENVS,
    build_wsl_tts_activation_script,
    wsl_tts_venv_candidates,
)


def test_wsl_tts_venv_candidates_prioritize_explicit_path() -> None:
    candidates = wsl_tts_venv_candidates("~/custom-qwen")

    assert candidates[0] == "~/custom-qwen"
    assert DEFAULT_WSL_TTS_VENVS[0] in candidates


def test_activation_script_checks_env_and_default_venvs() -> None:
    script = build_wsl_tts_activation_script()

    assert "BOOKS_TO_AUDIO_WSL_TTS_VENV" in script
    assert "QWEN3TTS_VENV" in script
    assert "~/venvs/qwen3tts" in script
    assert "~/venv" in script
    assert "source \"$_books_to_audio_tts_venv/bin/activate\"" in script
