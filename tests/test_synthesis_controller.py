from __future__ import annotations

import json
from pathlib import Path

import pytest

from book_normalizer.comfyui.server import ComfyUIStartResult
from book_normalizer.comfyui.synthesis import SynthesisSummary
from book_normalizer.tts import synthesis_controller
from book_normalizer.tts.synthesis_controller import SynthesisController, SynthesisRequest


def _write_manifest(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "version": 2,
                "chapters": [
                    {
                        "chapter_index": 0,
                        "chunks": [
                            {
                                "chapter_index": 0,
                                "chunk_index": 0,
                                "voice_label": "narrator",
                                "text": "Hello.",
                                "synthesized": False,
                            },
                        ],
                    },
                ],
            },
        ),
        encoding="utf-8",
    )
    return path


def _write_manifest_chunks(path: Path, *, total: int, synthesized: int = 0) -> Path:
    chunks = []
    for index in range(total):
        audio_path = path.parent / f"chunk_{index + 1:03d}.wav"
        is_done = index < synthesized
        if is_done:
            audio_path.write_bytes(b"RIFF$\x00\x00\x00WAVEfmt ")
        chunks.append(
            {
                "chapter_index": 0,
                "chunk_index": index,
                "voice_label": "narrator",
                "text": f"Chunk {index + 1}.",
                "synthesized": is_done,
                "audio_file": str(audio_path) if is_done else "",
            }
        )
    path.write_text(
        json.dumps(
            {
                "version": 2,
                "chapters": [{"chapter_index": 0, "chunks": chunks}],
            },
        ),
        encoding="utf-8",
    )
    return path


def test_synthesis_controller_autostarts_comfyui_before_failing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path = _write_manifest(tmp_path / "chunks_manifest_v2.json")
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text("{}", encoding="utf-8")
    started: list[str] = []

    class _Client:
        def __init__(self, base_url: str) -> None:
            self.base_url = base_url

        def is_reachable(self) -> bool:
            return bool(started)

    class _Builder:
        def __init__(self, path: Path) -> None:
            self.path = path

    def fake_start(url: str, **_kwargs) -> ComfyUIStartResult:  # noqa: ANN001
        started.append(url)
        return ComfyUIStartResult(
            api_url=url.rstrip("/") + "/system_stats",
            log_dir=tmp_path / "logs",
            root=tmp_path / "ComfyUI",
            started=True,
            message="ComfyUI started",
        )

    monkeypatch.setattr(synthesis_controller, "ComfyUIClient", _Client)
    monkeypatch.setattr(synthesis_controller, "WorkflowBuilder", _Builder)
    monkeypatch.setattr(synthesis_controller, "ensure_local_comfyui", fake_start)
    monkeypatch.setattr(
        synthesis_controller,
        "synthesize_manifest",
        lambda **_kwargs: SynthesisSummary(total=1, synthesized=1, skipped=0, failed=0),
    )

    logs: list[str] = []
    result = SynthesisController(
        SynthesisRequest(
            manifest_path=manifest_path,
            output_dir=tmp_path / "out",
            workflow_path=workflow_path,
            comfyui_url="http://localhost:8188",
            quality_loop=False,
            artifact_qa=False,
            asr_qa_after_synthesis=False,
        ),
        log=logs.append,
    ).run()

    assert started == ["http://localhost:8188"]
    assert result.synthesized == 1
    assert any("trying to start" in line for line in logs)
    assert "ComfyUI started" in logs


def test_synthesis_controller_estimates_eta_from_progress_lines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path = _write_manifest_chunks(
        tmp_path / "chunks_manifest_v2.json",
        total=5,
        synthesized=2,
    )
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text("{}", encoding="utf-8")

    class _Client:
        def __init__(self, base_url: str) -> None:
            self.base_url = base_url

        def is_reachable(self) -> bool:
            return True

    class _Builder:
        def __init__(self, path: Path) -> None:
            self.path = path

    def fake_synthesize_manifest(**kwargs) -> SynthesisSummary:  # noqa: ANN003
        kwargs["progress"]("PROGRESS 3/5")
        return SynthesisSummary(total=5, synthesized=1, skipped=2, failed=0)

    times = iter([100.0, 130.0])
    monkeypatch.setattr(synthesis_controller.time, "monotonic", lambda: next(times))
    monkeypatch.setattr(synthesis_controller, "ComfyUIClient", _Client)
    monkeypatch.setattr(synthesis_controller, "WorkflowBuilder", _Builder)
    monkeypatch.setattr(synthesis_controller, "synthesize_manifest", fake_synthesize_manifest)

    progress: list[tuple[int, int, str, int, int, float, int, int, int]] = []
    SynthesisController(
        SynthesisRequest(
            manifest_path=manifest_path,
            output_dir=tmp_path / "out",
            workflow_path=workflow_path,
            comfyui_url="http://localhost:8188",
        ),
        progress=lambda *args: progress.append(args),
    ).run()

    assert progress[0] == (3, 5, "1m 00s", 0, 0, 0.0, 2, 0, 0)
    assert progress[-1] == (5, 5, "0s", 0, 0, 0.0, 0, 0, 0)
