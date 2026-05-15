"""Dialogue detection for Russian literary text.

Identifies direct speech, narrator remarks, and quoted speech
using typographic conventions standard in Russian publishing.
"""

from __future__ import annotations

import logging
import re

from book_normalizer.dialogue.models import (
    AnnotatedChapter,
    AnnotatedParagraph,
    DialogueLine,
    SpeakerRole,
)
from book_normalizer.models.book import Book, Chapter

logger = logging.getLogger(__name__)

EM_DASH = "\u2014"
LEFT_QUOTE = "\u00ab"
RIGHT_QUOTE = "\u00bb"

# Matches a line that starts with em-dash (optionally preceded by whitespace).
_DIALOGUE_START_RE = re.compile(r"^\s*" + EM_DASH + r"\s*")

# Attribution verbs that signal the narrator is speaking about the character.
_ATTRIBUTION_VERBS = (
    "сказал", "сказала", "ответил", "ответила",
    "спросил", "спросила", "крикнул", "крикнула",
    "прошептал", "прошептала", "произнёс", "произнесла",
    "проговорил", "проговорила", "воскликнул", "воскликнула",
    "пробормотал", "пробормотала", "буркнул", "буркнула",
    "проронил", "проронила", "добавил", "добавила",
    "продолжил", "продолжила", "заметил", "заметила",
    "подтвердил", "подтвердила", "возразил", "возразила",
    "закричал", "закричала", "промолвил", "промолвила",
    "выдохнул", "выдохнула", "простонал", "простонала",
    "усмехнулся", "усмехнулась", "рассмеялся", "рассмеялась",
    "вздохнул", "вздохнула", "поинтересовался", "поинтересовалась",
    "обратился", "обратилась", "процедил", "процедила",
    "прокричал", "прокричала", "пояснил", "пояснила",
    "напомнил", "напомнила", "согласился", "согласилась",
    "попросил", "попросила", "приказал", "приказала",
    "велел", "велела", "потребовал", "потребовала",
    "предложил", "предложила", "переспросил", "переспросила",
)

# Pattern: em-dash followed by attribution verb — marks the narrator remark.
_NARRATOR_REMARK_RE = re.compile(
    r"\s*" + EM_DASH + r"\s+(?:" + "|".join(_ATTRIBUTION_VERBS) + r")\b",
    re.IGNORECASE,
)

# Quoted speech pattern: «text».
_QUOTED_SPEECH_RE = re.compile(
    LEFT_QUOTE + r"([^" + RIGHT_QUOTE + r"]+)" + RIGHT_QUOTE
)
_QUOTE_SPEECH_CONTEXT_RE = re.compile(
    r"\b(?:" + "|".join(_ATTRIBUTION_VERBS) + r")\b",
    re.IGNORECASE,
)


