#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"
export PYTHONUTF8=1
export PYTHONPATH="$SCRIPT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

CHECK_ONLY=0
WEB_MODE=0
WEB_HOST="${BOOKS_TO_AUDIO_WEB_HOST:-127.0.0.1}"
WEB_PORT="${BOOKS_TO_AUDIO_WEB_PORT:-6080}"
VNC_PORT="${BOOKS_TO_AUDIO_VNC_PORT:-5901}"
WEB_DISPLAY="${BOOKS_TO_AUDIO_WEB_DISPLAY:-:99}"
WEB_GEOMETRY="${BOOKS_TO_AUDIO_WEB_GEOMETRY:-1440x900}"
UPLOAD_HOST="${BOOKS_TO_AUDIO_WEB_UPLOAD_HOST:-$WEB_HOST}"
UPLOAD_PORT="${BOOKS_TO_AUDIO_WEB_UPLOAD_PORT:-6090}"
UPLOAD_DIR="${BOOKS_TO_AUDIO_WEB_UPLOAD_DIR:-$SCRIPT_DIR/web_uploads}"
UPLOAD_MARKER="${BOOKS_TO_AUDIO_WEB_UPLOAD_MARKER:-$UPLOAD_DIR/.latest_book_upload.json}"

usage() {
    cat <<'EOF'
Usage:
  ./run_gui.sh [--check]
  ./run_gui.sh [GUI args...]
  ./run_gui.sh --web [--web-host HOST] [--web-port PORT] [--vnc-port PORT]
               [--upload-host HOST] [--upload-port PORT] [--upload-dir DIR]
               [--display :N] [--geometry WIDTHxHEIGHT] [GUI args...]

Remote Linux server example:
  ./run_gui.sh --web
  ssh -L 6080:127.0.0.1:6080 -L 6090:127.0.0.1:6090 user@server
  open http://127.0.0.1:6080/vnc.html?autoconnect=1&resize=scale
  open http://127.0.0.1:6090/upload to upload a local book

Use --web-host 0.0.0.0 only when the server firewall and provider networking
are configured safely. SSH tunneling with the default 127.0.0.1 is preferred.
EOF
}
if [ "${1:-}" = "--check" ]; then
    CHECK_ONLY=1
    shift
fi

while [ "$#" -gt 0 ]; do
    case "$1" in
        --web)
            WEB_MODE=1
            shift
            ;;
        --web-host)
            WEB_HOST="${2:?Missing value for --web-host}"
            shift 2
            ;;
        --web-port)
            WEB_PORT="${2:?Missing value for --web-port}"
            shift 2
            ;;
        --vnc-port)
            VNC_PORT="${2:?Missing value for --vnc-port}"
            shift 2
            ;;
        --upload-host)
            UPLOAD_HOST="${2:?Missing value for --upload-host}"
            shift 2
            ;;
        --upload-port)
            UPLOAD_PORT="${2:?Missing value for --upload-port}"
            shift 2
            ;;
        --upload-dir)
            UPLOAD_DIR="${2:?Missing value for --upload-dir}"
            UPLOAD_MARKER="${BOOKS_TO_AUDIO_WEB_UPLOAD_MARKER:-$UPLOAD_DIR/.latest_book_upload.json}"
            shift 2
            ;;
        --display)
            WEB_DISPLAY="${2:?Missing value for --display}"
            shift 2
            ;;
        --geometry)
            WEB_GEOMETRY="${2:?Missing value for --geometry}"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            break
            ;;
    esac
done

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

