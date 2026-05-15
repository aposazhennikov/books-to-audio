"""LLM-based chunker for multi-voice Russian TTS synthesis.

Replaces the three-step pipeline (DialogueDetector → LlmAttributor →
chunk_annotated_book) with a single LLM pass that simultaneously:
  - splits text into small TTS-ready chunks,
  - assigns a speaker role (narrator / men / women),
  - produces a free-form English voice_tone description.

Output format per chunk (user-facing):
    {"narrator": "авторский текст", "voice_tone": "calm"}
    {"men":      "Что?! Как ты мог?!", "voice_tone": "angry"}
    {"women":    "Успокойся, это просто поездка.", "voice_tone": "gentle, warm"}

The chapter text is processed in windows of ~2 000 chars (split at paragraph
boundaries) to stay within the model context limit.  Results are cached per
(chapter_index, window_index) to support interrupted runs.

On repeated LLM failures the module falls back to the rule-based
HeuristicAttributor + chunk_annotated_book pipeline.
"""

# ruff: noqa: E501

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

DEFAULT_WINDOW_CHARS = 2000
MAX_RETRIES = 3
DEFAULT_MAX_CHUNK_CHARS = 400  # Prefer small chunks for stable intonation.
MAX_CHUNK_CHARS = DEFAULT_MAX_CHUNK_CHARS  # Backward-compatible alias.

# Maps voice label (returned by LLM) to TTS voice_id preset.
VOICE_ID_MAP: dict[str, str] = {
    "narrator": "narrator_calm",
    "men":      "male_young",
    "women":    "female_warm",
}

# Canonical voice name used internally (compatible with legacy pipeline).
VOICE_CANONICAL: dict[str, str] = {
    "narrator": "narrator",
    "men":      "male",
    "women":    "female",
}

VALID_VOICES = frozenset(VOICE_ID_MAP)

# ── LLM system prompt ─────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
Ты — движок разметки аудиокниги для многоголосового TTS.
Раздели текст на МАЛЕНЬКИЕ чанки (30–{max_chunk_chars} символов), каждому назначь роль и интонацию.

═══ ОБЯЗАТЕЛЬНЫЕ ПРАВИЛА ═══

1. ОБЯЗАТЕЛЬНО разделяй прямую речь и авторский текст — они НИКОГДА не идут в одном чанке.

2. ПРЯМАЯ РЕЧЬ — всё после «—» в начале или внутри предложения, а также текст в «»/«».
   «— Уходи!» → отдельный чанк men или women
   «— Я вернусь, — прошептал он.» → «— Я вернусь,» отдельно / «прошептал он.» отдельно

3. РОЛИ (выбери одну):
   "narrator" — авторский текст, описания, теги речи («сказал», «ответила», «крикнул»)
   "men"      — реплика мужчины (маркеры: сказал / спросил / воскликнул / крикнул / прошептал)
   "women"    — реплика женщины (маркеры: сказала / спросила / воскликнула / крикнула / прошептала)
   Если пол неизвестен из контекста — narrator.

4. voice_tone — 1–4 слова на АНГЛИЙСКОМ, РАЗНООБРАЗНО:
   боевая сцена → "tense", "urgent", "intense"
   гнев, грубость → "angry", "furious", "cold and harsh"
   крик → "shouting", "loud and urgent"
   шёпот → "whisper", "low and tense"
   страх, тревога → "fearful", "anxious"
   грусть → "sad", "tired and sad"
   радость → "happy", "cheerful"
   спокойное повествование → "calm"
   НЕ пиши везде "calm" — подбирай по смыслу сцены!

═══ ПРИМЕР ═══

ВВОД:
Иван вошёл в комнату. — Где ты был? — резко спросила Мария. — Не твоё дело, — огрызнулся он и хлопнул дверью. Она отвернулась к окну.

ВЫВОД:
[
  {{"narrator": "Иван вошёл в комнату.", "voice_tone": "calm"}},
  {{"women": "— Где ты был?", "voice_tone": "angry"}},
  {{"narrator": "резко спросила Мария.", "voice_tone": "calm"}},
  {{"men": "— Не твоё дело,", "voice_tone": "cold and angry"}},
  {{"narrator": "огрызнулся он и хлопнул дверью. Она отвернулась к окну.", "voice_tone": "tense"}}
]

═══ СТРОГИЕ ЗАПРЕТЫ ═══
— НЕ объединяй реплику «—» и авторский текст в одном чанке
— НЕ придумывай текст — бери ТОЛЬКО из оригинала
— НЕ пиши voice_tone на русском
— Верни ТОЛЬКО JSON-массив, без markdown, без комментариев

