"""Tests for ComfyUI workflow placeholder substitution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from book_normalizer.comfyui.generation_options import GenerationOptions
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
                    "language": "Russian",
                    "instruct": "{{INSTRUCT}}",
                    "filename_prefix": "out/{{OUTPUT_FILENAME}}",
                }
            }
        },
    )

    workflow = WorkflowBuilder(template).build(
        text="Hello.",
        voice_label="women",
        voice_tone="angry and tense",
        output_filename="chunk_001_women",
        language="en",
    )

    inputs = workflow["1"]["inputs"]
    assert inputs["text"] == "Hello."
    assert inputs["speaker"] == "Serena"
    assert inputs["language"] == "English"
    assert inputs["instruct"].endswith("Full tone: angry and tense.")
    assert len(inputs["instruct"].split(". ")) >= 3
    assert inputs["filename_prefix"] == "out/chunk_001_women"


def test_workflow_builder_replaces_language_placeholder(tmp_path: Path) -> None:
    template = _write_template(
        tmp_path / "workflow.json",
        {"1": {"inputs": {"language": "{{LANGUAGE}}"}}},
    )

    workflow = WorkflowBuilder(template).build(
        text="\u4f60\u597d\u3002",
        voice_label="narrator",
        voice_tone="calm",
        output_filename="chunk_001",
        language="zh",
    )

    assert workflow["1"]["inputs"]["language"] == "Chinese"


def test_voice_tone_to_instruct_maps_bright_emotional_tones() -> None:
    instruct = voice_tone_to_instruct("women", "cheerful")

    assert "Весело" in instruct


def test_narrator_calm_instruct_keeps_delivery_stable() -> None:
    instruct = voice_tone_to_instruct("narrator", "calm")

    assert "steady audiobook narrator delivery" in instruct
    assert "Do not shout" in instruct


def test_generation_options_default_to_stable_audiobook_sampling() -> None:
    options = GenerationOptions().for_attempt(0)

    assert options["temperature"] == 0.65
    assert options["top_p"] == 0.70
    assert options["top_k"] == 15
    assert options["seed"] == 42


def test_workflow_builder_uses_custom_speaker_override(tmp_path: Path) -> None:
    template = _write_template(
        tmp_path / "workflow.json",
        {"1": {"inputs": {"speaker": "{{SPEAKER}}", "text": "{{TEXT}}"}}},
    )

    workflow = WorkflowBuilder(template).build(
        text="Hello.",
        voice_label="women",
        voice_tone="calm",
        output_filename="chunk_001",
        speaker_override="margarita_sad",
    )

    assert workflow["1"]["inputs"]["speaker"] == "margarita_sad"


def test_workflow_builder_injects_generation_options(tmp_path: Path) -> None:
    template = _write_template(
        tmp_path / "workflow.json",
        {
            "1": {
                "inputs": {
                    "temperature": 1.0,
                    "top_p": 0.8,
                    "top_k": 20,
                    "repetition_penalty": 1.05,
                    "max_new_tokens": 2048,
                    "seed": -1,
                    "speech_rate": 1.0,
                    "text": "{{TEXT}}",
                }
            }
        },
    )

    workflow = WorkflowBuilder(template).build(
        text="Hello.",
        voice_label="narrator",
        voice_tone="calm",
        output_filename="chunk_001",
        generation_options={
            "temperature": 0.65,
            "top_p": 0.7,
            "top_k": 35,
            "repetition_penalty": 1.2,
            "max_new_tokens": 1024,
            "seed": 123,
            "speech_rate": 0.95,
        },
    )

    inputs = workflow["1"]["inputs"]
    assert inputs["temperature"] == 0.65
    assert inputs["top_p"] == 0.7
    assert inputs["top_k"] == 35
    assert inputs["repetition_penalty"] == 1.2
    assert inputs["max_new_tokens"] == 1024
    assert inputs["seed"] == 123
    assert inputs["speech_rate"] == 0.95


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
        ref_text="Reference text.",
    )

    assert workflow["1"]["inputs"] == {
        "audio": "sample.wav",
        "name": "narrator",
        "text": "Reference text.",
    }


def test_workflow_builder_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(WorkflowBuilderError):
        WorkflowBuilder(tmp_path / "missing.json")


def test_voice_tone_falls_back_to_neutral_for_unknown_tone() -> None:
    instruct = voice_tone_to_instruct("men", "mysterious")

    assert "Full tone:" not in instruct
    assert instruct.endswith(".")
