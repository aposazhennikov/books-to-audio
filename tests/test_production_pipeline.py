from __future__ import annotations

import json
import wave
from pathlib import Path

from click.testing import CliRunner

import book_normalizer.cli as cli
from book_normalizer.production.pipeline import run_production_preflight


def _write_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(b"\x00\x00" * 800)


def _manifest() -> dict:
    return {
        "version": 2,
        "book_title": "Production Test",
        "language": "en",
        "chapters": [
            {
                "chapter_index": 0,
                "chapter_title": "One",
                "chunks": [
                    {
                        "chapter_index": 0,
                        "chunk_index": 0,
                        "voice_label": "narrator",
                        "voice_tone": "neutral",
                        "text": "The night was calm.",
                        "synthesized": True,
                        "audio_file": "unused.wav",
                        "artifact_qa": {"status": "passed", "issues": [], "scores": {}},
                        "asr_qa": {"status": "passed", "issues": []},
                    }
                ],
            }
        ],
    }


def test_production_preflight_writes_all_artifacts_and_updates_manifest(tmp_path: Path) -> None:
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")

    result = run_production_preflight(manifest_path, output_dir=tmp_path / "production")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    chunk = manifest["chapters"][0]["chunks"][0]
    assert result.character_bible_path.exists()
    assert result.casting_plan_path.exists()
    assert result.voice_overrides_path.exists()
    assert result.director_score_path.exists()
    assert result.production_qa_report_path.exists()
    assert result.run_report_path.exists()
    assert chunk["canonical_speaker"] == "Narrator"
    assert chunk["cast_voice_id"] == "narrator_calm"
    assert chunk["director"]["scene"] == "ch001_scene01"
    assert chunk["qa_status"] == "passed"


def test_production_preflight_cli_can_prepare_package_dry_run(tmp_path: Path) -> None:
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")
    chapter_dir = tmp_path / "chapters"
    _write_wav(chapter_dir / "chapter_001.wav")

    result = CliRunner().invoke(
        cli.main,
        [
            "production-preflight",
            str(manifest_path),
            "--out-dir",
            str(tmp_path / "production"),
            "--package",
            "--chapter-audio-dir",
            str(chapter_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    run_report = json.loads((tmp_path / "production" / "production_run_report.json").read_text(encoding="utf-8"))
    package_report = tmp_path / "production" / "audiobook_package" / "audiobook_package_report.json"
    assert package_report.exists()
    assert run_report["production_qa"]["passed"] == 1
    assert run_report["package"]["dry_run"] is True
