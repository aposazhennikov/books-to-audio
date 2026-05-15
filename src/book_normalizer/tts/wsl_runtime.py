"""Helpers for invoking the WSL TTS runtime from the Windows GUI."""

from __future__ import annotations

import shlex

WSL_TTS_VENV_ENV_VARS = ("BOOKS_TO_AUDIO_WSL_TTS_VENV", "QWEN3TTS_VENV")
DEFAULT_WSL_TTS_VENVS = ("~/venvs/qwen3tts", "~/venv")


def wsl_tts_venv_candidates(explicit: str | None = None) -> list[str]:
    """Return candidate venv paths in the same order the shell will try them."""
    candidates: list[str] = []
    if explicit and explicit.strip():
        candidates.append(explicit.strip())

    candidates.extend(f"${{{name}:-}}" for name in WSL_TTS_VENV_ENV_VARS)
    candidates.extend(DEFAULT_WSL_TTS_VENVS)
    return candidates


def build_wsl_tts_activation_script(explicit_venv: str | None = None) -> str:
    """Return a bash snippet that activates the first available WSL TTS venv.

    The snippet deliberately runs inside WSL so ``$HOME`` and WSL-side
    environment variables are resolved by bash, not by the Windows GUI process.
    """
    candidates = wsl_tts_venv_candidates(explicit_venv)
    shell_candidates = " ".join(_candidate_for_shell(candidate) for candidate in candidates)
    tried = ", ".join(candidates)
    return f"""
set -e
_books_to_audio_expand_path() {{
    case "$1" in
        "~") printf '%s\\n' "$HOME" ;;
        "~/"*) printf '%s/%s\\n' "$HOME" "${{1#\\~/}}" ;;
        *) printf '%s\\n' "$1" ;;
    esac
}}
_books_to_audio_tts_venv=""
for _books_to_audio_candidate in {shell_candidates}; do
    [ -n "$_books_to_audio_candidate" ] || continue
    _books_to_audio_candidate="$(_books_to_audio_expand_path "$_books_to_audio_candidate")"
    if [ -f "$_books_to_audio_candidate/bin/activate" ]; then
        _books_to_audio_tts_venv="$_books_to_audio_candidate"
        break
    fi
done
if [ -z "$_books_to_audio_tts_venv" ]; then
    echo "ERROR: no WSL TTS venv found. Tried: {shlex.quote(tried)}" >&2
    echo "Set BOOKS_TO_AUDIO_WSL_TTS_VENV or create ~/venvs/qwen3tts." >&2
    exit 2
fi
source "$_books_to_audio_tts_venv/bin/activate"
echo "WSL TTS venv: $_books_to_audio_tts_venv"
""".strip()


def _candidate_for_shell(candidate: str) -> str:
    if candidate.startswith("${") and candidate.endswith("}"):
        return f'"{candidate}"'
    return shlex.quote(candidate)
