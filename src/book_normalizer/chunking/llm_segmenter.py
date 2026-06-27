"""LLM smart voice segmentation for GUI segment manifests."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from book_normalizer.chunking.llm_dialogue_markers import (
    _dash_starts_narrator_tag as _dash_starts_narrator_tag,
)
from book_normalizer.chunking.llm_dialogue_markers import (
    _starts_with_direct_speech_marker as _starts_with_direct_speech_marker,
)
from book_normalizer.chunking.llm_dialogue_markers import (
    _take_quoted_speech as _take_quoted_speech,
)
from book_normalizer.chunking.llm_dialogue_repair import (
    repair_segment_dialogue_boundaries as repair_segment_dialogue_boundaries,
)
from book_normalizer.chunking.llm_dialogue_speaker import (
    _clean_speaker,
    _remember_dialogue_speaker,
    _repair_dialogue_metadata,
)
from book_normalizer.chunking.llm_segmenter_cache import LlmSegmenterCacheMixin
from book_normalizer.chunking.llm_segmenter_config import (
    DEFAULT_WINDOW_CHARS,
    ROLE_TO_VOICE_ID,
)
from book_normalizer.chunking.llm_segmenter_failures import (
    LlmSegmentationError as LlmSegmentationError,
)
from book_normalizer.chunking.llm_segmenter_failures import (
    SegmentationFailure,
)
from book_normalizer.chunking.llm_segmenter_fields import (
    _clean_intonation,
    _clean_optional,
    _clean_section_kind,
    _is_dialogue_segment,
    _normalize_role,
)
from book_normalizer.chunking.llm_segmenter_text import (
    _build_windows,
    _chapter_text,
    _safe_int,
)
from book_normalizer.chunking.llm_segmenter_text import (
    _system_prompt_for_language as _system_prompt_for_language,
)
from book_normalizer.chunking.llm_segmenter_text import (
    _user_prompt_for_window as _user_prompt_for_window,
)
from book_normalizer.chunking.llm_segmenter_window import LlmSegmenterWindowMixin
from book_normalizer.chunking.llm_source_preservation import (
    _canonical_for_preservation as _canonical_for_preservation,
)
from book_normalizer.chunking.splitter import (
    DEFAULT_CHAPTER_PAUSE_MS,
    DEFAULT_MAX_CHUNK_CHARS,
    chunk_text,
)
from book_normalizer.languages import normalize_book_language
from book_normalizer.llm.model_router import model_plan_for_language
from book_normalizer.llm.ollama_client import OllamaChatClient

logger = logging.getLogger(__name__)


class LlmVoiceSegmenter(LlmSegmenterWindowMixin, LlmSegmenterCacheMixin):
    """Generate segment manifest rows directly from a local Ollama model."""

    def __init__(
        self,
        *,
        endpoint: str = "http://localhost:11434",
        model: str = "",
        api_key: str = "",
        language: str = "ru",
        cache_dir: Path | None = None,
        review_report_path: Path | None = None,
        window_chars: int = DEFAULT_WINDOW_CHARS,
        max_segment_chars: int = DEFAULT_MAX_CHUNK_CHARS,
        lightweight: bool = False,
        max_retries: int = 2,
        allow_source_fallback: bool = False,
    ) -> None:
        self._language = normalize_book_language(language)
        self._model_plan = model_plan_for_language(
            self._language,
            preferred_model=model,
            lightweight=lightweight,
        )
        self._client = OllamaChatClient(
            endpoint=endpoint,
            api_key=api_key,
            num_ctx=self._model_plan.num_ctx,
            num_parallel=self._model_plan.num_parallel,
            keep_alive=self._model_plan.keep_alive,
            think=self._model_plan.think,
        )
        self._cache_dir = cache_dir
        self._review_report_path = review_report_path
        self._window_chars = max(600, window_chars)
        self._max_segment_chars = max(80, max_segment_chars)
        self._max_retries = max(1, max_retries)
        self._allow_source_fallback = allow_source_fallback
        self._failures: list[SegmentationFailure] = []

    @property
    def model_candidates(self) -> tuple[str, ...]:
        return self._model_plan.candidates

    def segment_book(
        self,
        book: object,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> list[dict[str, Any]]:
        """Return flat segment-manifest rows for every chapter in a book."""

        self._failures = []
        try:
            rows = self._segment_book(book, progress_callback)
            if self._failures:
                self._write_review_report()
            return rows
        finally:
            self._client.unload_models(self._model_plan.candidates)

    def _segment_book(
        self,
        book: object,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> list[dict[str, Any]]:
        """Implementation for :meth:`segment_book`; split out for cleanup."""

        chapters = list(getattr(book, "chapters", []) or [])
        total_windows = sum(
            max(1, len(_build_windows(_chapter_text(chapter), self._window_chars)))
            for chapter in chapters
        )
        done_windows = 0
        rows: list[dict[str, Any]] = []
        segment_index = 0

        for chapter in chapters:
            recent_dialogue_speakers: list[tuple[str, str]] = []
            chapter_index = int(getattr(chapter, "index", len(rows)))
            chapter_text = _chapter_text(chapter)
            windows = _build_windows(chapter_text, self._window_chars)
            for window_index, window_text in enumerate(windows):
                progress_label = f"{chapter_index + 1}:{window_index + 1}/{len(windows)}"
                if progress_callback is not None:
                    progress_callback(done_windows, total_windows, progress_label)
                raw_segments = self._segment_window(chapter_index, window_index, window_text)
                for raw in raw_segments:
                    for text_part in chunk_text(
                        raw["text"],
                        max_chunk_chars=self._max_segment_chars,
                    ) or [raw["text"]]:
                        role = _normalize_role(raw.get("role", "narrator"))
                        speaker = _clean_speaker(raw.get("speaker"), self._language)
                        section_kind = _clean_section_kind(raw.get("section_kind"), role)
                        character_description = _clean_optional(
                            raw.get("character_description")
                            or raw.get("role_description")
                            or raw.get("description")
                        )
                        (
                            role,
                            speaker,
                            section_kind,
                            character_description,
                        ) = _repair_dialogue_metadata(
                            role=role,
                            speaker=speaker,
                            section_kind=section_kind,
                            character_description=character_description,
                            text=text_part,
                            language=self._language,
                            recent_dialogue_speakers=recent_dialogue_speakers,
                            force_narration=bool(raw.get("_narration_repaired")),
                            force_dialogue=bool(raw.get("_direct_speech_repaired")),
                        )
                        is_dialogue = _is_dialogue_segment(
                            role=role,
                            section_kind=section_kind,
                            speaker=speaker,
                            text=text_part,
                        )
                        if is_dialogue:
                            _remember_dialogue_speaker(
                                recent_dialogue_speakers,
                                speaker=speaker,
                                role=role,
                            )
                        rows.append(
                            {
                                "segment_index": segment_index,
                                "chapter_index": chapter_index,
                                "language": self._language,
                                "is_dialogue": is_dialogue,
                                "role": role,
                                "speaker": speaker,
                                "character_description": character_description,
                                "emotion": _clean_intonation(
                                    raw.get("emotion") or raw.get("intonation", "calm")
                                ),
                                "section_kind": section_kind,
                                "voice_id": ROLE_TO_VOICE_ID[role],
                                "intonation": _clean_intonation(raw.get("intonation", "calm")),
                                "text": text_part,
                                "pause_after_ms": _safe_int(raw.get("pause_after_ms")),
                                "boundary_after": str(raw.get("boundary_after") or ""),
                            }
                        )
                        segment_index += 1
                done_windows += 1
                if progress_callback is not None:
                    progress_callback(
                        done_windows,
                        total_windows,
                        progress_label,
                    )

        if rows:
            rows[-1]["boundary_after"] = "chapter"
            rows[-1]["pause_after_ms"] = max(
                _safe_int(rows[-1].get("pause_after_ms")),
                DEFAULT_CHAPTER_PAUSE_MS,
            )
        return rows





































































































































































