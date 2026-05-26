"""LLM smart voice segmentation for GUI segment manifests."""

from __future__ import annotations

import json
import logging
import re
import unicodedata
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

DEFAULT_WINDOW_CHARS = 900
_CACHE_VERSION = "llm-segmenter-v4-preservation-retry"

ROLE_TO_VOICE_ID = {
    "narrator": "narrator_calm",
    "male": "male_young",
    "female": "female_warm",
    "unknown": "narrator_calm",
}

_QUOTE_CHARS = frozenset("\"“”„‟«»‹›「」『』《》〈〉")
_DASH_CHARS = frozenset("—–-")

VOICE_LABEL_TO_ROLE = {
    "narrator": "narrator",
    "men": "male",
    "male": "male",
    "women": "female",
    "female": "female",
    "unknown": "unknown",
}

_SYSTEM_SECTION_KINDS = frozenset({
    "annotation",
    "preface",
    "epilogue",
    "chapter_title",
})

_RU_BAD_SPEAKER_TOKENS = frozenset({
    "а",
    "будешь",
    "в",
    "же",
    "здесь",
    "и",
    "или",
    "как",
    "мне",
    "на",
    "не",
    "но",
    "он",
    "она",
    "они",
    "оно",
    "от",
    "с",
    "сам",
    "сама",
    "самым",
    "себе",
    "сразу",
    "так",
    "тем",
    "то",
    "ты",
    "у",
    "я",
})

_RU_MALE_ATTRIBUTION = (
    "сказал",
    "ответил",
    "спросил",
    "крикнул",
    "прошептал",
    "произнёс",
    "произнес",
    "проговорил",
    "воскликнул",
    "пробормотал",
    "буркнул",
    "проронил",
    "добавил",
    "продолжил",
    "заметил",
    "подтвердил",
    "возразил",
    "закричал",
    "промолвил",
    "выдохнул",
    "простонал",
    "процедил",
    "прокричал",
    "пояснил",
    "напомнил",
    "согласился",
    "попросил",
    "приказал",
    "велел",
    "потребовал",
    "предложил",
    "переспросил",
    "усмехнулся",
    "рассмеялся",
    "вздохнул",
    "поинтересовался",
    "обратился",
    "задал",
    "начал",
)

_RU_FEMALE_ATTRIBUTION = (
    "сказала",
    "ответила",
    "спросила",
    "крикнула",
    "прошептала",
    "произнесла",
    "проговорила",
    "воскликнула",
    "пробормотала",
    "буркнула",
    "проронила",
    "добавила",
    "продолжила",
    "заметила",
    "подтвердила",
    "возразила",
    "закричала",
    "промолвила",
    "выдохнула",
    "простонала",
    "процедила",
    "прокричала",
    "пояснила",
    "напомнила",
    "согласилась",
    "попросила",
    "приказала",
    "велела",
    "потребовала",
    "предложила",
    "переспросила",
    "усмехнулась",
    "рассмеялась",
    "вздохнула",
    "поинтересовалась",
    "обратилась",
    "зашипела",
    "начала",
)

_RU_SPEAKER_TOKEN = r"[А-ЯЁ][А-ЯЁа-яё-]{1,40}|[а-яё]{3,40}"
_RU_ATTRIBUTION_MIDWORDS = r"(?:вопрос|запираться)"
_RU_MALE_ATTRIBUTION_RE = re.compile(
    rf"\b(?:{'|'.join(_RU_MALE_ATTRIBUTION)})\b"
    rf"(?:\s+{_RU_ATTRIBUTION_MIDWORDS}){{0,2}}\s+(?P<speaker>{_RU_SPEAKER_TOKEN})",
    re.IGNORECASE,
)
_RU_FEMALE_ATTRIBUTION_RE = re.compile(
    rf"\b(?:{'|'.join(_RU_FEMALE_ATTRIBUTION)})\b"
    rf"(?:\s+{_RU_ATTRIBUTION_MIDWORDS}){{0,2}}\s+(?P<speaker>{_RU_SPEAKER_TOKEN})",
    re.IGNORECASE,
)
_EN_SPEAKER_RE = re.compile(
    r"\b(?:(?:said|asked|replied|shouted|whispered|cried|muttered)\s+"
    r"(?P<after>[A-Z][A-Za-z'-]{1,40})|"
    r"(?P<before>[A-Z][A-Za-z'-]{1,40})\s+"
    r"(?:said|asked|replied|shouted|whispered|cried|muttered))\b"
)
_EN_MALE_ATTRIBUTION_RE = re.compile(
    r"\b(?:(?:he|him)\s+(?:said|asked|replied|shouted|whispered|cried|muttered)|"
    r"(?:said|asked|replied|shouted|whispered|cried|muttered)\s+(?:he|him))\b",
    re.IGNORECASE,
)
_EN_FEMALE_ATTRIBUTION_RE = re.compile(
    r"\b(?:(?:she|her)\s+(?:said|asked|replied|shouted|whispered|cried|muttered)|"
    r"(?:said|asked|replied|shouted|whispered|cried|muttered)\s+(?:she|her))\b",
    re.IGNORECASE,
)

