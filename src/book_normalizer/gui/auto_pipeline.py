"""Orchestration helpers for the unattended GUI audiobook pipeline."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from PyQt6.QtCore import QTimer


class AutoPipelineController(Protocol):
    """UI-facing operations needed by the automatic pipeline."""

    def build_tts_chunks(self) -> None: ...

    def run_synthesis(self) -> None: ...

    def run_asr_qa(self, pending_finish: tuple[str, int, int] | None = None) -> None: ...

    def run_assembly(self) -> None: ...

    def has_complete_audio(self, manifest_path: Path) -> bool: ...

    def status(self, message: str) -> None: ...

    def show_tab(self, index: int) -> None: ...

    def apply_quality_settings(self) -> None: ...

    def finish_for_manual_review(self) -> None: ...


class AutoPipelineOrchestrator:
    """Drive automatic pipeline transitions without knowing page internals."""

    def __init__(
        self,
        controller: AutoPipelineController,
        *,
        schedule: Callable[[int, Callable[[], None]], None] | None = None,
    ) -> None:
        self._controller = controller
        self._schedule = schedule or QTimer.singleShot

    def continue_after_segments(self, *, cached_chunks: Path | None) -> bool:
        """Start chunking unless a reusable chunks manifest is already available."""
        if cached_chunks is not None:
            return False
        self._controller.status("auto.chunks")
        self._controller.build_tts_chunks()
        return True

    def continue_after_chunks(self, manifest_path: Path, output_dir: Path) -> str:
        """Start synthesis or quality checks after chunks are available."""
        self._controller.show_tab(3)
        self._controller.apply_quality_settings()
        if self._controller.has_complete_audio(manifest_path):
            self._controller.status("auto.quality")
            self._schedule(
                0,
                lambda: self._controller.run_asr_qa(
                    (str(output_dir / "audio_chunks"), 0, 0),
                ),
            )
            return "quality"

        self._controller.status("auto.synthesis")
        self._schedule(0, self._controller.run_synthesis)
        return "synthesis"

    def continue_after_synthesis(self) -> None:
        """Start assembly after synthesis has finished."""
        self._controller.show_tab(4)
        self._controller.status("auto.assembly")
        self._schedule(0, self._controller.run_assembly)

    def continue_after_assembly(self) -> None:
        """Stop before packaging so a human can review the assembled audio."""
        self._controller.show_tab(4)
        self._controller.finish_for_manual_review()
