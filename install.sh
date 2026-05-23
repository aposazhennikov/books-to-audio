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

set +e

if [ -n "$USE_EXISTING_VENV" ] && [ -x ".venv/bin/python" ]; then
    .venv/bin/python install.py "$@"
    EXIT_CODE=$?
    goto_done=1
else
    goto_done=
fi

if [ -z "$goto_done" ]; then
    if command -v python3 >/dev/null 2>&1; then
        python3 install.py "$@"
        EXIT_CODE=$?
        goto_done=1
    fi
fi

if [ -z "$goto_done" ]; then
    if command -v python >/dev/null 2>&1; then
        python install.py "$@"
        EXIT_CODE=$?
        goto_done=1
    fi
fi

if [ -z "$goto_done" ]; then
    printf '%s\n' "Python 3.10 or newer was not found. Install python3 and try again." >&2
    EXIT_CODE=1
fi

if [ -t 0 ] && [ -z "${BOOKS_TO_AUDIO_FROM_RUN_GUI:-}" ]; then
    printf '\n%s\n%s\n' \
        "Press any key to exit terminal..." \
        "Нажмите любую кнопку для выхода из терминала..."
    # shellcheck disable=SC2034
    read -r _
fi

exit "$EXIT_CODE"
