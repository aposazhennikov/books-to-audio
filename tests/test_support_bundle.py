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
        "source_preview": "Source preview sentence must stay private.",
        "output_preview": "Output preview sentence must stay private.",
        "before_text": "Before sample must stay private.",
        "after_text": "After sample must stay private.",
        "first_paragraph": "First paragraph must stay private.",
        "last_paragraph": "Last paragraph must stay private.",
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
    (run_dir / "native_extract_preview.txt").write_text(
        "Plain text previews must not be bundled.",
        encoding="utf-8",
    )

    result = create_support_bundle(run_dir)

    with zipfile.ZipFile(result.bundle_path) as archive:
        combined = "\n".join(archive.read(name).decode("utf-8") for name in archive.namelist())

    assert "This exact book sentence" not in combined
    assert "Source preview sentence" not in combined
    assert "Output preview sentence" not in combined
    assert "Before sample" not in combined
    assert "After sample" not in combined
    assert "First paragraph" not in combined
    assert "Last paragraph" not in combined
    assert "Plain text previews" not in combined
    assert "native_extract_preview.txt" not in result.files
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


def test_support_bundle_uses_allowlist_and_skips_private_dirs(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "chunks_manifest_v2.json").write_text('{"book_title": "safe diagnostic"}', encoding="utf-8")
    (run_dir / "random.json").write_text('{"private": "must not be bundled"}', encoding="utf-8")
    (run_dir / "debug.log").write_text("debug log is useful", encoding="utf-8")
    (run_dir / "notes.log").write_text("unrelated log must not be bundled", encoding="utf-8")
    cache_dir = run_dir / "cache"
    cache_dir.mkdir()
    (cache_dir / "chunks_manifest_v2.json").write_text('{"text": "private cache"}', encoding="utf-8")
    private_dir = run_dir / "data"
    private_dir.mkdir()
    (private_dir / "chunks_manifest_v2.json").write_text('{"text": "private data"}', encoding="utf-8")

    result = create_support_bundle(run_dir)

    assert result.files == ["chunks_manifest_v2.json", "debug.log"]
    with zipfile.ZipFile(result.bundle_path) as archive:
        names = set(archive.namelist())
        combined = "\n".join(archive.read(name).decode("utf-8") for name in names)

    assert "chunks_manifest_v2.json" in names
    assert "debug.log" in names
    assert "random.json" not in names
    assert "notes.log" not in names
    assert "cache/chunks_manifest_v2.json" not in names
    assert "data/chunks_manifest_v2.json" not in names
    assert "must not be bundled" not in combined
    assert "private cache" not in combined
    assert "private data" not in combined


def test_support_bundle_skips_symlinks(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "debug.log").write_text("outside secret", encoding="utf-8")

    linked_log = run_dir / "debug.log"
    linked_dir = run_dir / "logs"
    try:
        linked_log.symlink_to(outside / "debug.log")
        linked_dir.symlink_to(outside, target_is_directory=True)
    except (NotImplementedError, OSError):
        return

    result = create_support_bundle(run_dir)

    assert result.files == []
    with zipfile.ZipFile(result.bundle_path) as archive:
        combined = "\n".join(archive.read(name).decode("utf-8") for name in archive.namelist())
    assert "outside secret" not in combined


def test_support_bundle_redacts_secrets_without_redacting_token_counters(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    payload = {
        "api_key": "sk-test-secret",
        "Authorization": "Bearer bearer-secret",
        "access_token": "access-secret",
        "password": "password-secret",
        "nested": {"client_secret": "client-secret"},
        "max_new_tokens": 2048,
        "token_count": 17,
        "notes": "Authorization: Bearer inline-secret\npassword=inline-password\ntoken: inline-token",
    }
    (run_dir / "chunks_manifest_v2.json").write_text(json.dumps(payload), encoding="utf-8")

    result = create_support_bundle(run_dir)

    with zipfile.ZipFile(result.bundle_path) as archive:
        bundled = json.loads(archive.read("chunks_manifest_v2.json").decode("utf-8"))
        combined = "\n".join(archive.read(name).decode("utf-8") for name in archive.namelist())

    assert bundled["api_key"] == "<REDACTED_SECRET>"
    assert bundled["Authorization"] == "<REDACTED_SECRET>"
    assert bundled["access_token"] == "<REDACTED_SECRET>"
    assert bundled["password"] == "<REDACTED_SECRET>"
    assert bundled["nested"]["client_secret"] == "<REDACTED_SECRET>"
    assert bundled["max_new_tokens"] == 2048
    assert bundled["token_count"] == 17
    assert "sk-test-secret" not in combined
    assert "bearer-secret" not in combined
    assert "inline-secret" not in combined
    assert "inline-password" not in combined
    assert "inline-token" not in combined
    assert "<REDACTED_SECRET>" in combined
