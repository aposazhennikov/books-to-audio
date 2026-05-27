"""Helpers for starting the local Ollama server from native launchers."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from book_normalizer.runtime_paths import (
    configured_ollama_bin,
    configured_ollama_endpoint,
    configured_ollama_models_dir,
)


def ensure_ollama_server(timeout: float = 20.0) -> None:
    """Start Ollama when the configured local endpoint is not responding."""

    endpoint = configured_ollama_endpoint().rstrip("/")
    if _endpoint_ready(endpoint):
        print(f"Ollama server is already running at {endpoint}.")
        return

    ollama_bin = configured_ollama_bin()
    env = os.environ.copy()
    models_dir = configured_ollama_models_dir()
    if models_dir is not None:
        env["OLLAMA_MODELS"] = str(models_dir)
        env["BOOKS_TO_AUDIO_OLLAMA_MODELS_DIR"] = str(models_dir)

    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    subprocess.Popen(
        [ollama_bin, "serve"],
        env=env,
        cwd=str(Path.cwd()),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
    )

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _endpoint_ready(endpoint):
            print(f"Ollama server started at {endpoint}.")
            return
        time.sleep(0.5)

    raise SystemExit(
        f"Ollama did not become ready at {endpoint}. "
        f"Check that '{ollama_bin} serve' can start on this machine."
    )


def _endpoint_ready(endpoint: str) -> bool:
    try:
        with urllib.request.urlopen(f"{endpoint}/api/tags", timeout=2.0) as response:
            if response.status != 200:
                return False
            json.loads(response.read().decode("utf-8"))
            return True
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return False


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    timeout = float(args[0]) if args else 20.0
    ensure_ollama_server(timeout=timeout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
