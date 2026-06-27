from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from book_normalizer.tts.model_download import (
    COSYVOICE_3,
    DEFAULT_TTS_MODEL_ID,
    F5_TTS,
    FISH_SPEECH_15,
    QWEN3_TTS_TOKENIZER,
    XTTS_V2,
    TTSModelDownloadError,
    expand_tts_model_ids,
    install_tts_models,
    missing_tts_model_ids,
    tts_model_install_path,
)


def test_tts_model_install_path_uses_audio_encoders(tmp_path: Path) -> None:
    path = tts_model_install_path(DEFAULT_TTS_MODEL_ID, tmp_path)

    assert path == tmp_path / "audio_encoders" / "Qwen3-TTS-12Hz-1.7B-CustomVoice"


def test_expand_tts_model_ids_adds_tokenizer_once() -> None:
    assert expand_tts_model_ids([DEFAULT_TTS_MODEL_ID, QWEN3_TTS_TOKENIZER]) == [
        DEFAULT_TTS_MODEL_ID,
        QWEN3_TTS_TOKENIZER,
    ]


def test_expand_tts_model_ids_resolves_new_engine_aliases_without_qwen_tokenizer() -> None:
    assert expand_tts_model_ids(
        ["fish-speech-1.5", "f5-tts", "xtts-v2", "cosyvoice-3"]
    ) == [
        FISH_SPEECH_15,
        F5_TTS,
        XTTS_V2,
        COSYVOICE_3,
    ]


def test_missing_tts_model_ids_detects_existing_model_and_missing_tokenizer(
    tmp_path: Path,
) -> None:
    model_dir = tts_model_install_path(DEFAULT_TTS_MODEL_ID, tmp_path)
    model_dir.mkdir(parents=True)
    (model_dir / "config.json").write_text("{}", encoding="utf-8")

    assert missing_tts_model_ids([DEFAULT_TTS_MODEL_ID], tmp_path) == [
        QWEN3_TTS_TOKENIZER,
    ]


def test_install_tts_models_skips_existing_model(tmp_path: Path) -> None:
    model_dir = tts_model_install_path(DEFAULT_TTS_MODEL_ID, tmp_path)
    model_dir.mkdir(parents=True)
    (model_dir / "config.json").write_text("{}", encoding="utf-8")
    messages: list[str] = []

    results = install_tts_models(
        [DEFAULT_TTS_MODEL_ID],
        tmp_path,
        include_tokenizer=False,
        progress=messages.append,
    )

    assert results[0].already_present is True
    assert "Already installed" in messages[0]


def test_install_tts_models_downloads_with_huggingface_hub(
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

    results = install_tts_models(
        [DEFAULT_TTS_MODEL_ID],
        tmp_path,
        token="secret",
        include_tokenizer=False,
    )

    assert results[0].already_present is False
    assert calls[0]["repo_id"] == DEFAULT_TTS_MODEL_ID
    assert calls[0]["repo_type"] == "model"
    assert calls[0]["token"] == "secret"


def test_install_tts_models_errors_when_hub_package_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setitem(sys.modules, "huggingface_hub", None)

    with pytest.raises(TTSModelDownloadError):
        install_tts_models([DEFAULT_TTS_MODEL_ID], tmp_path, include_tokenizer=False)
