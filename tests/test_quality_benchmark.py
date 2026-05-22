from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


def _load_benchmark_module() -> ModuleType:
    script = Path(__file__).resolve().parent.parent / "scripts" / "quality_benchmark.py"
    spec = importlib.util.spec_from_file_location("quality_benchmark", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_offline_quality_benchmark_covers_supported_languages(tmp_path: Path) -> None:
    module = _load_benchmark_module()

    report = module.run_benchmark(books_dir=tmp_path / "missing", run_ollama=False)

    languages = {case["language"] for case in report["cases"]}
    assert languages == {"ru", "en", "zh", "kk", "uz"}
    assert report["run_ollama"] is False
    assert all(case["text_preserved"] for case in report["cases"])
    assert all(case["chunks"] >= 1 for case in report["cases"])


def test_quality_benchmark_reads_local_txt_books(tmp_path: Path) -> None:
    module = _load_benchmark_module()
    books_dir = tmp_path / "books"
    books_dir.mkdir()
    (books_dir / "sample.txt").write_text("Alpha beta.\n\nGamma delta.", encoding="utf-8")

    report = module.run_benchmark(books_dir=books_dir, run_ollama=False)

    sources = {case["source"] for case in report["cases"]}
    assert str(books_dir / "sample.txt") in sources
