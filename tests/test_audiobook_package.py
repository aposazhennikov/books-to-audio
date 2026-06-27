from __future__ import annotations

import json
import wave
from pathlib import Path

import pytest
from click.testing import CliRunner

import book_normalizer.cli as cli
from book_normalizer.production.audiobook_package import build_audiobook_package


def _write_wav(path: Path, frames: int = 800) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(b"\x00\x00" * frames)


def _manifest() -> dict:
    return {
        "version": 2,
        "book_title": "Package Test",
        "language": "en",
        "chapters": [
            {
                "chapter_index": 0,
                "chapter_title": "Arrival",
                "chunks": [
                    {
                        "chapter_index": 0,
                        "chunk_index": 0,
                        "voice_label": "narrator",
                        "text": "Chapter one.",
                        "synthesized": True,
                        "audio_file": "unused.wav",
                        "qa_status": "passed",
                        "perceptual_qa": {"status": "passed", "score": 100, "issues": []},
                    }
                ],
            },
            {
                "chapter_index": 1,
                "chapter_title": "Departure",
                "chunks": [
                    {
                        "chapter_index": 1,
                        "chunk_index": 0,
                        "voice_label": "narrator",
                        "text": "Chapter two.",
                        "synthesized": True,
                        "audio_file": "unused.wav",
                        "qa_status": "passed",
                        "perceptual_qa": {"status": "passed", "score": 100, "issues": []},
                    }
                ],
            },
        ],
    }


def test_audiobook_package_writes_metadata_concat_and_commands(tmp_path: Path) -> None:
    chapter_dir = tmp_path / "mastered"
    _write_wav(chapter_dir / "chapter_001_mastered.wav", frames=800)
    _write_wav(chapter_dir / "chapter_002_mastered.wav", frames=1600)
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")

    result = build_audiobook_package(
        manifest_path,
        chapter_audio_dir=chapter_dir,
        output_dir=tmp_path / "package",
        author="Ada Author",
        dry_run=True,
    )

    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    ffmetadata = result.ffmetadata_path.read_text(encoding="utf-8")  # type: ignore[union-attr]
    concat = result.concat_path.read_text(encoding="utf-8")  # type: ignore[union-attr]

    assert report["title"] == "Package Test"
    assert report["author"] == "Ada Author"
    assert len(report["chapters"]) == 2
    assert len(report["commands"]) == 3
    assert report["loudness_target"] == -18.0
    assert report["package_qa"]["status"] == "passed"
    assert (tmp_path / "package" / "package_qa_report.json").exists()
    checksums = (tmp_path / "package" / "checksums.sha256").read_text(encoding="utf-8")
    assert "audiobook_package_report.json" in checksums
    assert any("loudnorm=I=-18" in " ".join(command) for command in report["commands"])
    assert "[CHAPTER]" in ffmetadata
    assert "genre=Audiobook" in ffmetadata
    assert "title=Arrival" in ffmetadata
    assert "chapter_001_mastered.wav" in concat
    assert result.m4b_path.name == "Package Test.m4b"  # type: ignore[union-attr]


def test_audiobook_package_blocks_unpassed_qa(tmp_path: Path) -> None:
    chapter_dir = tmp_path / "mastered"
    _write_wav(chapter_dir / "chapter_001_mastered.wav")
    manifest = _manifest()
    manifest["chapters"] = manifest["chapters"][:1]
    manifest["chapters"][0]["chunks"][0]["qa_status"] = "review"
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="Package blocked by QA status"):
        build_audiobook_package(
            manifest_path,
            chapter_audio_dir=chapter_dir,
            output_dir=tmp_path / "package",
            dry_run=True,
        )


def test_package_audiobook_cli_dry_run_writes_report(tmp_path: Path) -> None:
    chapter_dir = tmp_path / "chapters"
    _write_wav(chapter_dir / "chapter_001.wav")
    manifest = _manifest()
    manifest["chapters"] = manifest["chapters"][:1]
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = CliRunner().invoke(
        cli.main,
        [
            "package-audiobook",
            str(manifest_path),
            "--chapter-audio-dir",
            str(chapter_dir),
            "--format",
            "m4b",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    report = json.loads((tmp_path / "audiobook_package" / "audiobook_package_report.json").read_text(encoding="utf-8"))
    assert report["dry_run"] is True
    assert report["m4b_path"].endswith("Package Test.m4b")
    assert len(report["commands"]) == 1


def test_audiobook_package_rejects_invalid_cover(tmp_path: Path) -> None:
    chapter_dir = tmp_path / "mastered"
    _write_wav(chapter_dir / "chapter_001_mastered.wav")
    manifest = _manifest()
    manifest["chapters"] = manifest["chapters"][:1]
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    cover_path = tmp_path / "cover.txt"
    cover_path.write_text("not an image", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid cover image"):
        build_audiobook_package(
            manifest_path,
            chapter_audio_dir=chapter_dir,
            output_dir=tmp_path / "package",
            cover_path=cover_path,
            dry_run=True,
        )
