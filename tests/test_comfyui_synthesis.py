"""Tests for the shared ComfyUI v2 synthesis loop."""

from __future__ import annotations

import json
from pathlib import Path

from book_normalizer.comfyui.client import ComfyUIError
from book_normalizer.comfyui.synthesis import load_manifest, synthesize_manifest


class _Builder:
    def build(self, **kwargs):  # noqa: ANN001, ANN204
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


def test_synthesize_manifest_updates_successful_chunk(tmp_path: Path) -> None:
    manifest = _manifest()
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
    assert Path(chunk["audio_file"]).exists()
    assert "PROGRESS 1/1" in lines


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


def test_load_manifest_rejects_v1_list(tmp_path: Path) -> None:
    manifest_path = tmp_path / "chunks_manifest.json"
    manifest_path.write_text("[]", encoding="utf-8")

    try:
        load_manifest(manifest_path)
    except ValueError as exc:
        assert "v2 manifest" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError")
