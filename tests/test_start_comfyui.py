from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any


def _load_start_comfyui_module():
    script = Path("scripts/start_comfyui.py").resolve()
    spec = spec_from_file_location("test_start_comfyui_script", script)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resolve_comfyui_root_accepts_portable_layout(tmp_path: Path) -> None:
    module = _load_start_comfyui_module()
    root = tmp_path / "ComfyUI"
    (root / "python_embeded").mkdir(parents=True)
    (root / "ComfyUI").mkdir()
    (root / "python_embeded" / "python.exe").write_text("", encoding="utf-8")
    (root / "ComfyUI" / "main.py").write_text("", encoding="utf-8")

    assert module.resolve_comfyui_root(str(root)) == root


def test_start_comfyui_uses_detached_cmd_with_log_redirects(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_start_comfyui_module()
    root = tmp_path / "ComfyUI"
    (root / "python_embeded").mkdir(parents=True)
    (root / "ComfyUI").mkdir()
    (root / "python_embeded" / "python.exe").write_text("", encoding="utf-8")
    (root / "ComfyUI" / "main.py").write_text("", encoding="utf-8")
    calls: list[list[str]] = []

    class _FakePopen:
        def __init__(self, args: list[str], **_kwargs: Any) -> None:
            calls.append(args)

    monkeypatch.setattr(module, "_running_on_linux_windows_host", lambda: True)
    monkeypatch.setattr(module, "_cmd_exe_available", lambda: True)
    monkeypatch.setattr(module.subprocess, "Popen", _FakePopen)

    module.start_comfyui(
        root=root,
        host="127.0.0.1",
        port=8188,
        stdout_log=tmp_path / "stdout.log",
        stderr_log=tmp_path / "stderr.log",
    )

    assert calls
    assert calls[0][:4] == [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
    ]
    assert calls[0][4] == "-EncodedCommand"

    import base64

    command = base64.b64decode(calls[0][5]).decode("utf-16le")
    assert "Start-Process" in command
    assert "--windows-standalone-build" in command
    assert "'--listen', '127.0.0.1', '--port', '8188'" in command
    assert "stdout.log" in command
    assert "stderr.log" in command


def test_probe_url_can_fallback_to_windows_curl(monkeypatch) -> None:
    module = _load_start_comfyui_module()

    def fake_urlopen(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("WSL loopback unavailable")

    class _FakeRun:
        returncode = 0
        stdout = b"{\"system\": {}}"

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(module, "_running_on_linux_windows_host", lambda: True)
    monkeypatch.setattr(module, "_cmd_exe_available", lambda: True)
    monkeypatch.setattr(module.subprocess, "run", lambda *_args, **_kwargs: _FakeRun())

    assert module.probe_url("http://127.0.0.1:8188/system_stats") is True
