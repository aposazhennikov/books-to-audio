from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


def _load_audit_module() -> ModuleType:
    script = Path(__file__).resolve().parent.parent / "scripts" / "gui_visual_audit.py"
    spec = importlib.util.spec_from_file_location("gui_visual_audit", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_gui_visual_audit_renders_pngs_and_summary(tmp_path: Path) -> None:
    module = _load_audit_module()

    cases = module.run_visual_audit(
        out_dir=tmp_path / "gui_audit",
        sizes=((1180, 760),),
        scales=(1.0,),
        tabs=(0, 2),
    )

    assert len(cases) == 2
    assert all(not case.issues for case in cases)
    assert all(Path(case.screenshot).exists() for case in cases)
    summary = json.loads((tmp_path / "gui_audit" / "summary.json").read_text(encoding="utf-8"))
    assert [case["tab"] for case in summary] == [0, 2]
    assert all(case["average_luminance"] >= 210 for case in summary)
    assert all(case["purple_ratio"] <= 0.02 for case in summary)
    assert all(case["visible_scrollbars"] == [] for case in summary)


def test_gui_visual_audit_parses_sizes_and_tabs() -> None:
    module = _load_audit_module()

    assert module._parse_size("760x520") == (760, 520)
    assert module._parse_tabs(["0", "2"]) == (0, 2)
    assert module._parse_tabs(["all"]) is None
