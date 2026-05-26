from __future__ import annotations

import json
import wave
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_audit_module():
    script = Path("scripts/audit_tts_smoke.py").resolve()
    spec = spec_from_file_location("test_audit_tts_smoke_script", script)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_smoke_dir(
    path: Path,
    *,
    text: str = "Глава первая. Иван вошёл.",
    silent_tail_seconds: float = 0.0,
    clipped: bool = False,
) -> None:
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
                    {"text": text},
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
        voiced_frames = 24000
        silent_frames = int(24000 * silent_tail_seconds)
        for index in range(voiced_frames + silent_frames):
            if index >= voiced_frames:
                sample = 0
            elif clipped:
                sample = 32767 if index % 2 else -32768
            else:
                sample = 1000 if index % 2 else -1000
            payload.extend(sample.to_bytes(2, "little", signed=True))
        wav.writeframes(bytes(payload))


def test_audit_tts_smoke_accepts_clean_output(tmp_path: Path) -> None:
    module = _load_audit_module()
    smoke_dir = tmp_path / "smoke"
    _write_smoke_dir(smoke_dir)

    report = module.audit_tts_smoke(smoke_dir, min_duration=0.5)

    assert report["ok"] is True
    assert report["failures"] == []
    assert report["wav"]["sample_rate"] == 24000
    assert report["wav"]["clipping_ratio"] == 0
    assert report["wav"]["longest_silence_seconds"] == 0


def test_audit_tts_smoke_flags_front_matter(tmp_path: Path) -> None:
    module = _load_audit_module()
    smoke_dir = tmp_path / "smoke"
    _write_smoke_dir(smoke_dir, text="Royallib.ru: http://royallib.ru")

    report = module.audit_tts_smoke(smoke_dir, min_duration=0.5)

    assert report["ok"] is False
    assert "royallib" in report["bad_front_matter_terms"]


def test_audit_tts_smoke_flags_long_silence(tmp_path: Path) -> None:
    module = _load_audit_module()
    smoke_dir = tmp_path / "smoke"
    _write_smoke_dir(smoke_dir, silent_tail_seconds=3.0)

    report = module.audit_tts_smoke(
        smoke_dir,
        min_duration=0.5,
        max_silence_seconds=2.0,
    )

    assert report["ok"] is False
    assert any(item.startswith("longest_silence_seconds=") for item in report["failures"])


def test_audit_tts_smoke_flags_clipping(tmp_path: Path) -> None:
    module = _load_audit_module()
    smoke_dir = tmp_path / "smoke"
    _write_smoke_dir(smoke_dir, clipped=True)

    report = module.audit_tts_smoke(
        smoke_dir,
        min_duration=0.5,
        max_clipping_ratio=0.01,
    )

    assert report["ok"] is False
    assert any(item.startswith("clipping_ratio=") for item in report["failures"])
