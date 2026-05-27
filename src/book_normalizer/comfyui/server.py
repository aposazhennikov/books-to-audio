"""Helpers for probing and starting a local portable ComfyUI server."""

from __future__ import annotations

import base64
import os
import subprocess
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


class ComfyUIStartError(RuntimeError):
    """Raised when the local ComfyUI server cannot be started."""


@dataclass(frozen=True)
class ComfyUIStartResult:
    """Result from an attempt to ensure ComfyUI is reachable."""

    api_url: str
    log_dir: Path
    root: Path | None
    started: bool
    message: str


def ensure_local_comfyui(
    base_url: str,
    *,
    wait_seconds: float = 240.0,
    log_dir: Path = Path("output/runtime_logs"),
    root: str = "",
) -> ComfyUIStartResult:
    """Start a local portable ComfyUI server when the API is not reachable."""
    api_url = system_stats_url(base_url)
    if probe_url(api_url):
        return ComfyUIStartResult(
            api_url=api_url,
            log_dir=log_dir,
            root=None,
            started=False,
            message=f"ComfyUI already reachable: {api_url}",
        )

    if not is_local_url(base_url):
        raise ComfyUIStartError(f"auto-start supports only localhost URLs, got {base_url}")

    portable_root = resolve_comfyui_root(root)
    port = _port_from_url(base_url)
    host = _listen_host_from_url(base_url)
    log_dir.mkdir(parents=True, exist_ok=True)
    pid_file = log_dir / "comfyui.pid"
    start_comfyui(
        root=portable_root,
        host=host,
        port=port,
        stdout_log=log_dir / "comfyui_stdout.log",
        stderr_log=log_dir / "comfyui_stderr.log",
        pid_file=pid_file,
    )
    if not wait_for_api(api_url, timeout=wait_seconds):
        raise ComfyUIStartError(
            f"started from {portable_root}, but {api_url} did not respond within {wait_seconds:.0f}s. "
            f"Check logs in {log_dir}."
        )
    return ComfyUIStartResult(
        api_url=api_url,
        log_dir=log_dir,
        root=portable_root,
        started=True,
        message=f"ComfyUI started from {portable_root}: {api_url}",
    )


def is_local_url(base_url: str) -> bool:
    """Return True when a ComfyUI base URL targets the local machine."""
    parsed = urllib.parse.urlparse(base_url)
    hostname = (parsed.hostname or "").lower()
    return parsed.scheme in {"http", "https"} and hostname in LOCAL_HOSTS


def system_stats_url(base_url: str) -> str:
    """Return the ComfyUI health-check URL for a base URL."""
    return base_url.rstrip("/") + "/system_stats"


def resolve_comfyui_root(value: str = "") -> Path:
    """Return an existing ComfyUI portable root."""
    candidates: list[Path] = []
    if value:
        candidates.append(Path(value).expanduser())
    for env_name in ("BOOKS_TO_AUDIO_COMFYUI_ROOT", "COMFYUI_ROOT"):
        env_value = os.environ.get(env_name, "").strip()
        if env_value:
            candidates.append(Path(env_value).expanduser())
    candidates.extend((Path("D:/ComfyUI"), Path("C:/ComfyUI"), Path("/mnt/d/ComfyUI")))
    for candidate in candidates:
        if _looks_like_portable_comfyui(candidate):
            return candidate
    checked = ", ".join(str(path) for path in candidates) or "<none>"
    raise ComfyUIStartError(f"could not find portable ComfyUI root. Checked: {checked}")


def start_comfyui(
    *,
    root: Path,
    host: str,
    port: int,
    stdout_log: Path,
    stderr_log: Path,
    pid_file: Path | None = None,
) -> None:
    """Start ComfyUI detached and redirect logs to files."""
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
            pid_file=_windows_path(pid_file) if pid_file else "",
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
            ],
        )
        return

    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    with stdout_log.open("ab") as stdout, stderr_log.open("ab") as stderr:
        process = subprocess.Popen(
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
            creationflags=creationflags,
        )
    if pid_file is not None:
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid_file.write_text(str(process.pid), encoding="ascii")


def wait_for_api(url: str, *, timeout: float) -> bool:
    """Wait until a URL responds."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if probe_url(url):
            return True
        time.sleep(2.0)
    return False


def probe_url(url: str) -> bool:
    """Return True when a URL responds from this OS or the Windows host."""
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


def _port_from_url(base_url: str) -> int:
    parsed = urllib.parse.urlparse(base_url)
    return parsed.port or 8188


def _listen_host_from_url(base_url: str) -> str:
    parsed = urllib.parse.urlparse(base_url)
    hostname = (parsed.hostname or "").lower()
    return "::1" if hostname == "::1" else "127.0.0.1"


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
    pid_file: str = "",
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
    command = (
        f"$argsList = @({ps_args}); "
        f"$p = Start-Process -FilePath {_quote_ps_string(python_exe)} "
        "-ArgumentList $argsList "
        f"-WorkingDirectory {_quote_ps_string(root)} "
        "-WindowStyle Hidden "
        f"-RedirectStandardOutput {_quote_ps_string(stdout_log)} "
        f"-RedirectStandardError {_quote_ps_string(stderr_log)} "
        "-PassThru"
    )
    if pid_file:
        command += f"; Set-Content -LiteralPath {_quote_ps_string(pid_file)} -Value $p.Id -Encoding ascii"
    return command


def _quote_ps_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"
