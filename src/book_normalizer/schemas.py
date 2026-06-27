"""Central schema versions and lightweight migrations for local JSON artifacts."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

CURRENT_SCHEMA_VERSIONS: dict[str, int] = {
    "runtime_paths": 1,
    "manifest_v2": 2,
    "qa_report": 1,
    "voice_config": 1,
    "run_contract": 1,
    "stage_report": 1,
}


def schema_version_for(artifact: str) -> int:
    """Return the current schema version for a known artifact type."""
    try:
        return CURRENT_SCHEMA_VERSIONS[artifact]
    except KeyError as exc:
        raise KeyError(f"Unknown schema artifact: {artifact}") from exc


def migrate_json_record(
    record: dict[str, Any],
    artifact: str,
) -> dict[str, Any]:
    """Return a migrated copy of a local JSON artifact.

    Migrations are intentionally conservative: legacy files without a
    ``schema_version`` are accepted and tagged, while existing user payload is
    preserved. The manifest still keeps its domain ``version`` field.
    """
    migrated = deepcopy(record)
    target_version = schema_version_for(artifact)
    current = int(migrated.get("schema_version") or _legacy_version(migrated, artifact))
    if current > target_version:
        raise ValueError(
            f"{artifact} schema_version={current} is newer than supported {target_version}."
        )

    if artifact == "runtime_paths":
        migrated = _migrate_runtime_paths(migrated)
    elif artifact == "manifest_v2":
        migrated = _migrate_manifest_v2(migrated)
    elif artifact == "voice_config":
        migrated = _migrate_voice_config(migrated)
    elif artifact == "qa_report":
        migrated = _migrate_report(migrated)

    migrated["schema_version"] = target_version
    return migrated


def _legacy_version(record: dict[str, Any], artifact: str) -> int:
    if artifact == "manifest_v2":
        return int(record.get("version") or 1)
    return 0


def _migrate_runtime_paths(record: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "comfyui_models_dir": "models_dir",
        "hf_home": "hf_cache_dir",
        "tesseract": "tesseract_cmd",
        "ffmpeg": "ffmpeg_bin",
    }
    for old_key, new_key in aliases.items():
        if old_key in record and new_key not in record:
            record[new_key] = record[old_key]
    return record


def _migrate_manifest_v2(record: dict[str, Any]) -> dict[str, Any]:
    record.setdefault("version", 2)
    record.setdefault("chapters", [])
    for chapter in record.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter.setdefault("chunks", [])
        for chunk in chapter.get("chunks", []):
            if not isinstance(chunk, dict):
                continue
            if "qa" in chunk and isinstance(chunk["qa"], dict):
                chunk.setdefault("artifact_qa", chunk["qa"].get("artifact"))
                chunk.setdefault("asr_qa", chunk["qa"].get("asr"))
            chunk.setdefault("resynthesis_attempt", 0)
            chunk.setdefault("rejected_audio_files", [])
    return record


def _migrate_voice_config(record: dict[str, Any]) -> dict[str, Any]:
    for role in ("narrator", "male", "female"):
        profile = record.get(role)
        if isinstance(profile, dict):
            profile.setdefault("name", role)
            profile.setdefault("method", "clone")
    return record


def _migrate_report(record: dict[str, Any]) -> dict[str, Any]:
    record.setdefault("summary", {})
    return record
