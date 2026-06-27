from __future__ import annotations

import json
from pathlib import Path

import pytest

from book_normalizer.comfyui.server import ComfyUIStartResult
from book_normalizer.comfyui.synthesis import SynthesisSummary
from book_normalizer.tts import synthesis_controller
from book_normalizer.tts.synthesis_controller import (
    SynthesisCancelled,
    SynthesisController,
    SynthesisRequest,
)


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
    monkeypatch.setattr(synthesis_controller, "monotonic", lambda: next(times))
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


def test_synthesis_controller_reports_review_required_for_partial_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path = _write_manifest_chunks(
        tmp_path / "chunks_manifest_v2.json",
        total=3,
        synthesized=1,
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

    def fake_synthesize_manifest(**_kwargs) -> SynthesisSummary:  # noqa: ANN003
        return SynthesisSummary(total=3, synthesized=1, skipped=1, failed=1)

    monkeypatch.setattr(synthesis_controller, "ComfyUIClient", _Client)
    monkeypatch.setattr(synthesis_controller, "WorkflowBuilder", _Builder)
    monkeypatch.setattr(synthesis_controller, "synthesize_manifest", fake_synthesize_manifest)

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
    ).run()

    assert result.status == "review_required"
    assert result.total == 3
    assert result.failed == 1
    assert result.synthesized == 1
    assert result.skipped == 1


def test_synthesis_controller_routes_local_tts_engine_without_comfyui_workflow(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path = _write_manifest(tmp_path / "chunks_manifest_v2.json")
    (tmp_path / "models" / "audio_encoders" / "F5-TTS").mkdir(parents=True)
    calls: list[dict] = []

    def fake_synthesize_engine_manifest(**kwargs):  # noqa: ANN003
        calls.append(kwargs)
        kwargs["progress"]("PROGRESS 1/1")
        return SynthesisSummary(total=1, synthesized=1, skipped=0, failed=0)

    monkeypatch.setattr(
        "book_normalizer.tts.engine_synthesis.shutil.which",
        lambda command: f"/usr/bin/{command}",
    )
    monkeypatch.setattr(
        synthesis_controller,
        "synthesize_engine_manifest",
        fake_synthesize_engine_manifest,
    )

    result = SynthesisController(
        SynthesisRequest(
            manifest_path=manifest_path,
            output_dir=tmp_path / "out",
            workflow_path=tmp_path / "missing-workflow.json",
            tts_engine="f5-tts",
            models_dir=str(tmp_path / "models"),
        ),
    ).run()

    assert result.synthesized == 1
    assert calls[0]["engine_id"] == "f5-tts"
    assert calls[0]["models_dir"] == str(tmp_path / "models")
    contract = json.loads((tmp_path / "out" / "run_contract.json").read_text(encoding="utf-8"))
    assert contract["parameters"]["models_dir"] == str(tmp_path / "models")
    assert contract["parameters"]["resume_mode"] == "manifest_state"


def test_synthesis_controller_marks_cancelled_run_without_completed_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path = _write_manifest(tmp_path / "chunks_manifest_v2.json")
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
        assert kwargs["cancel_requested"]() is True
        return SynthesisSummary(total=1, synthesized=0, skipped=0, failed=0, status="cancelled")

    monkeypatch.setattr(synthesis_controller, "ComfyUIClient", _Client)
    monkeypatch.setattr(synthesis_controller, "WorkflowBuilder", _Builder)
    monkeypatch.setattr(synthesis_controller, "synthesize_manifest", fake_synthesize_manifest)

    with pytest.raises(SynthesisCancelled):
        SynthesisController(
            SynthesisRequest(
                manifest_path=manifest_path,
                output_dir=tmp_path / "out",
                workflow_path=workflow_path,
                comfyui_url="http://localhost:8188",
            ),
            cancel_requested=lambda: True,
        ).run()

    report = json.loads(
        (tmp_path / "out" / "stage_reports" / "tts_synthesis_report.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["status"] == "cancelled"
    assert report["summary"]["cancelled"] is True


def test_synthesis_controller_preflights_local_tts_cli_before_synthesis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path = _write_manifest(tmp_path / "chunks_manifest_v2.json")
    calls: list[dict] = []
    logs: list[str] = []

    def fake_synthesize_engine_manifest(**kwargs):  # noqa: ANN003
        calls.append(kwargs)
        return SynthesisSummary(total=1, synthesized=1, skipped=0, failed=0)

    monkeypatch.setattr(
        "book_normalizer.tts.engine_synthesis.shutil.which",
        lambda _command: None,
    )
    monkeypatch.setattr(
        synthesis_controller,
        "synthesize_engine_manifest",
        fake_synthesize_engine_manifest,
    )

    with pytest.raises(FileNotFoundError) as exc_info:
        SynthesisController(
            SynthesisRequest(
                manifest_path=manifest_path,
                output_dir=tmp_path / "out",
                workflow_path=tmp_path / "missing-workflow.json",
                tts_engine="f5-tts",
                models_dir=str(tmp_path / "models"),
            ),
            log=logs.append,
        ).run()

    message = str(exc_info.value)
    assert calls == []
    assert "f5-tts_infer-cli" in message
    assert "What to install:" in message
    assert "Command that would be invoked:" in message
    assert "BOOKS_TO_AUDIO_TTS_F5_TTS_COMMAND" in message
    assert any(line.startswith("Command preview:") for line in logs)


def test_synthesis_controller_runs_perceptual_qa_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path = _write_manifest_chunks(
        tmp_path / "chunks_manifest_v2.json",
        total=1,
        synthesized=1,
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

    from book_normalizer.tts.perceptual_qa import PerceptualChunkResult, PerceptualQaResult

    def fake_synthesize_manifest(**_kwargs) -> SynthesisSummary:  # noqa: ANN003
        return SynthesisSummary(total=1, synthesized=0, skipped=1, failed=0)

    def fake_run_perceptual_qa(*_args, **_kwargs):  # noqa: ANN002
        return PerceptualQaResult(
            backends=["nisqa-v2"],
            created_at="2026-01-01T00:00:00+00:00",
            chunks=[
                PerceptualChunkResult(
                    chapter_index=0,
                    chunk_index=0,
                    audio_file=str(tmp_path / "chunk_001.wav"),
                    status="passed",
                    scores={"nisqa-v2": {"mos": 4.0}},
                )
            ],
        )

    monkeypatch.setattr(synthesis_controller, "ComfyUIClient", _Client)
    monkeypatch.setattr(synthesis_controller, "WorkflowBuilder", _Builder)
    monkeypatch.setattr(synthesis_controller, "synthesize_manifest", fake_synthesize_manifest)
    monkeypatch.setattr(synthesis_controller, "run_perceptual_qa", fake_run_perceptual_qa)

    logs: list[str] = []
    SynthesisController(
        SynthesisRequest(
            manifest_path=manifest_path,
            output_dir=tmp_path / "out",
            workflow_path=workflow_path,
            comfyui_url="http://localhost:8188",
            perceptual_qa=True,
            perceptual_backends=("nisqa-v2",),
        ),
        log=logs.append,
    ).run()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["chapters"][0]["chunks"][0]["perceptual_qa"]["status"] == "passed"
    assert (tmp_path / "perceptual_qa_report.json").exists()
    assert any("Perceptual QA:" in line for line in logs)
