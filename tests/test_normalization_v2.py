"""Tests for Phase 2 normalization additions."""

from __future__ import annotations

from book_normalizer.models.book import Book, Chapter, Paragraph
from book_normalizer.normalization.encoding import fix_common_mojibake, normalize_encoding_artifacts
from book_normalizer.normalization.pipeline import NormalizationPipeline
from book_normalizer.normalization.whitespace import (
    normalize_spacing_around_punctuation,
    repair_hyphenated_words,
    repair_pdf_split_russian_words,
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

    def test_repairs_pdf_open_paren_line_wrap_artifacts(self) -> None:
        text = "из подпростран(\nства к солнеч(\n\nным ожогам и расхлё(\nбывать это"
        result = repair_hyphenated_words(text)
        assert result == "из подпространства к солнечным ожогам и расхлёбывать это"

    def test_preserves_real_parentheses(self) -> None:
        text = "слово(текст) осталось"
        result = repair_hyphenated_words(text)
        assert result == text

    def test_preserves_real_hyphens(self) -> None:
        text = "кое-что"
        result = repair_hyphenated_words(text)
        assert result == "кое-что"

    def test_preserves_dash_before_uppercase(self) -> None:
        text = "слово-\nСлово"
        result = repair_hyphenated_words(text)
        assert result == "слово-\nСлово"


class TestRepairPdfSplitRussianWords:
    def test_repairs_common_native_pdf_word_splits(self) -> None:
        text = "Нам придется расхлё бывать эту историю после абор дажном бою."

        assert repair_pdf_split_russian_words(text) == (
            "Нам придется расхлёбывать эту историю после абордажном бою."
        )

    def test_preserves_ordinary_short_words(self) -> None:
        text = "Он не хотел ни о чем говорить."

        assert repair_pdf_split_russian_words(text) == text

    def test_repairs_pdf_parenthesis_in_indefinite_particles(self) -> None:
        text = "Почему(то он вышел из(за бархана и взял что(либо."

        assert repair_pdf_split_russian_words(text) == "Почему-то он вышел из-за бархана и взял что-либо."


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
        assert "repair_pdf_split_russian_words" in names
        assert "normalize_spacing_around_punctuation" in names
        assert names.index("normalize_encoding_artifacts") < names.index("normalize_whitespace")
        assert names.index("repair_hyphenated_words") < names.index("repair_pdf_split_russian_words")

    def test_normalize_text_with_tracking(self) -> None:
        pipeline = NormalizationPipeline()
        text = "слово   слово"
        result, changed = pipeline.normalize_text_with_tracking(text)
        assert "   " not in result
        assert any(
            s in changed for s in ("normalize_whitespace", "fix_ocr_artifacts")
        )

    def test_cross_paragraph_pdf_open_paren_word_split(self) -> None:
        para1 = Paragraph(raw_text="терний и солнеч(", index_in_chapter=0)
        para2 = Paragraph(raw_text="ных ожогов.", index_in_chapter=1)
        ch = Chapter(title="Test", index=0, paragraphs=[para1, para2])
        book = Book(chapters=[ch])

        NormalizationPipeline().normalize_book(book)

        assert para1.normalized_text == "терний и солнечных ожогов."
        assert para2.normalized_text == ""
        assert ch.normalized_text == "терний и солнечных ожогов."

    def test_cross_paragraph_hyphen_moves_full_word_tail(self) -> None:
        para1 = Paragraph(raw_text="это при-", index_in_chapter=0)
        para2 = Paragraph(raw_text="мер переноса.", index_in_chapter=1)
        ch = Chapter(title="Test", index=0, paragraphs=[para1, para2])
        book = Book(chapters=[ch])

        NormalizationPipeline().normalize_book(book)

        assert para1.normalized_text == "это пример переноса."
        assert para2.normalized_text == ""
        assert ch.normalized_text == "это пример переноса."

    def test_cross_paragraph_pdf_open_paren_skips_blank_gap(self) -> None:
        para1 = Paragraph(raw_text="выдала полуоргани(", index_in_chapter=0)
        gap = Paragraph(raw_text="", index_in_chapter=1)
        para2 = Paragraph(raw_text="ческий механизм.", index_in_chapter=2)
        ch = Chapter(title="Test", index=0, paragraphs=[para1, gap, para2])
        book = Book(chapters=[ch])

        NormalizationPipeline().normalize_book(book)

        assert ch.normalized_text == "выдала полуорганический механизм."
        assert gap.raw_text == ""
        assert para2.normalized_text == ""

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
        assert any(
            s in audit["details"]
            for s in ("normalize_whitespace", "fix_ocr_artifacts")
        )

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
