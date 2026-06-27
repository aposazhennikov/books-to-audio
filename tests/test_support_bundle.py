from __future__ import annotations

import json
import zipfile
from pathlib import Path

from click.testing import CliRunner

import book_normalizer.cli as cli
from book_normalizer.diagnostics.support_bundle import create_support_bundle


def test_support_bundle_redacts_book_text_and_private_paths(tmp_path: Path) -> None:
    run_dir = tmp_path / "output" / "book_run"
    run_dir.mkdir(parents=True)
    manifest = {
        "book_title": "Secret Book",
        "chapters": [
            {
                "chunks": [
                    {
                        "text": "This exact book sentence must not leave the machine.",
                        "audio_file": str(run_dir / "audio_chunks" / "chunk.wav"),
                    }
                ]
            }
        ],
    }
    (run_dir / "chunks_manifest_v2.json").write_text(json.dumps(manifest), encoding="utf-8")
    (run_dir / "run.log").write_text(f"failed file {run_dir / 'books' / 'private.pdf'}", encoding="utf-8")

    result = create_support_bundle(run_dir)

    with zipfile.ZipFile(result.bundle_path) as archive:
        combined = "\n".join(archive.read(name).decode("utf-8") for name in archive.namelist())

    assert "This exact book sentence" not in combined
    assert str(run_dir) not in combined
    assert "<REDACTED_BOOK_TEXT>" in combined
    assert "<PRIVATE_PATH>" in combined


def test_support_bundle_cli_writes_zip(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "report.json").write_text('{"text": "private"}', encoding="utf-8")

    result = CliRunner().invoke(cli.main, ["support-bundle", str(run_dir)])

    assert result.exit_code == 0, result.output
    assert (run_dir / "support_bundle_redacted.zip").exists()
