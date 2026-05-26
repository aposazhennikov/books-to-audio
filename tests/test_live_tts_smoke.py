from __future__ import annotations

import wave
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_live_tts_smoke_module():
    script = Path("scripts/live_tts_smoke.py").resolve()
    spec = spec_from_file_location("test_live_tts_smoke_script", script)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _UnavailableClient:
    def __init__(self, _url: str) -> None:
        pass

    def is_reachable(self) -> bool:
        return False


class _FakeClient:
    def __init__(self, _url: str) -> None:
        self.calls = 0

    def is_reachable(self) -> bool:
        return True

    def synthesize_chunk(self, _workflow: dict, output_path: Path, timeout: float) -> Path:
        assert timeout == 1.0
        self.calls += 1
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(24000)
            payload = bytearray()
            for index in range(24000):
                sample = 1000 if index == 0 else (500 if index % 2 else -500)
                payload.extend(sample.to_bytes(2, "little", signed=True))
            wav.writeframes(bytes(payload))
        return output_path


class _FakeBuilder:
    def __init__(self, _workflow_path: Path) -> None:
        pass

    def build(self, **kwargs):  # noqa: ANN001, ANN204
        return {"prompt": kwargs}


def test_live_tts_smoke_reports_unavailable_comfyui(monkeypatch, tmp_path: Path) -> None:
    module = _load_live_tts_smoke_module()
    monkeypatch.setattr(module, "ComfyUIClient", _UnavailableClient)

    report = module.run_live_tts_smoke(
        comfyui_url="http://127.0.0.1:8188",
        workflow_path=tmp_path / "workflow.json",
        out_dir=tmp_path / "smoke",
    )

    assert report["status"] == "unavailable"
    assert "not reachable" in report["message"]


def test_live_tts_smoke_runs_synthesis_qa_and_assembly(monkeypatch, tmp_path: Path) -> None:
    module = _load_live_tts_smoke_module()
    monkeypatch.setattr(module, "ComfyUIClient", _FakeClient)
    monkeypatch.setattr(module, "WorkflowBuilder", _FakeBuilder)

    report = module.run_live_tts_smoke(
        comfyui_url="http://127.0.0.1:8188",
        workflow_path=tmp_path / "workflow.json",
        out_dir=tmp_path / "smoke",
        chunk_timeout=1.0,
    )

    assert report["status"] == "ok"
    assert report["synthesis"]["synthesized"] == 2
    assert report["audio_qa"]["ok"] is True
    assert Path(report["manifest"]).exists()
    assert Path(report["assembled_chapter"]).exists()
