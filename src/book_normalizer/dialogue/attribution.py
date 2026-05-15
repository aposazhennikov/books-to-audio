"""Speaker attribution strategies for dialogue lines.

Three modes are supported:
- heuristic: rule-based gender detection from attribution verbs and names.
- llm: send text to an LLM for speaker annotation.
- manual: interactive TUI for user-driven annotation.
"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from enum import Enum
from hashlib import sha1
from pathlib import Path
from typing import Any

from book_normalizer.dialogue.models import (
    AnnotatedChapter,
    DialogueLine,
    SpeakerAnnotationResult,
    SpeakerRole,
)

logger = logging.getLogger(__name__)


class SpeakerMode(str, Enum):
    """Available speaker attribution strategies."""

    HEURISTIC = "heuristic"
    LLM = "llm"
    MANUAL = "manual"


class BaseSpeakerAttributor(ABC):
    """Abstract base for speaker attribution strategies."""

    @abstractmethod
    def attribute(
        self, chapters: list[AnnotatedChapter]
    ) -> SpeakerAnnotationResult:
        """Assign SpeakerRole to all dialogue lines in the chapters."""


# ---------------------------------------------------------------------------
# Heuristic attributor
# ---------------------------------------------------------------------------

# Masculine verb endings used after em-dash in narrator remarks.
_MALE_PATTERNS = re.compile(
    r"\b(?:он|Он)\s+"
    r"|(?:сказал|ответил|спросил|крикнул|прошептал|произнёс|проговорил"
    r"|воскликнул|пробормотал|буркнул|проронил|добавил|продолжил"
    r"|заметил|подтвердил|возразил|закричал|промолвил|выдохнул"
    r"|простонал|процедил|прокричал|пояснил|напомнил|согласился"
    r"|попросил|приказал|велел|потребовал|предложил|переспросил"
    r"|усмехнулся|рассмеялся|вздохнул|поинтересовался|обратился)\b",
    re.IGNORECASE,
)

_FEMALE_PATTERNS = re.compile(
    r"\b(?:она|Она)\s+"
    r"|(?:сказала|ответила|спросила|крикнула|прошептала|произнесла"
    r"|проговорила|воскликнула|пробормотала|буркнула|проронила"
    r"|добавила|продолжила|заметила|подтвердила|возразила"
    r"|закричала|промолвила|выдохнула|простонала|процедила"
    r"|прокричала|пояснила|напомнила|согласилась"
    r"|попросила|приказала|велела|потребовала|предложила"
    r"|переспросила|усмехнулась|рассмеялась|вздохнула"
    r"|поинтересовалась|обратилась)\b",
    re.IGNORECASE,
)


def _detect_gender_from_text(text: str) -> SpeakerRole | None:
    """Try to detect speaker gender from attribution text."""
    male_score = len(_MALE_PATTERNS.findall(text))
    female_score = len(_FEMALE_PATTERNS.findall(text))
    if male_score > female_score:
        return SpeakerRole.MALE
    if female_score > male_score:
        return SpeakerRole.FEMALE
    return None


class HeuristicAttributor(BaseSpeakerAttributor):
    """Rule-based speaker attribution using verb endings and alternation.

    Strategy:
    1. Scan narrator remark lines for gendered verb forms.
    2. Assign the detected gender to the preceding dialogue line.
    3. When no attribution is found, alternate male/female.
    """

    def attribute(
        self, chapters: list[AnnotatedChapter]
    ) -> SpeakerAnnotationResult:
        """Assign speaker roles based on heuristic rules."""
        stats = _empty_stats("heuristic")

        for chapter in chapters:
            for para in chapter.paragraphs:
                self._attribute_paragraph(para.lines)
            stats["chapters_processed"] += 1

        return _build_result(chapters, stats)

    def _attribute_paragraph(self, lines: list[DialogueLine]) -> None:
        """Attribute speaker roles within a paragraph's lines."""
        last_dialogue_role: SpeakerRole | None = None

        i = 0
        while i < len(lines):
            line = lines[i]

            if not line.is_dialogue:
                gender = _detect_gender_from_text(line.text)
                if gender and i > 0 and lines[i - 1].is_dialogue:
                    lines[i - 1].role = gender
                    lines[i - 1].attribution_tag = "heuristic:remark"
                    last_dialogue_role = gender
                i += 1
                continue

            # Dialogue line: check if the next line is a narrator remark.
            if i + 1 < len(lines) and not lines[i + 1].is_dialogue:
                gender = _detect_gender_from_text(lines[i + 1].text)
                if gender:
                    line.role = gender
                    line.attribution_tag = "heuristic:lookahead"
                    last_dialogue_role = gender
                    i += 1
                    continue

            # No remark found — alternate gender.
            if line.role == SpeakerRole.UNKNOWN:
                if last_dialogue_role == SpeakerRole.MALE:
                    line.role = SpeakerRole.FEMALE
                elif last_dialogue_role == SpeakerRole.FEMALE:
                    line.role = SpeakerRole.MALE
                else:
                    line.role = SpeakerRole.MALE
                line.attribution_tag = "heuristic:alternation"
                last_dialogue_role = line.role

            i += 1