_ZH_SPEAKER_RE = re.compile(
    r"[”」』》〉\"，,、。！？!?]\s*"
    r"(?P<speaker>[\u3400-\u9fff]{1,12})(?:低声说|说道|问道|说|問|问|喊|回答)"
)
_ZH_MALE_ATTRIBUTION_RE = re.compile(r"(?:他(?:低声说|说道|问道|说|問|问|喊|回答))")
_ZH_FEMALE_ATTRIBUTION_RE = re.compile(r"(?:她(?:低声说|说道|问道|说|問|问|喊|回答))")
_ZH_BAD_SPEAKER_TOKENS = frozenset({"他", "她", "它", "他们", "她们", "它们"})

_KK_SPEAKER_TOKEN = r"[А-ЯӘҒҚҢӨҰҮҺІ][А-Яа-яӘәҒғҚқҢңӨөҰұҮүҺһІі-]{1,40}"
_KK_ATTRIBUTION_RE = re.compile(
    rf"\b(?:деді|сұрады|жауап\s+берді|айқайлады|сыбырлады)\s+(?P<speaker>{_KK_SPEAKER_TOKEN})",
    re.IGNORECASE,
)

_UZ_SPEAKER_TOKEN = r"[A-ZÀ-Žʻʼ][A-Za-zÀ-žʻʼ'-]{1,40}"
_UZ_ATTRIBUTION_RE = re.compile(
    rf"\b(?:dedi|so['ʻʼ]?radi|soradi|javob\s+berdi|qichqirdi|pichirladi)\s+"
    rf"(?P<speaker>{_UZ_SPEAKER_TOKEN})",
    re.IGNORECASE,
)

_SEGMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "role": {"type": "string", "enum": ["narrator", "male", "female"]},
                    "speaker": {"type": "string"},
                    "character_description": {"type": "string"},
                    "emotion": {"type": "string"},
                    "section_kind": {
                        "type": "string",
                        "enum": [
                            "narration",
                            "dialogue",
                            "annotation",
                            "preface",
                            "epilogue",
                            "chapter_title",
                        ],
                    },
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
Для прямой речи заполняй speaker именем персонажа, если оно доказано контекстом; иначе оставь пустым.
Для speaker дай краткий character_description и emotion. Для аннотаций/предисловий/эпилогов ставь section_kind.
Интонация должна быть короткой на английском: calm, tense, angry, whisper, sad, cheerful, fearful, urgent.
Верни только JSON вида {"segments": [{"role": "...", "speaker": "...", "text": "...", "intonation": "..."}]}.
""",
    "en": """\
You are a multi-voice audiobook director for English fiction.
Split the text into small ordered TTS segments while preserving every word in order.
Never rewrite, translate, add, remove, or summarize text.
Dialogue must be separated from narration and speech tags.
Roles: narrator, male, female. Use narrator when gender is not clear.
For dialogue, fill speaker with the proven character name when context supports it; otherwise leave it empty.
For each speaker add character_description and emotion.
Use section_kind for annotation, preface, epilogue, and chapter titles.
Use short English intonation labels such as calm, tense, angry, whisper, sad, cheerful, fearful, urgent.
Return only JSON: {"segments": [{"role": "...", "speaker": "...", "text": "...", "intonation": "..."}]}.
""",
    "zh": """\