Предыдущий голос в цепочке: {last_voice}
"""


# ── Data model ────────────────────────────────────────────────────────────────


@dataclass
class ChunkSpec:
    """A single TTS-ready chunk with speaker and tone annotation.

    ``voice_label`` is the user-facing key in the manifest
    (narrator / men / women).  ``voice`` is the canonical internal
    name (narrator / male / female).  ``voice_tone`` is a free-form
    English description of intonation.
    """

    chapter_index: int
    chunk_index: int
    voice_label: str          # narrator | men | women  (user-facing key)
    voice: str                # narrator | male | female  (canonical)
    voice_id: str             # narrator_calm | male_young | female_warm
    voice_tone: str           # free-form English, e.g. "calm", "angry and tense"
    text: str
    audio_file: str | None = None
    synthesized: bool = False
    pause_after_ms: int = 0
    boundary_after: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to manifest dict.

        The voice_label becomes the dict key whose value is the text,
        matching the user-facing format::

            {"narrator": "text", "voice_tone": "calm", ...}
        """
        result = {
            "chapter_index": self.chapter_index,
            "chunk_index": self.chunk_index,
            self.voice_label: self.text,   # narrator/men/women: text
            "voice": self.voice,
            "voice_id": self.voice_id,
            "voice_tone": self.voice_tone,
            "text": self.text,             # duplicate for TTS pipeline compat
            "audio_file": self.audio_file,
            "synthesized": self.synthesized,
        }
        if self.pause_after_ms:
            result["pause_after_ms"] = self.pause_after_ms
        if self.boundary_after:
            result["boundary_after"] = self.boundary_after
        return result


# ── LlmChunker ────────────────────────────────────────────────────────────────