# ---------------------------------------------------------------------------
# LLM attributor
# ---------------------------------------------------------------------------

_LLM_SYSTEM_PROMPT = (
    "You are a literary text analyst. Given a list of dialogue lines from a "
    "Russian book, determine the speaker's gender for each dialogue line. "
    "Respond with a JSON array of objects: "
    '[{"line_id": "...", "role": "male"|"female"}]. '
    "Only annotate lines marked as dialogue. "
    "Use context clues: verb endings, character names, pronouns."
)


class LlmAttributor(BaseSpeakerAttributor):
    """Speaker attribution using an LLM via OpenAI-compatible API.

    Sends chapter text to an LLM and parses structured gender annotations.
    Results are cached to avoid redundant API calls.
    """

    def __init__(
        self,
        endpoint: str = "http://localhost:11434/v1",
        model: str = "qwen3:8b",
        api_key: str = "",
        cache_dir: Path | None = None,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._cache_dir = cache_dir

    def attribute(
        self, chapters: list[AnnotatedChapter]
    ) -> SpeakerAnnotationResult:
        """Assign speaker roles via LLM for each chapter."""
        stats = _empty_stats("llm")

        for chapter in chapters:
            dialogue_lines = [
                line
                for para in chapter.paragraphs
                for line in para.lines
                if line.is_dialogue and line.role == SpeakerRole.UNKNOWN
            ]
            if not dialogue_lines:
                stats["chapters_processed"] += 1
                continue

            cache_key = self._cache_fingerprint(chapter, dialogue_lines)
            cached = self._load_cache(chapter.chapter_index, cache_key)
            if cached:
                self._apply_cached(dialogue_lines, cached, chapter.chapter_index)
            else:
                annotations = self._query_llm(chapter, dialogue_lines)
                if annotations:
                    self._apply_annotations(
                        dialogue_lines, annotations, chapter.chapter_index,
                    )
                    self._save_cache(
                        chapter.chapter_index, annotations, cache_key,
                    )

            stats["chapters_processed"] += 1

        return _build_result(chapters, stats)

    def _query_llm(
        self,
        chapter: AnnotatedChapter,
        dialogue_lines: list[DialogueLine],
    ) -> list[dict[str, str]]:
        """Send dialogue lines to the LLM and parse response."""
        try:
            import httpx
        except ImportError:
            logger.error("httpx is required for LLM attribution: pip install httpx")
            return []

        lines_payload = [
            {
                "line_id": _line_cache_key(line, chapter.chapter_index, i),
                "text": line.text[:200],
            }
            for i, line in enumerate(dialogue_lines)
        ]
        user_msg = (
            f"Chapter: {chapter.chapter_title}\n\n"
            f"Dialogue lines:\n{json.dumps(lines_payload, ensure_ascii=False, indent=2)}"
        )

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": _LLM_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            "temperature": 0.1,
        }

        try:
            resp = httpx.post(
                f"{self._endpoint}/chat/completions",
                json=payload,
                headers=headers,
                timeout=60.0,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return self._parse_llm_response(content)
        except Exception as exc:
            logger.warning("LLM attribution failed: %s", exc)
            return []

    @staticmethod
    def _parse_llm_response(content: str) -> list[dict[str, str]]:
        """Extract JSON array from LLM response text."""
        content = content.strip()
        start = content.find("[")
        end = content.rfind("]")
        if start < 0 or end < 0:
            return []
        try:
            return json.loads(content[start:end + 1])
        except json.JSONDecodeError:
            return []

    @staticmethod
    def _apply_annotations(
        lines: list[DialogueLine],
        annotations: list[dict[str, str]],
        chapter_index: int = 0,
    ) -> None:
        """Apply LLM annotations to dialogue lines."""
        mapping = {a["line_id"]: a.get("role", "") for a in annotations}
        for i, line in enumerate(lines):
            role_str = mapping.get(
                _line_cache_key(line, chapter_index, i),
                mapping.get(line.id, ""),
            )
            if role_str == "male":
                line.role = SpeakerRole.MALE
                line.attribution_tag = "llm"
            elif role_str == "female":
                line.role = SpeakerRole.FEMALE
                line.attribution_tag = "llm"

    @staticmethod
    def _apply_cached(
        lines: list[DialogueLine],
        cached: list[dict[str, str]],
        chapter_index: int = 0,
    ) -> None:
        """Apply cached annotations."""
        LlmAttributor._apply_annotations(lines, cached, chapter_index)

    def _cache_path(self, chapter_index: int, cache_key: str = "") -> Path | None:
        """Build cache file path for a chapter."""
        if not self._cache_dir:
            return None
        if cache_key:
            return self._cache_dir / f"speaker_ch{chapter_index:03d}_{cache_key}.json"
        return self._cache_dir / f"speaker_ch{chapter_index:03d}.json"

    def _load_cache(
        self, chapter_index: int, cache_key: str = ""
    ) -> list[dict[str, str]] | None:
        """Load cached annotations if available."""
        path = self._cache_path(chapter_index, cache_key)
        if path and path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return None
        return None

    def _save_cache(
        self,
        chapter_index: int,
        annotations: list[dict[str, str]],
        cache_key: str = "",
    ) -> None:
        """Persist annotations to cache."""
        path = self._cache_path(chapter_index, cache_key)
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(annotations, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def _cache_fingerprint(
        self,
        chapter: AnnotatedChapter,
        dialogue_lines: list[DialogueLine],
    ) -> str:
        """Return a cache fingerprint for chapter text + LLM settings."""
        line_payload = [
            {
                "key": _line_cache_key(line, chapter.chapter_index, i),
                "text": line.text,
            }
            for i, line in enumerate(dialogue_lines)
        ]
        payload = "\n\0".join((
            self._model,
            self._endpoint,
            _LLM_SYSTEM_PROMPT,
            chapter.chapter_title,
            json.dumps(line_payload, ensure_ascii=False, sort_keys=True),
        ))
        return sha1(payload.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Manual (TUI) attributor
# ---------------------------------------------------------------------------

class ManualAttributor(BaseSpeakerAttributor):
    """Interactive TUI for manual speaker attribution using rich."""

    def __init__(self, session_path: Path | None = None) -> None:
        self._session_path = session_path
        self._decisions: dict[str, str] = {}
        if session_path and session_path.exists():
            self._load_session()

    def attribute(
        self, chapters: list[AnnotatedChapter]
    ) -> SpeakerAnnotationResult:
        """Run interactive attribution in the terminal."""
        from rich.console import Console
        from rich.panel import Panel
        from rich.prompt import Prompt

        console = Console()
        stats = _empty_stats("manual")

        for chapter in chapters:
            dialogue_lines = [
                line
                for para in chapter.paragraphs
                for line in para.lines
                if line.is_dialogue and line.role == SpeakerRole.UNKNOWN
            ]
            if not dialogue_lines:
                stats["chapters_processed"] += 1
                continue

            console.print(
                Panel(
                    f"[bold]Chapter {chapter.chapter_index + 1}: "
                    f"{chapter.chapter_title}[/bold]\n"
                    f"{len(dialogue_lines)} dialogue line(s) to annotate",
                    title="Speaker Attribution",
                )
            )

            for i, line in enumerate(dialogue_lines):
                line_key = _line_cache_key(line, chapter.chapter_index, i)
                legacy_key = line.id
                if line_key in self._decisions or legacy_key in self._decisions:
                    role_str = self._decisions.get(
                        line_key,
                        self._decisions.get(legacy_key, ""),
                    )
                    line.role = SpeakerRole(role_str)
                    line.attribution_tag = "manual:cached"
                    continue

                console.print(f"\n[cyan]> {line.text[:120]}[/cyan]")
                choice = Prompt.ask(
                    "Speaker",
                    choices=["m", "f", "s"],
                    default="m",
                )
                if choice == "m":
                    line.role = SpeakerRole.MALE
                elif choice == "f":
                    line.role = SpeakerRole.FEMALE
                else:
                    line.role = SpeakerRole.UNKNOWN

                line.attribution_tag = "manual"
                self._decisions[line_key] = line.role.value
                self._save_session()

            stats["chapters_processed"] += 1

        return _build_result(chapters, stats)

    def _load_session(self) -> None:
        """Load previous manual decisions from disk."""
        if self._session_path and self._session_path.exists():
            try:
                self._decisions = json.loads(
                    self._session_path.read_text(encoding="utf-8")
                )
            except (json.JSONDecodeError, OSError):
                self._decisions = {}

    def _save_session(self) -> None:
        """Persist manual decisions to disk."""
        if self._session_path:
            self._session_path.parent.mkdir(parents=True, exist_ok=True)
            self._session_path.write_text(
                json.dumps(self._decisions, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_attributor(
    mode: SpeakerMode,
    *,
    llm_endpoint: str = "",
    llm_model: str = "qwen3:8b",
    llm_api_key: str = "",
    cache_dir: Path | None = None,
    session_path: Path | None = None,
) -> BaseSpeakerAttributor:
    """Create a speaker attributor for the given mode."""
    if mode == SpeakerMode.HEURISTIC:
        return HeuristicAttributor()
    if mode == SpeakerMode.LLM:
        return LlmAttributor(
            endpoint=llm_endpoint or "http://localhost:11434/v1",
            model=llm_model,
            api_key=llm_api_key,
            cache_dir=cache_dir,
        )
    if mode == SpeakerMode.MANUAL:
        return ManualAttributor(session_path=session_path)
    raise ValueError(f"Unknown speaker mode: {mode}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _empty_stats(strategy: str) -> dict[str, Any]:
    """Create an empty stats dict."""
    return {"strategy": strategy, "chapters_processed": 0}


def _line_cache_key(
    line: DialogueLine,
    chapter_index: int,
    ordinal: int,
) -> str:
    """Build a deterministic line key for caches and manual sessions."""
    text_hash = sha1(line.text.strip().encode("utf-8")).hexdigest()[:12]
    return f"ch{chapter_index:03d}:ord{ordinal:04d}:line{line.line_index:04d}:{text_hash}"


def _build_result(
    chapters: list[AnnotatedChapter], stats: dict[str, Any]
) -> SpeakerAnnotationResult:
    """Aggregate annotation statistics from chapters."""
    total = narrator = male = female = unknown = 0
    for ch in chapters:
        for para in ch.paragraphs:
            for line in para.lines:
                total += 1
                if not line.is_dialogue:
                    narrator += 1
                elif line.role == SpeakerRole.MALE:
                    male += 1
                elif line.role == SpeakerRole.FEMALE:
                    female += 1
                else:
                    unknown += 1
    return SpeakerAnnotationResult(
        total_lines=total,
        narrator_lines=narrator,
        male_lines=male,
        female_lines=female,
        unknown_lines=unknown,
        chapters_processed=stats["chapters_processed"],
        strategy=stats["strategy"],
    )