class DialogueDetector:
    """Detects dialogue vs narrator segments in Russian literary text.

    Handles:
    - Em-dash dialogue lines (— Привет! — сказал он.).
    - Narrator remarks embedded in dialogue lines.
    - Quoted speech in «guillemets».
    - Plain narration (everything else).
    """

    def detect_book(self, book: Book) -> list[AnnotatedChapter]:
        """Annotate all chapters of a book with dialogue detection."""
        result: list[AnnotatedChapter] = []
        for chapter in book.chapters:
            annotated = self.detect_chapter(chapter)
            result.append(annotated)
        logger.info(
            "Dialogue detection complete: %d chapter(s), %d dialogue lines",
            len(result),
            sum(ch.dialogue_count for ch in result),
        )
        return result

    def detect_chapter(self, chapter: Chapter) -> AnnotatedChapter:
        """Annotate a single chapter with dialogue detection."""
        annotated_paragraphs: list[AnnotatedParagraph] = []

        for para in chapter.paragraphs:
            text = para.normalized_text or para.raw_text
            if not text.strip():
                continue
            ap = self._detect_paragraph(text, para.id, chapter.index)
            annotated_paragraphs.append(ap)

        return AnnotatedChapter(
            chapter_index=chapter.index,
            chapter_title=chapter.title,
            paragraphs=annotated_paragraphs,
        )

    def _detect_paragraph(
        self, text: str, paragraph_id: str, chapter_index: int
    ) -> AnnotatedParagraph:
        """Split a paragraph into dialogue and narrator lines."""
        raw_lines = text.split("\n")
        dialogue_lines: list[DialogueLine] = []

        for idx, raw_line in enumerate(raw_lines):
            stripped = raw_line.strip()
            if not stripped:
                continue

            parts = self._parse_dialogue_line(stripped)
            for part_text, is_dialogue in parts:
                if not part_text.strip():
                    continue
                dialogue_lines.append(
                    DialogueLine(
                        text=part_text.strip(),
                        role=SpeakerRole.UNKNOWN if is_dialogue else SpeakerRole.NARRATOR,
                        paragraph_id=paragraph_id,
                        line_index=idx,
                        is_dialogue=is_dialogue,
                    )
                )

        return AnnotatedParagraph(
            paragraph_id=paragraph_id,
            chapter_index=chapter_index,
            lines=dialogue_lines,
        )

    def _parse_dialogue_line(self, line: str) -> list[tuple[str, bool]]:
        """Parse a single line into (text, is_dialogue) segments.

        Handles the pattern:
            — Прямая речь, — сказал он, — и ещё прямая речь.
        Result:
            [("Прямая речь,", True),
             ("сказал он,", False),
             ("и ещё прямая речь.", True)]
        """
        if not _DIALOGUE_START_RE.match(line):
            if self._has_quoted_speech(line):
                return self._split_quoted_speech(line)
            return [(line, False)]

        content = _DIALOGUE_START_RE.sub("", line, count=1)
        return self._split_dialogue_content(content)

    def _split_dialogue_content(self, content: str) -> list[tuple[str, bool]]:
        """Split dialogue content into speech and narrator remark segments."""
        remark_match = _NARRATOR_REMARK_RE.search(content)
        if not remark_match:
            return [(content, True)]

        parts: list[tuple[str, bool]] = []

        speech_before = content[:remark_match.start()].rstrip(" ,")
        if speech_before:
            parts.append((speech_before, True))

        # Strip the leading em-dash from the remark portion.
        rest = content[remark_match.start():]
        rest_clean = rest.lstrip().lstrip(EM_DASH).lstrip()

        # Look for a continuation em-dash that resumes direct speech.
        dash_pos = rest_clean.find(EM_DASH)
        if dash_pos > 0:
            remark_text = rest_clean[:dash_pos].rstrip(" ,")
            if remark_text:
                parts.append((remark_text, False))
            speech_after = rest_clean[dash_pos:].lstrip(EM_DASH).lstrip()
            if speech_after:
                parts.append((speech_after, True))
        else:
            if rest_clean:
                parts.append((rest_clean, False))

        return parts if parts else [(content, True)]

    def _has_quoted_speech(self, line: str) -> bool:
        """Check if line contains quoted speech in guillemets."""
        return any(
            self._is_speech_quote(line, match)
            for match in _QUOTED_SPEECH_RE.finditer(line)
        )

    def _split_quoted_speech(self, line: str) -> list[tuple[str, bool]]:
        """Split a narrator line that contains quoted speech."""
        parts: list[tuple[str, bool]] = []
        last_end = 0

        for m in _QUOTED_SPEECH_RE.finditer(line):
            if not self._is_speech_quote(line, m):
                continue
            before = line[last_end:m.start()].strip()
            if before:
                parts.append((before, False))
            parts.append((m.group(1), True))
            last_end = m.end()

        after = line[last_end:].strip()
        if after:
            parts.append((after, False))

        return parts if parts else [(line, False)]

    @staticmethod
    def _is_speech_quote(line: str, match: re.Match[str]) -> bool:
        """Return true when a guillemet span is likely direct speech."""
        before = line[:match.start()]
        after = line[match.end():]
        quote_text = match.group(1).strip()

        if before.rstrip().endswith(":"):
            return True

        context = f"{before[-100:]} {after[:100]}"
        if _QUOTE_SPEECH_CONTEXT_RE.search(context):
            return True

        # Punctuation-heavy quoted fragments are usually spoken, not titles.
        return bool(re.search(r"[!?…]$", quote_text))
