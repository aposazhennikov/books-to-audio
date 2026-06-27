"""Telemetry-free local observability artifacts for long audiobook runs."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from book_normalizer.schemas import schema_version_for


@dataclass
class StageObserver:
    """Write structured logs and machine-readable stage reports locally."""

    output_dir: Path
    run_id: str
    stage: str
    started_at: float = field(default_factory=time.monotonic)
    counters: dict[str, int | float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    @property
    def logs_dir(self) -> Path:
        return self.output_dir / "logs"

    @property
    def reports_dir(self) -> Path:
        return self.output_dir / "stage_reports"

    @property
    def log_path(self) -> Path:
        return self.logs_dir / f"{self.stage}.jsonl"

    def log(self, event: str, **fields: Any) -> None:
        payload = {
            "schema_version": schema_version_for("stage_report"),
            "timestamp": datetime.now(UTC).isoformat(),
            "run_id": self.run_id,
            "stage": self.stage,
            "event": event,
            **fields,
        }
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def increment(self, name: str, amount: int | float = 1) -> None:
        self.counters[name] = self.counters.get(name, 0) + amount

    def finish(
        self,
        status: str = "completed",
        *,
        elapsed_seconds: float | None = None,
        **summary: Any,
    ) -> Path:
        elapsed = elapsed_seconds
        if elapsed is None:
            elapsed = time.monotonic() - self.started_at
        report = {
            "schema_version": schema_version_for("stage_report"),
            "run_id": self.run_id,
            "stage": self.stage,
            "status": status,
            "elapsed_seconds": elapsed,
            "resource_usage": _resource_usage(),
            "counters": self.counters,
            "summary": summary,
        }
        path = self.reports_dir / f"{self.stage}_report.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return path


def _resource_usage() -> dict[str, Any]:
    usage: dict[str, Any] = {"ram_peak_mb": None, "vram_mb": None}
    try:
        import resource  # type: ignore[import-not-found]

        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        usage["ram_peak_mb"] = peak / 1024 if os.name != "posix" else peak / 1024
    except Exception:
        pass
    return usage
