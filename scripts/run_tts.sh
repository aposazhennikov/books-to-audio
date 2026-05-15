#!/bin/bash
# Run TTS synthesis in WSL with Qwen3-TTS.
# Usage: wsl -e bash scripts/run_tts.sh [chapter_number]

set -e

expand_path() {
    case "$1" in
        "~") printf '%s\n' "$HOME" ;;
        "~/"*) printf '%s/%s\n' "$HOME" "${1#\~/}" ;;
        *) printf '%s\n' "$1" ;;
    esac
}

TTS_VENV=""
for candidate in "${BOOKS_TO_AUDIO_WSL_TTS_VENV:-}" "${QWEN3TTS_VENV:-}" "~/venvs/qwen3tts" "~/venv"; do
    [ -n "$candidate" ] || continue
    candidate="$(expand_path "$candidate")"
    if [ -f "$candidate/bin/activate" ]; then
        TTS_VENV="$candidate"
        break
    fi
done

if [ -z "$TTS_VENV" ]; then
    echo "ERROR: no WSL TTS venv found. Set BOOKS_TO_AUDIO_WSL_TTS_VENV or create ~/venvs/qwen3tts." >&2
    exit 2
fi

source "$TTS_VENV/bin/activate"
echo "WSL TTS venv: $TTS_VENV"

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="$PROJECT_DIR/output/master_magii_1_pdf"
MANIFEST="$OUT_DIR/chunks_manifest.json"

CHAPTER_ARG=""
if [ -n "$1" ]; then
    CHAPTER_ARG="--chapter $1"
fi

SAGE_ARG=""
if [ "${USE_SAGE_ATTENTION:-0}" = "1" ]; then
    SAGE_ARG="--sage-attention"
fi

python "$PROJECT_DIR/scripts/tts_runner.py" \
    --chunks-json "$MANIFEST" \
    --out "$OUT_DIR" \
    --model "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice" \
    --models-dir "/mnt/d/ComfyUI-external/models" \
    --narrator-speaker "Aiden" \
    --male-speaker "Ryan" \
    --female-speaker "Serena" \
    --batch-size 1 \
    --resume \
    $SAGE_ARG \
    $CHAPTER_ARG
