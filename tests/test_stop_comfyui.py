from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any


def _load_stop_comfyui_module():
    script = Path("scripts/stop_comfyui.py").resolve()
    spec = spec_from_file_location("test_stop_comfyui_script", script)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_stop_comfyui_missing_pid_file_is_ok(tmp_path: Path) -> None:
    module = _load_stop_comfyui_module()

    assert module.main(["--pid-file", str(tmp_path / "missing.pid")]) == 0


def test_stop_comfyui_invalid_pid_file_is_error(tmp_path: Path) -> None:
    module = _load_stop_comfyui_module()
    pid_file = tmp_path / "comfyui.pid"
    pid_file.write_text("not-a-pid", encoding="ascii")

    assert module.main(["--pid-file", str(pid_file)]) == 2


def test_stop_comfyui_uses_windows_guarded_stop(monkeypatch) -> None:
    module = _load_stop_comfyui_module()
    calls: list[list[str]] = []

    class _FakeRun:
        returncode = 0
        stderr = b""

    def fake_run(args: list[str], **_kwargs: Any) -> _FakeRun:
        calls.append(args)
        return _FakeRun()

    monkeypatch.setattr(module, "_running_on_linux_windows_host", lambda: True)
    monkeypatch.setattr(module, "_powershell_available", lambda: True)
    monkeypatch.setattr(module.subprocess, "run", fake_run)

    assert module.stop_comfyui_process(1234) is True
    assert calls
    assert calls[0][:4] == [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
    ]
