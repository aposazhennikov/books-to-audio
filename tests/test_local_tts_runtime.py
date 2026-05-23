from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from book_normalizer.tts.local_runtime import (
    REQUIRED_TTS_MODULES,
    build_tts_preview_command,
    check_tts_python,
)


def test_build_tts_preview_command_uses_native_paths(tmp_path: Path) -> None:
    script = tmp_path / "generate_voice_previews.py"
    out_dir = tmp_path / "previews"
    models_dir = tmp_path / "models"

    cmd = build_tts_preview_command(
        script_path=script,
        out_dir=out_dir,
        text="Пример",
        voice_ids=["narrator_calm", "male_young"],
        model="Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        models_dir=models_dir,
        python_executable=sys.executable,
    )

    assert cmd[:3] == [sys.executable, "-u", str(script)]
    assert "wsl" not in [part.lower() for part in cmd]
    assert str(out_dir) in cmd
    assert str(models_dir) in cmd
    assert "narrator_calm,male_young" in cmd


def test_check_tts_python_reports_missing_packages(monkeypatch) -> None:
    def fake_run(*_args, **_kwargs):  # noqa: ANN001
        payload = {"executable": sys.executable, "missing": ["qwen_tts"]}
        return subprocess.CompletedProcess(["python"], 0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr("book_normalizer.tts.local_runtime.subprocess.run", fake_run)

    ok, detail = check_tts_python()

    assert ok is False
    assert "qwen_tts" in detail
    assert REQUIRED_TTS_MODULES[0] == "qwen_tts"


def test_check_tts_python_accepts_complete_runtime(monkeypatch) -> None:
    def fake_run(*_args, **_kwargs):  # noqa: ANN001
        payload = {"executable": sys.executable, "missing": []}
        return subprocess.CompletedProcess(["python"], 0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr("book_normalizer.tts.local_runtime.subprocess.run", fake_run)

    ok, detail = check_tts_python()

    assert ok is True
    assert detail == sys.executable
