#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"
export PYTHONUTF8=1

if [ ! -x ".venv/bin/python" ]; then
    ./install.sh --no-system-check
fi

if ! .venv/bin/python -c "import PyQt6, book_normalizer, huggingface_hub" >/dev/null 2>&1; then
    ./install.sh --no-system-check
fi

exec .venv/bin/python -m book_normalizer.gui.app
