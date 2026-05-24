from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _load_run_pipeline() -> ModuleType:
    script = Path("scripts/run_pipeline.py").resolve()
    spec = importlib.util.spec_from_file_location("test_run_pipeline_native_module", script)
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


def test_stage3_passes_language_and_review_report_to_native_chunker(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pipeline = _load_run_pipeline()
    book_dir = tmp_path / "book"
    book_dir.mkdir()
    (book_dir / "001_chapter_01.txt").write_text("Salom. \"Kim bor?\"", encoding="utf-8")
    captured: dict[str, object] = {}

    class _FakeSpec:
        chapter_index = 0

        def to_dict(self) -> dict[str, object]:
            return {
                "chapter_index": 0,
                "chunk_index": 0,
                "narrator": "Salom.",
                "voice_tone": "calm",
                "text": "Salom.",
            }

    class _FakeChunker:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

        def chunk_chapter(self, chapter_index: int, text: str) -> list[_FakeSpec]:
            assert chapter_index == 0
            assert "Salom" in text
            return [_FakeSpec()]

    import book_normalizer.chunking.llm_chunker as llm_chunker

    monkeypatch.setattr(llm_chunker, "LlmChunker", _FakeChunker)

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
