from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from book_normalizer.tts.audio_qa_model_download import (
    DEFAULT_LLM_AUDIO_QA_MODEL_ID,
    FORCED_ALIGNER_MODEL_ID,
    QWEN3_ASR_MODEL_ID,
    AudioQaModelDownloadError,
    audio_qa_model_install_path,
    expand_audio_qa_model_ids,
    install_audio_qa_models,
)


def test_audio_qa_model_install_path_uses_audio_qa_subdir(tmp_path: Path) -> None:
    path = audio_qa_model_install_path(DEFAULT_LLM_AUDIO_QA_MODEL_ID, tmp_path)

    assert path == tmp_path / "audio_qa" / "Qwen3-Omni-30B-A3B-Instruct"


def test_expand_audio_qa_model_ids_resolves_sets() -> None:
    assert expand_audio_qa_model_ids(["production"]) == [
        DEFAULT_LLM_AUDIO_QA_MODEL_ID,
        QWEN3_ASR_MODEL_ID,
        FORCED_ALIGNER_MODEL_ID,
    ]


def test_install_audio_qa_models_downloads_with_huggingface_hub(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, object]] = []

    def fake_snapshot_download(**kwargs: object) -> str:
        calls.append(kwargs)
        target = Path(str(kwargs["local_dir"]))
        target.mkdir(parents=True, exist_ok=True)
        (target / "config.json").write_text("{}", encoding="utf-8")
        return str(target)

    monkeypatch.setitem(
        sys.modules,
        "huggingface_hub",
        SimpleNamespace(snapshot_download=fake_snapshot_download),
    )

    results = install_audio_qa_models(["omni"], tmp_path, token="secret")

    assert results[0].already_present is False
    assert calls[0]["repo_id"] == DEFAULT_LLM_AUDIO_QA_MODEL_ID
    assert calls[0]["repo_type"] == "model"
    assert calls[0]["token"] == "secret"


def test_install_audio_qa_models_errors_when_hub_package_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setitem(sys.modules, "huggingface_hub", None)

    with pytest.raises(AudioQaModelDownloadError):
        install_audio_qa_models(["omni"], tmp_path)
