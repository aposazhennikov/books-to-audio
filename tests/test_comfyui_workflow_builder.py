"""Tests for ComfyUI workflow placeholder substitution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from book_normalizer.comfyui.workflow_builder import (
    WorkflowBuilder,
    WorkflowBuilderError,
    voice_tone_to_instruct,
)


def _write_template(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_workflow_builder_replaces_synthesis_placeholders(tmp_path: Path) -> None:
    template = _write_template(
        tmp_path / "workflow.json",
        {
            "1": {
                "inputs": {
                    "text": "{{TEXT}}",
                    "speaker": "{{SPEAKER}}",
                    "instruct": "{{INSTRUCT}}",
                    "filename_prefix": "out/{{OUTPUT_FILENAME}}",
                }
            }
        },
    )

    workflow = WorkflowBuilder(template).build(
        text="Привет.",
        voice_label="women",
        voice_tone="angry and tense",
        output_filename="chunk_001_women",
    )

    inputs = workflow["1"]["inputs"]
    assert inputs["text"] == "Привет."
    assert inputs["speaker"] == "Serena"
    assert inputs["instruct"] == "Женский персонаж. Жёстко и напряжённо."
    assert inputs["filename_prefix"] == "out/chunk_001_women"


def test_workflow_builder_reports_missing_placeholders(tmp_path: Path) -> None:
    template = _write_template(tmp_path / "workflow.json", {"1": {"inputs": {"text": "{{TEXT}}"}}})

    missing = WorkflowBuilder(template).missing_placeholders()

    assert "{{SPEAKER}}" in missing
    assert "{{INSTRUCT}}" in missing
    assert "{{OUTPUT_FILENAME}}" in missing


def test_workflow_builder_replaces_voice_setup_placeholders(tmp_path: Path) -> None:
    template = _write_template(
        tmp_path / "voice_setup.json",
        {"1": {"inputs": {"audio": "{{AUDIO_FILENAME}}", "name": "{{VOICE_NAME}}", "text": "{{REF_TEXT}}"}}},
    )

    workflow = WorkflowBuilder(template).build_voice_setup(
        audio_filename="sample.wav",
        voice_name="narrator",
        ref_text="Текст образца.",
    )

    assert workflow["1"]["inputs"] == {
        "audio": "sample.wav",
        "name": "narrator",
        "text": "Текст образца.",
    }


def test_workflow_builder_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(WorkflowBuilderError):
        WorkflowBuilder(tmp_path / "missing.json")


def test_voice_tone_falls_back_to_neutral_for_unknown_tone() -> None:
    assert voice_tone_to_instruct("men", "mysterious") == "Мужской персонаж. Ровно и чётко."
