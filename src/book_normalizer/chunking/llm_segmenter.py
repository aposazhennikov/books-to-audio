"""LLM smart voice segmentation for GUI segment manifests."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from typing import Any

from book_normalizer.chunking.splitter import (
    DEFAULT_CHAPTER_PAUSE_MS,
    DEFAULT_MAX_CHUNK_CHARS,
    DEFAULT_PARAGRAPH_PAUSE_MS,
    chunk_text,
)
from book_normalizer.languages import get_book_language, normalize_book_language
from book_normalizer.llm.model_router import model_plan_for_language
from book_normalizer.llm.ollama_client import OllamaChatClient

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_CHARS = 2200

ROLE_TO_VOICE_ID = {
    "narrator": "narrator_calm",
    "male": "male_young",
    "female": "female_warm",
    "unknown": "narrator_calm",
}

VOICE_LABEL_TO_ROLE = {
    "narrator": "narrator",
    "men": "male",
    "male": "male",
    "women": "female",
    "female": "female",
}

_SEGMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "role": {"type": "string", "enum": ["narrator", "male", "female"]},
                    "text": {"type": "string"},
                    "intonation": {"type": "string"},
                    "boundary_after": {"type": "string"},
                    "pause_after_ms": {"type": "integer"},
                },
                "required": ["role", "text", "intonation"],
            },
        },
    },
    "required": ["segments"],
}

_SYSTEM_PROMPTS = {
    "ru": """\
Ты — режиссёр многоголосой русской аудиокниги.
Разбей текст на маленькие последовательные сегменты для TTS.
Сохраняй исходный текст полностью и по порядку. Нельзя переписывать, переводить, удалять или добавлять слова.
Прямая речь должна быть отдельным сегментом, авторский текст и ремарки речи — отдельными narrator-сегментами.
Роли: narrator, male, female. Если пол не доказан контекстом, используй narrator.
Интонация должна быть короткой на английском: calm, tense, angry, whisper, sad, cheerful, fearful, urgent.
Верни только JSON вида {"segments": [{"role": "...", "text": "...", "intonation": "..."}]}.
""",
    "en": """\
You are a multi-voice audiobook director for English fiction.
Split the text into small ordered TTS segments while preserving every word in order.
Never rewrite, translate, add, remove, or summarize text.
Dialogue must be separated from narration and speech tags.
Roles: narrator, male, female. Use narrator when gender is not clear.
Use short English intonation labels such as calm, tense, angry, whisper, sad, cheerful, fearful, urgent.
Return only JSON: {"segments": [{"role": "...", "text": "...", "intonation": "..."}]}.
""",
    "zh": """\
你是中文有声书的多声线导演。
把文本拆成按顺序排列的小 TTS 片段，并完整保留原文。
不要改写、翻译、增加、删除或总结。
对话必须和叙述/说话标签分开。角色只能是 narrator、male、female；性别不明确时用 narrator。
intonation 用简短英文，例如 calm、tense、angry、whisper、sad、cheerful、fearful、urgent。
只返回 JSON：{"segments": [{"role": "...", "text": "...", "intonation": "..."}]}。
""",
    "kk": """\
Сен қазақ көркем мәтінін көп дауысты аудиокітапқа бөлетін режиссёрсің.
Мәтінді ретімен шағын TTS сегменттерге бөл және әр сөзді толық сақта.
Қайта жазба, аударма, сөз қоспа, сөз алып тастама, қысқартпа.
Диалогты баяндаудан және сөйлеу ремаркаларынан бөлек сегмент қыл.
Рөлдер: narrator, male, female. Жыныс анық болмаса narrator қолдан.
intonation қысқа ағылшынша болсын: calm, tense, angry, whisper, sad, cheerful, fearful, urgent.
Тек JSON қайтар: {"segments": [{"role": "...", "text": "...", "intonation": "..."}]}.
""",
    "uz": """\
