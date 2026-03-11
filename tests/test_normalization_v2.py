"""Tests for Phase 2 normalization additions."""

from __future__ import annotations

from book_normalizer.models.book import Book, Chapter, Paragraph
from book_normalizer.normalization.encoding import fix_common_mojibake, normalize_encoding_artifacts
from book_normalizer.normalization.pipeline import NormalizationPipeline
from book_normalizer.normalization.whitespace import (
    normalize_spacing_around_punctuation,
    repair_hyphenated_words,
)


class TestRepairHyphenatedWords:
    def test_soft_hyphen_across_lines(self) -> None:
        text = "при\u00ad\nмер"
        result = repair_hyphenated_words(text)
        assert result == "пример"

    def test_dash_hyphen_across_lines(self) -> None:
        text = "при-\nмер"
        result = repair_hyphenated_words(text)
        assert result == "пример"

    def test_preserves_real_hyphens(self) -> None:
        text = "кое-что"
        result = repair_hyphenated_words(text)
        assert result == "кое-что"

    def test_preserves_dash_before_uppercase(self) -> None:
        text = "слово-\nСлово"
        result = repair_hyphenated_words(text)
        assert result == "слово-\nСлово"


class TestSpacingAroundPunctuation:
    def test_removes_space_before_comma(self) -> None:
        assert normalize_spacing_around_punctuation("слово , слово") == "слово, слово"

    def test_removes_space_before_period(self) -> None:
        assert normalize_spacing_around_punctuation("конец .") == "конец."

    def test_adds_space_after_comma(self) -> None:
        assert normalize_spacing_around_punctuation("слово,слово") == "слово, слово"

    def test_adds_space_after_period(self) -> None:
        result = normalize_spacing_around_punctuation("Конец.Начало")
        assert result == "Конец. Начало"

    def test_no_double_space(self) -> None:
        result = normalize_spacing_around_punctuation("слово ,  слово")
        assert "  " not in result


class TestEncodingNormalization:
    def test_removes_replacement_char(self) -> None:
        result = normalize_encoding_artifacts("текст\ufffdтекст")
        assert "\ufffd" not in result
        assert result == "тексттекст"

    def test_removes_control_characters(self) -> None:
        result = normalize_encoding_artifacts("текст\x03текст")
        assert "\x03" not in result

    def test_removes_bom(self) -> None:
        result = normalize_encoding_artifacts("\ufeffтекст")
        assert result == "текст"


class TestMojibakeFix:
    def test_known_pattern(self) -> None:
        for bad, good in [
            ("\u0432\u0402\u201c", "\u2014"),
            ("\u0432\u0402\u201d", "\u2014"),
        ]:
            assert fix_common_mojibake(f"text{bad}text") == f"text{good}text"

    def test_clean_text_unchanged(self) -> None:
        text = "Чистый русский текст без артефактов."
        assert fix_common_mojibake(text) == text


class TestPipelineV2:
    def test_stage_names(self) -> None:
        pipeline = NormalizationPipeline()
        names = pipeline.stage_names
        assert "normalize_encoding_artifacts" in names
        assert "repair_hyphenated_words" in names
        assert "normalize_spacing_around_punctuation" in names
        assert names.index("normalize_encoding_artifacts") < names.index("normalize_whitespace")

    def test_normalize_text_with_tracking(self) -> None:
        pipeline = NormalizationPipeline()
        text = "слово   слово"
        result, changed = pipeline.normalize_text_with_tracking(text)
        assert "   " not in result
        assert "normalize_whitespace" in changed

    def test_tracking_empty_for_clean_text(self) -> None:
        pipeline = NormalizationPipeline()
        clean = "Чистый текст."
        result, changed = pipeline.normalize_text_with_tracking(clean)
        assert result == clean
        assert len(changed) == 0

    def test_detailed_audit_in_book(self) -> None:
        para = Paragraph(raw_text="слово   слово...", index_in_chapter=0)
        ch = Chapter(title="Test", index=0, paragraphs=[para])
        book = Book(chapters=[ch])

        pipeline = NormalizationPipeline()
        pipeline.normalize_book(book, detailed_audit=True)

        assert para.normalized_text
        audit = book.audit_trail[-1]
        assert "active_stages" in audit["details"]
        assert "normalize_whitespace" in audit["details"]

    def test_insert_stage_before(self) -> None:
        pipeline = NormalizationPipeline(stages=[("a", str.strip), ("c", str.upper)])
        pipeline.insert_stage_before("c", "b", str.title)
        assert pipeline.stage_names == ["a", "b", "c"]

    def test_remove_stage(self) -> None:
        pipeline = NormalizationPipeline(stages=[("a", str.strip), ("b", str.upper)])
        removed = pipeline.remove_stage("a")
        assert removed is True
        assert pipeline.stage_names == ["b"]

    def test_remove_nonexistent_stage(self) -> None:
        pipeline = NormalizationPipeline(stages=[("a", str.strip)])
        removed = pipeline.remove_stage("z")
        assert removed is False
