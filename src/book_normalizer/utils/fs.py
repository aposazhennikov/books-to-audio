"""File-system utility helpers."""

from __future__ import annotations

from pathlib import Path


def ensure_dir(path: Path) -> Path:
    """Create directory (and parents) if it doesn't exist; return the path."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_output_dir(base: Path, book_name: str) -> Path:
    """Build a deterministic output directory for a given book."""
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in book_name)
    return ensure_dir(base / safe_name)
