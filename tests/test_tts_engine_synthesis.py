from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from book_normalizer.tts.engine_synthesis import preflight_engine_command, synthesize_engine_manifest


def test_local_engine_synthesis_runs_command_and_updates_manifest(
    monkeypatch,
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest = {
        "version": 2,
        "language": "en",
        "chapters": [
            {
                "chapter_index": 0,
                "chunks": [
                    {
                        "chapter_index": 0,
                        "chunk_index": 0,
                        "voice_label": "narrator",
                        "voice_id": "narrator_calm",
                        "text": "Hello from F5.",
                        "synthesized": False,
                    }
                ],
            }
        ],
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setenv(
        "BOOKS_TO_AUDIO_TTS_F5_TTS_COMMAND",
        "fake-f5 --gen_file {text_file} --output_file {output_file}",
    )
    calls: list[list[str]] = []

    def fake_run(argv, **_kwargs):  # noqa: ANN001
        calls.append(argv)
        output_path = Path(argv[argv.index("--output_file") + 1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"RIFF$\x00\x00\x00WAVEfmt ")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("book_normalizer.tts.engine_synthesis.subprocess.run", fake_run)

    def fake_export(source: Path, output=None, **_kwargs):  # noqa: ANN001, ANN202
        target = output or source.with_suffix(".MP3")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"mp3")
        return target

    monkeypatch.setattr("book_normalizer.tts.engine_synthesis.export_compatible_mp3", fake_export)

    summary = synthesize_engine_manifest(
        manifest=manifest,
        manifest_path=manifest_path,
        engine_id="f5-tts",
        out_dir=tmp_path / "audio_chunks",
        models_dir=tmp_path / "models",
    )

    saved = json.loads(manifest_path.read_text(encoding="utf-8"))
    chunk = saved["chapters"][0]["chunks"][0]
    assert summary.synthesized == 1
    assert calls and calls[0][0] == "fake-f5"
    assert chunk["synthesized"] is True
    assert chunk["tts_engine"] == "f5-tts"
    assert (tmp_path / chunk["audio_file"]).exists()
    assert chunk["compatible_audio_file"].endswith(".MP3")
    assert (tmp_path / chunk["compatible_audio_file"]).exists()


def test_local_engine_preflight_reports_structured_checks(
    monkeypatch,
    tmp_path: Path,
) -> None:
    model_dir = tmp_path / "models"
    model_path = model_dir / "audio_encoders" / "F5-TTS"
    model_path.mkdir(parents=True)
    output_dir = tmp_path / "out"
    reference_audio = tmp_path / "voice.wav"
    reference_audio.write_bytes(b"RIFF$\x00\x00\x00WAVEfmt ")
    clone_config = tmp_path / "clone.json"
    clone_config.write_text(
        json.dumps({"__all__": {"ref_audio": str(reference_audio), "ref_text": "hello"}}),
        encoding="utf-8",
    )
    ffmpeg = tmp_path / "ffmpeg"
    ffmpeg.write_text("", encoding="utf-8")
    monkeypatch.setenv(
        "BOOKS_TO_AUDIO_TTS_F5_TTS_COMMAND",
        "python -m f5 --gen_file {text_file} --output_file {output_file} "
        "--model {model_path} --ref_audio {ref_audio} --ref_text {ref_text}",
    )
    monkeypatch.setattr("book_normalizer.tts.engine_synthesis.shutil.which", lambda exe: f"/bin/{exe}")
    monkeypatch.setattr(
        "book_normalizer.tts.engine_synthesis.configured_ffmpeg_bin",
        lambda: ffmpeg,
    )

    preflight = preflight_engine_command(
        "f5-tts",
        model_dir,
        output_dir=output_dir,
        clone_config_path=clone_config,
    )

    checks = {check.name: check for check in preflight.checks}
    assert preflight.ok
    assert checks["executable"].ok
    assert checks["template"].ok
    assert checks["model"].ok
    assert checks["output"].ok
    assert checks["reference"].ok
    assert checks["ffmpeg"].ok


def test_local_engine_preflight_fails_for_missing_model_and_ffmpeg(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(
        "BOOKS_TO_AUDIO_TTS_F5_TTS_COMMAND",
        "missing-f5 --gen_file {text_file} --output_file {output_file}",
    )
    monkeypatch.setattr("book_normalizer.tts.engine_synthesis.shutil.which", lambda _exe: None)
    monkeypatch.setattr(
        "book_normalizer.tts.engine_synthesis.configured_ffmpeg_bin",
        lambda: tmp_path / "missing-ffmpeg",
    )

    preflight = preflight_engine_command(
        "f5-tts",
        tmp_path / "models",
        output_dir=tmp_path / "out",
    )

    checks = {check.name: check for check in preflight.checks}
    assert not preflight.ok
    assert not checks["executable"].ok
    assert not checks["model"].ok
    assert not checks["ffmpeg"].ok


def test_local_engine_synthesis_returns_cancelled_without_running_command(
    monkeypatch,
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest = {
        "version": 2,
        "language": "en",
        "chapters": [
            {
                "chapter_index": 0,
                "chunks": [
                    {
                        "chapter_index": 0,
                        "chunk_index": 0,
                        "voice_label": "narrator",
                        "voice_id": "narrator_calm",
                        "text": "Hello from F5.",
                        "synthesized": False,
                    }
                ],
            }
        ],
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setenv(
        "BOOKS_TO_AUDIO_TTS_F5_TTS_COMMAND",
        "fake-f5 --gen_file {text_file} --output_file {output_file}",
    )
    calls: list[list[str]] = []

    def fake_run(argv, **_kwargs):  # noqa: ANN001
        calls.append(argv)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("book_normalizer.tts.engine_synthesis.subprocess.run", fake_run)

    summary = synthesize_engine_manifest(
        manifest=manifest,
        manifest_path=manifest_path,
        engine_id="f5-tts",
        out_dir=tmp_path / "audio_chunks",
        models_dir=tmp_path / "models",
        cancel_requested=lambda: True,
    )

    saved = json.loads(manifest_path.read_text(encoding="utf-8"))
    chunk = saved["chapters"][0]["chunks"][0]
    assert summary.status == "cancelled"
    assert summary.synthesized == 0
    assert summary.failed == 0
    assert calls == []
    assert chunk["synthesized"] is False
