#!/usr/bin/env python3
"""Start a local ComfyUI portable server and wait for the API.

The script is intentionally tiny and conservative: it only starts the server,
does not queue any workflow, and writes ComfyUI stdout/stderr into
``output/runtime_logs`` so Qwen-TTS custom nodes keep a valid stdout handle.
"""

from __future__ import annotations

import argparse
import base64
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


DEFAULT_PORTABLE_ROOTS = (
    Path("/mnt/d/ComfyUI"),
    Path("D:/ComfyUI"),
    Path("C:/ComfyUI"),
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start portable ComfyUI for live TTS smoke checks.")
    parser.add_argument("--root", default="", help="ComfyUI portable root, e.g. D:/ComfyUI or /mnt/d/ComfyUI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8188)
    parser.add_argument("--wait-seconds", type=float, default=240.0)
    parser.add_argument("--log-dir", default="output/runtime_logs")
    parser.add_argument("--no-start", action="store_true", help="Only probe the API; do not start a process.")
    args = parser.parse_args(argv)

    root = resolve_comfyui_root(args.root)
    api_url = f"http://{args.host}:{args.port}/system_stats"
    if probe_url(api_url):
        print(f"ComfyUI already reachable: {api_url}")
        return 0

    if args.no_start:
        print(f"ComfyUI is not reachable: {api_url}", file=sys.stderr)
        return 2

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    start_comfyui(
        root=root,
        host=args.host,
        port=args.port,
        stdout_log=log_dir / "comfyui_stdout.log",
        stderr_log=log_dir / "comfyui_stderr.log",
    )
    print(f"Starting ComfyUI from {root}...")
    if wait_for_api(api_url, timeout=args.wait_seconds):
        print(f"ComfyUI reachable: {api_url}")
        return 0

    print(f"ComfyUI did not become reachable within {args.wait_seconds:.0f}s.", file=sys.stderr)
    print(f"Check logs under {log_dir}.", file=sys.stderr)
    return 1


def resolve_comfyui_root(value: str = "") -> Path:
    """Return an existing ComfyUI portable root."""
    candidates = [Path(value).expanduser()] if value else []
    candidates.extend(DEFAULT_PORTABLE_ROOTS)
    for root in candidates:
        if _looks_like_portable_comfyui(root):
            return root
    joined = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"Could not find portable ComfyUI root. Checked: {joined}")


def start_comfyui(
    *,
    root: Path,
    host: str,
    port: int,
    stdout_log: Path,
    stderr_log: Path,
) -> None:
    """Start ComfyUI detached through Windows cmd when available."""
    python_exe = root / "python_embeded" / "python.exe"
    main_py = root / "ComfyUI" / "main.py"
    if _running_on_linux_windows_host() and _cmd_exe_available():
        command = _powershell_start_process_command(
            python_exe=_windows_path(python_exe),
            main_py=_windows_path(main_py),
            root=_windows_path(root),
            host=host,
            port=port,
            stdout_log=_windows_path(stdout_log),
            stderr_log=_windows_path(stderr_log),
        )
        encoded = base64.b64encode(command.encode("utf-16le")).decode("ascii")
        subprocess.Popen(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-EncodedCommand",
                encoded,
            ]
        )
        return

    with stdout_log.open("ab") as stdout, stderr_log.open("ab") as stderr:
        subprocess.Popen(
            [
                str(python_exe),
                "-s",
                str(main_py),
                "--windows-standalone-build",
                "--listen",
                host,
                "--port",
                str(port),
            ],
            cwd=str(root),
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
        )


def wait_for_api(url: str, *, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if probe_url(url):
            return True
        time.sleep(2.0)
    return False


def probe_url(url: str) -> bool:
    """Return True when the API is reachable from this OS or Windows host."""
    try:
        with urllib.request.urlopen(url, timeout=2.0) as response:
            return 200 <= response.status < 500
    except Exception:
        pass

    if _running_on_linux_windows_host() and _cmd_exe_available():
        try:
            result = subprocess.run(
                ["cmd.exe", "/c", "curl", "-sS", "-m", "2", url],
                capture_output=True,
                timeout=5.0,
                check=False,
            )
            return result.returncode == 0 and bool(result.stdout)
        except (OSError, subprocess.SubprocessError):
            return False
    return False


def _looks_like_portable_comfyui(root: Path) -> bool:
    return (root / "python_embeded" / "python.exe").exists() and (root / "ComfyUI" / "main.py").exists()


def _running_on_linux_windows_host() -> bool:
    try:
        return "microsoft" in Path("/proc/sys/kernel/osrelease").read_text(encoding="utf-8").lower()
    except OSError:
        return False


def _cmd_exe_available() -> bool:
    try:
        result = subprocess.run(["cmd.exe", "/c", "ver"], capture_output=True, timeout=5.0, check=False)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _windows_path(path: Path) -> str:
    text = str(path)
    if text.startswith("/mnt/") and len(text) >= 7:
        drive = text[5].upper()
        rest = text[7:].replace("/", "\\")
        return f"{drive}:\\" + rest
    return text.replace("/", "\\")


def _powershell_start_process_command(
    *,
    python_exe: str,
    main_py: str,
    root: str,
    host: str,
    port: int,
    stdout_log: str,
    stderr_log: str,
) -> str:
    arguments = [
        "-s",
        main_py,
        "--windows-standalone-build",
        "--listen",
        host,
        "--port",
        str(port),
    ]
    ps_args = ", ".join(_quote_ps_string(arg) for arg in arguments)
    return (
        f"$argsList = @({ps_args}); "
        f"Start-Process -FilePath {_quote_ps_string(python_exe)} "
        "-ArgumentList $argsList "
        f"-WorkingDirectory {_quote_ps_string(root)} "
        "-WindowStyle Hidden "
        f"-RedirectStandardOutput {_quote_ps_string(stdout_log)} "
        f"-RedirectStandardError {_quote_ps_string(stderr_log)}"
    )


def _quote_ps_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


if __name__ == "__main__":
    raise SystemExit(main())
