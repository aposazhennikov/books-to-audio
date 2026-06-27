from __future__ import annotations

import json
from pathlib import Path

from book_normalizer.diagnostics.error_guidance import error_action
from book_normalizer.observability import StageObserver
from book_normalizer.production.run_contract import build_run_contract, write_run_contract
from book_normalizer.schemas import migrate_json_record


def test_runtime_paths_migration_accepts_legacy_aliases() -> None:
    migrated = migrate_json_record(
        {
            "comfyui_models_dir": "D:/models",
            "hf_home": "D:/hf",
            "tesseract": "D:/tools/tesseract.exe",
            "ffmpeg": "D:/tools/ffmpeg.exe",
        },
        "runtime_paths",
    )

    assert migrated["schema_version"] == 1
    assert migrated["models_dir"] == "D:/models"
    assert migrated["hf_cache_dir"] == "D:/hf"
    assert migrated["tesseract_cmd"].endswith("tesseract.exe")
    assert migrated["ffmpeg_bin"].endswith("ffmpeg.exe")


def test_run_contract_records_hashes_and_stable_id(tmp_path: Path) -> None:
    manifest = tmp_path / "chunks_manifest_v2.json"
    workflow = tmp_path / "workflow.json"
    voice = tmp_path / "voice.json"
    manifest.write_text('{"version": 2, "chapters": []}', encoding="utf-8")
    workflow.write_text('{"workflow": true}', encoding="utf-8")
    voice.write_text('{"speaker": "Aiden"}', encoding="utf-8")

    contract = build_run_contract(
        output_dir=tmp_path,
        stage="tts_synthesis",
        manifest_path=manifest,
        workflow_path=workflow,
        voice_preset_paths=[voice],
        model_versions={"tts_engine": "qwen"},
        parameters={"failed_only": True},
        resume_from="failed_only",
    )
    second = build_run_contract(
        output_dir=tmp_path,
        stage="tts_synthesis",
        manifest_path=manifest,
        workflow_path=workflow,
        voice_preset_paths=[voice],
        model_versions={"tts_engine": "qwen"},
        parameters={"failed_only": True},
        resume_from="failed_only",
    )
    path = write_run_contract(tmp_path, contract)

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["schema_version"] == 1
    assert saved["run_id"] == second["run_id"]
    assert saved["provenance"]["manifest_hash"]
    assert saved["provenance"]["workflow_hash"]
    assert saved["provenance"]["voice_preset_hashes"][str(voice)]


def test_stage_observer_writes_jsonl_and_report(tmp_path: Path) -> None:
    observer = StageObserver(tmp_path, "run-1", "chunking")
    observer.log("started", chapter=1)
    observer.increment("chunks", 3)
    report_path = observer.finish("completed", throughput_chunks_per_hour=360.0)

    log_lines = (tmp_path / "logs" / "chunking.jsonl").read_text(encoding="utf-8").splitlines()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert json.loads(log_lines[0])["event"] == "started"
    assert report["counters"]["chunks"] == 3
    assert report["summary"]["throughput_chunks_per_hour"] == 360.0


def test_error_guidance_returns_actionable_gui_hint() -> None:
    assert "doctor" in error_action("ComfyUI server not reachable at http://localhost:8188")
    assert "install-tts-models" in error_action("model missing from models dir")