if [ "$WEB_MODE" = "1" ]; then
    for command in Xvfb x11vnc websockify; do
        if ! command -v "$command" >/dev/null 2>&1; then
            printf '%s\n' "Missing command: $command"
            printf '%s\n' "Install web GUI system tools, then retry:"
            printf '%s\n' "  sudo apt-get update && sudo apt-get install -y xvfb x11vnc novnc websockify"
            printf '%s\n' "or run:"
            printf '%s\n' "  python install.py --install-system-tools"
            exit 1
        fi
    done

    NOVNC_WEB="${NOVNC_WEB:-}"
    if [ -z "$NOVNC_WEB" ]; then
        if [ -d /usr/share/novnc ]; then
            NOVNC_WEB=/usr/share/novnc
        elif [ -d /usr/share/webapps/novnc ]; then
            NOVNC_WEB=/usr/share/webapps/novnc
        else
            printf '%s\n' "Could not find noVNC web files."
            printf '%s\n' "Set NOVNC_WEB=/path/to/novnc or install the novnc package."
            exit 1
        fi
    fi

    cleanup_web_gui() {
        if [ -n "${APP_PID:-}" ]; then kill "$APP_PID" >/dev/null 2>&1 || true; fi
        if [ -n "${UPLOAD_PID:-}" ]; then kill "$UPLOAD_PID" >/dev/null 2>&1 || true; fi
        if [ -n "${WEBSOCKIFY_PID:-}" ]; then kill "$WEBSOCKIFY_PID" >/dev/null 2>&1 || true; fi
        if [ -n "${X11VNC_PID:-}" ]; then kill "$X11VNC_PID" >/dev/null 2>&1 || true; fi
        if [ -n "${XVFB_PID:-}" ]; then kill "$XVFB_PID" >/dev/null 2>&1 || true; fi
    }
    require_running() {
        pid="$1"
        name="$2"
        if ! kill -0 "$pid" >/dev/null 2>&1; then
            printf '%s\n' "$name failed to start."
            exit 1
        fi
    }
    trap cleanup_web_gui EXIT INT TERM

    env -u WAYLAND_DISPLAY -u XDG_SESSION_TYPE \
        Xvfb "$WEB_DISPLAY" -screen 0 "${WEB_GEOMETRY}x24" -ac +extension GLX +render -noreset &
    XVFB_PID=$!
    sleep 1
    require_running "$XVFB_PID" "Xvfb"

    env -u WAYLAND_DISPLAY -u XDG_SESSION_TYPE \
        x11vnc -display "$WEB_DISPLAY" -localhost -forever -shared -nopw -quiet -rfbport "$VNC_PORT" &
    X11VNC_PID=$!
    sleep 1
    require_running "$X11VNC_PID" "x11vnc"

    websockify --web "$NOVNC_WEB" "$WEB_HOST:$WEB_PORT" "127.0.0.1:$VNC_PORT" &
    WEBSOCKIFY_PID=$!
    sleep 1
    require_running "$WEBSOCKIFY_PID" "websockify"

    BOOKS_TO_AUDIO_WEB_UPLOAD_DIR="$UPLOAD_DIR" \
    BOOKS_TO_AUDIO_WEB_UPLOAD_MARKER="$UPLOAD_MARKER" \
        .venv/bin/python -m book_normalizer.gui.web_upload_server \
            --host "$UPLOAD_HOST" \
            --port "$UPLOAD_PORT" \
            --upload-dir "$UPLOAD_DIR" \
            --marker "$UPLOAD_MARKER" &
    UPLOAD_PID=$!
    sleep 1
    require_running "$UPLOAD_PID" "upload server"

    printf '%s\n' "Books-to-Audio web GUI is starting."
    printf '%s\n' "Browser URL: http://127.0.0.1:$WEB_PORT/vnc.html?autoconnect=1&resize=scale"
    printf '%s\n' "Upload URL: http://127.0.0.1:$UPLOAD_PORT/upload"
    printf '%s\n' "Uploaded books are saved on the server in: $UPLOAD_DIR"
    printf '%s\n' "Remote server access:"
    printf '%s\n' "  ssh -L $WEB_PORT:127.0.0.1:$WEB_PORT -L $UPLOAD_PORT:127.0.0.1:$UPLOAD_PORT user@server"
    printf '%s\n' "  then open the Browser URL and Upload URL on your laptop."
    if [ "$WEB_HOST" != "127.0.0.1" ] && [ "$WEB_HOST" != "localhost" ]; then
        printf '%s\n' "Listening on $WEB_HOST:$WEB_PORT. Protect this port with firewall/provider rules."
    fi
    if [ "$UPLOAD_HOST" != "127.0.0.1" ] && [ "$UPLOAD_HOST" != "localhost" ]; then
        printf '%s\n' "Upload server listening on $UPLOAD_HOST:$UPLOAD_PORT. Protect this port with firewall/provider rules."
    fi

    env -u WAYLAND_DISPLAY -u XDG_SESSION_TYPE \
        DISPLAY="$WEB_DISPLAY" QT_QPA_PLATFORM=xcb \
        BOOKS_TO_AUDIO_WEB_UPLOAD_DIR="$UPLOAD_DIR" \
        BOOKS_TO_AUDIO_WEB_UPLOAD_MARKER="$UPLOAD_MARKER" \
        .venv/bin/python -m book_normalizer.gui.app "$@" &
    APP_PID=$!
    wait "$APP_PID"
    exit $?
fi

exec .venv/bin/python -m book_normalizer.gui.app "$@"
