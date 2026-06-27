from __future__ import annotations

import json
import subprocess
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_release_module():
    script = Path("scripts/release_build.py").resolve()
    spec = spec_from_file_location("test_release_build_script", script)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_release_versions_accept_v_prefixed_tag() -> None:
    module = _load_release_module()

    check = module.validate_versions("v0.1.0")

    assert check.ok is True
    assert check.pyproject_version == "0.1.0"
    assert check.package_version == "0.1.0"
    assert check.tag_version == "0.1.0"


def test_release_versions_reject_mismatched_tag() -> None:
    module = _load_release_module()

    check = module.validate_versions("v9.9.9")

    assert check.ok is False


def test_release_gate_requires_human_listening_pass(tmp_path: Path, monkeypatch) -> None:
    module = _load_release_module()
    report = tmp_path / "final_readiness_report.json"
    verdict = tmp_path / "manual_listening_verdict.json"

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN202
        assert "final_readiness_check.py" in cmd[1]
        report.write_text(json.dumps({"complete_with_human_review": False}), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, stdout="{}", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    payload = module.run_final_readiness_gate(report, verdict)

    assert payload["complete_with_human_review"] is False


def test_release_main_fails_when_human_gate_is_open(tmp_path: Path, monkeypatch, capsys) -> None:
    module = _load_release_module()

    monkeypatch.setattr(module, "run_final_readiness_gate", lambda *_args: {"complete_with_human_review": False})

    code = module.main(["--tag", "v0.1.0", "--no-build", "--readiness-report", str(tmp_path / "report.json")])

    assert code == 1
    assert "Final readiness gate is not accepted" in capsys.readouterr().err


def test_release_main_can_validate_without_building(tmp_path: Path, monkeypatch, capsys) -> None:
    module = _load_release_module()

    monkeypatch.setattr(module, "run_final_readiness_gate", lambda *_args: {"complete_with_human_review": True})
    monkeypatch.setattr(module, "build_python_artifacts", lambda *_args: (_ for _ in ()).throw(AssertionError))

    code = module.main(["--tag", "v0.1.0", "--no-build", "--readiness-report", str(tmp_path / "report.json")])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["release_gate"] == "passed"
    assert payload["version"] == "0.1.0"