你是中文有声书的多声线导演。
把文本拆成按顺序排列的小 TTS 片段，并完整保留原文。
不要改写、翻译、增加、删除或总结。
对话必须和叙述/说话标签分开。角色只能是 narrator、male、female；性别不明确时用 narrator。
对话中如果上下文能证明人物姓名，请填写 speaker；否则留空。
为人物填写 character_description 和 emotion。注释、前言、后记、章节标题请填写 section_kind。
intonation 用简短英文，例如 calm、tense、angry、whisper、sad、cheerful、fearful、urgent。
只返回 JSON：{"segments": [{"role": "...", "speaker": "...", "text": "...", "intonation": "..."}]}。
""",
    "kk": """\
Сен қазақ көркем мәтінін көп дауысты аудиокітапқа бөлетін режиссёрсің.
Мәтінді ретімен шағын TTS сегменттерге бөл және әр сөзді толық сақта.
Қайта жазба, аударма, сөз қоспа, сөз алып тастама, қысқартпа.
Диалогты баяндаудан және сөйлеу ремаркаларынан бөлек сегмент қыл.
Рөлдер: narrator, male, female. Жыныс анық болмаса narrator қолдан.
Диалогта кейіпкер аты контекстен анық болса speaker толтыр; анық болмаса бос қалдыр.
Кейіпкерге character_description және emotion бер.
Аннотация/алғысөз/эпилог/тарау атауы үшін section_kind қолдан.
intonation қысқа ағылшынша болсын: calm, tense, angry, whisper, sad, cheerful, fearful, urgent.
Тек JSON қайтар: {"segments": [{"role": "...", "speaker": "...", "text": "...", "intonation": "..."}]}.
""",
    "uz": """\
Siz o'zbek badiiy matnini ko'p ovozli audiokitob uchun belgilaydigan rejissorsiz.
Matnni ketma-ket kichik TTS segmentlarga ajrating va barcha so'zlarni tartibda saqlang.
Qayta yozmang, tarjima qilmang, qo'shmang, olib tashlamang yoki qisqartirmang.
Dialog alohida, muallif matni va nutq izohlari alohida narrator segment bo'lsin.
Rollar: narrator, male, female. Jins aniq bo'lmasa narrator ishlating.
Dialogda qahramon nomi kontekstdan aniq bo'lsa speaker to'ldiring; aks holda bo'sh qoldiring.
Har speaker uchun character_description va emotion bering.
Annotatsiya, so'zboshi, epilog va bob sarlavhalari uchun section_kind ishlating.
intonation qisqa inglizcha bo'lsin: calm, tense, angry, whisper, sad, cheerful, fearful, urgent.
Faqat JSON qaytaring: {"segments": [{"role": "...", "speaker": "...", "text": "...", "intonation": "..."}]}.
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
                        speaker = _clean_optional(raw.get("speaker"))
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
                    if reconciled is not None:
                        segments = reconciled
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
            return _source_fallback_segments(window_text)

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
        paragraph_parts = (
            chunk_text(paragraph, max_chunk_chars=max_chars)
            if len(paragraph) > max_chars
            else [paragraph]
        )
        for part in paragraph_parts:
            sep = 2 if current else 0
            if current and current_len + sep + len(part) > max_chars:
                windows.append("\n\n".join(current))
                current = [part]
                current_len = len(part)
            else:
                current.append(part)
                current_len += sep + len(part)
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
                "speaker": _clean_optional(item.get("speaker") or item.get("character")),
                "character_description": _clean_optional(
                    item.get("character_description")
                    or item.get("role_description")
                    or item.get("description")
                ),
                "emotion": _clean_intonation(item.get("emotion") or item.get("intonation") or "calm"),
                "section_kind": _clean_section_kind(item.get("section_kind"), role),
                "text": text,
                "intonation": _clean_intonation(item.get("intonation") or item.get("voice_tone") or "calm"),
                "pause_after_ms": _safe_int(item.get("pause_after_ms")),
                "boundary_after": str(item.get("boundary_after") or ""),
            }
        )
    return segments


