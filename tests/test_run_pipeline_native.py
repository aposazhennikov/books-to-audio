from __future__ import annotations

import importlib.util
import json
import wave
from pathlib import Path
from types import ModuleType

import pytest


def _load_run_pipeline() -> ModuleType:
    script = Path("scripts/run_pipeline.py").resolve()
    spec = importlib.util.spec_from_file_location("test_run_pipeline_native_module", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_export_chunks() -> ModuleType:
    script = Path("scripts/export_chunks.py").resolve()
    spec = importlib.util.spec_from_file_location("test_export_chunks_native_module", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_synthesize_comfyui() -> ModuleType:
    script = Path("scripts/synthesize_comfyui.py").resolve()
    spec = importlib.util.spec_from_file_location("test_synthesize_comfyui_module", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_pipeline_stages_do_not_spawn_child_python() -> None:
    source = Path("scripts/run_pipeline.py").read_text(encoding="utf-8")

    assert "import subprocess" not in source
    assert "subprocess.run" not in source
    assert "sys.executable" not in source
    assert "wsl" not in source.lower()


def test_stage1_normalize_invokes_click_command_in_process(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pipeline = _load_run_pipeline()
    book_path = tmp_path / "My Book.txt"
    output_root = tmp_path / "out"
    book_path.write_text("Hello.", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_process_main(**kwargs):  # noqa: ANN001
        captured.update(kwargs)
        book_dir = pipeline.find_book_dir(output_root, book_path)
        book_dir.mkdir(parents=True)
        (book_dir / "001_chapter_01.txt").write_text("Hello.", encoding="utf-8")

    monkeypatch.setattr(pipeline.process_command, "main", fake_process_main)

    result = pipeline.run_stage1_normalize(book_path, output_root, "force")

    assert result == pipeline.find_book_dir(output_root, book_path)
    assert captured["args"] == [
        str(book_path),
        "--out",
        str(output_root),
        "--ocr-mode",
        "force",
        "-v",
    ]
    assert captured["prog_name"] == "normalize-book process"
    assert captured["standalone_mode"] is False


def test_stage3_passes_language_and_review_report_to_smart_segmenter(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pipeline = _load_run_pipeline()
    book_dir = tmp_path / "book"
    book_dir.mkdir()
    (book_dir / "001_chapter_01.txt").write_text("Salom. \"Kim bor?\"", encoding="utf-8")
    captured: dict[str, object] = {}

    class _FakeSegmenter:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

        def segment_book(self, book):  # noqa: ANN001
            assert book.chapters[0].index == 0
            assert "Salom" in book.chapters[0].paragraphs[0].raw_text
            return [
                {
                    "chapter_index": 0,
                    "segment_index": 0,
                    "language": "uz",
                    "role": "narrator",
                    "voice_id": "narrator_calm",
                    "intonation": "calm",
                    "section_kind": "narration",
                    "text": "Salom.",
                }
            ]

    import book_normalizer.chunking.llm_segmenter as llm_segmenter

    monkeypatch.setattr(llm_segmenter, "LlmVoiceSegmenter", _FakeSegmenter)

    manifest_path = pipeline.run_stage3_llm_chunking(
        book_dir,
        "http://127.0.0.1:11434",
        "model",
        "uz",
        chapter_filter=None,
        llm_max_retries=1,
        max_chunk_chars=400,
    )

    assert manifest_path == book_dir / "chunks_manifest_v2.json"
    assert captured["language"] == "uz"
    assert captured["review_report_path"] == book_dir / "llm_chunking_review_report.json"
    assert captured["max_segment_chars"] == 400
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["chunker"] == "llm-smart-segments"
    assert manifest["chapters"][0]["chunks"][0]["speaker"] == ""


def test_export_chunks_llm_uses_smart_segmenter_and_repairs_dialogue(
    tmp_path: Path,
    monkeypatch,
) -> None:
    export_chunks = _load_export_chunks()
    book_dir = tmp_path / "book"
    book_dir.mkdir()
    text = (
        "- Что это? - спросил он, наконец, дрогнувшим голосом. - "
        "Моя невеста, - гордо ответил я тёмному божеству."
    )
    (book_dir / "001_chapter_01.txt").write_text(text, encoding="utf-8")
    captured: dict[str, object] = {}

    class _FakeSegmenter:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

        def segment_book(self, book):  # noqa: ANN001
            return [
                {
                    "chapter_index": book.chapters[0].index,
                    "segment_index": 0,
                    "language": "ru",
                    "role": "narrator",
                    "voice_id": "narrator_calm",
                    "intonation": "calm",
                    "section_kind": "narration",
                    "text": text,
                }
            ]

    import book_normalizer.chunking.llm_segmenter as llm_segmenter

    monkeypatch.setattr(llm_segmenter, "LlmVoiceSegmenter", _FakeSegmenter)

    export_chunks.main([
        "--book-dir",
        str(book_dir),
        "--mode",
        "llm",
        "--max-chunk-chars",
        "400",
    ])

    manifest = json.loads((book_dir / "chunks_manifest_v2.json").read_text(encoding="utf-8"))
    chunks = manifest["chapters"][0]["chunks"]
    assert captured["max_segment_chars"] == 400
    assert manifest["chunker"] == "llm-smart-segments"
    assert [chunk["text"] for chunk in chunks] == [
        "- Что это?",
        "- спросил он, наконец, дрогнувшим голосом.",
        "- Моя невеста,",
        "- гордо ответил я тёмному божеству.",
    ]
    assert [chunk["voice"] for chunk in chunks] == ["male", "narrator", "male", "narrator"]


def test_export_chunks_llm_rejects_mixed_dialogue_manifest(
    tmp_path: Path,
    monkeypatch,
) -> None:
    export_chunks = _load_export_chunks()
    book_dir = tmp_path / "book"
    book_dir.mkdir()
    (book_dir / "001_chapter_01.txt").write_text("Hello.", encoding="utf-8")

    class _FakeSegmenter:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def segment_book(self, book):  # noqa: ANN001
            return [
                {
                    "chapter_index": book.chapters[0].index,
                    "segment_index": 0,
                    "language": "ru",
                    "role": "male",
                    "voice_id": "male_young",
                    "intonation": "calm",
                    "section_kind": "dialogue",
                    "text": "unused",
                }
            ]

    def fake_build_chunks_from_segments(_segments, *, max_chunk_chars):  # noqa: ANN001, ARG001
        return [
            {
                "chapter_index": 0,
                "chunk_index": 0,
                "language": "ru",
                "role": "male",
                "voice_id": "male_young",
                "section_kind": "dialogue",
                "text": "- Что случилось? - спросил он.",
            }
        ]

    import book_normalizer.chunking.llm_segmenter as llm_segmenter
    import book_normalizer.chunking.voice_splitter as voice_splitter

    monkeypatch.setattr(llm_segmenter, "LlmVoiceSegmenter", _FakeSegmenter)
    monkeypatch.setattr(voice_splitter, "build_chunks_from_segments", fake_build_chunks_from_segments)

    with pytest.raises(ValueError, match="Dialogue chunk boundary audit failed"):
        export_chunks.main([
            "--book-dir",
            str(book_dir),
            "--mode",
            "llm",
        ])

    assert not (book_dir / "chunks_manifest_v2.json").exists()


def test_stage3_llm_rejects_mixed_dialogue_manifest(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pipeline = _load_run_pipeline()
    book_dir = tmp_path / "book"
    book_dir.mkdir()
    (book_dir / "001_chapter_01.txt").write_text("Hello.", encoding="utf-8")

    class _FakeSegmenter:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def segment_book(self, book):  # noqa: ANN001
            return [
                {
                    "chapter_index": book.chapters[0].index,
                    "segment_index": 0,
                    "language": "ru",
                    "role": "male",
                    "voice_id": "male_young",
                    "intonation": "calm",
                    "section_kind": "dialogue",
                    "text": "unused",
                }
            ]

    def fake_build_chunks_from_segments(_segments, *, max_chunk_chars):  # noqa: ANN001, ARG001
        return [
            {
                "chapter_index": 0,
                "chunk_index": 0,
                "language": "ru",
                "role": "male",
                "voice_id": "male_young",
                "section_kind": "dialogue",
                "text": "- Что случилось? - спросил он.",
            }
        ]

    import book_normalizer.chunking.llm_segmenter as llm_segmenter
    import book_normalizer.chunking.voice_splitter as voice_splitter

    monkeypatch.setattr(llm_segmenter, "LlmVoiceSegmenter", _FakeSegmenter)
    monkeypatch.setattr(voice_splitter, "build_chunks_from_segments", fake_build_chunks_from_segments)

    with pytest.raises(ValueError, match="Dialogue chunk boundary audit failed"):
        pipeline.run_stage3_llm_chunking(
            book_dir,
            "http://127.0.0.1:11434",
            "model",
            "ru",
            chapter_filter=None,
            llm_max_retries=1,
            max_chunk_chars=400,
        )

    assert not (book_dir / "chunks_manifest_v2.json").exists()


def test_stage3_heuristic_invokes_native_exporter_and_filters_chapter(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pipeline = _load_run_pipeline()
    book_dir = tmp_path / "book"
    book_dir.mkdir()
    captured: list[tuple[str, list[str]]] = []

    def fake_run_script_main(script_name: str, argv: list[str]) -> None:
        captured.append((script_name, argv))
        manifest_path = book_dir / "chunks_manifest_v2.json"
        manifest_path.write_text(
            """
{
  "version": 2,
  "book_title": "book",
  "chunker": "heuristic",
  "chapters": [
    {"chapter_index": 0, "chunks": [{"chunk_index": 0, "text": "One."}]},
    {"chapter_index": 1, "chunks": [{"chunk_index": 0, "text": "Two."}]}
  ]
}
""".strip(),
            encoding="utf-8",
        )

    monkeypatch.setattr(pipeline, "_run_script_main", fake_run_script_main)

    manifest_path = pipeline.run_stage3_heuristic_chunking(
        book_dir,
        max_chunk_chars=120,
        chapter_filter=2,
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert captured == [
        (
            "export_chunks.py",
            [
                "--book-dir",
                str(book_dir),
                "--mode",
                "heuristic",
                "--max-chunk-chars",
                "120",
            ],
        )
    ]
    assert [chapter["chapter_index"] for chapter in manifest["chapters"]] == [1]


def test_synthesis_and_assembly_stages_invoke_script_mains_in_process(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pipeline = _load_run_pipeline()
    captured: list[tuple[str, list[str]]] = []

    def fake_run_script_main(script_name: str, argv: list[str]) -> None:
        captured.append((script_name, argv))

    monkeypatch.setattr(pipeline, "_run_script_main", fake_run_script_main)

    manifest_path = tmp_path / "chunks_manifest_v2.json"
    audio_dir = tmp_path / "audio_chunks"
    workflow_path = tmp_path / "workflow.json"

    pipeline.run_stage4_synthesize(
        manifest_path,
        audio_dir,
        "http://127.0.0.1:8188",
        str(workflow_path),
        chapter_filter=2,
    )
    pipeline.run_stage5_assemble(manifest_path, tmp_path, chapter_filter=None)

    assert captured == [
        (
            "synthesize_comfyui.py",
            [
                "--chunks-json",
                str(manifest_path),
                "--out",
                str(audio_dir),
                "--workflow",
                str(workflow_path),
                "--comfyui-url",
                "http://127.0.0.1:8188",
                "--chapter",
                "2",
            ],
        ),
        (
            "assemble_chapter.py",
            [
                "--manifest",
                str(manifest_path),
                "--out",
                str(tmp_path),
                "--all",
            ],
        ),
    ]


def test_pipeline_accepts_direct_omni_audio_qa_without_endpoint(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pipeline = _load_run_pipeline()
    book_path = tmp_path / "book.txt"
    book_path.write_text("Hello.", encoding="utf-8")
    output_root = tmp_path / "out"
    book_dir = output_root / "book_txt"
    manifest_path = book_dir / "chunks_manifest_v2.json"
    captured: dict[str, object] = {}

    def fake_stage1(_book_path: Path, _output_root: Path, _ocr_mode: str) -> Path:
        book_dir.mkdir(parents=True)
        manifest_path.write_text('{"version": 2, "chapters": []}', encoding="utf-8")
        return book_dir

    def fake_stage3(
        _book_dir: Path,
        _endpoint: str,
        _model: str,
        _language: str,
        _chapter_filter: int | None,
        _llm_max_retries: int,
        _max_chunk_chars: int,
    ) -> Path:
        return manifest_path

    def fake_stage4(
        _manifest_path: Path,
        _audio_dir: Path,
        _comfyui_url: str,
        _workflow_path: str,
        _chapter_filter: int | None,
        **kwargs: object,
    ) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(pipeline, "run_stage1_normalize", fake_stage1)
    monkeypatch.setattr(pipeline, "run_stage3_llm_chunking", fake_stage3)
    monkeypatch.setattr(pipeline, "run_stage4_synthesize", fake_stage4)

    pipeline.main(
        [
            "--book",
            str(book_path),
            "--out",
            str(output_root),
            "--synthesize",
            "--workflow",
            "workflow.json",
            "--quality-loop",
            "--llm-audio-qa",
            "--llm-audio-qa-model",
            "models/audio_qa/Qwen3-Omni-30B-A3B-Instruct",
        ]
    )

    assert captured["llm_audio_qa"] is True
    assert captured["llm_audio_qa_model"] == "models/audio_qa/Qwen3-Omni-30B-A3B-Instruct"
    assert captured["llm_audio_qa_endpoint"] == ""


def test_synthesize_accepts_direct_omni_audio_qa_without_endpoint(
    tmp_path: Path,
    monkeypatch,
) -> None:
    synth = _load_synthesize_comfyui()
    manifest_path = tmp_path / "chunks_manifest_v2.json"
    workflow_path = tmp_path / "workflow.json"
    manifest_path.write_text('{"version": 2, "chapters": []}', encoding="utf-8")
    workflow_path.write_text("{}", encoding="utf-8")
    captured: dict[str, object] = {}

    class _Client:
        def __init__(self, url: str) -> None:
            self.url = url

        def is_reachable(self) -> bool:
            return True

    class _Builder:
        def __init__(self, path: str) -> None:
            self.path = path

    def fake_run_llm_audio_qa(_manifest: dict, *, config, manifest_path: Path):  # noqa: ANN001
        captured["model"] = config.model
        captured["endpoint"] = config.endpoint
        captured["manifest_path"] = manifest_path
        return type(
            "_Result",
            (),
            {
                "status": "passed",
                "summary": {"failed": 0, "warning": 0, "error": 0},
            },
        )()

    monkeypatch.setattr(synth, "ComfyUIClient", _Client)
    monkeypatch.setattr(synth, "WorkflowBuilder", _Builder)
    monkeypatch.setattr(synth, "synthesize_manifest", lambda **_kwargs: None)
    monkeypatch.setattr(synth, "run_llm_audio_qa", fake_run_llm_audio_qa)
    monkeypatch.setattr(synth, "write_llm_audio_qa_report", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(synth, "annotate_manifest_with_llm_audio_qa", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(synth, "save_manifest", lambda *_args, **_kwargs: None)

    synth.main(
        [
            "--chunks-json",
            str(manifest_path),
            "--out",
            str(tmp_path / "audio"),
            "--workflow",
            str(workflow_path),
            "--llm-audio-qa",
            "--llm-audio-qa-model",
            "models/audio_qa/Qwen3-Omni-30B-A3B-Instruct",
        ]
    )

    assert captured["model"] == "models/audio_qa/Qwen3-Omni-30B-A3B-Instruct"
    assert captured["endpoint"] == ""
    assert captured["manifest_path"] == manifest_path


def test_stage5_asr_qa_writes_report_and_manifest_annotations(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pipeline = _load_run_pipeline()
    import book_normalizer.tts.asr_qa as asr_qa

    class _FakeBackend:
        name = "fake"

        def __init__(self, model: str, **_kwargs: object) -> None:
            self.model = model

        def transcribe(self, audio_path: Path, *, language: str | None = None):  # noqa: ANN001
            return asr_qa.AsrTranscript(
                text="hello world",
                language="en",
                confidence=0.98,
                duration_seconds=1.0,
            )

    monkeypatch.setattr(asr_qa, "FasterWhisperBackend", _FakeBackend)
    wav_path = tmp_path / "audio_chunks" / "chapter_001" / "chunk_001_narrator.wav"
    wav_path.parent.mkdir(parents=True)
    with wave.open(str(wav_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b"\x01\x00" * 24000)

    manifest_path = tmp_path / "chunks_manifest_v2.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": 2,
                "language": "en",
                "chapters": [
                    {
                        "chapter_index": 0,
                        "chunks": [
                            {
                                "chunk_index": 0,
                                "voice": "narrator",
                                "voice_id": "narrator_calm",
                                "text": "Hello world.",
                                "synthesized": True,
                                "audio_file": "audio_chunks/chapter_001/chunk_001_narrator.wav",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report_path = pipeline.run_stage5_asr_qa(
        manifest_path,
        asr_model="unit",
        max_wer=0.3,
        max_cer=0.2,
        min_match_ratio=0.8,
        timeout_seconds=30,
        mark_failed_on_asr=False,
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert report["audio_qa"]["checked_files"] == 1
    assert not any(
        issue["kind"] == "missing_audio_file"
        for issue in report["audio_qa"]["issues"]
    )
    assert report["asr_qa"]["status"] == "passed"
    assert manifest["chapters"][0]["chunks"][0]["asr_qa"]["status"] == "passed"
