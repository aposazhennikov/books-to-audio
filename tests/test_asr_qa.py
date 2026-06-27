from __future__ import annotations

import json
import wave
from pathlib import Path

from book_normalizer.tts.asr_qa import (
    AsrQaConfig,
    AsrTranscript,
    annotate_manifest_with_asr,
    normalize_asr_text,
    run_asr_qa,
    write_asr_diff,
)


class FakeBackend:
    name = "fake"
    model = "unit"

    def __init__(self, text: str, *, language: str = "ru", confidence: float = 0.95) -> None:
        self._text = text
        self._language = language
        self._confidence = confidence
        self.calls = 0

    def transcribe(self, audio_path: Path, *, language: str | None = None) -> AsrTranscript:
        self.calls += 1
        assert audio_path.exists()
        return AsrTranscript(
            text=self._text,
            language=self._language,
            confidence=self._confidence,
            segments=[{"start": 0.0, "end": 0.5, "text": self._text}],
            duration_seconds=0.5,
        )


def _write_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b"\x01\x00" * 2400)


def _manifest(wav_path: Path) -> dict:
    return {
        "version": 2,
        "language": "ru",
        "chapters": [
            {
                "chapter_index": 0,
                "chunks": [
                    {
                        "chunk_index": 0,
                        "voice": "narrator",
                        "voice_id": "narrator_calm",
                        "text": "Ёжик шел домой.",
                        "synthesized": True,
                        "audio_file": str(wav_path),
                    }
                ],
            }
        ],
    }


def test_normalize_asr_text_applies_yo_tolerance_and_replacements() -> None:
    text = normalize_asr_text(
        "ЁЖИК, №1!",
        replacements={"№": "номер "},
        yo_tolerance=True,
    )

    assert text == "ежик номер 1"


def test_run_asr_qa_passes_matching_chunk_and_writes_compact_manifest(tmp_path: Path) -> None:
    wav_path = tmp_path / "chunk.wav"
    _write_wav(wav_path)
    manifest = _manifest(wav_path)

    result = run_asr_qa(
        manifest,
        config=AsrQaConfig(max_wer=0.5, max_cer=0.5),
        backend=FakeBackend("ежик шел домой"),
        manifest_path=tmp_path / "chunks_manifest_v2.json",
    )
    annotate_manifest_with_asr(manifest, result, report_path=tmp_path / "asr.json")

    chunk = result.chunks[0]
    assert result.status.value == "passed"
    assert chunk.wer == 0
    block = manifest["chapters"][0]["chunks"][0]["asr_qa"]
    assert block["status"] == "passed"
    assert block["issues"] == []
    assert "transcript_text" not in block
    assert manifest["chapters"][0]["chunks"][0]["synthesized"] is True
    assert manifest["chapters"][0]["chunks"][0]["audio_file"] == str(wav_path)


def test_run_asr_qa_reports_bad_chunk_spans_and_diff(tmp_path: Path) -> None:
    wav_path = tmp_path / "chunk.wav"
    _write_wav(wav_path)

    result = run_asr_qa(
        _manifest(wav_path),
        config=AsrQaConfig(max_wer=0.1, max_cer=0.1, min_match_ratio=0.9),
        backend=FakeBackend("ежик ежик пошел в лес"),
        manifest_path=tmp_path / "chunks_manifest_v2.json",
    )
    diff_path = tmp_path / "asr.diff.txt"
    write_asr_diff(diff_path, result)

    chunk = result.chunks[0]
    issue_kinds = {issue.kind for issue in chunk.issues}
    assert result.status.value == "failed"
    assert {"high_wer", "high_cer", "missing_words", "extra_words"} <= issue_kinds
    assert chunk.missing_spans
    assert chunk.extra_spans
    assert "expected:" in diff_path.read_text(encoding="utf-8")


def test_run_asr_qa_continues_after_backend_error(tmp_path: Path) -> None:
    class ErrorBackend:
        name = "fake"
        model = "error"

        def transcribe(self, audio_path: Path, *, language: str | None = None) -> AsrTranscript:
            raise RuntimeError("backend unavailable")

    wav_path = tmp_path / "chunk.wav"
    _write_wav(wav_path)

    result = run_asr_qa(
        _manifest(wav_path),
        backend=ErrorBackend(),
        manifest_path=tmp_path / "chunks_manifest_v2.json",
    )

    assert result.status.value == "error"
    assert result.chunks[0].issues[0].kind == "asr_error"


def test_run_asr_qa_skips_unsafe_audio_path_without_transcribing(tmp_path: Path) -> None:
    backend = FakeBackend("unused")
    manifest = _manifest(tmp_path / "outside.wav")
    manifest["chapters"][0]["chunks"][0]["audio_file"] = "../outside.wav"

    result = run_asr_qa(
        manifest,
        backend=backend,
        manifest_path=tmp_path / "book" / "chunks_manifest_v2.json",
    )

    assert backend.calls == 0
    assert result.status.value == "skipped"
    assert result.chunks[0].status.value == "skipped"
    assert result.chunks[0].issues[0].kind == "unsafe_audio_file_path"


def test_asr_live_smoke_is_gated(tmp_path: Path) -> None:
    import os

    if os.environ.get("RUN_ASR_LIVE_TESTS") != "1":
        return
    from book_normalizer.tts.asr_qa import FasterWhisperBackend

    wav_path = tmp_path / "chunk.wav"
    _write_wav(wav_path)
    report = run_asr_qa(
        _manifest(wav_path),
        backend=FasterWhisperBackend("tiny"),
        manifest_path=tmp_path / "chunks_manifest_v2.json",
    ).to_dict()
    assert json.dumps(report, ensure_ascii=False)
