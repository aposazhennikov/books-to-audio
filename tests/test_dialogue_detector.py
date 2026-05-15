"""Tests for dialogue detection in Russian literary text."""

from __future__ import annotations

from book_normalizer.dialogue.detector import DialogueDetector
from book_normalizer.dialogue.models import SpeakerRole
from book_normalizer.models.book import Book, Chapter, Paragraph


def _make_chapter(text: str, index: int = 0) -> Chapter:
    """Build a single-paragraph chapter from text."""
    para = Paragraph(raw_text=text, normalized_text=text, index_in_chapter=0)
    return Chapter(title=f"Chapter {index}", index=index, paragraphs=[para])


def _make_multi_para_chapter(paragraphs: list[str], index: int = 0) -> Chapter:
    """Build a chapter with multiple paragraphs."""
    paras = [
        Paragraph(raw_text=t, normalized_text=t, index_in_chapter=i)
        for i, t in enumerate(paragraphs)
    ]
    return Chapter(title=f"Chapter {index}", index=index, paragraphs=paras)


class TestDialogueDetector:
    """Tests for DialogueDetector."""

    def setup_method(self) -> None:
        self.detector = DialogueDetector()

    def test_plain_narration(self) -> None:
        chapter = _make_chapter("Солнце зашло за горизонт. Стало темно.")
        result = self.detector.detect_chapter(chapter)
        assert len(result.paragraphs) == 1
        assert result.dialogue_count == 0
        assert result.narrator_count == 1
        lines = result.paragraphs[0].lines
        assert lines[0].role == SpeakerRole.NARRATOR
        assert not lines[0].is_dialogue

    def test_simple_dialogue_line(self) -> None:
        chapter = _make_chapter("\u2014 \u041f\u0440\u0438\u0432\u0435\u0442!")
        result = self.detector.detect_chapter(chapter)
        lines = result.paragraphs[0].lines
        assert len(lines) == 1
        assert lines[0].is_dialogue
        assert lines[0].text == "\u041f\u0440\u0438\u0432\u0435\u0442!"

    def test_dialogue_with_narrator_remark(self) -> None:
        text = "\u2014 \u041f\u0440\u0438\u0432\u0435\u0442, \u2014 \u0441\u043a\u0430\u0437\u0430\u043b \u043e\u043d."
        chapter = _make_chapter(text)
        result = self.detector.detect_chapter(chapter)
        lines = result.paragraphs[0].lines
        assert len(lines) == 2
        assert lines[0].is_dialogue
        assert "\u041f\u0440\u0438\u0432\u0435\u0442" in lines[0].text
        assert not lines[1].is_dialogue
        assert "\u0441\u043a\u0430\u0437\u0430\u043b" in lines[1].text

    def test_dialogue_remark_continuation(self) -> None:
        text = (
            "\u2014 \u0414\u043e\u0431\u0440\u043e\u0435 \u0443\u0442\u0440\u043e, "
            "\u2014 \u0441\u043a\u0430\u0437\u0430\u043b\u0430 \u043e\u043d\u0430, "
            "\u2014 \u043a\u0430\u043a \u0434\u0435\u043b\u0430?"
        )
        chapter = _make_chapter(text)
        result = self.detector.detect_chapter(chapter)
        lines = result.paragraphs[0].lines
        dialogue_parts = [line for line in lines if line.is_dialogue]
        narrator_parts = [line for line in lines if not line.is_dialogue]
        assert len(dialogue_parts) >= 1
        assert len(narrator_parts) >= 1

    def test_multi_line_dialogue(self) -> None:
        text = (
            "\u2014 \u041f\u043e\u0439\u0434\u0451\u043c \u0434\u043e\u043c\u043e\u0439.\n"
            "\u2014 \u0425\u043e\u0440\u043e\u0448\u043e, "
            "\u2014 \u043e\u0442\u0432\u0435\u0442\u0438\u043b \u043e\u043d."
        )
        chapter = _make_chapter(text)
        result = self.detector.detect_chapter(chapter)
        lines = result.paragraphs[0].lines
        dialogue_lines = [line for line in lines if line.is_dialogue]
        assert len(dialogue_lines) >= 2

    def test_quoted_speech_in_narration(self) -> None:
        text = (
            "\u041e\u043d \u043f\u0440\u043e\u0448\u0435\u043f\u0442\u0430\u043b "
            "\u00ab\u043f\u043e\u043c\u043e\u0433\u0438\u0442\u0435\u00bb "
            "\u0438 \u0437\u0430\u043c\u043e\u043b\u0447\u0430\u043b."
        )
        chapter = _make_chapter(text)
        result = self.detector.detect_chapter(chapter)
        lines = result.paragraphs[0].lines
        has_dialogue = any(line.is_dialogue for line in lines)
        assert has_dialogue

    def test_empty_paragraph_skipped(self) -> None:
        para = Paragraph(raw_text="", normalized_text="", index_in_chapter=0)
        chapter = Chapter(title="Empty", index=0, paragraphs=[para])
        result = self.detector.detect_chapter(chapter)
        assert len(result.paragraphs) == 0

    def test_multi_paragraph_chapter(self) -> None:
        paras = [
            "\u041d\u0430\u0440\u0440\u0430\u0442\u043e\u0440 \u0433\u043e\u0432\u043e\u0440\u0438\u0442.",
            "\u2014 \u0414\u0438\u0430\u043b\u043e\u0433!",
            "\u041e\u043f\u044f\u0442\u044c \u043d\u0430\u0440\u0440\u0430\u0442\u043e\u0440.",
        ]
        chapter = _make_multi_para_chapter(paras)
        result = self.detector.detect_chapter(chapter)
        assert len(result.paragraphs) == 3
        assert result.dialogue_count >= 1
        assert result.narrator_count >= 2

    def test_detect_book(self) -> None:
        ch1 = _make_chapter(
            "\u0422\u0435\u043a\u0441\u0442 "
            "\u043f\u0435\u0440\u0432\u043e\u0439 "
            "\u0433\u043b\u0430\u0432\u044b.",
            index=0,
        )
        ch2 = _make_chapter(
            "\u2014 \u0414\u0438\u0430\u043b\u043e\u0433 "
            "\u0432\u0442\u043e\u0440\u043e\u0439 "
            "\u0433\u043b\u0430\u0432\u044b!",
            index=1,
        )
        book = Book(chapters=[ch1, ch2])
        results = self.detector.detect_book(book)
        assert len(results) == 2
        assert results[0].dialogue_count == 0
        assert results[1].dialogue_count >= 1

    def test_dialogue_line_without_space_after_dash(self) -> None:
        text = "\u2014\u041f\u0440\u0438\u0432\u0435\u0442!"
        chapter = _make_chapter(text)
        result = self.detector.detect_chapter(chapter)
        lines = result.paragraphs[0].lines
        assert lines[0].is_dialogue

    def test_multiple_attribution_verbs(self) -> None:
        verbs = [
            "\u043e\u0442\u0432\u0435\u0442\u0438\u043b",
            "\u0441\u043f\u0440\u043e\u0441\u0438\u043b\u0430",
            "\u043a\u0440\u0438\u043a\u043d\u0443\u043b",
            "\u043f\u0440\u043e\u0448\u0435\u043f\u0442\u0430\u043b\u0430",
        ]
        for verb in verbs:
            text = f"\u2014 \u0422\u0435\u043a\u0441\u0442, \u2014 {verb} \u043e\u043d."
            chapter = _make_chapter(text)
            result = self.detector.detect_chapter(chapter)
            lines = result.paragraphs[0].lines
            narrator_lines = [line for line in lines if not line.is_dialogue]
            assert len(narrator_lines) >= 1, f"Failed for verb: {verb}"
