from __future__ import annotations

from pathlib import Path

from book_normalizer.gui.auto_pipeline import AutoPipelineOrchestrator


class _Controller:
    def __init__(self, *, complete_audio: bool = False) -> None:
        self.complete_audio = complete_audio
        self.calls: list[tuple] = []

    def build_tts_chunks(self) -> None:
        self.calls.append(("build_tts_chunks",))

    def run_synthesis(self) -> None:
        self.calls.append(("run_synthesis",))

    def run_asr_qa(self, pending_finish=None) -> None:  # noqa: ANN001
        self.calls.append(("run_asr_qa", pending_finish))

    def run_assembly(self) -> None:
        self.calls.append(("run_assembly",))

    def run_production_package(self) -> None:
        self.calls.append(("run_production_package",))

    def has_complete_audio(self, manifest_path: Path) -> bool:
        self.calls.append(("has_complete_audio", manifest_path))
        return self.complete_audio

    def status(self, message: str) -> None:
        self.calls.append(("status", message))

    def show_tab(self, index: int) -> None:
        self.calls.append(("show_tab", index))

    def apply_quality_settings(self) -> None:
        self.calls.append(("apply_quality_settings",))


def _immediate(_delay: int, callback) -> None:  # noqa: ANN001
    callback()


def test_auto_pipeline_orchestrator_starts_chunk_build_without_cache() -> None:
    controller = _Controller()
    orchestrator = AutoPipelineOrchestrator(controller, schedule=_immediate)

    started = orchestrator.continue_after_segments(cached_chunks=None)

    assert started is True
    assert controller.calls == [
        ("status", "auto.chunks"),
        ("build_tts_chunks",),
    ]


def test_auto_pipeline_orchestrator_skips_chunk_build_with_cache(tmp_path: Path) -> None:
    controller = _Controller()
    orchestrator = AutoPipelineOrchestrator(controller, schedule=_immediate)

    started = orchestrator.continue_after_segments(
        cached_chunks=tmp_path / "chunks_manifest_v2.json",
    )

    assert started is False
    assert controller.calls == []


def test_auto_pipeline_orchestrator_runs_asr_when_audio_is_complete(
    tmp_path: Path,
) -> None:
    controller = _Controller(complete_audio=True)
    orchestrator = AutoPipelineOrchestrator(controller, schedule=_immediate)
    manifest_path = tmp_path / "chunks_manifest_v2.json"

    step = orchestrator.continue_after_chunks(manifest_path, tmp_path)

    assert step == "quality"
    assert controller.calls == [
        ("show_tab", 3),
        ("apply_quality_settings",),
        ("has_complete_audio", manifest_path),
        ("status", "auto.quality"),
        ("run_asr_qa", (str(tmp_path / "audio_chunks"), 0, 0)),
    ]


def test_auto_pipeline_orchestrator_runs_synthesis_when_audio_is_missing(
    tmp_path: Path,
) -> None:
    controller = _Controller(complete_audio=False)
    orchestrator = AutoPipelineOrchestrator(controller, schedule=_immediate)
    manifest_path = tmp_path / "chunks_manifest_v2.json"

    step = orchestrator.continue_after_chunks(manifest_path, tmp_path)

    assert step == "synthesis"
    assert controller.calls == [
        ("show_tab", 3),
        ("apply_quality_settings",),
        ("has_complete_audio", manifest_path),
        ("status", "auto.synthesis"),
        ("run_synthesis",),
    ]


def test_auto_pipeline_orchestrator_continues_terminal_stages() -> None:
    controller = _Controller()
    orchestrator = AutoPipelineOrchestrator(controller, schedule=_immediate)

    orchestrator.continue_after_synthesis()
    orchestrator.continue_after_assembly()

    assert controller.calls == [
        ("show_tab", 4),
        ("status", "auto.assembly"),
        ("run_assembly",),
        ("show_tab", 4),
        ("status", "auto.production"),
        ("run_production_package",),
    ]
