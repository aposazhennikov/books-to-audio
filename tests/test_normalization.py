"""Tests for normalization pipeline and individual stages."""

from __future__ import annotations

from book_normalizer.models.book import Book, Chapter, Paragraph
from book_normalizer.normalization.cleanup import (
    is_likely_publisher_boilerplate,
    remove_page_numbers,
    remove_publisher_boilerplate,
    remove_repeated_headers,
    strip_ssml_markup,
)
from book_normalizer.normalization.paragraphs import collapse_empty_lines
from book_normalizer.normalization.pipeline import NormalizationPipeline
from book_normalizer.normalization.punctuation import (
    adapt_punctuation_for_tts,
    normalize_dashes,
    normalize_ellipsis,
    normalize_pdf_parenthesis_hyphens,
    normalize_quotes,
    normalize_repeated_commas,
)
from book_normalizer.normalization.whitespace import normalize_whitespace, repair_broken_lines


class TestWhitespace:
    def test_collapse_multiple_spaces(self) -> None:
        assert normalize_whitespace("Привет    мир") == "Привет мир"

    def test_remove_nbsp(self) -> None:
        assert normalize_whitespace("Привет\u00a0мир") == "Привет мир"

    def test_remove_zero_width(self) -> None:
        assert normalize_whitespace("Текст\u200bтекст") == "Тексттекст"

    def test_strip_trailing_spaces(self) -> None:
        result = normalize_whitespace("Текст   \nЕщё   ")
        assert "   " not in result


class TestRepairBrokenLines:
    def test_joins_broken_word(self) -> None:
        result = repair_broken_lines("прекрас\nный")
        assert result == "прекрас ный"

    def test_preserves_paragraph_breaks(self) -> None:
        text = "Конец абзаца.\n\nНовый абзац."
        result = repair_broken_lines(text)
        assert "\n\n" in result


class TestPunctuation:
    def test_normalize_straight_quotes(self) -> None:
        result = normalize_quotes('"текст"')
        assert result == "«текст»"

    def test_normalize_dashes(self) -> None:
        assert "—" in normalize_dashes("слово -- слово")
        assert "—" in normalize_dashes("слово – слово")

    def test_normalize_ellipsis(self) -> None:
        assert normalize_ellipsis("текст...") == "текст…"
        assert normalize_ellipsis("текст....") == "текст…"

    def test_normalize_repeated_commas(self) -> None:
        assert normalize_repeated_commas("— Это же Геркулес,, закричали воины.") == (
            "— Это же Геркулес, закричали воины."
        )

    def test_normalize_pdf_parenthesis_hyphens(self) -> None:
        source = "Применю(ка террористов(сантехников 15(й Аркан"

        assert normalize_pdf_parenthesis_hyphens(source) == "Применю-ка террористов-сантехников 15-й Аркан"

    def test_normalize_pdf_parenthesis_split_words(self) -> None:
        source = "чай с малиновым варень( ем, в комнате при( торно пахло, церк( ви"

        assert normalize_pdf_parenthesis_hyphens(source) == (
            "чай с малиновым вареньем, в комнате приторно пахло, церкви"
        )

    def test_normalize_pdf_parenthesis_hyphens_preserves_normal_parentheses(self) -> None:
        source = "Сергей (похоже) молчал."

        assert normalize_pdf_parenthesis_hyphens(source) == source

    def test_adapt_punctuation_for_tts_does_not_double_dialogue_commas(self) -> None:
        assert adapt_punctuation_for_tts("— Иди с миром, — сказал Сергей.") == (
            "— Иди с миром, сказал Сергей."
        )


