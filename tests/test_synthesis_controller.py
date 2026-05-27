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
