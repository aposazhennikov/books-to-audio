"""Real packaging checks.

These tests intentionally invoke the same PEP 517 build command a user runs
locally, so a broken Windows/Linux build cannot hide behind mocked imports.
"""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path


def test_wheel_builds_and_contains_gui_assets(tmp_path: Path) -> None:
    out_dir = tmp_path / "dist"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--outdir",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    wheel = next(out_dir.glob("book_normalizer-*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())

    assert "book_normalizer/gui/assets/icon.svg" in names
    assert "book_normalizer/gui/assets/check.svg" in names
    assert "book_normalizer/gui/app.py" in names
