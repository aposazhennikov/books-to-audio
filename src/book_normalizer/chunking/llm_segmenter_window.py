"""Single-window LLM segmentation retry loop."""

from __future__ import annotations

import logging
from typing import Any

from book_normalizer.chunking.llm_dialogue_splitter import (
    _repair_dialogue_segment_boundaries,
    _split_mixed_dialogue_segments,
)
from book_normalizer.chunking.llm_segmenter_config import _SEGMENT_SCHEMA
from book_normalizer.chunking.llm_segmenter_failures import (
    LlmSegmentationError,
    SegmentationFailure,
)
from book_normalizer.chunking.llm_segmenter_text import (
    _normalise_segments,
    _source_fallback_segments,
    _system_prompt_for_language,
    _user_prompt_for_window,
)
from book_normalizer.chunking.llm_source_preservation import (
    _reconcile_segments_to_source,
    _reconcile_segments_to_source_with_gaps,
    _segments_preserve_source,
)

logger = logging.getLogger(__name__)


class LlmSegmenterWindowMixin:
    """Run and validate one LLM segmentation window."""

    def _segment_window(
        self,
        chapter_index: int,
        window_index: int,
        window_text: str,
    ) -> list[dict[str, Any]]:
        cached = self._load_cache(chapter_index, window_index, window_text)
        if cached is not None:
            return cached

        last_error = ""
        previous_issues: list[str] = []
        for model in self._model_plan.candidates:
            for attempt_index in range(1, self._max_retries + 1):
                try:
                    attempt = self._client.chat_json_with_fallback(
                        models=[model],
                        messages=[
                            {"role": "system", "content": _system_prompt_for_language(self._language)},
                            {
                                "role": "user",
                                "content": _user_prompt_for_window(
                                    language=self._language,
                                    chapter_index=chapter_index,
                                    window_index=window_index,
                                    window_text=window_text,
                                    previous_issues=previous_issues,
                                ),
                            },
                        ],
                        schema=_SEGMENT_SCHEMA,
                        temperature=0.1,
                    )
                    segments = _normalise_segments(attempt.data)
                    if not segments:
                        raise ValueError("empty segments")
                    reconciled = _reconcile_segments_to_source(window_text, segments)
                    if reconciled is None:
                        reconciled = _reconcile_segments_to_source_with_gaps(window_text, segments)
                    if reconciled is not None:
                        segments = reconciled
                    segments = _repair_dialogue_segment_boundaries(segments)
                    segments = _split_mixed_dialogue_segments(segments, language=self._language)
                    if not _segments_preserve_source(window_text, segments):
                        failure = SegmentationFailure(
                            chapter_index,
                            window_index,
                            model,
                            "text_preservation_failed",
                            window_text[:500],
                            " ".join(seg["text"] for seg in segments)[:500],
                        )
                        self._failures.append(failure)
                        last_error = failure.reason
                        previous_issues = [
                            "The previous segment list did not preserve input.text exactly.",
                            "Return fewer segments if needed, but do not change, drop, or add text.",
                        ]
                        self._client.unload_model(model)
                        continue
                    self._save_cache(chapter_index, window_index, window_text, segments)
                    return segments
                except Exception as exc:  # noqa: BLE001
                    last_error = f"{type(exc).__name__}: {exc}"
                    previous_issues = [last_error]
                    self._failures.append(
                        SegmentationFailure(
                            chapter_index,
                            window_index,
                            model,
                            f"attempt {attempt_index}/{self._max_retries}: {last_error}",
                            window_text[:500],
                        )
                    )
                    self._client.unload_model(model)

        if self._allow_source_fallback:
            segments = _source_fallback_segments(window_text)
            self._failures.append(
                SegmentationFailure(
                    chapter_index,
                    window_index,
                    "source-preserving-fallback",
                    f"used_original_text_after_llm_failure: {last_error}",
                    window_text[:500],
                    window_text[:500],
                )
            )
            logger.warning(
                "LLM voice segmentation failed for chapter %d window %d; "
                "using source-preserving narrator fallback",
                chapter_index,
                window_index,
            )
            self._save_cache(chapter_index, window_index, window_text, segments)
            return segments

        self._write_review_report()
        raise LlmSegmentationError(
            "LLM voice segmentation failed validation for "
            f"chapter {chapter_index}, window {window_index}: {last_error}. "
            f"Review report: {self._review_report_path or '(not configured)'}"
        )