Siz o'zbek badiiy matnini ko'p ovozli audiokitob uchun belgilaydigan rejissorsiz.
Matnni ketma-ket kichik TTS segmentlarga ajrating va barcha so'zlarni tartibda saqlang.
Qayta yozmang, tarjima qilmang, qo'shmang, olib tashlamang yoki qisqartirmang.
Dialog alohida, muallif matni va nutq izohlari alohida narrator segment bo'lsin.
Rollar: narrator, male, female. Jins aniq bo'lmasa narrator ishlating.
intonation qisqa inglizcha bo'lsin: calm, tense, angry, whisper, sad, cheerful, fearful, urgent.
Faqat JSON qaytaring: {"segments": [{"role": "...", "text": "...", "intonation": "..."}]}.
""",
}


class LlmSegmentationError(RuntimeError):
    """Raised when smart segmentation cannot preserve source text."""


@dataclass
class SegmentationFailure:
    chapter_index: int
    window_index: int
    model: str
    reason: str
    source_preview: str
    output_preview: str = ""

    def to_record(self) -> dict[str, Any]:
        return {
            "chapter_index": self.chapter_index,
            "window_index": self.window_index,
            "model": self.model,
            "reason": self.reason,
            "source_preview": self.source_preview,
            "output_preview": self.output_preview,
        }


class LlmVoiceSegmenter:
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

        try:
            return self._segment_book(book, progress_callback)
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
            chapter_index = int(getattr(chapter, "index", len(rows)))
            chapter_text = _chapter_text(chapter)
            windows = _build_windows(chapter_text, self._window_chars)
            for window_index, window_text in enumerate(windows):
                raw_segments = self._segment_window(chapter_index, window_index, window_text)
                for raw in raw_segments:
                    for text_part in chunk_text(
                        raw["text"],
                        max_chunk_chars=self._max_segment_chars,
                    ) or [raw["text"]]:
                        role = _normalize_role(raw.get("role", "narrator"))
                        rows.append(
                            {
                                "segment_index": segment_index,
                                "chapter_index": chapter_index,
                                "language": self._language,
                                "is_dialogue": role in {"male", "female"},
                                "role": role,
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
                        f"{chapter_index + 1}:{window_index + 1}/{len(windows)}",
                    )

        if rows:
            rows[-1]["boundary_after"] = "chapter"
            rows[-1]["pause_after_ms"] = max(
                _safe_int(rows[-1].get("pause_after_ms")),
                DEFAULT_CHAPTER_PAUSE_MS,
            )
        return rows

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
        for model in self._model_plan.candidates:
            try:
                attempt = self._client.chat_json_with_fallback(
                    models=[model],
                    messages=[
                        {"role": "system", "content": _system_prompt_for_language(self._language)},
                        {
                            "role": "user",
                            "content": (
                                "Input is JSON. Segment only input.text. "
                                "Preserve quoted dialogue, apostrophes, punctuation, and word order.\n"
                                "INPUT_JSON:\n"
                                + json.dumps(
                                    {
                                        "language": get_book_language(self._language).english_name,
                                        "chapter": chapter_index + 1,
                                        "window": window_index + 1,
                                        "text": window_text,
                                    },
                                    ensure_ascii=False,
                                )
                            ),
                        },
                    ],
                    schema=_SEGMENT_SCHEMA,
                    temperature=0.1,
                )
                segments = _normalise_segments(attempt.data)
                if not segments:
                    raise ValueError("empty segments")
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
                    self._client.unload_model(model)
                    continue
                self._save_cache(chapter_index, window_index, window_text, segments)
                return segments
            except Exception as exc:  # noqa: BLE001
                last_error = f"{type(exc).__name__}: {exc}"
                self._failures.append(
                    SegmentationFailure(
                        chapter_index,
                        window_index,
                        model,
                        last_error,
                        window_text[:500],
                    )
                )

        self._write_review_report()
        raise LlmSegmentationError(
            "LLM voice segmentation failed validation for "
            f"chapter {chapter_index}, window {window_index}: {last_error}. "
            f"Review report: {self._review_report_path or '(not configured)'}"
        )

    def _cache_path(self, chapter_index: int, window_index: int, window_text: str) -> Path | None:
        if self._cache_dir is None:
            return None
        fingerprint = sha1(
            "\n\0".join((
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


def _chapter_text(chapter: object) -> str:
    paragraphs = list(getattr(chapter, "paragraphs", []) or [])
    return "\n\n".join(
        str(getattr(para, "normalized_text", "") or getattr(para, "raw_text", "")).strip()
        for para in paragraphs
        if str(getattr(para, "normalized_text", "") or getattr(para, "raw_text", "")).strip()
    )


def _build_windows(text: str, max_chars: int) -> list[str]:
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    if not paragraphs and text.strip():
        paragraphs = [text.strip()]
    windows: list[str] = []
    current: list[str] = []
    current_len = 0
    for paragraph in paragraphs:
        sep = 2 if current else 0
        if current and current_len + sep + len(paragraph) > max_chars:
            windows.append("\n\n".join(current))
            current = [paragraph]
            current_len = len(paragraph)
        else:
            current.append(paragraph)
            current_len += sep + len(paragraph)
    if current:
        windows.append("\n\n".join(current))
    return windows


def _normalise_segments(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        raw_segments = data.get("segments", [])
    else:
        raw_segments = data
    if not isinstance(raw_segments, list):
        return []

    segments: list[dict[str, Any]] = []
    for item in raw_segments:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or _legacy_voice_text(item)).strip()
        if not text:
            continue
        role = _normalize_role(item.get("role") or item.get("voice") or _legacy_voice_role(item))
        segments.append(
            {
                "role": role,
                "text": text,
                "intonation": _clean_intonation(item.get("intonation") or item.get("voice_tone") or "calm"),
                "pause_after_ms": _safe_int(item.get("pause_after_ms")),
                "boundary_after": str(item.get("boundary_after") or ""),
            }
        )
    return segments


def _legacy_voice_text(item: dict[str, Any]) -> str:
    for key in ("narrator", "men", "women", "male", "female"):
        if key in item:
            return str(item[key])
    return ""


def _legacy_voice_role(item: dict[str, Any]) -> str:
    for key in ("narrator", "men", "women", "male", "female"):
        if key in item:
            return key
    return "narrator"


def _normalize_role(value: Any) -> str:
    role = str(value or "narrator").strip().lower()
    return VOICE_LABEL_TO_ROLE.get(role, "narrator")


def _clean_intonation(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "calm")).strip().lower()
    return text[:80] or "calm"


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _segments_preserve_source(source_text: str, segments: list[dict[str, Any]]) -> bool:
    joined = " ".join(str(segment.get("text") or "") for segment in segments)
    return _canonical_for_preservation(source_text) == _canonical_for_preservation(joined)


def _canonical_for_preservation(text: str) -> str:
    text = re.sub(r"[—–-]", "", text or "")
    return re.sub(r"\s+", "", text)


def _system_prompt_for_language(language: str | None) -> str:
    code = normalize_book_language(language)
    return _SYSTEM_PROMPTS.get(code, _SYSTEM_PROMPTS["ru"])


def apply_paragraph_boundary_pauses(rows: list[dict[str, Any]]) -> None:
    """Ensure rows that already mark paragraph boundaries carry a pause."""

    for row in rows:
        if row.get("boundary_after") == "paragraph":
            row["pause_after_ms"] = max(
                _safe_int(row.get("pause_after_ms")),
                DEFAULT_PARAGRAPH_PAUSE_MS,
            )
