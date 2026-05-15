"""Tests for speaker attribution strategies."""

from __future__ import annotations

from pathlib import Path

import pytest

from book_normalizer.dialogue.attribution import (
    HeuristicAttributor,
    LlmAttributor,
    ManualAttributor,
    SpeakerMode,
    _line_cache_key,
    create_attributor,
)
from book_normalizer.dialogue.models import (
    AnnotatedChapter,
    AnnotatedParagraph,
    DialogueLine,
    SpeakerRole,
)


def _make_annotated_chapter(
    lines_spec: list[tuple[str, bool]],
    chapter_index: int = 0,
) -> AnnotatedChapter:
    """Build an AnnotatedChapter from (text, is_dialogue) pairs."""
    lines = []
    for i, (text, is_dialogue) in enumerate(lines_spec):
        lines.append(
            DialogueLine(
                text=text,
                role=SpeakerRole.UNKNOWN if is_dialogue else SpeakerRole.NARRATOR,
                paragraph_id="p0",
                line_index=i,
                is_dialogue=is_dialogue,
            )
        )
    para = AnnotatedParagraph(
        paragraph_id="p0", chapter_index=chapter_index, lines=lines
    )
    return AnnotatedChapter(
        chapter_index=chapter_index,
        chapter_title=f"Chapter {chapter_index}",
        paragraphs=[para],
    )


class TestHeuristicAttributor:
    """Tests for the rule-based heuristic attributor."""

    def setup_method(self) -> None:
        self.attr = HeuristicAttributor()

    def test_male_attribution_from_remark(self) -> None:
        chapter = _make_annotated_chapter([
            ("\u041f\u0440\u0438\u0432\u0435\u0442", True),
            ("\u0441\u043a\u0430\u0437\u0430\u043b \u043e\u043d.", False),
        ])
        self.attr.attribute([chapter])
        lines = chapter.paragraphs[0].lines
        assert lines[0].role == SpeakerRole.MALE

    def test_female_attribution_from_remark(self) -> None:
        chapter = _make_annotated_chapter([
            ("\u0414\u043e\u0431\u0440\u043e\u0435 \u0443\u0442\u0440\u043e", True),
            ("\u0441\u043a\u0430\u0437\u0430\u043b\u0430 \u043e\u043d\u0430.", False),
        ])
        self.attr.attribute([chapter])
        lines = chapter.paragraphs[0].lines
        assert lines[0].role == SpeakerRole.FEMALE

    def test_alternation_without_attribution(self) -> None:
        chapter = _make_annotated_chapter([
            ("\u041f\u0440\u0438\u0432\u0435\u0442", True),
            ("\u0441\u043a\u0430\u0437\u0430\u043b \u043e\u043d.", False),
            ("\u0417\u0434\u0440\u0430\u0432\u0441\u0442\u0432\u0443\u0439\u0442\u0435!", True),
            ("\u041a\u0430\u043a \u0434\u0435\u043b\u0430?", True),
        ])
        self.attr.attribute([chapter])
        lines = chapter.paragraphs[0].lines
        assert lines[0].role == SpeakerRole.MALE
        assert lines[2].role == SpeakerRole.FEMALE
        assert lines[3].role == SpeakerRole.MALE

    def test_alternation_carries_across_paragraphs(self) -> None:
        ch = AnnotatedChapter(
            chapter_index=0,
            chapter_title="Chapter 0",
            paragraphs=[
                AnnotatedParagraph(
                    paragraph_id="p0",
                    chapter_index=0,
                    lines=[
                        DialogueLine(
                            text="First",
                            role=SpeakerRole.UNKNOWN,
                            is_dialogue=True,
                            paragraph_id="p0",
                        ),
                    ],
                ),
                AnnotatedParagraph(
                    paragraph_id="p1",
                    chapter_index=0,
                    lines=[
                        DialogueLine(
                            text="Second",
                            role=SpeakerRole.UNKNOWN,
                            is_dialogue=True,
                            paragraph_id="p1",
                        ),
                    ],
                ),
            ],
        )

        self.attr.attribute([ch])

        first = ch.paragraphs[0].lines[0]
        second = ch.paragraphs[1].lines[0]
        assert first.role == SpeakerRole.MALE
        assert second.role == SpeakerRole.FEMALE

    def test_narrator_lines_unchanged(self) -> None:
        chapter = _make_annotated_chapter([
            ("\u041d\u0430\u0440\u0440\u0430\u0442\u043e\u0440 \u0433\u043e\u0432\u043e\u0440\u0438\u0442.", False),
        ])
        self.attr.attribute([chapter])
        lines = chapter.paragraphs[0].lines
        assert lines[0].role == SpeakerRole.NARRATOR

    def test_result_statistics(self) -> None:
        chapter = _make_annotated_chapter([
            ("\u041d\u0430\u0440\u0440\u0430\u0446\u0438\u044f.", False),
            ("\u0420\u0435\u043f\u043b\u0438\u043a\u0430", True),
            ("\u0441\u043a\u0430\u0437\u0430\u043b \u043e\u043d.", False),
        ])
        result = self.attr.attribute([chapter])
        assert result.strategy == "heuristic"
        assert result.total_lines == 3
        assert result.narrator_lines == 2
        assert result.male_lines == 1
        assert result.chapters_processed == 1

    def test_multiple_chapters(self) -> None:
        ch1 = _make_annotated_chapter([
            ("\u0420\u0435\u043f\u043b\u0438\u043a\u0430", True),
            ("\u0441\u043a\u0430\u0437\u0430\u043b \u043e\u043d.", False),
        ], chapter_index=0)
        ch2 = _make_annotated_chapter([
            ("\u0414\u0440\u0443\u0433\u0430\u044f \u0440\u0435\u043f\u043b\u0438\u043a\u0430", True),
            ("\u043e\u0442\u0432\u0435\u0442\u0438\u043b\u0430 \u043e\u043d\u0430.", False),
        ], chapter_index=1)
        result = self.attr.attribute([ch1, ch2])
        assert result.male_lines == 1
        assert result.female_lines == 1
        assert result.chapters_processed == 2


