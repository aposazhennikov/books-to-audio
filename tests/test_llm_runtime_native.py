from __future__ import annotations

import ast
import json
from pathlib import Path

from book_normalizer.gui.workers.normalize_worker import NormalizeWorker
from book_normalizer.gui.workers.tts_worker import ExportSegmentsWorker
from book_normalizer.models.book import Book, Metadata
from book_normalizer.runtime_paths import reset_runtime_path_cache

_LLM_RUNTIME_FILES = [
    Path("src/book_normalizer/llm/ollama_client.py"),
    Path("src/book_normalizer/normalization/llm_normalizer.py"),
    Path("src/book_normalizer/chunking/llm_chunker.py"),
    Path("src/book_normalizer/chunking/llm_segmenter.py"),
    Path("src/book_normalizer/dialogue/attribution.py"),
    Path("src/book_normalizer/gui/workers/normalize_worker.py"),
    Path("src/book_normalizer/gui/workers/tts_worker.py"),
    Path("src/book_normalizer/gui/pages/normalize_page.py"),
    Path("src/book_normalizer/gui/pages/roles_page.py"),
    Path("src/book_normalizer/gui/pages/voices_page.py"),
]


def test_llm_runtime_does_not_shell_out_or_use_wsl() -> None:
    """LLM work must use native HTTP endpoints, not WSL or Ollama CLI wrappers."""
    forbidden_imports = {"subprocess", "pexpect", "shlex"}
    forbidden_shell_calls = {
        ("os", "system"),
        ("os", "popen"),
        ("subprocess", "run"),
        ("subprocess", "Popen"),
        ("subprocess", "call"),
        ("subprocess", "check_call"),
        ("subprocess", "check_output"),
    }
    forbidden_text = ("wsl", "ollama run", "ollama pull", "ollama.exe")

    for path in _LLM_RUNTIME_FILES:
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()
        assert not any(token in lowered for token in forbidden_text), path

        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = {alias.name.split(".", maxsplit=1)[0] for alias in node.names}
                assert imported.isdisjoint(forbidden_imports), path
            elif isinstance(node, ast.ImportFrom):
                module = (node.module or "").split(".", maxsplit=1)[0]
                assert module not in forbidden_imports, path
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                owner = node.func.value
                if isinstance(owner, ast.Name):
                    assert (owner.id, node.func.attr) not in forbidden_shell_calls, path


def test_llm_client_is_native_ollama_http_client() -> None:
    source = Path("src/book_normalizer/llm/ollama_client.py").read_text(encoding="utf-8")

    assert "/api/chat" in source
    assert "httpx.post" in source
    assert "subprocess" not in source
    assert "wsl" not in source.lower()


def test_gui_llm_workers_default_to_configured_native_endpoint(
    tmp_path: Path,
    monkeypatch,
) -> None:
    endpoint = "http://127.0.0.1:11555"
    config_path = tmp_path / "local_runtime_paths.json"
    config_path.write_text(
        json.dumps({"ollama_endpoint": endpoint}),
        encoding="utf-8",
    )
    monkeypatch.setenv("BOOKS_TO_AUDIO_RUNTIME_CONFIG", str(config_path))
    monkeypatch.delenv("BOOKS_TO_AUDIO_OLLAMA_ENDPOINT", raising=False)
    reset_runtime_path_cache()

    book = Book(metadata=Metadata(language="ru"))
    normalize_worker = NormalizeWorker(input_path=tmp_path / "book.txt")
    export_worker = ExportSegmentsWorker(book=book, output_dir=tmp_path)

    assert normalize_worker._llm_endpoint == endpoint
    assert export_worker._llm_endpoint == endpoint

    reset_runtime_path_cache()
