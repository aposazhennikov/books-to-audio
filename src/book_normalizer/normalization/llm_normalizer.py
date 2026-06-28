"""LLM-based text normalizer for multilingual literary prose.

Runs a single Ollama pass over each paragraph (or short block) to:
  - fix typos and spelling errors,
  - improve punctuation (comma placement, em-dashes, quotation marks),
  - restore the letter Ё where it belongs (yofication),

CRITICAL constraint: the LLM must NOT change the story, rephrase
sentences, add new content, or remove existing sentences.

After every LLM response the result is validated by
:class:`TextPreservationValidator`.  If the validator rejects the
output (similarity too low, words added/removed), the original
paragraph is kept unchanged and a warning is logged.

All results are cached per (chapter_index, paragraph_index) so the
pipeline can be resumed without re-querying the LLM.

Usage::

    normalizer = LlmNormalizer(
        endpoint="http://localhost:11434",
        cache_dir=Path("output/mybook/llm_norm_cache"),
    )
    corrected_text = normalizer.normalize_chapter(raw_text, chapter_index=0)
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from typing import TYPE_CHECKING, Any

from book_normalizer.languages import get_book_language, normalize_book_language
from book_normalizer.llm.model_router import model_plan_for_language
from book_normalizer.llm.ollama_client import OllamaChatClient
from book_normalizer.normalization.text_validator import (
    TextPreservationValidator,
    ValidationResult,
)
from book_normalizer.prompts.loader import load_language_prompt, load_prompt

if TYPE_CHECKING:
    from book_normalizer.models.book import Book

logger = logging.getLogger(__name__)

BookProgressCallback = Callable[[int, int, int, int], None]

# ── Prompt ────────────────────────────────────────────────────────────────────

_PROMPTS: dict[str, str] = {
    "ru": """\
Ты — корректор русского текста. Твоя задача — минимальная правка:

1. Исправь явные опечатки, OCR-артефакты и орфографические ошибки.
2. Улучши пунктуацию: запятые, точки и тире только там, где это безопасно.
3. Восстанови букву «Ё» там, где она необходима.

СТРОГО ЗАПРЕЩЕНО:
- Менять сюжет, события, имена персонажей или топонимы.
- Добавлять или удалять предложения.
- Перефразировать или менять стиль автора.
- Добавлять пояснения, комментарии или заголовки.

Если безопасная правка невозможна, верни исходный текст без изменений.
Верни JSON строго такого вида: {"text": "исправленный текст"}.
""",
    "en": """\
You are a careful English literary proofreader. Make only minimal corrections:

1. Fix obvious OCR, spelling, spacing, and punctuation errors.
2. Preserve the author's wording, sentence order, names, places, and style.
3. Do not summarize, rewrite, add explanations, remove sentences, or translate.

If a safe minimal correction is impossible, return the input text unchanged.
Return strict JSON only: {"text": "corrected text"}.
""",
    "zh": """\
你是中文小说文本校对员。只做最小必要修改：

1. 修正明显 OCR、错别字、空格和标点问题。
2. 保留原文内容、人物、地名、句子顺序和作者风格。
3. 不要改写、扩写、删句、解释或翻译。

如果不能安全修改，请原样返回输入文本。
只返回严格 JSON：{"text": "校对后的文本"}。
""",
    "kk": """\
Сен қазақ тіліндегі көркем мәтінді мұқият түзететін редакторсың. Тек ең аз түзету жаса:

1. Айқын OCR, емле, бос орын және тыныс белгілер қателерін түзет.
2. Автор стилін, сөйлем тәртібін, есімдерді және жер атауларын сақта.
3. Қайта жазба, қысқартпа, жаңа сөйлем қоспа, түсініктеме берме және аударма.

Қауіпсіз түзету жасау мүмкін болмаса, бастапқы мәтінді өзгертпей қайтар.
Тек қатаң JSON қайтар: {"text": "түзетілген мәтін"}.
""",
    "uz": """\
Siz o'zbek adabiy matnini ehtiyotkor tahrir qiluvchi muharrirsiz. Faqat minimal tuzatish qiling:

