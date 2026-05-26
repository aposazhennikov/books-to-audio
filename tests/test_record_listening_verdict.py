from __future__ import annotations

import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


def _load_verdict_module():
    script = Path("scripts/record_listening_verdict.py").resolve()
    spec = spec_from_file_location("test_record_listening_verdict_script", script)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_verdict_record_pass_links_readiness_audio(tmp_path: Path) -> None:
    module = _load_verdict_module()
    readiness = tmp_path / "readiness.json"
    readiness.write_text(
        json.dumps({
            "automated_gates_ok": True,
            "tts_smoke_audit": {
                "wav": {"path": "output/live_tts_real_book_smoke_after_filter/chapter_001.wav"},
            },
        }),
        encoding="utf-8",
    )

    record = module.build_verdict_record(
        verdict="pass",
        notes="Sounds acceptable.",
        checklist=tmp_path / "checklist.md",
        readiness_report=readiness,
    )

    assert record["passed"] is True
    assert record["requires_review"] is False
    assert record["failed"] is False
    assert record["automated_gates_ok"] is True
    assert record["audio_path"].endswith("chapter_001.wav")
    assert record["notes"] == "Sounds acceptable."


def test_build_verdict_record_rejects_unknown_verdict(tmp_path: Path) -> None:
    module = _load_verdict_module()

    with pytest.raises(ValueError, match="Unknown verdict"):
        module.build_verdict_record(
            verdict="maybe",
            notes="",
            checklist=tmp_path / "checklist.md",
            readiness_report=tmp_path / "readiness.json",
        )


def test_main_returns_nonzero_for_review(tmp_path: Path) -> None:
    module = _load_verdict_module()
    out = tmp_path / "verdict.json"

    result = module.main([
        "--verdict",
        "review",
        "--notes",
        "Voice needs adjustment.",
        "--out",
        str(out),
    ])

    assert result == 1
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["requires_review"] is True
