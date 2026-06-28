from __future__ import annotations

from pathlib import Path

from book_normalizer.tts.llm_audio_qa import (
    LlmAudioQaConfig,
    LlmAudioQaIssue,
    LlmAudioQaReview,
    annotate_manifest_with_llm_audio_qa,
    run_llm_audio_qa,
)


class _FakeBackend:
    name = "fake-llm-audio"
    model = "fake-model"

    def __init__(self, review: LlmAudioQaReview) -> None:
        self.review = review
        self.calls: list[tuple[Path, str]] = []

    def review_chunk(self, audio_path: Path, *, expected_text: str, language: str) -> LlmAudioQaReview:
        self.calls.append((audio_path, expected_text))
        assert language == "ru"
        return self.review


def _manifest(audio_path: Path) -> dict:
    return {
        "version": 2,
        "language": "ru",
        "chapters": [
            {
                "chapter_index": 0,
                "chunks": [
                    {
                        "chapter_index": 0,
                        "chunk_index": 0,
                        "voice_label": "narrator",
                        "text": "Привет, мир.",
                        "synthesized": True,
                        "audio_file": str(audio_path),
                        "last_generation_options": {
                            "temperature": 0.55,
                            "top_p": 0.65,
                            "repetition_penalty": 1.08,
                            "speech_rate": 1.0,
                        },
                    }
                ],
            }
        ],
    }


def test_llm_audio_qa_records_passed_review(tmp_path: Path) -> None:
    audio_path = tmp_path / "chunk.wav"
    audio_path.write_bytes(b"fake wav")
    manifest = _manifest(audio_path)
    backend = _FakeBackend(LlmAudioQaReview(status="passed", score=94, review="Звучит естественно."))

    result = run_llm_audio_qa(
        manifest,
        config=LlmAudioQaConfig(model="fake-model"),
        backend=backend,
        manifest_path=tmp_path / "chunks_manifest_v2.json",
    )
    annotate_manifest_with_llm_audio_qa(manifest, result, report_path=tmp_path / "llm_audio.json")

    block = manifest["chapters"][0]["chunks"][0]["llm_audio_qa"]
    assert result.status == "passed"
    assert block["status"] == "passed"
    assert block["score"] == 94
    assert "Звучит естественно" in block["review"]
    assert backend.calls == [(audio_path, "Привет, мир.")]


def test_llm_audio_qa_failed_review_resets_chunk_and_sets_retry_options(tmp_path: Path) -> None:
    audio_path = tmp_path / "chunk.wav"
    audio_path.write_bytes(b"fake wav")
    manifest = _manifest(audio_path)
    review = LlmAudioQaReview(
        status="failed",
        score=47,
        review="Паузы неестественные, речь слишком быстрая.",
        issues=[
            LlmAudioQaIssue(
                "unnatural_pause",
                "resynthesize",
                "Пауза перед второй фразой ломает интонацию.",
                start_seconds=1.2,
                end_seconds=1.8,
            )
        ],
        recommendations={
            "temperature_delta": -0.08,
            "repetition_penalty_delta": 0.12,
            "speech_rate_delta": -0.04,
        },
    )

    result = run_llm_audio_qa(
        manifest,
        config=LlmAudioQaConfig(model="fake-model"),
        backend=_FakeBackend(review),
        manifest_path=tmp_path / "chunks_manifest_v2.json",
    )
    annotate_manifest_with_llm_audio_qa(
        manifest,
        result,
        reset_bad_chunks=True,
        max_resynthesis_attempts=2,
    )

    chunk = manifest["chapters"][0]["chunks"][0]
    assert result.status == "failed"
    assert chunk["failed"] is True
    assert chunk["synthesized"] is False
    assert chunk["audio_file"] is None
    assert chunk["resynthesis_attempt"] == 1
    assert chunk["resynthesis_reason"] == "llm_audio_qa: unnatural_pause"
    assert str(audio_path) in chunk["rejected_audio_files"]
    assert chunk["next_generation_options"]["temperature"] == 0.47
    assert chunk["next_generation_options"]["repetition_penalty"] == 1.2
    assert chunk["next_generation_options"]["speech_rate"] == 0.96
