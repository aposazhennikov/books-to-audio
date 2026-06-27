"""Production run identity, provenance, and resume contract helpers."""

from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from book_normalizer.schemas import schema_version_for

RUN_CONTRACT_NAME = "run_contract.json"


def build_run_contract(
    *,
    output_dir: Path,
    stage: str,
    parameters: dict[str, Any],
    manifest_path: Path | None = None,
    workflow_path: Path | None = None,
    voice_preset_paths: list[Path] | None = None,
    model_versions: dict[str, str] | None = None,
    resume_from: str | None = None,
) -> dict[str, Any]:
    """Build a serializable run contract for a production step."""
    run_id = _stable_run_id(output_dir, manifest_path, parameters)
    voice_hashes = {
        str(path): _file_sha256(path)
        for path in voice_preset_paths or []
        if path and path.exists()
    }
    return {
        "schema_version": schema_version_for("run_contract"),
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "stage": stage,
        "resume_from": resume_from or "",
        "parameters": parameters,
        "provenance": {
            "commit": _git_commit_hash(),
            "manifest_path": str(manifest_path or ""),
            "manifest_hash": _file_sha256(manifest_path) if manifest_path else "",
            "workflow_path": str(workflow_path or ""),
            "workflow_hash": _file_sha256(workflow_path) if workflow_path else "",
            "voice_preset_hashes": voice_hashes,
            "model_versions": model_versions or {},
        },
    }


def write_run_contract(output_dir: Path, contract: dict[str, Any]) -> Path:
    """Write the contract into the book output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / RUN_CONTRACT_NAME
    path.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _stable_run_id(output_dir: Path, manifest_path: Path | None, parameters: dict[str, Any]) -> str:
    payload = {
        "output_dir": str(output_dir.resolve()),
        "manifest": str(manifest_path.resolve()) if manifest_path else "",
        "parameters": parameters,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return str(uuid.UUID(digest[:32]))


def _file_sha256(path: Path | None) -> str:
    if path is None or not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_commit_hash() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
    except Exception:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""
