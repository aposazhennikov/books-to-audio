from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from book_normalizer.tts.engine_synthesis import synthesize_engine_manifest


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

