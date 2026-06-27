from __future__ import annotations

from pathlib import Path

from book_normalizer.tts.perceptual_qa import (
    PerceptualPrediction,
    annotate_manifest_with_perceptual,
    run_perceptual_qa,
)


class _FakeBackend:
    def __init__(self, name: str, scores: dict[str, float]) -> None:
        self.name = name
        self._scores = scores

    def predict(self, audio_path: Path) -> PerceptualPrediction:
        assert audio_path.exists()
        return PerceptualPrediction(backend=self.name, scores=self._scores)


def _manifest(audio_path: Path) -> dict:
    return {
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
                        "text": "hello world",
                        "synthesized": True,
                        "audio_file": str(audio_path),
                    }
                ],
            }
        ],
    }


def test_perceptual_qa_records_nisqa_and_mosnet_scores(tmp_path: Path) -> None:
    audio_path = tmp_path / "chunk.wav"
    audio_path.write_bytes(b"fake wav")
    manifest = _manifest(audio_path)

    result = run_perceptual_qa(
        manifest,
        manifest_path=tmp_path / "chunks_manifest_v2.json",
        backends=[
            _FakeBackend(
                "nisqa-v2",
                {
                    "mos": 4.2,
                    "noisiness": 4.0,
                    "discontinuity": 3.9,
                    "coloration": 3.8,
                    "loudness": 4.1,
                },
            ),
            _FakeBackend("mosnet", {"mos": 3.7}),
        ],
    )
    annotate_manifest_with_perceptual(manifest, result, report_path=tmp_path / "perceptual.json")

    chunk = result.chunks[0]
    block = manifest["chapters"][0]["chunks"][0]["perceptual_qa"]
    assert result.status == "passed"
    assert chunk.scores["nisqa-v2"]["mos"] == 4.2
    assert chunk.scores["mosnet"]["mos"] == 3.7
    assert block["status"] == "passed"
    assert block["scores"]["nisqa-v2"]["discontinuity"] == 3.9


def test_perceptual_qa_low_mos_resets_bad_chunk(tmp_path: Path) -> None:
    audio_path = tmp_path / "chunk.wav"
    audio_path.write_bytes(b"fake wav")
    manifest = _manifest(audio_path)

    result = run_perceptual_qa(
        manifest,
        manifest_path=tmp_path / "chunks_manifest_v2.json",
        backends=[_FakeBackend("nisqa-v2", {"mos": 2.1, "noisiness": 4.0})],
    )
    annotate_manifest_with_perceptual(
        manifest,
        result,
        reset_bad_chunks=True,
        max_resynthesis_attempts=2,
    )

    chunk = manifest["chapters"][0]["chunks"][0]
    assert result.status == "failed"
    assert "low_mos" in chunk["perceptual_qa"]["issues"]
    assert chunk["failed"] is True
    assert chunk["synthesized"] is False
    assert chunk["audio_file"] is None
    assert chunk["resynthesis_attempt"] == 1
    assert str(audio_path) in chunk["rejected_audio_files"]


def test_perceptual_backend_errors_are_skipped_not_failed(tmp_path: Path) -> None:
    class _BrokenBackend:
        name = "mosnet"

        def predict(self, _audio_path: Path) -> PerceptualPrediction:
            raise RuntimeError("backend unavailable")

    audio_path = tmp_path / "chunk.wav"
    audio_path.write_bytes(b"fake wav")

    result = run_perceptual_qa(
        _manifest(audio_path),
        manifest_path=tmp_path / "chunks_manifest_v2.json",
        backends=[_BrokenBackend()],
    )

    assert result.status == "skipped"
    assert result.chunks[0].issues[0].kind == "backend_error"