def _source_fallback_segments(window_text: str) -> list[dict[str, Any]]:
    """Preserve a failed LLM window as a safe narrator segment."""
    return [
        {
            "role": "narrator",
            "speaker": "",
            "character_description": "",
            "emotion": "neutral",
            "section_kind": "narration",
            "text": window_text,
            "intonation": "calm",
            "pause_after_ms": 0,
            "boundary_after": "",
        }
    ]


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


def _repair_dialogue_metadata(
    *,
    role: str,
    speaker: str,
    section_kind: str,
    character_description: str,
    text: str,
    language: str,
    recent_dialogue_speakers: list[tuple[str, str]],
) -> tuple[str, str, str, str]:
    if section_kind in _SYSTEM_SECTION_KINDS:
        return role, speaker, section_kind, character_description
    if not _has_direct_speech_marker(text):
        return role, speaker, section_kind, character_description

    inferred_speaker, inferred_role = _infer_dialogue_speaker(text, language)
    if inferred_speaker:
        speaker = speaker or inferred_speaker
    if inferred_role in {"male", "female"}:
        role = inferred_role

    if not speaker:
        speaker, known_role = _alternate_dialogue_speaker(recent_dialogue_speakers, role)
        if known_role in {"male", "female"} and role == "narrator":
            role = known_role

    if role == "narrator":
        role = "unknown"

    if not section_kind or section_kind == "narration":
        section_kind = "dialogue"
    if speaker and not character_description:
        character_description = "Direct-speech character inferred from local dialogue context."
    return role, speaker, section_kind, character_description


def _has_direct_speech_marker(text: str) -> bool:
    stripped = text.lstrip()
    return bool(stripped and (stripped[0] in _QUOTE_CHARS or stripped[0] in _DASH_CHARS))


def _infer_dialogue_speaker(text: str, language: str) -> tuple[str, str]:
    language = normalize_book_language(language)
    if language == "ru":
        return _infer_ru_dialogue_speaker(text)
    if language == "en":
        return _infer_en_dialogue_speaker(text)
    if language == "zh":
        return _infer_zh_dialogue_speaker(text)
    if language == "kk":
        return _infer_regex_dialogue_speaker(text, _KK_ATTRIBUTION_RE, _clean_cyrillic_speaker)
    if language == "uz":
        return _infer_regex_dialogue_speaker(text, _UZ_ATTRIBUTION_RE, _clean_latin_speaker)
    return "", ""


def _infer_ru_dialogue_speaker(text: str) -> tuple[str, str]:
    for regex, role in (
        (_RU_MALE_ATTRIBUTION_RE, "male"),
        (_RU_FEMALE_ATTRIBUTION_RE, "female"),
    ):
        for match in regex.finditer(text):
            speaker = _clean_ru_speaker(match.group("speaker"))
            if speaker:
                return speaker, role
    if _text_has_ru_gendered_attribution(text, _RU_MALE_ATTRIBUTION):
        return "", "male"
    if _text_has_ru_gendered_attribution(text, _RU_FEMALE_ATTRIBUTION):
        return "", "female"
    return "", ""


def _infer_en_dialogue_speaker(text: str) -> tuple[str, str]:
    role = ""
    if _EN_MALE_ATTRIBUTION_RE.search(text or ""):
        role = "male"
    elif _EN_FEMALE_ATTRIBUTION_RE.search(text or ""):
        role = "female"
    match = _EN_SPEAKER_RE.search(text or "")
    if not match:
        return "", role
    speaker = _clean_optional(match.group("after") or match.group("before"))
    return speaker, role or ("unknown" if speaker else "")


def _infer_zh_dialogue_speaker(text: str) -> tuple[str, str]:
    role = ""
    if _ZH_MALE_ATTRIBUTION_RE.search(text or ""):
        role = "male"
    elif _ZH_FEMALE_ATTRIBUTION_RE.search(text or ""):
        role = "female"
    for match in _ZH_SPEAKER_RE.finditer(text or ""):
        speaker = _clean_zh_speaker(match.group("speaker"))
        if speaker:
            return speaker, role or "unknown"
    return "", role


def _infer_regex_dialogue_speaker(
    text: str,
    regex: re.Pattern[str],
    cleaner: Callable[[str], str],
) -> tuple[str, str]:
    for match in regex.finditer(text or ""):
        speaker = cleaner(match.group("speaker"))
        if speaker:
            return speaker, "unknown"
    return "", ""