class TestLlmAttributor:
    """Tests for the LLM attributor (parsing and caching logic)."""

    def test_parse_valid_json(self) -> None:
        content = '[{"line_id": "abc", "role": "male"}]'
        result = LlmAttributor._parse_llm_response(content)
        assert len(result) == 1
        assert result[0]["role"] == "male"

    def test_parse_json_with_surrounding_text(self) -> None:
        content = 'Here is the result:\n[{"line_id": "x", "role": "female"}]\nDone.'
        result = LlmAttributor._parse_llm_response(content)
        assert len(result) == 1
        assert result[0]["role"] == "female"

    def test_parse_invalid_json_returns_empty(self) -> None:
        result = LlmAttributor._parse_llm_response("not json at all")
        assert result == []

    def test_apply_annotations(self) -> None:
        line = DialogueLine(
            id="test1", text="\u041f\u0440\u0438\u0432\u0435\u0442", is_dialogue=True, role=SpeakerRole.UNKNOWN
        )
        annotations = [{"line_id": "test1", "role": "female"}]
        LlmAttributor._apply_annotations([line], annotations)
        assert line.role == SpeakerRole.FEMALE
        assert line.attribution_tag == "llm"

    def test_context_payload_includes_narrator_remark(self) -> None:
        chapter = _make_annotated_chapter([
            ("\u041f\u0440\u0438\u0432\u0435\u0442", True),
            ("\u0441\u043a\u0430\u0437\u0430\u043b \u043e\u043d.", False),
        ])
        line = chapter.paragraphs[0].lines[0]

        payload = LlmAttributor._build_context_payload(chapter, [line])

        assert payload[0]["kind"] == "dialogue"
        assert "line_id" in payload[0]
        assert payload[1] == {
            "kind": "narrator",
            "text": "\u0441\u043a\u0430\u0437\u0430\u043b \u043e\u043d.",
        }

    def test_cache_save_and_load(self, tmp_path: Path) -> None:
        attr = LlmAttributor(cache_dir=tmp_path)
        data = [{"line_id": "a", "role": "male"}]
        attr._save_cache(0, data)
        loaded = attr._load_cache(0)
        assert loaded == data

    def test_cache_miss_returns_none(self, tmp_path: Path) -> None:
        attr = LlmAttributor(cache_dir=tmp_path)
        assert attr._load_cache(99) is None

    def test_cache_key_depends_on_text_and_model(self, tmp_path: Path) -> None:
        ch = _make_annotated_chapter([("Hello?", True)])
        lines = ch.paragraphs[0].lines
        attr1 = LlmAttributor(model="model-a", cache_dir=tmp_path)
        attr2 = LlmAttributor(model="model-b", cache_dir=tmp_path)

        key1 = attr1._cache_fingerprint(ch, lines)
        key2 = attr2._cache_fingerprint(ch, lines)
        lines[0].text = "Changed?"
        key3 = attr1._cache_fingerprint(ch, lines)

        assert key1 != key2
        assert key1 != key3


class TestManualAttributor:
    """Tests for the manual attributor session persistence."""

    def test_session_save_load(self, tmp_path: Path) -> None:
        session_path = tmp_path / "manual_session.json"
        attr = ManualAttributor(session_path=session_path)
        attr._decisions = {"line1": "male", "line2": "female"}
        attr._save_session()

        attr2 = ManualAttributor(session_path=session_path)
        assert attr2._decisions == {"line1": "male", "line2": "female"}

    def test_empty_session(self, tmp_path: Path) -> None:
        session_path = tmp_path / "nonexistent.json"
        attr = ManualAttributor(session_path=session_path)
        assert attr._decisions == {}

    def test_session_reuses_stable_line_key(self, tmp_path: Path) -> None:
        session_path = tmp_path / "manual_session.json"
        chapter = _make_annotated_chapter([("Hello?", True)], chapter_index=2)
        line = chapter.paragraphs[0].lines[0]
        key = _line_cache_key(line, chapter.chapter_index, 0)

        attr = ManualAttributor(session_path=session_path)
        attr._decisions = {key: "female"}
        attr._save_session()

        # Recreate the chapter so DialogueLine.id changes, but text/index stay stable.
        recreated = _make_annotated_chapter([("Hello?", True)], chapter_index=2)
        attr2 = ManualAttributor(session_path=session_path)
        attr2.attribute([recreated])

        recreated_line = recreated.paragraphs[0].lines[0]
        assert recreated_line.role == SpeakerRole.FEMALE
        assert recreated_line.attribution_tag == "manual:cached"


class TestFactory:
    """Tests for the create_attributor factory."""

    def test_create_heuristic(self) -> None:
        attr = create_attributor(SpeakerMode.HEURISTIC)
        assert isinstance(attr, HeuristicAttributor)

    def test_create_llm(self) -> None:
        attr = create_attributor(
            SpeakerMode.LLM, llm_endpoint="http://test:1234"
        )
        assert isinstance(attr, LlmAttributor)

    def test_create_manual(self) -> None:
        attr = create_attributor(SpeakerMode.MANUAL)
        assert isinstance(attr, ManualAttributor)

    def test_invalid_mode_raises(self) -> None:
        with pytest.raises(ValueError):
            create_attributor("invalid")  # type: ignore[arg-type]
