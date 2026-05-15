"""Integration tests for the full TTS synthesis pipeline.

These tests verify the pipeline from book text through dialogue detection,
speaker attribution, voice-annotated chunking, and audio assembly —
without requiring GPU or actual TTS model weights.
"""

from __future__ import annotations

import json
import wave
from pathlib import Path

import pytest

from book_normalizer.chunking.voice_splitter import chunk_annotated_book
from book_normalizer.dialogue.attribution import (
    HeuristicAttributor,
)
from book_normalizer.dialogue.detector import DialogueDetector
from book_normalizer.dialogue.models import SpeakerRole
from book_normalizer.models.book import Book, Chapter, Paragraph
from book_normalizer.tts.assembler import AudioAssembler
from book_normalizer.tts.synthesizer import SynthesisProgress
from book_normalizer.tts.voice_config import VoiceConfig, VoiceMethod, VoiceProfile

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_TEXT = (
    "Солнце садилось за горизонт. Вечер был тёплый и тихий.\n\n"
    "— Пойдём домой, — сказал он, оглядываясь.\n\n"
    "— Подожди ещё немного, — ответила она.\n\n"
    "— Хорошо, — согласился он. — Пять минут.\n\n"
    "Они стояли молча, наблюдая закат."
)


def _build_test_book() -> Book:
    """Build a test Book with dialogue and narration."""
    paragraphs = []
    for i, para_text in enumerate(SAMPLE_TEXT.split("\n\n")):
        paragraphs.append(
            Paragraph(
                raw_text=para_text,
                normalized_text=para_text,
                index_in_chapter=i,
            )
        )
    chapter = Chapter(title="Test Chapter", index=0, paragraphs=paragraphs)
    return Book(chapters=[chapter])


def _write_test_wav(path: Path, duration_ms: int = 100, sample_rate: int = 24000) -> None:
    """Write a minimal valid WAV file for testing."""
    n_frames = int(sample_rate * duration_ms / 1000)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"\x00\x00" * n_frames)


# ---------------------------------------------------------------------------
# Pipeline integration tests
# ---------------------------------------------------------------------------

class TestFullPipeline:
    """End-to-end pipeline: book → dialogue → attribution → chunks."""

    def test_pipeline_produces_voice_chunks(self) -> None:
        book = _build_test_book()

        detector = DialogueDetector()
        annotated = detector.detect_book(book)

        attributor = HeuristicAttributor()
        result = attributor.attribute(annotated)

        chunked = chunk_annotated_book(annotated)

        assert 0 in chunked
        chunks = chunked[0]
        assert len(chunks) > 0

        roles = {c.role for c in chunks}
        assert SpeakerRole.NARRATOR in roles
        assert SpeakerRole.MALE in roles or SpeakerRole.FEMALE in roles

        assert result.male_lines > 0 or result.female_lines > 0
        assert result.narrator_lines > 0

    def test_all_chunks_have_text(self) -> None:
        book = _build_test_book()

        detector = DialogueDetector()
        annotated = detector.detect_book(book)
        HeuristicAttributor().attribute(annotated)
        chunked = chunk_annotated_book(annotated)

        for ch_chunks in chunked.values():
            for chunk in ch_chunks:
                assert chunk.text.strip()

    def test_voice_ids_are_valid(self) -> None:
        book = _build_test_book()

        detector = DialogueDetector()
        annotated = detector.detect_book(book)
        HeuristicAttributor().attribute(annotated)
        chunked = chunk_annotated_book(annotated)

        valid_ids = {"narrator", "male", "female"}
        for ch_chunks in chunked.values():
            for chunk in ch_chunks:
                assert chunk.voice_id in valid_ids


# ---------------------------------------------------------------------------
# Voice config tests
# ---------------------------------------------------------------------------

class TestVoiceConfig:

    def test_json_round_trip(self, tmp_path: Path) -> None:
        cfg = VoiceConfig(
            narrator=VoiceProfile(
                name="narrator", method=VoiceMethod.CLONE,
                ref_audio="voices/nar.wav", ref_text="Test.",
            ),
            male=VoiceProfile(
                name="male", method=VoiceMethod.CLONE,
                ref_audio="voices/m.wav", ref_text="Test.",
            ),
            female=VoiceProfile(
                name="female", method=VoiceMethod.CLONE,
                ref_audio="voices/f.wav", ref_text="Test.",
            ),
        )
        path = tmp_path / "vc.json"
        cfg.to_json(path)
        loaded = VoiceConfig.from_json(path)
        assert loaded.narrator.ref_audio == "voices/nar.wav"
        assert loaded.male.method == VoiceMethod.CLONE

    def test_validation_errors_for_empty_clone(self) -> None:
        cfg = VoiceConfig.default_clone_config()
        errors = cfg.validate_all()
        assert len(errors) > 0

    def test_valid_custom_voice_config(self) -> None:
        cfg = VoiceConfig.default_custom_voice_config()
        errors = cfg.validate_all()
        assert errors == []

    def test_get_profile(self) -> None:
        cfg = VoiceConfig.default_custom_voice_config()
        assert cfg.get_profile("narrator").speaker == "Aiden"
        assert cfg.get_profile("female").speaker == "Serena"

    def test_get_profile_invalid(self) -> None:
        cfg = VoiceConfig()
        with pytest.raises(KeyError):
            cfg.get_profile("unknown_role")


