from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

import book_normalizer.cli as cli


def test_pipeline_command_runs_in_process_without_subprocess(
    tmp_path: Path,
    monkeypatch,
) -> None:
    book_path = tmp_path / "book.txt"
    book_path.write_text("Hello.", encoding="utf-8")
    captured: dict[str, list[str]] = {}

    def fake_run_pipeline(argv: list[str]) -> None:
        captured["argv"] = argv

    monkeypatch.setattr(cli, "_run_pipeline_in_process", fake_run_pipeline)

    result = CliRunner().invoke(
        cli.main,
        [
            "pipeline",
            str(book_path),
            "--out",
            str(tmp_path / "out"),
            "--llm-normalize",
            "--synthesize",
            "--workflow",
            "workflow.json",
            "--comfyui-url",
            "http://127.0.0.1:8188",
            "--assemble",
            "--chapter",
            "2",
            "--skip-stage1",
            "--ocr-mode",
            "force",
        ],
    )

    assert result.exit_code == 0
    assert captured["argv"] == [
        "--book",
        str(book_path),
        "--out",
        str(tmp_path / "out"),
        "--llm-model",
        "hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M",
        "--llm-endpoint",
        "http://localhost:11434",
        "--chunk-mode",
        "llm",
        "--max-chunk-chars",
        "400",
        "--ocr-mode",
        "force",
        "--llm-normalize",
        "--synthesize",
        "--workflow",
        "workflow.json",
        "--comfyui-url",
        "http://127.0.0.1:8188",
        "--assemble",
        "--chapter",
        "2",
        "--skip-stage1",
    ]


def test_pipeline_command_source_does_not_shell_out_to_child_python() -> None:
    source = Path("src/book_normalizer/cli.py").read_text(encoding="utf-8")
    pipeline_source = source.split("def pipeline_command", maxsplit=1)[1].split(
        "@main.command(name=\"doctor\")",
        maxsplit=1,
    )[0]

    assert "subprocess" not in pipeline_source
    assert "Popen" not in pipeline_source
    assert "sys.executable" not in pipeline_source
    assert "wsl" not in pipeline_source.lower()
