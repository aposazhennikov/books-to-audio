from __future__ import annotations

import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_checklist_module():
    script = Path("scripts/create_listening_checklist.py").resolve()
    spec = spec_from_file_location("test_create_listening_checklist_script", script)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_listening_checklist_includes_audio_and_review_items(tmp_path: Path) -> None:
    module = _load_checklist_module()
    smoke_dir = tmp_path / "smoke"
    smoke_dir.mkdir()
    (smoke_dir / "audit_report.json").write_text(
        json.dumps({
            "wav": {"duration_seconds": 45.48},
            "bad_front_matter_terms": [],
        }),
        encoding="utf-8",
    )
    (smoke_dir / "chunks_manifest_v2.json").write_text(
        json.dumps({
            "chapters": [{
                "chunks": [
                    {"text": "Book title and narrator opening."},
                    {"text": "Second narrator smoke chunk."},
                ],
            }],
        }),
        encoding="utf-8",
    )

    checklist = module.build_listening_checklist(smoke_dir)

    assert "chapter_001.wav" in checklist
    assert "45.48" in checklist
    assert "Book title and narrator opening." in checklist
    assert "PASS: ready" in checklist
    assert "FAIL: fix synthesis" in checklist
