from __future__ import annotations

import json
import wave
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_readiness_module():
    script = Path("scripts/final_readiness_check.py").resolve()
    spec = spec_from_file_location("test_final_readiness_check_script", script)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_smoke_dir(path: Path) -> None:
    path.mkdir(parents=True)
    (path / "live_tts_smoke_report.json").write_text(
        json.dumps({
            "status": "ok",
            "synthesis": {"synthesized": 2},
            "audio_qa": {"ok": True},
        }),
        encoding="utf-8",
    )
    (path / "chunks_manifest_v2.json").write_text(
        json.dumps({
            "chapters": [{
                "chunks": [
                    {"text": "Глава первая. Иван вошёл."},
                    {"text": "Мария ответила спокойно."},
                ],
            }],
        }),
        encoding="utf-8",
    )
    with wave.open(str(path / "chapter_001.wav"), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        payload = bytearray()
        for index in range(24000 * 11):
            sample = 1000 if index % 2 else -1000
            payload.extend(sample.to_bytes(2, "little", signed=True))
        wav.writeframes(bytes(payload))


def _write_quality_doc(path: Path, *, include_all: bool = True) -> None:
    markers = [
        "885 passed, 9 skipped",
        "Live real-book TTS smoke passed",
        "Qwen3-8B-GGUF:Q4_K_M",
        "Qwen3-4B-GGUF:Q4_K_M",
        "ComfyUI was stopped",
        "`ollama ps` was empty",
    ]
    if not include_all:
        markers.pop()
    path.write_text("\n".join(markers), encoding="utf-8")


def test_final_readiness_reports_automated_gates_ok(tmp_path: Path) -> None:
    module = _load_readiness_module()
    smoke_dir = tmp_path / "smoke"
    quality_doc = tmp_path / "quality.md"
    _write_smoke_dir(smoke_dir)
    _write_quality_doc(quality_doc)

    report = module.build_readiness_report(smoke_dir, quality_doc)

    assert report["automated_gates_ok"] is True
    assert report["complete_without_human_review"] is False
    assert report["manual_remaining"]


def test_final_readiness_reports_missing_quality_markers(tmp_path: Path) -> None:
    module = _load_readiness_module()
    smoke_dir = tmp_path / "smoke"
    quality_doc = tmp_path / "quality.md"
    _write_smoke_dir(smoke_dir)
    _write_quality_doc(quality_doc, include_all=False)

    report = module.build_readiness_report(smoke_dir, quality_doc)

    assert report["automated_gates_ok"] is False
    assert report["missing_quality_markers"] == ["`ollama ps` was empty"]
