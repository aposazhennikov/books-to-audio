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
            "--llm-normalize-workers",
            "2",
            "--llm-normalize-start-chapter",
            "46",
            "--llm-chunk-workers",
            "2",
            "--llm-max-retries",
            "1",
            "--synthesize",
            "--synthesis-workers",
            "2",
            "--asr-qa-after-synthesis",
            "--asr-model",
            "tiny",
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
        "2400",
        "--ocr-mode",
        "force",
        "--llm-normalize",
        "--llm-normalize-workers",
        "2",
        "--llm-normalize-start-chapter",
        "46",
        "--llm-chunk-workers",
        "2",
        "--llm-max-retries",
        "1",
        "--synthesize",
        "--workflow",
        "workflow.json",
        "--comfyui-url",
        "http://127.0.0.1:8188",
        "--synthesis-workers",
        "2",
        "--asr-qa-after-synthesis",
        "--asr-model",
        "tiny",
        "--assemble",
        "--chapter",
        "2",
        "--skip-stage1",
    ]


def test_pipeline_command_forwards_llm_audio_qa_options(
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
            "--llm-audio-qa",
            "--llm-audio-qa-model",
            "Qwen/Qwen3-Omni-30B-A3B-Instruct",
            "--llm-audio-qa-endpoint",
            "http://127.0.0.1:8801/v1",
            "--llm-audio-qa-min-score",
            "88",
        ],
    )

    assert result.exit_code == 0
    assert "--llm-audio-qa" in captured["argv"]
    assert captured["argv"][captured["argv"].index("--llm-audio-qa-model") + 1] == (
        "Qwen/Qwen3-Omni-30B-A3B-Instruct"
    )
    assert captured["argv"][captured["argv"].index("--llm-audio-qa-endpoint") + 1] == (
        "http://127.0.0.1:8801/v1"
    )
    assert captured["argv"][captured["argv"].index("--llm-audio-qa-min-score") + 1] == "88"


def test_pipeline_command_accepts_image_ocr_mode(
    tmp_path: Path,
    monkeypatch,
) -> None:
    book_path = tmp_path / "book.pdf"
    book_path.write_bytes(b"%PDF-1.4 dummy")
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
            "--ocr-mode",
            "image",
        ],
    )

    assert result.exit_code == 0
    assert captured["argv"][captured["argv"].index("--ocr-mode") + 1] == "image"


def test_pipeline_command_accepts_book_option_alias(
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
            "--book",
            str(book_path),
            "--out",
            str(tmp_path / "out"),
            "--chunk-mode",
            "heuristic",
        ],
    )

    assert result.exit_code == 0
    assert captured["argv"][:4] == ["--book", str(book_path), "--out", str(tmp_path / "out")]
    assert "--chunk-mode" in captured["argv"]
    assert captured["argv"][captured["argv"].index("--chunk-mode") + 1] == "heuristic"


def test_pipeline_command_rejects_missing_book() -> None:
    result = CliRunner().invoke(cli.main, ["pipeline"])

    assert result.exit_code != 0
    assert "INPUT_PATH or with --book" in result.output


def test_pipeline_command_rejects_conflicting_book_paths(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("One.", encoding="utf-8")
    second.write_text("Two.", encoding="utf-8")

    result = CliRunner().invoke(cli.main, ["pipeline", str(first), "--book", str(second)])

    assert result.exit_code != 0
    assert "INPUT_PATH and --book differ" in result.output


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
