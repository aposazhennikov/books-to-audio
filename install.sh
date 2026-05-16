#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

USE_EXISTING_VENV=1
for arg in "$@"; do
    if [ "$arg" = "--recreate" ]; then
        USE_EXISTING_VENV=
    fi
done

if [ -n "$USE_EXISTING_VENV" ] && [ -x ".venv/bin/python" ]; then
    exec .venv/bin/python install.py "$@"
fi

if command -v python3 >/dev/null 2>&1; then
    exec python3 install.py "$@"
fi

if command -v python >/dev/null 2>&1; then
    exec python install.py "$@"
fi

printf '%s\n' "Python 3.10 or newer was not found. Install python3 and try again." >&2
exit 1