class LlmChunker:
    """Split a book chapter into annotated TTS chunks using a local LLM.

    Uses an OpenAI-compatible endpoint (default: Ollama at port 11434).
    Results are cached per chapter window to support interrupted runs.
    Falls back to rule-based chunking when the LLM consistently fails.
    """

    def __init__(
        self,
        endpoint: str = "http://localhost:11434/v1",
        model: str = "gemma3:4b",
        cache_dir: Path | None = None,
        window_chars: int = DEFAULT_WINDOW_CHARS,
        max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
        api_key: str = "",
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._model = model
        self._cache_dir = cache_dir
        self._window_chars = window_chars
        self._max_chunk_chars = max(1, max_chunk_chars)
        self._api_key = api_key
        self._max_retries = max_retries

    # ── Public API ────────────────────────────────────────────────────────────

    def chunk_chapter(
        self,
        chapter_index: int,
        chapter_text: str,
    ) -> list[ChunkSpec]:
        """Split a chapter into voice-annotated TTS chunks.

        Args:
            chapter_index: Zero-based chapter index used for cache keys.
            chapter_text: Fully normalised Russian chapter text.

        Returns:
            Ordered list of ``ChunkSpec`` objects ready for synthesis.
        """
        paragraphs = [p.strip() for p in chapter_text.split("\n\n") if p.strip()]
        if not paragraphs:
            return []

        windows = _build_windows(paragraphs, self._window_chars)
        all_raw: list[dict[str, str]] = []
        last_voice = "narrator"

        total_windows = len(windows)
        chapter_t0 = time.monotonic()

        for win_idx, window_text in enumerate(windows):
            win_t0 = time.monotonic()
            cached = self._load_cache(chapter_index, win_idx, window_text, last_voice)
            if cached is not None:
                logger.debug(
                    "Chapter %d window %d: loaded %d chunks from cache",
                    chapter_index, win_idx, len(cached),
                )
                all_raw.extend(cached)
            else:
                try:
                    raw = self._process_window(
                        window_text, last_voice, chapter_index, win_idx
                    )
                except RuntimeError:
                    logger.warning(
                        "Chapter %d: LLM chunking failed; falling back to heuristic chunking",
                        chapter_index,
                        exc_info=True,
                    )
                    return self._heuristic_fallback(chapter_index, chapter_text)
                all_raw.extend(raw)
                self._save_cache(chapter_index, win_idx, window_text, last_voice, raw)

            if all_raw:
                # Track last voice label for cross-window context.
                last_raw = all_raw[-1]
                last_voice = _detect_voice_label(last_raw)

            win_elapsed = time.monotonic() - win_t0
            processed = win_idx + 1
            total_elapsed = time.monotonic() - chapter_t0
            avg_per_window = total_elapsed / processed
            remaining = total_windows - processed
            eta = remaining * avg_per_window

            logger.info(
                "Chapter %d window %d/%d: %.1fs (elapsed %.1fs, eta ≈ %.1fs)",
                chapter_index,
                processed,
                total_windows,
                win_elapsed,
                total_elapsed,
                eta,
            )

        if not all_raw:
            logger.warning(
                "LLM chunker produced no chunks for chapter %d — falling back to heuristic",
                chapter_index,
            )
            return self._heuristic_fallback(chapter_index, chapter_text)

        return _build_chunk_specs(
            chapter_index, all_raw, self._max_chunk_chars,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _process_window(
        self,
        text: str,
        last_voice: str,
        chapter_index: int,
        window_index: int,
    ) -> list[dict[str, str]]:
        """Query the LLM for one text window, with retry.

        If all attempts fail, this raises RuntimeError. ``chunk_chapter`` catches
        it and falls back to rule-based chunking for the whole chapter so the
        output does not silently mix LLM and heuristic chunks.
        """
        prompt = _SYSTEM_PROMPT.format(
            last_voice=last_voice,
            max_chunk_chars=self._max_chunk_chars,
        )

        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                raw = _normalise_llm_items(self._query_llm(prompt, text))
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning(
                    "Chapter %d window %d: LLM attempt %d/%d failed: %s: %s",
                    chapter_index,
                    window_index,
                    attempt,
                    self._max_retries,
                    type(exc).__name__,
                    exc,
                )
                continue

            if raw:
                if not _items_preserve_source_text(text, raw):
                    logger.warning(
                        "Chapter %d window %d: LLM attempt %d/%d failed text "
                        "preservation check",
                        chapter_index,
                        window_index,
                        attempt,
                        self._max_retries,
                    )
                    continue
                logger.debug(
                    "Chapter %d window %d: LLM returned %d chunks (attempt %d)",
                    chapter_index,
                    window_index,
                    len(raw),
                    attempt,
                )
                return raw

            logger.warning(
                "Chapter %d window %d: LLM attempt %d/%d returned empty result",
                chapter_index,
                window_index,
                attempt,
                self._max_retries,
            )

        message = (
            f"Chapter {chapter_index} window {window_index}: all LLM attempts failed; "
            f"last_error={last_error!r}"
        )
        logger.error(message)
        raise RuntimeError(message)

    def _query_llm(self, system_prompt: str, user_text: str) -> list[dict[str, str]]:
        """Send one chat request to the OpenAI-compatible endpoint and parse JSON."""
        try:
            import httpx
        except ImportError:
            logger.error("httpx is required for LLM chunking: pip install httpx")
            return []

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            "temperature": 0.1,
        }

        try:
            resp = httpx.post(
                f"{self._endpoint}/chat/completions",
                json=payload,
                headers=headers,
                timeout=300.0,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # Log full HTTP status + a slice of the body to understand why Ollama failed.
            body = exc.response.text[:1000] if exc.response is not None else ""
            logger.error(
                "LLM HTTP error for model %s (status %s): %s\nResponse body (truncated): %s",
                self._model,
                exc.response.status_code if exc.response is not None else "?",
                exc,
                body,
            )
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "LLM request failed for model %s at %s: %s",
                self._model,
                self._endpoint,
                exc,
                exc_info=True,
            )
            raise

        content: str = resp.json()["choices"][0]["message"]["content"]
        return _parse_llm_response(content)

    # ── Cache ─────────────────────────────────────────────────────────────────

    def _cache_path(
        self,
        chapter_index: int,
        window_index: int,
        window_text: str,
        last_voice: str,
    ) -> Path | None:
        """Build cache file path for a specific chapter + window."""
        if not self._cache_dir:
            return None
        fingerprint = self._cache_fingerprint(window_text, last_voice)
        return (
            self._cache_dir
            / (
                f"llm_chunks_ch{chapter_index:03d}_win{window_index:03d}"
                f"_max{self._max_chunk_chars:04d}_{fingerprint}.json"
            )
        )

    def _load_cache(
        self,
        chapter_index: int,
        window_index: int,
        window_text: str,
        last_voice: str,
    ) -> list[dict[str, str]] | None:
        """Return cached window data, or None if unavailable."""
        path = self._cache_path(
            chapter_index, window_index, window_text, last_voice,
        )
        if path and path.exists():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return None
            items = _normalise_llm_items(loaded)
            if items and _items_preserve_source_text(window_text, items):
                return items
            logger.warning(
                "Ignoring stale LLM chunk cache that fails text preservation: %s",
                path,
            )
        return None

    def _save_cache(
        self,
        chapter_index: int,
        window_index: int,
        window_text: str,
        last_voice: str,
        data: list[dict[str, str]],
    ) -> None:
        """Persist window data to disk cache."""
        path = self._cache_path(
            chapter_index, window_index, window_text, last_voice,
        )
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def _cache_fingerprint(self, window_text: str, last_voice: str) -> str:
        """Return a cache fingerprint for text + LLM settings."""
        prompt = _SYSTEM_PROMPT.format(
            last_voice=last_voice,
            max_chunk_chars=self._max_chunk_chars,
        )
        payload = "\n\0".join((
            self._model,
            self._endpoint,
            prompt,
            window_text,
        ))
        return sha1(payload.encode("utf-8")).hexdigest()[:16]

    # ── Fallback ──────────────────────────────────────────────────────────────

    def _heuristic_fallback(
        self, chapter_index: int, chapter_text: str
    ) -> list[ChunkSpec]:
        """Fall back to rule-based chunking when LLM is unavailable."""
        from book_normalizer.chunking.splitter import chunk_text
        from book_normalizer.chunking.voice_splitter import chunk_annotated_chapter
        from book_normalizer.dialogue.attribution import HeuristicAttributor
        from book_normalizer.dialogue.detector import DialogueDetector
        from book_normalizer.dialogue.models import SpeakerRole
        from book_normalizer.models.book import Chapter, Paragraph

        paras = [
            Paragraph(
                raw_text=p,
                normalized_text=p,
                index_in_chapter=i,
            )
            for i, p in enumerate(
                p.strip() for p in chapter_text.split("\n\n") if p.strip()
            )
        ]
        dummy_chapter = Chapter(
            title=f"Chapter {chapter_index + 1}",
            index=chapter_index,
            paragraphs=paras,
        )

        detector = DialogueDetector()
        annotated_ch = detector.detect_chapter(dummy_chapter)

        attributor = HeuristicAttributor()
        attributor.attribute([annotated_ch])

        role_to_label: dict[SpeakerRole, str] = {
            SpeakerRole.NARRATOR: "narrator",
            SpeakerRole.MALE:     "men",
            SpeakerRole.FEMALE:   "women",
            SpeakerRole.UNKNOWN:  "narrator",
        }

        legacy_chunks = chunk_annotated_chapter(
            annotated_ch, self._max_chunk_chars,
        )
        if not legacy_chunks:
            raw_chunks = chunk_text(chapter_text, self._max_chunk_chars)
            return [
                ChunkSpec(
                    chapter_index=chapter_index,
                    chunk_index=i,
                    voice_label="narrator",
                    voice="narrator",
                    voice_id="narrator_calm",
                    voice_tone="calm",
                    text=t,
                )
                for i, t in enumerate(raw_chunks)
            ]

        specs: list[ChunkSpec] = []
        for i, chunk in enumerate(legacy_chunks):
            label = role_to_label.get(chunk.role, "narrator")
            specs.append(
                ChunkSpec(
                    chapter_index=chapter_index,
                    chunk_index=i,
                    voice_label=label,
                    voice=VOICE_CANONICAL.get(label, "narrator"),
                    voice_id=VOICE_ID_MAP.get(label, "narrator_calm"),
                    voice_tone="calm",
                    text=chunk.text,
                )
            )
        return specs


# ── Module-level helpers ───────────────────────────────────────────────────────


def _build_windows(paragraphs: list[str], max_chars: int) -> list[str]:
    """Group paragraphs into windows of at most max_chars characters."""
    windows: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    for para in paragraphs:
        sep = 2 if current_parts else 0
        if current_len + sep + len(para) > max_chars and current_parts:
            windows.append("\n\n".join(current_parts))
            current_parts = [para]
            current_len = len(para)
        else:
            current_parts.append(para)
            current_len += sep + len(para)

    if current_parts:
        windows.append("\n\n".join(current_parts))

    return windows


def _detect_voice_label(raw: dict[str, str]) -> str:
    """Return the voice label (narrator/men/women) from a raw LLM item."""
    if not isinstance(raw, dict):
        return "narrator"
    for key in ("narrator", "men", "women"):
        if key in raw:
            return key
    return raw.get("voice", "narrator")


def _normalise_llm_items(raw: Any) -> list[dict[str, str]]:
    """Convert raw LLM/cache output into validated chunk dictionaries."""
    if isinstance(raw, str):
        return _parse_llm_response(raw)
    if isinstance(raw, list):
        return _validate_items(raw)
    return []


def _parse_llm_response(content: str) -> list[dict[str, str]]:
    """Extract and validate the JSON array from LLM response text."""
    content = content.strip()
    # Strip markdown fences.
    content = re.sub(r"^```[a-z]*\n?", "", content, flags=re.MULTILINE)
    content = re.sub(r"```$", "", content, flags=re.MULTILINE)
    content = content.strip()

    start = content.find("[")
    end = content.rfind("]")
    if start < 0 or end < 0:
        return []

    try:
        items: list[Any] = json.loads(content[start : end + 1])
    except json.JSONDecodeError:
        return []

    return _validate_items(items)


def _validate_items(items: list[Any]) -> list[dict[str, str]]:
    """Filter and normalise LLM output items.

    Accepts both formats:
    - New: ``{"narrator": "text", "voice_tone": "calm"}``
    - Legacy: ``{"voice": "narrator", "mood": "neutral", "text": "text"}``
    """
    valid: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        # Detect new format first (voice label is the key).
        voice_label, text = _extract_voice_text(item)
        if not text or not text.strip():
            continue

        voice_tone = str(item.get("voice_tone", item.get("mood", "calm"))).strip()
        if not voice_tone:
            voice_tone = "calm"

        valid.append({
            voice_label: text.strip(),
            "voice_tone": voice_tone,
        })

    return valid


def _extract_voice_text(item: dict[str, Any]) -> tuple[str, str]:
    """Extract (voice_label, text) from an LLM response item.

    Handles both new-format keys (narrator/men/women) and the legacy
    ``voice`` + ``text`` format.
    """
    for label in ("narrator", "men", "women"):
        if label in item:
            return label, str(item[label])

    # Legacy fallback: {"voice": "...", "text": "..."}
    raw_voice = str(item.get("voice", "narrator")).lower()
    text = str(item.get("text", ""))
    label_map = {"narrator": "narrator", "male": "men", "female": "women"}
    label = label_map.get(raw_voice, "narrator")
    return label, text


def _build_chunk_specs(
    chapter_index: int,
    raw: list[dict[str, str]],
    max_chunk_chars: int = MAX_CHUNK_CHARS,
) -> list[ChunkSpec]:
    """Convert validated raw dicts into indexed ChunkSpec objects."""
    from book_normalizer.chunking.splitter import chunk_text

    specs: list[ChunkSpec] = []
    chunk_index = 0
    for item in raw:
        voice_label, text = _extract_voice_text(item)
        voice_tone = str(item.get("voice_tone", "calm")).strip()
        text_parts = chunk_text(text, max_chunk_chars=max_chunk_chars)
        for part in text_parts or [text]:
            specs.append(
                ChunkSpec(
                    chapter_index=chapter_index,
                    chunk_index=chunk_index,
                    voice_label=voice_label,
                    voice=VOICE_CANONICAL.get(voice_label, "narrator"),
                    voice_id=VOICE_ID_MAP.get(voice_label, "narrator_calm"),
                    voice_tone=voice_tone,
                    text=part,
                )
            )
            chunk_index += 1
    return specs


def _items_preserve_source_text(source_text: str, items: list[dict[str, str]]) -> bool:
    """Return true when concatenated chunk text exactly preserves source text."""
    joined = " ".join(
        _extract_voice_text(item)[1]
        for item in items
    )
    return _canonical_text_for_preservation(source_text) == _canonical_text_for_preservation(joined)


def _canonical_text_for_preservation(text: str) -> str:
    """Normalize whitespace and dialogue delimiter dashes for preservation checks."""
    text = re.sub(r"[—–-]", "", text or "")
    return re.sub(r"\s+", "", text)


def _heuristic_chunk_text(
    text: str,
    last_voice: str,
    max_chunk_chars: int = MAX_CHUNK_CHARS,
) -> list[dict[str, str]]:
    """Simple rule-based chunking used as a per-window fallback."""
    from book_normalizer.chunking.splitter import chunk_text

    parts = chunk_text(text, max_chunk_chars)
    label = last_voice if last_voice in VALID_VOICES else "narrator"
    return [
        {label: p, "voice_tone": "calm"}
        for p in parts
        if p.strip()
    ]
