"""Tests for the shared ComfyUI v2 synthesis loop."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from book_normalizer.comfyui.client import ComfyUIError
from book_normalizer.comfyui.synthesis import load_manifest, synthesize_manifest


class _Builder:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def build(self, **kwargs):  # noqa: ANN001, ANN204
        self.calls.append(kwargs)
        return {"prompt": kwargs}


class _Client:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    def synthesize_chunk(self, workflow: dict, output_path: Path, timeout: float) -> Path:
        self.calls += 1
        if self.fail:
            raise ComfyUIError("boom")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"wav")
        return output_path


class _FailOnceClient:
    def __init__(self) -> None:
        self.calls = 0

    def synthesize_chunk(self, workflow: dict, output_path: Path, timeout: float) -> Path:
        self.calls += 1
        raise ComfyUIError("timeout")


def _manifest() -> dict:
    return {
        "version": 2,
        "chapters": [
            {
                "chapter_index": 0,
                "chunks": [
                    {
                        "chapter_index": 0,
                        "chunk_index": 0,
                        "voice_label": "narrator",
                        "voice_tone": "calm",
                        "text": "Привет.",
                        "synthesized": False,
                    }
                ],
            }
        ],
    }


@pytest.fixture(autouse=True)
def _fake_compatible_export(monkeypatch) -> None:  # noqa: ANN001
    def fake_export(source: Path, output=None, **_kwargs):  # noqa: ANN001, ANN202
        target = output or source.with_suffix(".MP3")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"mp3")
        return target

    monkeypatch.setattr("book_normalizer.comfyui.synthesis.export_compatible_mp3", fake_export)


def test_synthesize_manifest_updates_successful_chunk(tmp_path: Path) -> None:
    manifest = _manifest()
    manifest["chapters"][0]["chunks"][0]["voice_id"] = "narrator_calm"
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    lines: list[str] = []
    client = _Client()

    summary = synthesize_manifest(
        manifest=manifest,
        manifest_path=manifest_path,
        client=client,  # type: ignore[arg-type]
        builder=_Builder(),  # type: ignore[arg-type]
        out_dir=tmp_path / "audio_chunks",
        progress=lines.append,
    )

    chunk = manifest["chapters"][0]["chunks"][0]
    assert summary.synthesized == 1
    assert client.calls == 1
    assert chunk["synthesized"] is True
    assert not Path(chunk["audio_file"]).is_absolute()
    assert (manifest_path.parent / chunk["audio_file"]).exists()
    assert chunk["compatible_audio_file"].endswith(".MP3")
    assert (manifest_path.parent / chunk["compatible_audio_file"]).exists()
    assert any("[narrator/Narrator - Calm/calm]" in line for line in lines)
    assert "PROGRESS 1/1" in lines


def test_synthesize_manifest_localizes_chunk_log(tmp_path: Path) -> None:
    manifest = _manifest()
    manifest["chapters"][0]["chunks"][0].update(
        {
            "voice_label": "women",
            "voice_id": "female_gentle",
            "voice_tone": "calm",
        }
    )
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    lines: list[str] = []

    synthesize_manifest(
        manifest=manifest,
        manifest_path=manifest_path,
        client=_Client(),  # type: ignore[arg-type]
        builder=_Builder(),  # type: ignore[arg-type]
        out_dir=tmp_path / "audio_chunks",
        progress=lines.append,
        log_language="ru",
    )

    assert any("Женский - Нежный" in line and "спокойная" in line for line in lines)
    assert not any("Synthesizing ch" in line for line in lines)


def test_synthesize_manifest_passes_manifest_language_to_workflow(tmp_path: Path) -> None:
    manifest = _manifest()
    manifest["language"] = "uz"
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    builder = _Builder()

    synthesize_manifest(
        manifest=manifest,
        manifest_path=manifest_path,
        client=_Client(),  # type: ignore[arg-type]
        builder=builder,  # type: ignore[arg-type]
        out_dir=tmp_path / "audio_chunks",
    )

    assert builder.calls[0]["language"] == "uz"


def test_synthesize_manifest_passes_character_voice_override(tmp_path: Path) -> None:
    manifest = _manifest()
    chunk = manifest["chapters"][0]["chunks"][0]
    chunk.update(
        {
            "voice_label": "women",
            "voice_id": "female_warm",
            "role": "female",
            "speaker": "Маргарита",
            "emotion": "sad",
        }
    )
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    builder = _Builder()

    synthesize_manifest(
        manifest=manifest,
        manifest_path=manifest_path,
        client=_Client(),  # type: ignore[arg-type]
        builder=builder,  # type: ignore[arg-type]
        out_dir=tmp_path / "audio_chunks",
        speaker_overrides={"speaker:Маргарита|emotion:sad": "margarita_sad"},
    )

    assert builder.calls[0]["speaker_override"] == "margarita_sad"


def test_synthesize_manifest_passes_generation_options_and_director(tmp_path: Path) -> None:
    manifest = _manifest()
    chunk = manifest["chapters"][0]["chunks"][0]
    chunk.update(
        {
            "speaker": "Alice",
            "emotion": "tense",
            "section_kind": "dialogue",
            "director": {"pace": "slow", "volume": "quiet"},
            "resynthesis_attempt": 1,
        }
    )
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    builder = _Builder()

    synthesize_manifest(
        manifest=manifest,
        manifest_path=manifest_path,
        client=_Client(),  # type: ignore[arg-type]
        builder=builder,  # type: ignore[arg-type]
        out_dir=tmp_path / "audio_chunks",
        generation_options={
            "temperature": 0.9,
            "top_p": 0.75,
            "top_k": 30,
            "repetition_penalty": 1.1,
            "max_new_tokens": 1024,
            "seed": 77,
            "speech_rate": 0.98,
        },
    )

    call = builder.calls[0]
    assert call["speaker"] == "Alice"
    assert call["emotion"] == "tense"
    assert call["section_kind"] == "dialogue"
    assert call["director"] == {"pace": "slow", "volume": "quiet"}
    assert call["resynthesis_attempt"] == 1
    assert call["generation_options"]["temperature"] == 0.9
    assert call["generation_options"]["seed"] != 77
    assert manifest["chapters"][0]["chunks"][0]["last_generation_options"] == call["generation_options"]


def test_synthesize_manifest_marks_failed_chunk(tmp_path: Path) -> None:
    manifest = _manifest()
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    summary = synthesize_manifest(
        manifest=manifest,
        manifest_path=manifest_path,
        client=_Client(fail=True),  # type: ignore[arg-type]
        builder=_Builder(),  # type: ignore[arg-type]
        out_dir=tmp_path / "audio_chunks",
    )

    chunk = manifest["chapters"][0]["chunks"][0]
    assert summary.failed == 1
    assert chunk["failed"] is True
    assert chunk["error"] == "boom"


def test_synthesize_manifest_recovers_and_retries_current_chunk(tmp_path: Path) -> None:
    manifest = _manifest()
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    failing_client = _FailOnceClient()
    recovered_client = _Client()
    recovery_errors: list[str] = []
    lines: list[str] = []

    def recover(exc: ComfyUIError, attempt: int) -> _Client:
        recovery_errors.append(f"{attempt}:{exc}")
        return recovered_client

    summary = synthesize_manifest(
        manifest=manifest,
        manifest_path=manifest_path,
        client=failing_client,  # type: ignore[arg-type]
        builder=_Builder(),  # type: ignore[arg-type]
        out_dir=tmp_path / "audio_chunks",
        progress=lines.append,
        recovery=recover,  # type: ignore[arg-type]
        max_recovery_retries=1,
    )

    chunk = manifest["chapters"][0]["chunks"][0]
    assert summary.synthesized == 1
    assert summary.failed == 0
    assert failing_client.calls == 1
    assert recovered_client.calls == 1
    assert recovery_errors == ["1:timeout"]
    assert chunk["synthesized"] is True
    assert chunk["failed"] is False
    assert "PROGRESS 1/1" in lines


def test_synthesize_manifest_failed_only_skips_unfailed_chunks(tmp_path: Path) -> None:
    manifest = _manifest()
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    client = _Client()

    summary = synthesize_manifest(
        manifest=manifest,
        manifest_path=manifest_path,
        client=client,  # type: ignore[arg-type]
        builder=_Builder(),  # type: ignore[arg-type]
        out_dir=tmp_path / "audio_chunks",
        failed_only=True,
    )

    assert summary.synthesized == 0
    assert client.calls == 0


def test_synthesize_manifest_retries_synthesized_chunk_when_audio_is_missing(
    tmp_path: Path,
) -> None:
    manifest = _manifest()
    chunk = manifest["chapters"][0]["chunks"][0]
    chunk["synthesized"] = True
    chunk["audio_file"] = str(tmp_path / "missing.wav")
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    client = _Client()

    summary = synthesize_manifest(
        manifest=manifest,
        manifest_path=manifest_path,
        client=client,  # type: ignore[arg-type]
        builder=_Builder(),  # type: ignore[arg-type]
        out_dir=tmp_path / "audio_chunks",
    )

    assert summary.synthesized == 1
    assert client.calls == 1
    assert (manifest_path.parent / chunk["audio_file"]).exists()


def test_synthesize_manifest_resume_resolves_relative_audio_from_manifest_dir(
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "renamed_project"
    audio_path = project_dir / "audio_chunks" / "chapter_001" / "chunk_001_narrator.wav"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"wav")
    manifest = _manifest()
    chunk = manifest["chapters"][0]["chunks"][0]
    chunk["synthesized"] = True
    chunk["audio_file"] = "audio_chunks/chapter_001/chunk_001_narrator.wav"
    manifest_path = project_dir / "chunks_manifest_v2.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    client = _Client()

    summary = synthesize_manifest(
        manifest=manifest,
        manifest_path=manifest_path,
        client=client,  # type: ignore[arg-type]
        builder=_Builder(),  # type: ignore[arg-type]
        out_dir=project_dir / "audio_chunks",
    )

    assert summary.synthesized == 0
    assert summary.skipped == 1
    assert client.calls == 0


def test_synthesize_manifest_skips_deleted_chunks(tmp_path: Path) -> None:
    manifest = _manifest()
    chunks = manifest["chapters"][0]["chunks"]
    chunks.append(
        {
            "chapter_index": 0,
            "chunk_index": 1,
            "voice_label": "narrator",
            "voice_tone": "calm",
            "text": "Deleted publisher boilerplate.",
            "synthesized": False,
            "deleted": True,
            "excluded_from_tts": True,
        }
    )
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    client = _Client()
    lines: list[str] = []

    summary = synthesize_manifest(
        manifest=manifest,
        manifest_path=manifest_path,
        client=client,  # type: ignore[arg-type]
        builder=_Builder(),  # type: ignore[arg-type]
        out_dir=tmp_path / "audio_chunks",
        progress=lines.append,
    )

    assert summary.total == 1
    assert summary.synthesized == 1
    assert client.calls == 1
    assert chunks[0]["synthesized"] is True
    assert chunks[1]["synthesized"] is False
    assert "PROGRESS 1/1" in lines


def test_load_manifest_rejects_v1_list(tmp_path: Path) -> None:
    manifest_path = tmp_path / "chunks_manifest.json"
    manifest_path.write_text("[]", encoding="utf-8")

    try:
        load_manifest(manifest_path)
    except ValueError as exc:
        assert "v2 manifest" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError")
