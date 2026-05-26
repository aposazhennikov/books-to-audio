#!/usr/bin/env python3
"""Stop a ComfyUI process previously launched by scripts/start_comfyui.py."""

from __future__ import annotations

import argparse
import base64
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stop portable ComfyUI started by start_comfyui.py.")
    parser.add_argument("--pid-file", default="output/runtime_logs/comfyui.pid")
    parser.add_argument("--wait-seconds", type=float, default=30.0)
    args = parser.parse_args(argv)

    pid_file = Path(args.pid_file)
    if not pid_file.exists():
        print(f"ComfyUI pid file does not exist: {pid_file}")
        return 0
    try:
        pid = int(pid_file.read_text(encoding="ascii").strip())
    except ValueError:
        print(f"Invalid ComfyUI pid file: {pid_file}", file=sys.stderr)
        return 2

    if not stop_comfyui_process(pid, timeout=args.wait_seconds):
        return 3
    pid_file.unlink(missing_ok=True)
    print(f"Stopped ComfyUI process {pid}.")
    return 0


def stop_comfyui_process(pid: int, *, timeout: float = 30.0) -> bool:
    """Stop a PID only when it still looks like a ComfyUI main.py process."""
    if _running_on_linux_windows_host() and _powershell_available():
        return _stop_windows_process(pid, timeout=timeout)
    return _stop_posix_process(pid, timeout=timeout)


def _stop_windows_process(pid: int, *, timeout: float) -> bool:
    command = (
        f"$pidValue = {pid}; "
        '$proc = Get-CimInstance Win32_Process -Filter "ProcessId = $pidValue"; '
        "if ($null -eq $proc) { exit 0 }; "
        "if ($proc.CommandLine -notmatch 'ComfyUI.*main\\.py') { "
        "Write-Error 'PID does not look like ComfyUI'; exit 3 }; "
        "Stop-Process -Id $pidValue -Force"
    )
    encoded = base64.b64encode(command.encode("utf-16le")).decode("ascii")
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-EncodedCommand",
            encoded,
        ],
        capture_output=True,
        timeout=max(timeout, 5.0),
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr.decode("utf-8", errors="replace"))
        return False
    return True


def _stop_posix_process(pid: int, *, timeout: float) -> bool:
    if not _posix_pid_looks_like_comfyui(pid):
        return not Path(f"/proc/{pid}").exists()
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return True

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not Path(f"/proc/{pid}").exists():
            return True
        time.sleep(0.5)
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return True
    return not Path(f"/proc/{pid}").exists()


def _posix_pid_looks_like_comfyui(pid: int) -> bool:
    try:
        cmdline = Path(f"/proc/{pid}/cmdline").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return "ComfyUI" in cmdline and "main.py" in cmdline


def _running_on_linux_windows_host() -> bool:
    try:
        return "microsoft" in Path("/proc/sys/kernel/osrelease").read_text(encoding="utf-8").lower()
    except OSError:
        return False


def _powershell_available() -> bool:
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", "$PSVersionTable.PSVersion"],
            capture_output=True,
            timeout=5.0,
            check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


if __name__ == "__main__":
    raise SystemExit(main())