1. Aniq OCR, imlo, bo'shliq va tinish belgisi xatolarini tuzating.
2. Muallif uslubi, gap tartibi, ismlar va joy nomlarini saqlang.
3. Qayta yozmang, qisqartirmang, yangi gap qo'shmang, izoh bermang va tarjima qilmang.

Agar xavfsiz minimal tuzatish imkonsiz bo'lsa, kirish matnini o'zgarishsiz qaytaring.
Faqat qat'iy JSON qaytaring: {"text": "tuzatilgan matn"}.
""",
}

_NORMALIZATION_SCHEMA = {
    "type": "object",
    "properties": {"text": {"type": "string"}},
    "required": ["text"],
}

_TITLE_CORRECTION_SCHEMA = {
    "type": "object",
    "properties": {"title": {"type": "string"}},
    "required": ["title"],
}


@dataclass
class NormalizationFailure:
    """One LLM normalization attempt that needs human review."""

    chapter_index: int
    paragraph_index: int
    model: str
    reason: str
    source_preview: str
    output_preview: str = ""

    def to_record(self) -> dict[str, Any]:
        return {
            "chapter_index": self.chapter_index,
            "paragraph_index": self.paragraph_index,
            "model": self.model,
            "reason": self.reason,
            "source_preview": self.source_preview,
            "output_preview": self.output_preview,
        }


# ── LlmNormalizer ─────────────────────────────────────────────────────────────


class LlmNormalizer:
    """Correct grammar, punctuation, and OCR noise with local Ollama.

    Args:
        endpoint:   Native Ollama API base URL.
        model:      Optional model override; blank selects the language router.
        cache_dir:  Directory for paragraph-level result cache.
        validator:  Custom :class:`TextPreservationValidator` instance.
                    If *None*, a default validator is created.
        api_key:    Bearer token (leave empty for local Ollama).
        max_retries: How many times to retry a failed/rejected LLM call.
    """

    def __init__(
        self,
        endpoint: str = "http://localhost:11434",
        model: str = "",
        cache_dir: Path | None = None,
        validator: TextPreservationValidator | None = None,
        api_key: str = "",
        max_retries: int = 2,
        language: str = "ru",
        lightweight: bool = False,
        review_report_path: Path | None = None,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._language = normalize_book_language(language)
        self._model_plan = model_plan_for_language(
            self._language,
            preferred_model=model,
            lightweight=lightweight,
        )
        self._model = self._model_plan.primary_model
        self._model_candidates = self._model_plan.candidates
        self._cache_dir = cache_dir
        self._validator = validator or TextPreservationValidator()
        self._api_key = api_key
        self._max_retries = max_retries
        self._review_report_path = review_report_path
        self._failures: list[NormalizationFailure] = []
        self._client = OllamaChatClient(
            endpoint=endpoint,
            api_key=api_key,
            num_ctx=self._model_plan.num_ctx,
            num_parallel=self._model_plan.num_parallel,
            keep_alive=self._model_plan.keep_alive,
            think=self._model_plan.think,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def normalize_chapter(
        self,
        chapter_text: str,
        chapter_index: int = 0,
    ) -> str:
        """Normalise all paragraphs in a chapter text.

        Paragraphs are split by ``\\n\\n``.  Each paragraph is corrected
        individually and then reassembled.  If a paragraph's corrected version
        fails validation, the original paragraph is kept.

        Args:
            chapter_text:  Full text of one chapter (paragraphs sep by \\n\\n).
            chapter_index: Zero-based chapter index (used for cache keys).

        Returns:
            Normalised chapter text with ``\\n\\n`` paragraph separators.
        """
        paragraphs = [p.strip() for p in chapter_text.split("\n\n") if p.strip()]
        if not paragraphs:
            return chapter_text

        corrected_parts: list[str] = []
        accepted = rejected = 0

        for para_idx, para in enumerate(paragraphs):
            if para_idx == 0 and _is_title_like_paragraph(para):
                result = self.normalize_title(para, chapter_index, para_idx)
            else:
                result = self.normalize_paragraph(para, chapter_index, para_idx)
            corrected_parts.append(result.accepted_text)
            if result.is_valid:
                accepted += 1
            else:
                rejected += 1
                logger.warning(
                    "Chapter %d paragraph %d: LLM output rejected (%s) — keeping original",
                    chapter_index, para_idx, "; ".join(result.issues),
                )

        logger.info(
            "Chapter %d normalisation: %d paragraphs accepted, %d kept original",
            chapter_index, accepted, rejected,
        )
        return "\n\n".join(corrected_parts)

    def normalize_title(
        self,
        text: str,
        chapter_index: int,
        paragraph_index: int,
    ) -> ValidationResult:
        """Normalise a short chapter title with stricter title-specific guards."""

        if not text or not text.strip():
            return ValidationResult(
                is_valid=True,
                similarity=1.0,
                word_ratio=1.0,
                sentence_ratio=1.0,
                original=text,
                corrected=text,
            )

        cached = self._load_cache(chapter_index, paragraph_index, text, kind="title")
        if cached is not None:
            cached_result = _validate_title_correction(text, cached)
            if cached_result.is_valid:
                return cached_result
            self._discard_cache(chapter_index, paragraph_index, text, kind="title")

        corrected: str | None = None
        last_error: Exception | None = None
        last_issues: list[str] = []

        for attempt in range(1, self._max_retries + 1):
            for model in self._model_candidates:
                try:
                    raw = self._query_title_llm(text, model=model)
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    self._failures.append(
                        NormalizationFailure(
                            chapter_index=chapter_index,
                            paragraph_index=paragraph_index,
                            model=model,
                            reason=f"title {type(exc).__name__}: {exc}",
                            source_preview=text[:500],
                        )
                    )
                    continue

                if raw:
                    result = _validate_title_correction(text, raw)
                    if result.is_valid:
                        self._save_cache(chapter_index, paragraph_index, text, raw, kind="title")
                        return result

                    corrected = raw
                    last_issues = list(result.issues)
                    self._failures.append(
                        NormalizationFailure(
                            chapter_index=chapter_index,
                            paragraph_index=paragraph_index,
                            model=model,
                            reason="title " + "; ".join(result.issues),
                            source_preview=text[:500],
                            output_preview=raw[:500],
                        )
                    )
                    self._client.unload_model(model)

        issues: list[str] = []
        if last_error is not None:
            issues.append(f"LLM error: {type(last_error).__name__}: {last_error}")
        if last_issues:
            issues.append("Validation issues: " + "; ".join(last_issues))
        if not issues:
            issues.append("All title LLM attempts failed or returned empty output")

        return ValidationResult(
            is_valid=False,
            similarity=0.0,
            word_ratio=1.0,
            sentence_ratio=1.0,
            original=text,
            corrected=corrected or text,
            issues=issues,
        )

    def normalize_paragraph(
        self,
        text: str,
        chapter_index: int,
        paragraph_index: int,
    ) -> ValidationResult:
        """Normalise a single paragraph, with caching and fallback.

        Returns a :class:`ValidationResult`.  Call ``.accepted_text`` to get
        the corrected text (or the original if validation failed).

        Args:
            text:            Paragraph text.
            chapter_index:   Used for cache key.
            paragraph_index: Used for cache key.
        """
        if not text or not text.strip():
            return ValidationResult(
                is_valid=True,
                similarity=1.0,
                word_ratio=1.0,
                sentence_ratio=1.0,
                original=text,
                corrected=text,
            )

        # Check cache first.
        cached = self._load_cache(chapter_index, paragraph_index, text)
        if cached is not None:
            cached_result = self._validator.validate(text, cached)
            if cached_result.is_valid:
                return cached_result
            self._discard_cache(chapter_index, paragraph_index, text)
            self._failures.append(
                NormalizationFailure(
                    chapter_index=chapter_index,
                    paragraph_index=paragraph_index,
                    model="cache",
                    reason="Cached LLM output failed text preservation: "
                    + "; ".join(cached_result.issues),
                    source_preview=text[:500],
                    output_preview=cached[:500],
                )
            )

        corrected: str | None = None
        last_error: Exception | None = None
        last_issues: list[str] = []

        for attempt in range(1, self._max_retries + 1):
            for model in self._model_candidates:
                try:
                    if attempt > 1 and last_issues:
                        raw = self._query_llm(
                            text,
                            model=model,
                            previous_issues=last_issues,
                        )
                    else:
                        raw = self._query_llm(text, model=model)
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    logger.warning(
                        "Chapter %d paragraph %d attempt %d/%d model %s: LLM request failed: %s: %s",
                        chapter_index,
                        paragraph_index,
                        attempt,
                        self._max_retries,
                        model,
                        type(exc).__name__,
                        exc,
                    )
                    self._failures.append(
                        NormalizationFailure(
                            chapter_index=chapter_index,
                            paragraph_index=paragraph_index,
                            model=model,
                            reason=f"{type(exc).__name__}: {exc}",
                            source_preview=text[:500],
                        )
                    )
                    continue

                if raw:
                    result = self._validator.validate(text, raw)
                    if result.is_valid:
                        self._save_cache(chapter_index, paragraph_index, text, raw)
                        return result

                    last_issues = list(result.issues)
                    logger.debug(
                        "Chapter %d paragraph %d attempt %d/%d model %s: validation rejected — %s",
                        chapter_index,
                        paragraph_index,
                        attempt,
                        self._max_retries,
                        model,
                        "; ".join(result.issues),
                    )
                    self._failures.append(
                        NormalizationFailure(
                            chapter_index=chapter_index,
                            paragraph_index=paragraph_index,
                            model=model,
                            reason="; ".join(result.issues),
                            source_preview=text[:500],
                            output_preview=raw[:500],
                        )
                    )
                    corrected = raw
                    self._client.unload_model(model)
                else:
                    logger.debug(
                        "Chapter %d paragraph %d attempt %d/%d model %s: LLM returned empty text",
                        chapter_index,
                        paragraph_index,
                        attempt,
                        self._max_retries,
                        model,
                    )

        # All attempts failed or rejected — return original and surface reason.
        issues: list[str] = []
        if last_error is not None:
            issues.append(f"LLM error: {type(last_error).__name__}: {last_error}")
        if last_issues:
            issues.append("Validation issues: " + "; ".join(last_issues))
        if not issues:
            issues.append("All LLM attempts failed or returned empty output")

        logger.warning(
            "Chapter %d paragraph %d: LLM output rejected — %s",
            chapter_index,
            paragraph_index,
            "; ".join(issues),
        )
        self._write_review_report()

        similarity = 0.0
        if corrected is not None:
            similarity = self._validator.validate(text, corrected).similarity

        return ValidationResult(
            is_valid=False,
            similarity=similarity,
            word_ratio=1.0,
            sentence_ratio=1.0,
            original=text,
            corrected=corrected or text,
            issues=issues,
        )

    def normalize_book(
        self,
        book: Book,
        progress_callback: BookProgressCallback | None = None,
    ) -> tuple[int, int]:
        """Apply LLM normalization to every paragraph in a book.

        The method mutates ``paragraph.normalized_text`` in place. Rejected
        model outputs leave the paragraph text unchanged.

        Args:
            book: Book object to update.
            progress_callback: Optional callback called as
                ``(done, total, accepted, rejected)`` after each paragraph.

        Returns:
            ``(accepted, rejected)`` paragraph counts.
        """
        total = sum(len(chapter.paragraphs) for chapter in book.chapters)
        accepted = rejected = done = 0

        try:
            for chapter in book.chapters:
                for para in chapter.paragraphs:
                    source = para.normalized_text or para.raw_text
                    if not source.strip():
                        done += 1
                        if progress_callback is not None:
                            progress_callback(done, total, accepted, rejected)
                        continue

                    result = self.normalize_paragraph(
                        source,
                        chapter.index,
                        para.index_in_chapter,
                    )
                    if result.is_valid:
                        para.normalized_text = result.accepted_text
                        accepted += 1
                    else:
                        rejected += 1

                    done += 1
                    if progress_callback is not None:
                        progress_callback(done, total, accepted, rejected)
        finally:
            self._client.unload_models(self._model_candidates)

        book.add_audit(
            "llm_normalization",
            "pipeline_complete",
            f"models={list(self._model_candidates)}, endpoint={self._endpoint}, "
            f"language={self._language}, "
            f"paragraphs={total}, accepted={accepted}, rejected={rejected}",
        )
        if rejected and self._review_report_path is not None:
            self._write_review_report()
            book.add_audit(
                "llm_normalization",
                "review_required",
                f"report={self._review_report_path}, rejected={rejected}",
            )
        return accepted, rejected

    # ── LLM query ─────────────────────────────────────────────────────────────

    def _query_llm(
        self,
        text: str,
        *,
        model: str | None = None,
        previous_issues: list[str] | None = None,
    ) -> str:
        """Send one paragraph to a local Ollama model and return corrected text."""

        retry_guard = ""
        if previous_issues:
            retry_guard = (
                "\nPREVIOUS_OUTPUT_FAILED_VALIDATION:\n"
                + json.dumps({"issues": previous_issues[:6]}, ensure_ascii=False)
                + "\nReturn the original input.text unchanged if you cannot make a safe "
                "minimal correction while preserving every word and sentence."
            )

        attempt = self._client.chat_json_with_fallback(
            models=[model or self._model],
            messages=[
                {"role": "system", "content": _system_prompt_for_language(self._language)},
                {
                    "role": "user",
                    "content": (
                        load_prompt("normalization/minimal_text_correction_user.txt")
                        .replace(
                            "{{INPUT_JSON}}",
                            json.dumps(
                            {
                                "language": get_book_language(self._language).english_name,
                                "text": text,
                            },
                            ensure_ascii=False,
                            ),
                        )
                        .replace("{{RETRY_GUARD}}", retry_guard)
                    ),
                },
            ],
            schema=_NORMALIZATION_SCHEMA,
            temperature=0.05,
        )
        if isinstance(attempt.data, dict):
            return _clean_llm_output(str(attempt.data.get("text") or ""))
        return _clean_llm_output(attempt.content)

    def _query_title_llm(
        self,
        text: str,
        *,
        model: str | None = None,
    ) -> str:
        """Send one short title to a local Ollama model and return corrected title."""

        attempt = self._client.chat_json_with_fallback(
            models=[model or self._model],
            messages=[
                {
                    "role": "system",
                    "content": load_language_prompt(
                        "normalization",
                        "title_ocr_correction_system",
                        self._language,
                        fallback_language="en",
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        load_prompt("normalization/title_ocr_correction_user.txt")
                        .replace(
                            "{{INPUT_JSON}}",
                            json.dumps(
                                {
                                    "language": get_book_language(self._language).english_name,
                                    "title": text,
                                },
                                ensure_ascii=False,
                            ),
                        )
                    ),
                },
            ],
            schema=_TITLE_CORRECTION_SCHEMA,
            temperature=0.0,
        )
        if isinstance(attempt.data, dict):
            return _clean_llm_output(str(attempt.data.get("title") or ""))
        return _clean_llm_output(attempt.content)

    # ── Cache ─────────────────────────────────────────────────────────────────

    def _cache_path(
        self,
        chapter_index: int,
        paragraph_index: int,
        source_text: str,
        *,
        kind: str = "norm",
    ) -> Path | None:
        """Return cache file path for one paragraph."""
        if not self._cache_dir:
            return None
        fingerprint = self._cache_fingerprint(source_text, kind=kind)
        return (
            self._cache_dir
            / (
                f"{kind}_ch{chapter_index:03d}_para{paragraph_index:04d}"
                f"_{fingerprint}.txt"
            )
        )

    def _load_cache(
        self,
        chapter_index: int,
        paragraph_index: int,
        source_text: str,
        *,
        kind: str = "norm",
    ) -> str | None:
        """Return cached corrected text, or None if unavailable."""
        path = self._cache_path(chapter_index, paragraph_index, source_text, kind=kind)
        if path and path.exists():
            try:
                return path.read_text(encoding="utf-8")
            except OSError:
                return None
        return None

    def _discard_cache(
        self,
        chapter_index: int,
        paragraph_index: int,
        source_text: str,
        *,
        kind: str = "norm",
    ) -> None:
        """Remove a cached paragraph result that no longer passes validation."""
        path = self._cache_path(chapter_index, paragraph_index, source_text, kind=kind)
        if path is None:
            return
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.debug("Could not discard invalid LLM cache: %s", path)

    def _save_cache(
        self,
        chapter_index: int,
        paragraph_index: int,
        source_text: str,
        corrected_text: str,
        *,
        kind: str = "norm",
    ) -> None:
        """Persist corrected text to disk cache."""
        path = self._cache_path(chapter_index, paragraph_index, source_text, kind=kind)
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(corrected_text, encoding="utf-8")

    def _cache_fingerprint(self, source_text: str, *, kind: str = "norm") -> str:
        """Return a cache fingerprint for text + LLM settings."""
        prompt = _system_prompt_for_language(self._language)
        if kind == "title":
            prompt = load_language_prompt(
                "normalization",
                "title_ocr_correction_system",
                self._language,
                fallback_language="en",
            )
        payload = "\n\0".join((
            kind,
            ",".join(self._model_candidates),
            self._endpoint,
            self._language,
            prompt,
            source_text,
        ))
        return sha1(payload.encode("utf-8")).hexdigest()[:16]

    def _write_review_report(self) -> None:
        if self._review_report_path is None or not self._failures:
            return
        self._review_report_path.parent.mkdir(parents=True, exist_ok=True)
        self._review_report_path.write_text(
            json.dumps(
                {
                    "language": self._language,
                    "models": list(self._model_candidates),
                    "failures": [failure.to_record() for failure in self._failures],
                    "requires_human_review": True,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


# ── Helpers ───────────────────────────────────────────────────────────────────


def _clean_llm_output(content: str) -> str:
    """Strip markdown fences, leading/trailing quotes, and extra whitespace."""
    content = content.strip()
    # Remove markdown code fences.
    import re
    content = re.sub(r"^```[a-z]*\n?", "", content, flags=re.MULTILINE)
    content = re.sub(r"```\s*$", "", content, flags=re.MULTILINE)
    # Remove wrapping quotes the LLM sometimes adds.
    if (content.startswith('"') and content.endswith('"')) or \
       (content.startswith("'") and content.endswith("'")):
        content = content[1:-1]
    return content.strip()


def _is_title_like_paragraph(text: str) -> bool:
    """Return True for short standalone chapter headings, not prose."""

    stripped = text.strip()
    if not stripped or len(stripped) > 140:
        return False
    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    if not lines or len(lines) > 2:
        return False
    if any(line.startswith(("—", "-", "–")) for line in lines):
        return False
    if stripped.endswith((".", "!", "?", "…")):
        return False
    words = _title_words(stripped)
    return 1 <= len(words) <= 10


def _validate_title_correction(original: str, corrected: str) -> ValidationResult:
    """Validate a conservative OCR/spelling correction for a short heading."""

    base = TextPreservationValidator(
        min_similarity=0.72,
        min_word_ratio=0.95,
        max_word_ratio=1.05,
        min_sentence_ratio=0.95,
        max_sentence_ratio=1.05,
    ).validate(original, corrected)
    issues = [
        issue for issue in base.issues
        if not issue.startswith("Unexpected word substitution after OCR normalization:")
        and not issue.startswith("Word counts:")
        and not issue.startswith("Word mismatches:")
    ]

    original_words = _title_words(original)
    corrected_words = _title_words(corrected)
    if len(original_words) != len(corrected_words):
        issues.append(
            "Title word count changed: "
            f"original={len(original_words)}, corrected={len(corrected_words)}"
        )
    else:
        for idx, (source_word, corrected_word) in enumerate(zip(original_words, corrected_words)):
            if source_word == corrected_word:
                continue
            similarity = _word_similarity(source_word, corrected_word)
            if similarity < 0.67:
                issues.append(
                    f"Title word rewrite at {idx}: {source_word!r} -> {corrected_word!r}"
                )
                break

    return ValidationResult(
        is_valid=not issues,
        similarity=base.similarity,
        word_ratio=base.word_ratio,
        sentence_ratio=base.sentence_ratio,
        original=original,
        corrected=corrected,
        issues=issues,
    )


def _title_words(text: str) -> list[str]:
    import re

    return [word.casefold() for word in re.findall(r"[\wёЁ]+", text, flags=re.UNICODE)]


def _word_similarity(left: str, right: str) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    from difflib import SequenceMatcher

    return SequenceMatcher(None, left.casefold(), right.casefold()).ratio()


def _system_prompt_for_language(language: str | None) -> str:
    """Return the minimal-edit prompt for a selected book language."""

    code = normalize_book_language(language)
    return load_language_prompt("normalization", "minimal_text_correction_system", code)
