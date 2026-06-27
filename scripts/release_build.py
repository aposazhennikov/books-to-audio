#!/usr/bin/env python3
"""Build release artifacts only after the final acceptance gate passes."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import zipfile
from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple

import tomllib

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
PACKAGE_INIT = ROOT / "src" / "book_normalizer" / "__init__.py"
DEFAULT_DIST = ROOT / "dist" / "release"


class VersionCheck(NamedTuple):
    pyproject_version: str
    package_version: str
    tag_version: str

    @property
    def ok(self) -> bool:
        return self.pyproject_version == self.package_version == self.tag_version


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the final release gate and build source/wheel artifacts.")
    parser.add_argument(
        "--tag",
        help="Release tag to validate, e.g. v0.1.0. Defaults to the exact current git tag.",
    )
    parser.add_argument(
        "--dist-dir",
        type=Path,
        default=DEFAULT_DIST,
        help="Directory for release artifacts.",
    )
    parser.add_argument(
        "--readiness-report",
        type=Path,
        default=ROOT / "output" / "final_readiness_report.json",
        help="Where final_readiness_check writes its JSON report.",
    )
    parser.add_argument(
        "--verdict-report",
        type=Path,
        default=ROOT / "output" / "manual_listening_verdict.json",
        help="Human listen-through verdict consumed by final_readiness_check.",
    )
    parser.add_argument(
        "--no-build",
        action="store_true",
        help="Validate the release gate and versions without building artifacts.",
    )
    args = parser.parse_args(argv)

    try:
        tag = args.tag or current_exact_git_tag(ROOT)
        check = validate_versions(tag)
        if not check.ok:
            raise ReleaseError(
                "Version mismatch: "
                f"book_normalizer.__version__={check.package_version}, "
                f"pyproject.toml={check.pyproject_version}, tag={check.tag_version}"
            )
        report = run_final_readiness_gate(args.readiness_report, args.verdict_report)
        if not report.get("complete_with_human_review"):
            raise ReleaseError(
                "Final readiness gate is not accepted. "
                "Run the smoke, listen through the required audio sample, and record a pass verdict."
            )
        artifacts: list[Path] = []
        if not args.no_build:
            artifacts = build_python_artifacts(args.dist_dir)
            verify_python_artifacts(args.dist_dir, check.pyproject_version)
        print(
            json.dumps(
                {
                    "release_gate": "passed",
                    "version": check.pyproject_version,
                    "tag": tag,
                    "readiness_report": str(args.readiness_report),
                    "artifacts": [str(path) for path in artifacts],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    except ReleaseError as exc:
        print(f"release error: {exc}", file=sys.stderr)
        return 1
    return 0


class ReleaseError(RuntimeError):
    """Raised when the release gate cannot be satisfied."""


def current_exact_git_tag(cwd: Path) -> str:
    result = subprocess.run(
        ["git", "describe", "--tags", "--exact-match"],
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise ReleaseError("Current commit is not exactly on a release tag. Pass --tag to validate explicitly.")
    return result.stdout.strip()


def validate_versions(tag: str) -> VersionCheck:
    pyproject_version = read_pyproject_version(PYPROJECT)
    package_version = read_package_version(PACKAGE_INIT)
    tag_version = normalize_tag_version(tag)
    return VersionCheck(
        pyproject_version=pyproject_version,
        package_version=package_version,
        tag_version=tag_version,
    )


def read_pyproject_version(path: Path) -> str:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def read_package_version(path: Path) -> str:
    namespace: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("__version__"):
            exec(line, {}, namespace)  # noqa: S102 - trusted local package metadata.
            return namespace["__version__"]
    raise ReleaseError(f"Could not find __version__ in {path}")


def normalize_tag_version(tag: str) -> str:
    value = tag.strip()
    if value.startswith("refs/tags/"):
        value = value.removeprefix("refs/tags/")
    return value[1:] if value.startswith("v") else value


def run_final_readiness_gate(readiness_report: Path, verdict_report: Path) -> dict[str, object]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "final_readiness_check.py"),
        "--verdict-report",
        str(verdict_report),
        "--write-report",
        str(readiness_report),
    ]
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise ReleaseError(result.stdout.strip() or result.stderr.strip() or "final_readiness_check failed")
    try:
        return json.loads(readiness_report.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ReleaseError(f"Readiness report was not written: {readiness_report}") from exc
    except json.JSONDecodeError as exc:
        raise ReleaseError(f"Readiness report is not valid JSON: {readiness_report}") from exc


def build_python_artifacts(dist_dir: Path) -> list[Path]:
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [sys.executable, "-m", "build", "--sdist", "--wheel", "--outdir", str(dist_dir)],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise ReleaseError(result.stdout + result.stderr)
    return sorted(dist_dir.glob("*"))


def verify_python_artifacts(dist_dir: Path, version: str) -> None:
    wheel = dist_dir / f"book_normalizer-{version}-py3-none-any.whl"
    source = dist_dir / f"book_normalizer-{version}.tar.gz"
    missing = [path.name for path in (wheel, source) if not path.exists()]
    if missing:
        raise ReleaseError(f"Missing release artifact(s): {', '.join(missing)}")
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
    expected = {
        "book_normalizer/__init__.py",
        "book_normalizer/gui/app.py",
        "book_normalizer/gui/assets/icon.ico",
    }
    missing_from_wheel = sorted(expected - names)
    if missing_from_wheel:
        raise ReleaseError(f"Wheel is missing expected file(s): {', '.join(missing_from_wheel)}")


if __name__ == "__main__":
    raise SystemExit(main())