def _clean_ru_speaker(value: str) -> str:
    speaker = re.sub(r"^[\s,.;:!?—–-]+|[\s,.;:!?—–-]+$", "", value or "")
    if not speaker:
        return ""
    if speaker.casefold() in _RU_BAD_SPEAKER_TOKENS:
        return ""
    if not re.fullmatch(_RU_SPEAKER_TOKEN, speaker):
        return ""
    if speaker[0].islower():
        speaker = speaker[0].upper() + speaker[1:]
    return _clean_optional(speaker)


def _clean_cyrillic_speaker(value: str) -> str:
    speaker = re.sub(r"^[\s,.;:!?—–-]+|[\s,.;:!?—–-]+$", "", value or "")
    if not re.fullmatch(_KK_SPEAKER_TOKEN, speaker or ""):
        return ""
    return _clean_optional(speaker)


def _clean_latin_speaker(value: str) -> str:
    speaker = re.sub(r"^[\s,.;:!?—–-]+|[\s,.;:!?—–-]+$", "", value or "")
    if not re.fullmatch(_UZ_SPEAKER_TOKEN, speaker or ""):
        return ""
    return _clean_optional(speaker)


def _clean_zh_speaker(value: str) -> str:
    speaker = re.sub(
        r"^[\s，。！？、；：“”‘’「」『』《》〈〉]+|[\s，。！？、；：“”‘’「」『』《》〈〉]+$",
        "",
        value or "",
    )
    if not speaker or speaker in _ZH_BAD_SPEAKER_TOKENS:
        return ""
    if not re.fullmatch(r"[\u3400-\u9fff]{1,12}", speaker):
        return ""
    return _clean_optional(speaker)


def _text_has_ru_gendered_attribution(text: str, verbs: tuple[str, ...]) -> bool:
    return bool(re.search(rf"\b(?:{'|'.join(verbs)})\b", text or "", re.IGNORECASE))


def _alternate_dialogue_speaker(
    recent_dialogue_speakers: list[tuple[str, str]],
    role: str,
) -> tuple[str, str]:
    if not recent_dialogue_speakers:
        return "", ""
    previous_speaker, _previous_role = recent_dialogue_speakers[-1]
    for speaker, speaker_role in reversed(recent_dialogue_speakers[:-1]):
        if speaker and speaker != previous_speaker:
            if role in {"male", "female"} and speaker_role not in {role, "unknown"}:
                continue
            return speaker, speaker_role
    return "", ""


def _remember_dialogue_speaker(
    recent_dialogue_speakers: list[tuple[str, str]],
    *,
    speaker: str,
    role: str,
) -> None:
    if not speaker:
        return
    normalized_role = role if role in {"male", "female"} else "unknown"
    record = (speaker, normalized_role)
    if recent_dialogue_speakers and recent_dialogue_speakers[-1] == record:
        return
    recent_dialogue_speakers.append(record)
    del recent_dialogue_speakers[:-8]


def _clean_intonation(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "calm")).strip().lower()
    return text[:80] or "calm"


def _clean_optional(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:180]


def _clean_section_kind(value: Any, role: str) -> str:
    text = re.sub(r"\s+", "_", str(value or "").strip().lower())
    allowed = {
        "narration",
        "dialogue",
        "annotation",
        "preface",
        "epilogue",
        "chapter_title",
    }
    if text in allowed:
        return text
    return "dialogue" if role in {"male", "female", "unknown"} else "narration"


def _is_dialogue_segment(
    *,
    role: str,
    section_kind: str,
    speaker: str,
    text: str,
) -> bool:
    """Detect direct speech even when the LLM cannot prove speaker gender."""
    if role in {"male", "female", "unknown"} or section_kind == "dialogue" or speaker:
        return True
    stripped = text.lstrip()
    return bool(stripped and (stripped[0] in _QUOTE_CHARS or stripped[0] in _DASH_CHARS))


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _segments_preserve_source(source_text: str, segments: list[dict[str, Any]]) -> bool:
    joined = " ".join(str(segment.get("text") or "") for segment in segments)
    return _canonical_for_preservation(source_text) == _canonical_for_preservation(joined)


