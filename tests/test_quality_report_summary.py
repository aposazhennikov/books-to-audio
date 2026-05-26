from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType


def _load_summary_module() -> ModuleType:
    script = Path(__file__).resolve().parent.parent / "scripts" / "summarize_quality_reports.py"
    spec = importlib.util.spec_from_file_location("quality_report_summary", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_summarize_quality_reports_combines_real_report_shapes(tmp_path: Path) -> None:
    module = _load_summary_module()
    first = tmp_path / "quality_report_a.json"
    second = tmp_path / "quality_report_b.json"
    first.write_text(
        json.dumps(
            {
                "run_ollama": True,
                "primary_model": "hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M",
                "languages": ["ru"],
                "cases": [
                    {
                        "status": "ok",
                        "language": "ru",
                        "source": "books/sample.pdf",
                        "chars_before": 384,
                        "segments": 4,
                        "chunks": 1,
                        "text_preserved": True,
                        "segments_preserve_text": True,
                        "chunk_text_preserved": True,
                        "metadata_extra": {"pdf_text_variant": "ocr"},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    second.write_text(
        json.dumps(
            {
                "run_ollama": False,
                "primary_model": "hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M",
                "languages": ["en", "zh"],
                "cases": [
                    {
                        "status": "offline_checked",
                        "language": "en",
                        "source": "public/en.txt",
                        "chars_before": 995,
                        "segments": 2,
                        "chunks": 2,
                        "text_preserved": True,
                    },
                    {
                        "status": "review_required",
                        "language": "zh",
                        "source": "public/zh.txt",
                        "chars_before": 100,
                        "segments": 1,
                        "chunks": 0,
                        "text_preserved": True,
                        "segments_preserve_text": False,
                        "chunk_text_preserved": False,
                        "error": "chunk mismatch",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    markdown = module.summarize_reports([first, second])

    assert "# Current Quality Verification" in markdown
    assert "- Reports: 2" in markdown
    assert "- Cases: 3" in markdown
    assert "- OK/offline checked: 2" in markdown
    assert "- Review required/errors: 1" in markdown
    assert "- Text preserved: 2/3" in markdown
    assert "books/sample.pdf" in markdown
    assert "PDF: ocr" in markdown
    assert "chunk mismatch" in markdown
