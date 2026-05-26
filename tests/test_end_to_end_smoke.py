"""Small drift-catching smoke test for the recommended v2 pipeline shape."""

from __future__ import annotations

import json
import wave
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from click.testing import CliRunner

from book_normalizer.chunking.manifest_v2 import chunks_to_manifest
from book_normalizer.chunking.role_inventory import build_role_inventory
from book_normalizer.chunking.voice_splitter import build_chunks_from_segments
from book_normalizer.cli import _build_output_dir, main
from book_normalizer.tts.audio_qa import run_audio_qa
from book_normalizer.tts.manifest_assembly import assemble_from_manifest


def _write_wav(path: Path, frames: int = 1200, sample_rate: int = 24000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x10\x00" * frames)


def _write_varied_wav(path: Path, frames: int = 24000, sample_rate: int = 24000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        payload = bytearray()
        for index in range(frames):
            sample = ((index % 400) - 200) * 10
            payload.extend(sample.to_bytes(2, "little", signed=True))
        wav.writeframes(bytes(payload))


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


def test_role_chunks_voice_assignment_audio_qa_and_assembly_skip_deleted_text(
    tmp_path: Path,
) -> None:
    segments = [
        {
            "chapter_index": 0,
            "segment_index": 0,
            "role": "narrator",
            "voice_id": "narrator_calm",
            "intonation": "calm",
            "section_kind": "chapter_title",
            "text": "Глава первая.",
            "language": "ru",
            "pause_after_ms": 500,
            "boundary_after": "paragraph",
        },
        {
            "chapter_index": 0,
            "segment_index": 1,
            "role": "narrator",
            "voice_id": "narrator_calm",
            "intonation": "calm",
            "text": "Маргарита вошла в комнату.",
            "language": "ru",
            "pause_after_ms": 300,
            "boundary_after": "paragraph",
        },
        {
            "chapter_index": 0,
            "segment_index": 2,
            "role": "female",
            "voice_id": "female_warm",
            "speaker": "Маргарита",
            "character_description": "Смелая и напряженная.",
            "emotion": "fearful",
            "intonation": "fearful",
            "text": "Кто здесь?",
            "language": "ru",
            "is_dialogue": True,
        },
        {
            "chapter_index": 0,
            "segment_index": 3,
            "role": "male",
            "voice_id": "male_young",
            "speaker": "Мастер",
            "character_description": "Усталый, мягкий голос.",
            "emotion": "sad",
            "intonation": "sad",
            "text": "Это я.",
            "language": "ru",
            "is_dialogue": True,
            "pause_after_ms": 800,
            "boundary_after": "speaker",
        },
        {
            "chapter_index": 0,
            "segment_index": 4,
            "role": "narrator",
            "voice_id": "narrator_calm",
            "intonation": "calm",
            "text": "Книга подготовлена агентством и не должна звучать.",
            "language": "ru",
            "deleted": True,
            "excluded_from_tts": True,
        },
    ]
    inventory = build_role_inventory(segments, language="ru")

    assert inventory["total_direct_speech"] == 2
    assert [role["display_name"] for role in inventory["roles"][:2]] == [
        "Маргарита",
        "Мастер",
    ]

    active_segments = [
        segment for segment in segments
        if not segment.get("deleted") and not segment.get("excluded_from_tts")
    ]
    chunks = build_chunks_from_segments(active_segments, max_chunk_chars=80)
    manifest_model = chunks_to_manifest(
        chunks,
        book_title="Audiobook E2E",
        language="ru",
        chunker="llm-smart",
        model="hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M",
        max_chunk_chars=80,
    )
    manifest = manifest_model.to_record()

    stale_deleted_audio = tmp_path / "audio_chunks" / "chapter_001" / "chunk_999_deleted.wav"
    _write_varied_wav(stale_deleted_audio)
    manifest["chapters"][0]["chunks"].append(
        {
            "chapter_index": 0,
            "chunk_index": 99,
            "voice_label": "narrator",
            "voice": "narrator",
            "voice_id": "narrator_calm",
            "text": "Книга подготовлена агентством и не должна звучать.",
            "synthesized": True,
            "audio_file": str(stale_deleted_audio),
            "deleted": True,
            "excluded_from_tts": True,
        }
    )

    for chunk in manifest["chapters"][0]["chunks"]:
        if chunk.get("excluded_from_tts"):
            continue
        audio_path = (
            tmp_path
            / "audio_chunks"
            / "chapter_001"
            / f"chunk_{chunk['chunk_index'] + 1:03d}_{chunk['voice_label']}.wav"
        )
        _write_varied_wav(audio_path)
        chunk["synthesized"] = True
        chunk["audio_file"] = str(audio_path)

    qa = run_audio_qa(manifest)
    results = assemble_from_manifest(
        manifest,
        tmp_path,
        pause_same_voice_ms=0,
        pause_voice_change_ms=0,
    )

    assert qa.total_chunks == len(chunks)
    assert qa.synthesized_chunks == len(chunks)
    assert not any(issue.severity == "error" for issue in qa.issues)
    assert results[0].chunks == len(chunks)
    assert stale_deleted_audio.exists()
    assembled_chunks = [
        chunk for chunk in manifest["chapters"][0]["chunks"]
        if not chunk.get("excluded_from_tts")
    ]
    expected_pause_frames = sum(
        int(chunk.get("pause_after_ms") or 0) * 24
        for chunk in assembled_chunks[:-1]
    )
    with wave.open(str(tmp_path / "chapter_001.wav"), "rb") as assembled:
        assert assembled.getnframes() == len(chunks) * 24000 + expected_pause_frames
