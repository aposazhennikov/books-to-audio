"""Cache and review-report helpers for LLM segmentation."""

from __future__ import annotations

import json
from hashlib import sha1
from pathlib import Path
from typing import Any

from book_normalizer.chunking.llm_segmenter_config import _CACHE_VERSION
from book_normalizer.chunking.llm_segmenter_text import _normalise_segments, _system_prompt_for_language
from book_normalizer.chunking.llm_source_preservation import _segments_preserve_source


class LlmSegmenterCacheMixin:
    """Disk cache and validation report behavior for LLM segmentation."""

    def _cache_path(self, chapter_index: int, window_index: int, window_text: str) -> Path | None:
        if self._cache_dir is None:
            return None
        fingerprint = sha1(
            "\n\0".join((
                _CACHE_VERSION,
                self._language,
                ",".join(self._model_plan.candidates),
                _system_prompt_for_language(self._language),
                window_text,
            )).encode("utf-8")
        ).hexdigest()[:16]
        return self._cache_dir / f"segments_ch{chapter_index:03d}_win{window_index:03d}_{fingerprint}.json"

    def _load_cache(
        self,
        chapter_index: int,
        window_index: int,
        window_text: str,
    ) -> list[dict[str, Any]] | None:
        path = self._cache_path(chapter_index, window_index, window_text)
        if path is None or not path.exists():
            return None
        try:
            loaded = _normalise_segments(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            return None
        if loaded and _segments_preserve_source(window_text, loaded):
            return loaded
        return None

    def _save_cache(
        self,
        chapter_index: int,
        window_index: int,
        window_text: str,
        segments: list[dict[str, Any]],
    ) -> None:
        path = self._cache_path(chapter_index, window_index, window_text)
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8")

    def _write_review_report(self) -> None:
        if self._review_report_path is None:
            return
        self._review_report_path.parent.mkdir(parents=True, exist_ok=True)
        self._review_report_path.write_text(
            json.dumps(
                {
                    "language": self._language,
                    "models": list(self._model_plan.candidates),
                    "failures": [failure.to_record() for failure in self._failures],
                    "requires_human_review": True,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