# ---------------------------------------------------------------------------
# Synthesis progress tests
# ---------------------------------------------------------------------------

class TestSynthesisProgress:

    def test_mark_and_check(self, tmp_path: Path) -> None:
        p = SynthesisProgress(tmp_path / "progress.json")
        assert not p.is_done(0, 0)
        p.mark_done(0, 0)
        assert p.is_done(0, 0)
        assert p.completed_count == 1

    def test_persistence(self, tmp_path: Path) -> None:
        path = tmp_path / "progress.json"
        p1 = SynthesisProgress(path)
        p1.mark_done(1, 5)

        p2 = SynthesisProgress(path)
        assert p2.is_done(1, 5)


# ---------------------------------------------------------------------------
# Audio assembler tests
# ---------------------------------------------------------------------------

class TestAudioAssembler:

    def test_assemble_chapter(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"
        chunks_dir = output_dir / "audio_chunks" / "chapter_001"
        chunks_dir.mkdir(parents=True)

        _write_test_wav(chunks_dir / "chunk_001_narrator.wav")
        _write_test_wav(chunks_dir / "chunk_002_male.wav")
        _write_test_wav(chunks_dir / "chunk_003_female.wav")

        manifest = [
            {"chapter_index": 0, "chunk_index": 0, "voice_id": "narrator",
             "role": "narrator", "text_len": 10,
             "file": "audio_chunks/chapter_001/chunk_001_narrator.wav"},
            {"chapter_index": 0, "chunk_index": 1, "voice_id": "male",
             "role": "male", "text_len": 10,
             "file": "audio_chunks/chapter_001/chunk_002_male.wav"},
            {"chapter_index": 0, "chunk_index": 2, "voice_id": "female",
             "role": "female", "text_len": 10,
             "file": "audio_chunks/chapter_001/chunk_003_female.wav"},
        ]
        manifest_path = output_dir / "synthesis_manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        assembler = AudioAssembler(output_dir)
        result = assembler.assemble()

        assert "chapter_001" in result
        assert result["chapter_001"].exists()
        assert "full_book" in result
        assert result["full_book"].exists()

    def test_empty_manifest(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "empty_output"
        output_dir.mkdir()
        assembler = AudioAssembler(output_dir)
        result = assembler.assemble()
        assert result == {}

    def test_speaker_change_pause(self, tmp_path: Path) -> None:
        output_dir = tmp_path / "pause_test"
        chunks_dir = output_dir / "audio_chunks" / "chapter_001"
        chunks_dir.mkdir(parents=True)

        _write_test_wav(chunks_dir / "chunk_001_narrator.wav", duration_ms=50)
        _write_test_wav(chunks_dir / "chunk_002_male.wav", duration_ms=50)

        manifest = [
            {"chapter_index": 0, "chunk_index": 0, "voice_id": "narrator",
             "role": "narrator", "text_len": 5,
             "file": "audio_chunks/chapter_001/chunk_001_narrator.wav"},
            {"chapter_index": 0, "chunk_index": 1, "voice_id": "male",
             "role": "male", "text_len": 5,
             "file": "audio_chunks/chapter_001/chunk_002_male.wav"},
        ]
        (output_dir / "synthesis_manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )

        assembler = AudioAssembler(
            output_dir, pause_phrase_ms=100, pause_speaker_ms=500
        )
        result = assembler.assemble()

        chapter_wav = result["chapter_001"]
        with wave.open(str(chapter_wav), "rb") as w:
            n_frames = w.getnframes()

        # 50ms + 50ms audio + 500ms pause ≈ 600ms → ~14400 frames at 24kHz.
        expected_min = int(24000 * 0.55)
        assert n_frames >= expected_min


# ---------------------------------------------------------------------------
# CLI init-voices test
# ---------------------------------------------------------------------------

class TestCliInitVoices:

    def test_init_voices_creates_config(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from book_normalizer.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["init-voices", "--out", str(tmp_path), "--preset", "clone"])
        assert result.exit_code == 0
        assert (tmp_path / "voice_config.json").exists()

    def test_init_voices_custom_preset(self, tmp_path: Path) -> None:
        from click.testing import CliRunner

        from book_normalizer.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["init-voices", "--out", str(tmp_path), "--preset", "custom"])
        assert result.exit_code == 0
        data = json.loads((tmp_path / "voice_config.json").read_text(encoding="utf-8"))
        assert data["narrator"]["speaker"] == "Aiden"
