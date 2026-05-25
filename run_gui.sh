#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"
export PYTHONUTF8=1
export PYTHONPATH="$SCRIPT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

CHECK_ONLY=0
if [ "${1:-}" = "--check" ]; then
    CHECK_ONLY=1
    shift
fi

if [ ! -x ".venv/bin/python" ]; then
    if [ "$CHECK_ONLY" = "1" ]; then
        printf '%s\n' "Native POSIX GUI environment is not ready."
        printf '%s\n' "   Нативная POSIX-среда GUI не готова."
        printf '%s\n' "Run ./install.sh first, then try ./run_gui.sh --check again."
        printf '%s\n' "   Сначала запустите ./install.sh, затем повторите ./run_gui.sh --check."
        exit 1
    fi
    ./install.sh --no-system-check
fi

if ! .venv/bin/python -c "import PyQt6, book_normalizer, huggingface_hub" >/dev/null 2>&1; then
    if [ "$CHECK_ONLY" = "1" ]; then
        printf '%s\n' "Native POSIX GUI environment is not ready."
        printf '%s\n' "   Нативная POSIX-среда GUI не готова."
        printf '%s\n' "Run ./install.sh first, then try ./run_gui.sh --check again."
        printf '%s\n' "   Сначала запустите ./install.sh, затем повторите ./run_gui.sh --check."
        exit 1
    fi
    ./install.sh --no-system-check
fi

if [ "$CHECK_ONLY" = "1" ]; then
    printf '%s\n' "Native POSIX GUI environment OK."
    printf '%s\n' "   Нативная POSIX-среда GUI готова."
    exit 0
fi

exec .venv/bin/python -m book_normalizer.gui.app "$@"