class TestCleanup:
    def test_remove_page_numbers(self) -> None:
        text = "Текст.\n123\nЕщё текст."
        result = remove_page_numbers(text)
        assert "123" not in result
        assert "Текст." in result

    def test_remove_repeated_headers(self) -> None:
        text = "Заголовок\nТекст.\nЗаголовок\nЕщё.\nЗаголовок\nКонец."
        result = remove_repeated_headers(text, min_occurrences=3)
        assert "Заголовок" not in result

    def test_remove_repeated_headers_keeps_repeated_chapter_headings(self) -> None:
        text = (
            "Глава первая,\nТекст.\n"
            "Глава первая,\nЕщё текст.\n"
            "Глава первая,\nКонец.\n"
            "Колонтитул\nКолонтитул\nКолонтитул"
        )

        result = remove_repeated_headers(text, min_occurrences=3)

        assert result.count("Глава первая,") == 3
        assert "Колонтитул" not in result

    def test_detect_publisher_boilerplate_urls(self) -> None:
        text = (
            "Спасибо, что скачали книгу в бесплатной электронной библиотеке "
            "Royallib.ru: http://royallib.ru Все книги автора: http://example.test"
        )

        assert is_likely_publisher_boilerplate(text) is True

    def test_publisher_boilerplate_detector_keeps_narration(self) -> None:
        text = "Иван вошёл в комнату и остановился у окна. За стеклом шумел дождь."

        assert is_likely_publisher_boilerplate(text) is False

    def test_remove_publisher_boilerplate_keeps_attached_title(self) -> None:
        text = (
            "Приятного чтения! МОНОСОВ Борис Моисеевич\n"
            "Эта же книга в других форматах: http://royallib.ru/example\n"
            "Глава первая"
        )

        result = remove_publisher_boilerplate(text)

        assert result == "МОНОСОВ Борис Моисеевич\nГлава первая"


class TestCollapseEmptyLines:
    def test_triple_newlines_collapsed(self) -> None:
        result = collapse_empty_lines("A\n\n\n\nB")
        assert result == "A\n\nB"


class TestSsmlCleanup:
    def test_strip_ssml_markup_preserves_dialogue_boundaries(self) -> None:
        text = (
            "<speak xml:lang=\"ru-RU\"><s>\u0413\u043b\u0430\u0432\u0430.</s>"
            "<s>\u2014 \u0412\u044b \u043d\u0435\u043f\u0440\u0430\u0432\u044b.</s></speak>"
        )

        result = strip_ssml_markup(text)

        assert "<s" not in result
        assert "\n\u2014 \u0412\u044b \u043d\u0435\u043f\u0440\u0430\u0432\u044b." in result


class TestNormalizationPipeline:
    def test_normalize_text(self) -> None:
        pipeline = NormalizationPipeline()
        result = pipeline.normalize_text("Привет    мир...  ")
        assert "  " not in result
        assert "…" in result

    def test_normalize_book(self) -> None:
        para = Paragraph(raw_text="Текст   с   пробелами...", index_in_chapter=0)
        ch = Chapter(title="Test", index=0, paragraphs=[para])
        book = Book(chapters=[ch])

        pipeline = NormalizationPipeline()
        pipeline.normalize_book(book)

        assert para.normalized_text
        assert "   " not in para.normalized_text

    def test_custom_stage(self) -> None:
        pipeline = NormalizationPipeline(stages=[])
        pipeline.add_stage("upper", str.upper)
        assert pipeline.normalize_text("hello") == "HELLO"

    def test_ssml_dialogue_survives_pipeline(self) -> None:
        pipeline = NormalizationPipeline()
        text = "<speak><s>\u2014 \u0412\u044b \u043d\u0435\u043f\u0440\u0430\u0432\u044b.</s></speak>"

        result = pipeline.normalize_text(text)

        assert result.startswith("\u2014 \u0412\u044b")

    def test_pipeline_repairs_repeated_commas_before_tts(self) -> None:
        pipeline = NormalizationPipeline()

        result = pipeline.normalize_text("— Феб,, закричали греки,, сам стреловержец Феб здесь.")

        assert result == "— Феб, закричали греки, сам стреловержец Феб здесь."

    def test_pipeline_preserves_dialogue_attribution_dash_for_role_detection(self) -> None:
        pipeline = NormalizationPipeline()

        result = pipeline.normalize_text("— Иди с миром, — сказал Сергей.")

        assert result == "— Иди с миром, — сказал Сергей."

    def test_pipeline_repairs_pdf_parenthesis_hyphens_before_tts(self) -> None:
        pipeline = NormalizationPipeline()

        result = pipeline.normalize_text("Применю(ка свою Звезду. Это 15(й Аркан.")

        assert result == "Применю-ка свою Звезду. Это пятнадцатый Аркан."

    def test_pipeline_repairs_pdf_parenthesis_split_words_before_tts(self) -> None:
        pipeline = NormalizationPipeline()

        result = pipeline.normalize_text("Сергей пил чай с малиновым варень( ем. Фюрер (он же вождь) ждал.")

        assert result == "Сергей пил чай с малиновым вареньем. Фюрер (он же вождь) ждал."
