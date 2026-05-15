#!/bin/bash
set -euo pipefail

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
    echo "ERROR: no WSL TTS venv found."
    echo "Set BOOKS_TO_AUDIO_WSL_TTS_VENV or create ~/venvs/qwen3tts."
    exit 2
fi

source "$TTS_VENV/bin/activate"
echo "WSL TTS venv: $TTS_VENV"
echo "Python: $(python --version)"
python -c "from qwen_tts import Qwen3TTSModel; print('qwen_tts: OK')"
python -c "import soundfile; print('soundfile: OK')"
python -c "import torch; print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"
python -c "import importlib.util as u; print('sageattention:', 'OK' if u.find_spec('sageattention') else 'missing')"
python -c "import importlib.util as u; print('flash_attn:', 'OK' if u.find_spec('flash_attn') else 'missing')"
echo "VRAM: $(nvidia-smi --query-gpu=memory.total,memory.free --format=csv,noheader 2>/dev/null || echo 'N/A')"
