from __future__ import annotations

import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


def _load_review_module():
    script = Path("scripts/prepare_listening_review.py").resolve()
    spec = spec_from_file_location("test_prepare_listening_review_script", script)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_readiness(path: Path, audio_path: Path, *, gates_ok: bool = True) -> None:
    path.write_text(
        json.dumps({
            "automated_gates_ok": gates_ok,
            "manual_verdict_status": "missing",
            "estimated_completion_percent": 99.95,
            "remaining_percent": 0.05,
            "tts_smoke_audit": {
                "wav": {
                    "path": str(audio_path),
                    "duration_seconds": 45.48,
                },
            },
        }),
        encoding="utf-8",
    )


def test_build_review_payload_returns_exact_next_commands(tmp_path: Path) -> None:
    module = _load_review_module()
    audio = tmp_path / "chapter_001.wav"
    checklist = tmp_path / "checklist.md"
    readiness = tmp_path / "readiness.json"
    audio.write_bytes(b"RIFF")
    checklist.write_text("# Checklist", encoding="utf-8")
    _write_readiness(readiness, audio)

    payload = module.build_review_payload(readiness, checklist)

    assert payload["ready_for_human_listening"] is True
    assert payload["audio_path"] == str(audio)
    assert payload["checklist"] == str(checklist)
    assert payload["remaining_percent"] == 0.05
    assert "--verdict pass" in payload["record_pass_command"]
    assert "--refresh-readiness" in payload["record_pass_command"]
    assert "--verdict review" in payload["record_review_command"]
    assert "--verdict fail" in payload["record_fail_command"]


def test_build_review_payload_rejects_failed_automated_gates(tmp_path: Path) -> None:
    module = _load_review_module()
    audio = tmp_path / "chapter_001.wav"
    checklist = tmp_path / "checklist.md"
    readiness = tmp_path / "readiness.json"
    audio.write_bytes(b"RIFF")
    checklist.write_text("# Checklist", encoding="utf-8")
    _write_readiness(readiness, audio, gates_ok=False)

    with pytest.raises(ValueError, match="automated gates"):
        module.build_review_payload(readiness, checklist)


def test_open_for_review_uses_windows_fallback_on_wsl(tmp_path: Path, monkeypatch) -> None:
    module = _load_review_module()
    calls: list[list[str]] = []
    monkeypatch.setattr(module, "_running_on_linux_windows_host", lambda: True)
    monkeypatch.setattr(module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(module.subprocess, "Popen", lambda args: calls.append(args))

    module.open_for_review(tmp_path / "audio.wav", tmp_path / "checklist.md")

    assert len(calls) == 2
    assert calls[0][:4] == ["cmd.exe", "/c", "start", ""]
