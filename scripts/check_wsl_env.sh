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
INVALID_VENVS=""

validate_tts_venv() {
    "$1/bin/python" - <<'PY'
import importlib.util
import sys

required = ("qwen_tts", "torch", "soundfile", "numpy")
missing = [name for name in required if importlib.util.find_spec(name) is None]
if missing:
    print("missing Python packages: " + ", ".join(missing), file=sys.stderr)
    sys.exit(1)
PY
}

for candidate in "${BOOKS_TO_AUDIO_WSL_TTS_VENV:-}" "${QWEN3TTS_VENV:-}" "~/venvs/qwen3tts" "~/venv"; do
    [ -n "$candidate" ] || continue
    candidate="$(expand_path "$candidate")"
    if [ -f "$candidate/bin/activate" ]; then
        if missing="$(validate_tts_venv "$candidate" 2>&1)"; then
            TTS_VENV="$candidate"
            break
        fi
        INVALID_VENVS="${INVALID_VENVS}
- ${candidate}: ${missing}"
    fi
done

if [ -z "$TTS_VENV" ]; then
    echo "ERROR: no usable WSL TTS venv found."
    if [ -n "$INVALID_VENVS" ]; then
        echo "Found WSL venv(s), but none has the required TTS packages:"
        printf '%s\n' "$INVALID_VENVS"
        echo "Install them inside WSL, preferably in ~/venvs/qwen3tts:"
        echo "  python3 -m venv ~/venvs/qwen3tts"
        echo "  source ~/venvs/qwen3tts/bin/activate"
        echo "  pip install qwen-tts torch soundfile numpy"
    fi
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
