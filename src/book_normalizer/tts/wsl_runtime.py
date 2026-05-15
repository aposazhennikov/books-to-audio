"""Helpers for invoking the WSL TTS runtime from the Windows GUI."""

from __future__ import annotations

import shlex

WSL_TTS_VENV_ENV_VARS = ("BOOKS_TO_AUDIO_WSL_TTS_VENV", "QWEN3TTS_VENV")
DEFAULT_WSL_TTS_VENVS = ("~/venvs/qwen3tts", "~/venv")
REQUIRED_WSL_TTS_MODULES = ("qwen_tts", "torch", "soundfile", "numpy")


def wsl_tts_venv_candidates(explicit: str | None = None) -> list[str]:
    """Return candidate venv paths in the same order the shell will try them."""
    candidates: list[str] = []
    if explicit and explicit.strip():
        candidates.append(explicit.strip())

    candidates.extend(f"${{{name}:-}}" for name in WSL_TTS_VENV_ENV_VARS)
    candidates.extend(DEFAULT_WSL_TTS_VENVS)
    return candidates


def build_wsl_tts_activation_script(
    explicit_venv: str | None = None,
    *,
    validate_packages: bool = True,
) -> str:
    """Return a bash snippet that activates the first available WSL TTS venv.

    The snippet deliberately runs inside WSL so ``$HOME`` and WSL-side
    environment variables are resolved by bash, not by the Windows GUI process.
    """
    candidates = wsl_tts_venv_candidates(explicit_venv)
    shell_candidates = " ".join(_candidate_for_shell(candidate) for candidate in candidates)
    tried = ", ".join(candidates)
    validation_func = ""
    candidate_body = """
        _books_to_audio_tts_venv="$_books_to_audio_candidate"
        break
""".rstrip()
    missing_packages_hint = ""
    if validate_packages:
        validation_func = f"""
_books_to_audio_validate_tts_venv() {{
    "$1/bin/python" - <<'PY'
import importlib.util
import sys

required = {REQUIRED_WSL_TTS_MODULES!r}
missing = [name for name in required if importlib.util.find_spec(name) is None]
if missing:
    print("missing Python packages: " + ", ".join(missing), file=sys.stderr)
    sys.exit(1)
PY
}}
""".rstrip()
        candidate_body = """
        if _books_to_audio_missing="$(_books_to_audio_validate_tts_venv "$_books_to_audio_candidate" 2>&1)"; then
            _books_to_audio_tts_venv="$_books_to_audio_candidate"
            break
        fi
        _books_to_audio_invalid_venvs="${_books_to_audio_invalid_venvs}
- $_books_to_audio_candidate: $_books_to_audio_missing"
""".rstrip()
        missing_packages_hint = """
    if [ -n "$_books_to_audio_invalid_venvs" ]; then
        echo "Found WSL venv(s), but none has the required TTS packages:" >&2
        printf '%s\\n' "$_books_to_audio_invalid_venvs" >&2
        echo "Install them inside WSL, preferably in ~/venvs/qwen3tts:" >&2
        echo "  python3 -m venv ~/venvs/qwen3tts" >&2
        echo "  source ~/venvs/qwen3tts/bin/activate" >&2
        echo "  pip install qwen-tts torch soundfile numpy" >&2
    fi
""".rstrip()
    return f"""
set -e
_books_to_audio_expand_path() {{
    case "$1" in
        "~") printf '%s\\n' "$HOME" ;;
        "~/"*) printf '%s/%s\\n' "$HOME" "${{1#\\~/}}" ;;
        *) printf '%s\\n' "$1" ;;
    esac
}}
{validation_func}
_books_to_audio_tts_venv=""
_books_to_audio_invalid_venvs=""
for _books_to_audio_candidate in {shell_candidates}; do
    [ -n "$_books_to_audio_candidate" ] || continue
    _books_to_audio_candidate="$(_books_to_audio_expand_path "$_books_to_audio_candidate")"
    if [ -f "$_books_to_audio_candidate/bin/activate" ]; then
{candidate_body}
    fi
done
if [ -z "$_books_to_audio_tts_venv" ]; then
    echo "ERROR: no usable WSL TTS venv found. Tried: {shlex.quote(tried)}" >&2
{missing_packages_hint}
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