def _reconcile_segments_to_source(
    source_text: str,
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]] | None:
    """Restore exact source punctuation around LLM-proposed segment boundaries."""
    source_canonical, source_map = _canonical_with_index_map(source_text)
    if not source_canonical:
        return None

    spans: list[tuple[int, int]] = []
    offset = 0
    previous_end = 0
    for segment in segments:
        segment_canonical, _segment_map = _canonical_with_index_map(str(segment.get("text") or ""))
        if not segment_canonical:
            return None
        if not source_canonical.startswith(segment_canonical, offset):
            return None

        start = source_map[offset]
        end = source_map[offset + len(segment_canonical) - 1] + 1
        start = _extend_segment_start(source_text, start, previous_end)
        end = _extend_segment_end(source_text, end)
        spans.append((start, end))
        previous_end = end
        offset += len(segment_canonical)

    if offset != len(source_canonical):
        return None

    reconciled: list[dict[str, Any]] = []
    for segment, (start, end) in zip(segments, spans, strict=True):
        restored = source_text[start:end].strip()
        if not restored:
            return None
        row = dict(segment)
        row["text"] = restored
        reconciled.append(row)
    return reconciled


def _canonical_with_index_map(text: str) -> tuple[str, list[int]]:
    chars: list[str] = []
    indexes: list[int] = []
    for index, char in enumerate(text or ""):
        if char.isspace() or _is_match_ignored_char(char):
            continue
        chars.append(char)
        indexes.append(index)
    return "".join(chars), indexes


def _extend_segment_start(source_text: str, start: int, lower_bound: int) -> int:
    while start > lower_bound and _is_match_ignored_char(source_text[start - 1]):
        start -= 1

    probe = start
    while probe > lower_bound and source_text[probe - 1].isspace() and source_text[probe - 1] not in "\r\n":
        probe -= 1
    if probe > lower_bound and source_text[probe - 1] in _DASH_CHARS:
        return probe - 1
    return start


def _extend_segment_end(source_text: str, end: int) -> int:
    while end < len(source_text):
        if _is_match_ignored_char(source_text[end]):
            end += 1
            continue
        probe = end
        while probe < len(source_text) and source_text[probe].isspace() and source_text[probe] not in "\r\n":
            probe += 1
        if probe < len(source_text) and _is_match_ignored_char(source_text[probe]):
            end = probe
            continue
        break
    return end


def _is_match_ignored_char(char: str) -> bool:
    return char in _DASH_CHARS or unicodedata.category(char).startswith("P")


def _canonical_for_preservation(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _system_prompt_for_language(language: str | None) -> str:
    code = normalize_book_language(language)
    return _SYSTEM_PROMPTS.get(code, _SYSTEM_PROMPTS["ru"])


def _user_prompt_for_window(
    *,
    language: str,
    chapter_index: int,
    window_index: int,
    window_text: str,
    previous_issues: list[str] | None = None,
) -> str:
    retry_guard = ""
    if previous_issues:
        retry_guard = (
            "\nPREVIOUS_OUTPUT_FAILED_VALIDATION:\n"
            + json.dumps({"issues": previous_issues[:6]}, ensure_ascii=False)
            + "\nThe next answer must preserve input.text exactly. "
            "If dialogue boundaries are uncertain, return fewer larger segments."
        )
    return (
        "Input is JSON. Segment only input.text. "
        "Preserve quoted dialogue, apostrophes, punctuation, and word order. "
        "The ordered concatenation of all segment.text values must reproduce "
        "input.text exactly after whitespace normalization.\n"
        "INPUT_JSON:\n"
        + json.dumps(
            {
                "language": get_book_language(language).english_name,
                "chapter": chapter_index + 1,
                "window": window_index + 1,
                "text": window_text,
            },
            ensure_ascii=False,
        )
        + retry_guard
    )


def apply_paragraph_boundary_pauses(rows: list[dict[str, Any]]) -> None:
    """Ensure rows that already mark paragraph boundaries carry a pause."""

    for row in rows:
        if row.get("boundary_after") == "paragraph":
            row["pause_after_ms"] = max(
                _safe_int(row.get("pause_after_ms")),
                DEFAULT_PARAGRAPH_PAUSE_MS,
            )
