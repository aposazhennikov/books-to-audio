#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"
export PYTHONUTF8=1

pause_for_key() {
    if [ ! -t 0 ] || [ -n "${BOOKS_TO_AUDIO_FROM_RUN_GUI:-}" ]; then
        return
    fi

    printf '\n%s\n%s\n' \
        "Press any key to exit terminal..." \
        "Нажмите любую кнопку для выхода из терминала..."

    old_stty=$(stty -g 2>/dev/null || true)
    if [ -n "$old_stty" ]; then
        stty raw -echo 2>/dev/null || true
        dd bs=1 count=1 of=/dev/null 2>/dev/null || true
        stty "$old_stty" 2>/dev/null || true
        printf '\n'
        return
    fi

    # Fallback for unusual terminals that do not expose stty state.
    # shellcheck disable=SC2034
    read -r _
}

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
        python3 -c "import sys, venv; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >/dev/null 2>&1
        if [ "$?" -eq 0 ]; then
            python3 install.py "$@"
            EXIT_CODE=$?
            goto_done=1
        fi
    fi
fi

if [ -z "$goto_done" ]; then
    if command -v python >/dev/null 2>&1; then
        python -c "import sys, venv; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >/dev/null 2>&1
        if [ "$?" -eq 0 ]; then
            python install.py "$@"
            EXIT_CODE=$?
            goto_done=1
        fi
    fi
fi

if [ -z "$goto_done" ]; then
    printf '%s\n%s\n' \
        "Python 3.10 or newer with venv was not found. Install python3 and try again." \
        "Python 3.10+ с модулем venv не найден. Установите python3 и повторите запуск." >&2
    EXIT_CODE=1
fi

pause_for_key

exit "$EXIT_CODE"
