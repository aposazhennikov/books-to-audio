#!/bin/bash
# Run TTS synthesis in WSL with Qwen3-TTS.
# Usage: wsl -e bash scripts/run_tts.sh [chapter_number]

set -e
source ~/venvs/qwen3tts/bin/activate

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="$PROJECT_DIR/output/master_magii_1_pdf"
MANIFEST="$OUT_DIR/chunks_manifest.json"

CHAPTER_ARG=""
if [ -n "$1" ]; then
    CHAPTER_ARG="--chapter $1"
fi

python "$PROJECT_DIR/scripts/tts_runner.py" \
    --chunks-json "$MANIFEST" \
    --out "$OUT_DIR" \
    --model "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice" \
    --narrator-speaker "Aiden" \
    --male-speaker "Ryan" \
    --female-speaker "Serena" \
    --resume \
    $CHAPTER_ARG
