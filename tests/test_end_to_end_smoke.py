"""Small drift-catching smoke test for the recommended v2 pipeline shape."""

from __future__ import annotations

import json
import wave
from pathlib import Path

from click.testing import CliRunner

from book_normalizer.chunking.manifest import chunks_to_v2_manifest
from book_normalizer.cli import _build_output_dir, main
from book_normalizer.tts.manifest_assembly import assemble_from_manifest


def _write_wav(path: Path, frames: int = 1200, sample_rate: int = 24000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x10\x00" * frames)


def test_txt_to_v2_manifest_to_fake_audio_to_assembled_chapter(tmp_path: Path) -> None:
    book_path = tmp_path / "mini.txt"
    book_path.write_text(
        "Глава 1\n\nИван вошёл в комнату. — Привет, Мария.\n\nОна улыбнулась.",
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

    chunks = [
        {
            "chapter_index": 0,
            "chunk_index": 0,
            "role": "narrator",
            "voice_id": "narrator_calm",
            "intonation": "calm",
            "text": "Иван вошёл в комнату.",
        },
        {
            "chapter_index": 0,
            "chunk_index": 1,
            "role": "male",
            "voice_id": "male_young",
            "intonation": "neutral",
            "text": "— Привет, Мария.",
        },
    ]
    manifest = chunks_to_v2_manifest(chunks, book_title="mini", chunker="smoke", max_chunk_chars=400)
    for chunk in manifest["chapters"][0]["chunks"]:
        audio_path = book_dir / "audio_chunks" / "chapter_001" / f"chunk_{chunk['chunk_index'] + 1:03d}.wav"
        _write_wav(audio_path)
        chunk["synthesized"] = True
        chunk["audio_file"] = str(audio_path)

    manifest_path = book_dir / "chunks_manifest_v2.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    results = assemble_from_manifest(manifest, book_dir, pause_same_voice_ms=0, pause_voice_change_ms=0)

    assert results[0].chunks == 2
    assert (book_dir / "chapter_001.wav").exists()
