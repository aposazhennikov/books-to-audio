from __future__ import annotations

import json

from click.testing import CliRunner

import book_normalizer.cli as cli
from book_normalizer.production.quality import (
    annotate_manifest_with_production_qa,
    run_production_qa,
)


def _good_chunk() -> dict:
    return {
        "chapter_index": 0,
        "chunk_index": 0,
        "voice_label": "women",
        "speaker": "Alice",
        "canonical_speaker": "Alice",
        "cast_voice_id": "female_warm",
        "voice_strategy": "builtin",
        "emotion": "calm",
        "text": "Everything is ready.",
        "synthesized": True,
        "audio_file": "chunk.wav",
        "pause_after_ms": 650,
        "director": {
            "scene": "ch001_scene01",
            "pace": "natural conversational tempo",
            "pause": "clear speaker handoff beat",
            "volume": "normal",
            "tension": "low",
            "delivery": "grounded and natural",
        },
        "artifact_qa": {"status": "passed", "issues": [], "scores": {}},
        "asr_qa": {"status": "passed", "issues": []},
    }


def _manifest(chunk: dict) -> dict:
    return {
        "version": 2,
        "language": "en",
        "chapters": [
            {
                "chapter_index": 0,
                "chunks": [chunk],
            }
        ],
    }


def test_production_qa_passes_fully_checked_chunk() -> None:
    report = run_production_qa(_manifest(_good_chunk()))

    assert report["status"] == "passed"
    assert report["chunks"][0]["score"] == 100
    assert report["chunks"][0]["issues"] == []


def test_production_qa_marks_artifact_risk_for_resynthesis() -> None:
    chunk = _good_chunk()
    chunk["artifact_qa"] = {
        "status": "failed",
        "issues": ["repeated_audio"],
        "scores": {"repeat_similarity": 0.95},
    }
    manifest = _manifest(chunk)

    report = run_production_qa(manifest)
    annotate_manifest_with_production_qa(
        manifest,
        report,
        reset_bad_chunks=True,
        max_resynthesis_attempts=2,
    )

    result_chunk = manifest["chapters"][0]["chunks"][0]
    assert report["status"] == "resynthesize"
    assert report["chunks"][0]["status"] == "resynthesize"
    assert result_chunk["qa_status"] == "resynthesize"
    assert result_chunk["perceptual_qa"]["issues"] == [
        "artifact_qa_failed",
        "perceptual_artifact_risk",
    ]
    assert result_chunk["failed"] is True
    assert result_chunk["synthesized"] is False
    assert result_chunk["audio_file"] is None
    assert result_chunk["resynthesis_attempt"] == 1


def test_production_qa_reviews_missing_director_and_casting() -> None:
    chunk = _good_chunk()
    chunk.pop("director")
    chunk.pop("cast_voice_id")

    report = run_production_qa(_manifest(chunk))
    issues = {issue["kind"] for issue in report["chunks"][0]["issues"]}

    assert report["status"] == "review"
    assert {"director_missing", "cast_voice_missing"} <= issues


def test_production_qa_cli_writes_report_and_manifest(tmp_path) -> None:  # noqa: ANN001
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest_path.write_text(json.dumps(_manifest(_good_chunk())), encoding="utf-8")

    result = CliRunner().invoke(
        cli.main,
        ["production-qa", str(manifest_path), "--write-manifest"],
    )

    assert result.exit_code == 0, result.output
    report = json.loads((tmp_path / "production_qa_report.json").read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    chunk = manifest["chapters"][0]["chunks"][0]
    assert report["status"] == "passed"
    assert chunk["qa_status"] == "passed"
    assert chunk["perceptual_qa"]["score"] == 100
