"""Lightweight repository secret scanner for pre-commit and CI use."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".venv-windows",
    ".venv-w" + "sl",
    "ComfyUI",
    "__pycache__",
    "books",
    "books-to-audio-models",
    "build",
    "data",
    "dist",
    "env",
    "hf-cache",
    "ollama-models",
    "output",
    "venv",
}
EXCLUDED_SUFFIXES = {
    ".ico",
    ".jpg",
    ".jpeg",
    ".mp3",
    ".m4b",
    ".ogg",
    ".png",
    ".pyc",
    ".wav",
    ".webp",
}
PATTERNS = {
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b"),
    "generic_secret_assignment": re.compile(
        r"(?i)\b(?:api[_-]?key|secret|password|access[_-]?token|auth[_-]?token)\b"
        r"\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{20,}"
    ),
    "private_key": re.compile(r"-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, default=[Path(".")])
    args = parser.parse_args(argv)
    findings = scan_paths(args.paths)
    for path, line_no, kind in findings:
        print(f"{path}:{line_no}: possible secret ({kind})")
    return 1 if findings else 0


def scan_paths(paths: list[Path]) -> list[tuple[Path, int, str]]:
    findings: list[tuple[Path, int, str]] = []
    for path in paths:
        if not path.exists():
            continue
        candidates = [path] if path.is_file() else _walk(path)
        for candidate in candidates:
            if _skip(candidate):
                continue
            findings.extend(_scan_file(candidate))
    return findings


def _walk(root: Path) -> list[Path]:
    files: list[Path] = []
    for current, dirs, names in os.walk(root, topdown=True):
        dirs[:] = [name for name in dirs if name not in EXCLUDED_DIRS]
        current_path = Path(current)
        for name in names:
            files.append(current_path / name)
    return files


def _skip(path: Path) -> bool:
    parts = set(path.parts)
    return bool(parts & EXCLUDED_DIRS) or path.suffix.lower() in EXCLUDED_SUFFIXES


def _scan_file(path: Path) -> list[tuple[Path, int, str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    findings: list[tuple[Path, int, str]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if "pragma: allowlist secret" in line:
            continue
        for kind, pattern in PATTERNS.items():
            if pattern.search(line):
                findings.append((path, line_no, kind))
    return findings


if __name__ == "__main__":
    raise SystemExit(main())
