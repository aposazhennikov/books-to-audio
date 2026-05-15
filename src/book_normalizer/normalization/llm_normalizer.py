"""LLM-based text normalizer for Russian literary prose.

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
        endpoint="http://localhost:11434/v1",
        model="gemma3:4b",
        cache_dir=Path("output/mybook/llm_norm_cache"),
    )
    corrected_text = normalizer.normalize_chapter(raw_text, chapter_index=0)
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from hashlib import sha1
from pathlib import Path
from typing import TYPE_CHECKING, Any

from book_normalizer.normalization.text_validator import (
    TextPreservationValidator,
    ValidationResult,
)

if TYPE_CHECKING:
    from book_normalizer.models.book import Book

logger = logging.getLogger(__name__)

BookProgressCallback = Callable[[int, int, int, int], None]

# ── Prompt ────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
Ты — корректор русского текста. Твоя задача — минимальная правка:

1. Исправь явные опечатки и орфографические ошибки.
2. Улучши пунктуацию: расставь запятые, точки, тире там, где они нужны.
3. Восстанови букву «Ё» там, где она необходима (йо-фикация).

СТРОГО ЗАПРЕЩЕНО:
- Менять сюжет, события, имена персонажей или топонимы.
- Добавлять или удалять предложения.
- Перефразировать или менять стиль автора.
- Добавлять пояснения, комментарии или заголовки.

Верни ТОЛЬКО исправленный текст — без кавычек, без пояснений, без markdown.
"""

# ── LlmNormalizer ─────────────────────────────────────────────────────────────


class LlmNormalizer:
    """Correct grammar / punctuation / yofication of Russian text via Ollama.

    Args:
        endpoint:   OpenAI-compatible API base URL (default: Ollama).
        model:      Model identifier (e.g. ``"gemma3:4b"``).
        cache_dir:  Directory for paragraph-level result cache.
        validator:  Custom :class:`TextPreservationValidator` instance.
                    If *None*, a default validator is created.
        api_key:    Bearer token (leave empty for local Ollama).
        max_retries: How many times to retry a failed/rejected LLM call.
    """

    def __init__(
        self,
        endpoint: str = "http://localhost:11434/v1",
        model: str = "gemma3:4b",
        cache_dir: Path | None = None,
        validator: TextPreservationValidator | None = None,
        api_key: str = "",
        max_retries: int = 2,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._model = model
        self._cache_dir = cache_dir
        self._validator = validator or TextPreservationValidator()
        self._api_key = api_key
        self._max_retries = max_retries

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
            return self._validator.validate(text, cached)

        # Try LLM correction with retries.
        corrected: str | None = None
        last_error: Exception | None = None
        last_issues: list[str] = []

        for attempt in range(1, self._max_retries + 1):
            try:
                raw = self._query_llm(text)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning(
                    "Chapter %d paragraph %d attempt %d/%d: LLM request failed: %s: %s",
                    chapter_index,
                    paragraph_index,
                    attempt,
                    self._max_retries,
                    type(exc).__name__,
                    exc,
                )
                continue

            if raw:
                result = self._validator.validate(text, raw)
                if result.is_valid:
                    self._save_cache(chapter_index, paragraph_index, text, raw)
                    return result

                last_issues = list(result.issues)
                logger.debug(
                    "Chapter %d paragraph %d attempt %d/%d: validation rejected — %s",
                    chapter_index,
                    paragraph_index,
                    attempt,
                    self._max_retries,
                    "; ".join(result.issues),
                )
                corrected = raw  # keep last attempt even if invalid
            else:
                logger.debug(
                    "Chapter %d paragraph %d attempt %d/%d: LLM returned empty text",
                    chapter_index,
                    paragraph_index,
                    attempt,
                    self._max_retries,
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

        book.add_audit(
            "llm_normalization",
            "pipeline_complete",
            f"model={self._model}, endpoint={self._endpoint}, "
            f"paragraphs={total}, accepted={accepted}, rejected={rejected}",
        )
        return accepted, rejected

    # ── LLM query ─────────────────────────────────────────────────────────────

    def _query_llm(self, text: str) -> str:
        """Send one paragraph to the LLM and return the corrected text."""
        try:
            import httpx
        except ImportError:
            logger.error("httpx is required for LLM normalisation: pip install httpx")
            return ""

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            "temperature": 0.05,   # Very low — we want minimal changes.
        }

        try:
            resp = httpx.post(
                f"{self._endpoint}/chat/completions",
                json=payload,
                headers=headers,
                timeout=60.0,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:1000] if exc.response is not None else ""
            logger.error(
                "LLM normalisation HTTP error for model %s (status %s): %s\n"
                "Response body (truncated): %s",
                self._model,
                exc.response.status_code if exc.response is not None else "?",
                exc,
                body,
            )
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "LLM normalisation request failed for model %s at %s: %s",
                self._model,
                self._endpoint,
                exc,
                exc_info=True,
            )
            raise

        content: str = resp.json()["choices"][0]["message"]["content"]
        return _clean_llm_output(content)

    # ── Cache ─────────────────────────────────────────────────────────────────

    def _cache_path(
        self,
        chapter_index: int,
        paragraph_index: int,
        source_text: str,
    ) -> Path | None:
        """Return cache file path for one paragraph."""
        if not self._cache_dir:
            return None
        fingerprint = self._cache_fingerprint(source_text)
        return (
            self._cache_dir
            / (
                f"norm_ch{chapter_index:03d}_para{paragraph_index:04d}"
                f"_{fingerprint}.txt"
            )
        )

    def _load_cache(
        self,
        chapter_index: int,
        paragraph_index: int,
        source_text: str,
    ) -> str | None:
        """Return cached corrected text, or None if unavailable."""
        path = self._cache_path(chapter_index, paragraph_index, source_text)
        if path and path.exists():
            try:
                return path.read_text(encoding="utf-8")
            except OSError:
                return None
        return None

    def _save_cache(
        self,
        chapter_index: int,
        paragraph_index: int,
        source_text: str,
        corrected_text: str,
    ) -> None:
        """Persist corrected text to disk cache."""
        path = self._cache_path(chapter_index, paragraph_index, source_text)
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(corrected_text, encoding="utf-8")

    def _cache_fingerprint(self, source_text: str) -> str:
        """Return a cache fingerprint for text + LLM settings."""
        payload = "\n\0".join((
            self._model,
            self._endpoint,
            _SYSTEM_PROMPT,
            source_text,
        ))
        return sha1(payload.encode("utf-8")).hexdigest()[:16]


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
