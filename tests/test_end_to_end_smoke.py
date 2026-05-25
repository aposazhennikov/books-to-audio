"""Small drift-catching smoke test for the recommended v2 pipeline shape."""

from __future__ import annotations

import json
import wave
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from click.testing import CliRunner

from book_normalizer.cli import _build_output_dir, main
from book_normalizer.tts.manifest_assembly import assemble_from_manifest


def _write_wav(path: Path, frames: int = 1200, sample_rate: int = 24000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x10\x00" * frames)


def _load_export_chunks_main():
    script = Path("scripts/export_chunks.py").resolve()
    spec = spec_from_file_location("test_export_chunks_smoke", script)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main


def test_txt_to_v2_manifest_to_fake_audio_to_assembled_chapter(tmp_path: Path) -> None:
    book_path = tmp_path / "mini.txt"
    book_path.write_text(
        (
            "Глава 1\n\n"
            "Иван вошёл в комнату и остановился у окна. За стеклом шумел дождь.\n\n"
            "— Привет, Мария, — сказал Иван.\n\n"
            "— Здравствуй, Иван, — ответила Мария.\n\n"
            "Она улыбнулась и поставила чайник на стол."
        ),
        encoding="utf-8",
    )
    out_root = tmp_path / "output"

    result = CliRunner().invoke(
        main,
        [
            "process",
            str(book_path),
            "--out",
            str(out_root),
            "--skip-stress",
            "--skip-punctuation-review",
            "--skip-spellcheck",
        ],
    )

    assert result.exit_code == 0, result.output
    book_dir = _build_output_dir(book_path, out_root).resolve()
    assert (book_dir / "001_chapter_01.txt").exists()

    export_chunks_main = _load_export_chunks_main()
    export_chunks_main([
        "--book-dir",
        str(book_dir),
        "--mode",
        "heuristic",
        "--max-chunk-chars",
        "80",
    ])

    manifest_path = book_dir / "chunks_manifest_v2.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    all_chunks = [
        chunk
        for chapter in manifest["chapters"]
        for chunk in chapter["chunks"]
    ]
    combined_text = "\n".join(chunk["text"] for chunk in all_chunks)

    assert manifest["chunker"] == "heuristic"
    assert len(all_chunks) >= 2
    assert "Иван вошёл" in combined_text
    assert "Привет" in combined_text
    assert {chunk["voice"] for chunk in all_chunks} & {"narrator", "male", "female"}

    for chunk in all_chunks:
        audio_path = (
            book_dir
            / "audio_chunks"
            / f"chapter_{chunk['chapter_index'] + 1:03d}"
            / f"chunk_{chunk['chunk_index'] + 1:03d}.wav"
        )
        _write_wav(audio_path)
        chunk["synthesized"] = True
        chunk["audio_file"] = str(audio_path)

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    results = assemble_from_manifest(manifest, book_dir, pause_same_voice_ms=0, pause_voice_change_ms=0)

    assert results[0].chunks == len(all_chunks)
    assert (book_dir / "chapter_001.wav").exists()
