"""Tests for the PDF loader."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from book_normalizer.config import OcrMode
from book_normalizer.loaders.pdf_loader import (
    PdfLoader,
    PdfOcrCompareResult,
    PdfTextVariant,
    _looks_like_toc,
    _postprocess_ocr_text,
    _prepare_ocr_page_images,
    _repair_ocr_cross_segment_breaks,
    _should_keep_ocr_text,
    extract_pdf_with_ocr_mode,
    select_pdf_text_for_mode,
)


class TestPdfLoader:
    def test_supported_extensions(self) -> None:
        loader = PdfLoader()
        assert ".pdf" in loader.supported_extensions

    def test_can_load(self, tmp_path: Path) -> None:
        loader = PdfLoader()
        assert loader.can_load(tmp_path / "book.pdf")
        assert not loader.can_load(tmp_path / "book.txt")

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        loader = PdfLoader()
        with pytest.raises(FileNotFoundError):
            loader.load(tmp_path / "missing.pdf")

    @patch("book_normalizer.loaders.pdf_loader.PdfLoader._extract_text")
    def test_load_with_mocked_extraction(self, mock_extract: MagicMock, tmp_path: Path) -> None:
        mock_extract.return_value = "Первый абзац.\n\nВторой абзац."

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy")

        loader = PdfLoader()
        book = loader.load(pdf_file)

        assert book.metadata.source_format == "pdf"
        assert len(book.chapters[0].paragraphs) == 2
        assert book.chapters[0].paragraphs[0].raw_text == "Первый абзац."

    @patch("book_normalizer.loaders.pdf_loader.PdfLoader._extract_text")
    def test_audit_trail(self, mock_extract: MagicMock, tmp_path: Path) -> None:
        mock_extract.return_value = "Текст."
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy")

        loader = PdfLoader()
        book = loader.load(pdf_file)
        assert any(r["stage"] == "loading" for r in book.audit_trail)


class TestOcrModeSelection:
    def test_extract_pdf_with_ocr_mode_off_returns_only_native(self, tmp_path: Path) -> None:
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 dummy")

        with patch.object(PdfLoader, "_extract_text", return_value="native text"):
            result = extract_pdf_with_ocr_mode(pdf_file, OcrMode.OFF)

        assert result.native.text == "native text"
        assert result.ocr is None

    def test_select_pdf_text_for_mode_off_uses_native(self) -> None:
        compare = PdfOcrCompareResult(
            native=PdfTextVariant(kind="native", text="native"),
            ocr=PdfTextVariant(kind="ocr", text="ocr"),
        )
        chosen, stats = select_pdf_text_for_mode(compare, OcrMode.OFF)
        assert chosen.kind == "native"
        assert stats["selected"] == "native"

    def test_select_pdf_text_for_mode_force_uses_ocr(self) -> None:
        compare = PdfOcrCompareResult(
            native=PdfTextVariant(kind="native", text="native"),
            ocr=PdfTextVariant(kind="ocr", text="ocr"),
        )
        chosen, stats = select_pdf_text_for_mode(compare, OcrMode.FORCE)
        assert chosen.kind == "ocr"
        assert stats["selected"] == "ocr"

    def test_select_pdf_text_for_mode_auto_falls_back_when_native_empty(self) -> None:
        compare = PdfOcrCompareResult(
            native=PdfTextVariant(kind="native", text="   "),
            ocr=PdfTextVariant(kind="ocr", text="Распознанный русский текст"),
        )
        chosen, stats = select_pdf_text_for_mode(compare, OcrMode.AUTO)
        assert chosen.kind == "ocr"
        assert stats["selected"] == "ocr"
        assert stats["ocr_unreadable"] is False

    def test_select_pdf_text_for_mode_auto_does_not_use_unreadable_ocr(self) -> None:
        compare = PdfOcrCompareResult(
            native=PdfTextVariant(kind="native", text="Co,11;ep'l\\:aHne rJIABA"),
            ocr=PdfTextVariant(kind="ocr", text="lorem ipsum OCR garbage"),
        )

        chosen, stats = select_pdf_text_for_mode(compare, OcrMode.AUTO)

        assert chosen.kind == "native"
        assert stats["native_unreadable"] is True
        assert stats["ocr_unreadable"] is True
        assert stats["reason"] == "auto_mode_no_readable_ocr"

    def test_select_pdf_text_for_mode_auto_prefers_native_when_not_empty(self) -> None:
        compare = PdfOcrCompareResult(
            native=PdfTextVariant(kind="native", text="Родной текст на русском языке"),
            ocr=PdfTextVariant(kind="ocr", text="Текст после распознавания"),
        )
        chosen, stats = select_pdf_text_for_mode(compare, OcrMode.AUTO)
        assert chosen.kind == "native"
        assert stats["selected"] == "native"
        assert stats["native_unreadable"] is False

    def test_select_pdf_text_for_mode_compare_uses_ocr_when_native_is_short_overlay(self) -> None:
        native = "Верёвка есть вервие простое Из учебного наставления для палачей"
        ocr_text = (
            "ГЛАВА ПЕРВАЯ Повествующая, в общем-то, ни о чем, но зато содержащая "
            "глубокое исследование этого предмета. Сергей сидел за столом и пил "
            "чай с малиновым вареньем. Состояние было весьма тоскливым. "
        ) * 20
        compare = PdfOcrCompareResult(
            native=PdfTextVariant(kind="native", text=native),
            ocr=PdfTextVariant(kind="ocr", text=ocr_text),
        )

        chosen, stats = select_pdf_text_for_mode(compare, OcrMode.COMPARE)

        assert chosen.kind == "ocr"
        assert stats["selected"] == "ocr"
        assert stats["native_unreadable"] is False
        assert stats["ocr_much_longer"] is True
        assert stats["reason"] == "compare_mode_ocr_much_longer_use_ocr"

    def test_select_pdf_text_for_mode_marks_broken_native_when_ocr_unavailable(self) -> None:
        compare = PdfOcrCompareResult(
            native=PdfTextVariant(kind="native", text="Co,11;ep'l\\:aHne rJIABA llEPBMI"),
            ocr=None,
        )

        chosen, stats = select_pdf_text_for_mode(compare, OcrMode.AUTO)

        assert chosen.kind == "native"
        assert stats["native_unreadable"] is True
        assert stats["reason"] == "ocr_unavailable_native_unreadable"


class TestOcrImagePreparation:
    def test_prepare_ocr_page_images_splits_landscape_spread(self) -> None:
        pil_image = pytest.importorskip("PIL.Image")

        img = pil_image.new("L", (1000, 600), 255)
        for x0 in (120, 620):
            for y in range(120, 480, 18):
                for x in range(x0, x0 + 260):
                    img.putpixel((x, y), 0)

        segments = _prepare_ocr_page_images(img)

        assert len(segments) == 2
        assert all(segment.size[0] < img.size[0] for segment in segments)

    def test_postprocess_ocr_text_drops_noise_and_joins_hyphenation(self) -> None:
        raw = "' \\\\ . p .\nСОДЕРЖА-\nЩАЯ ГЛУБОКОЕ\nисследование предмета ^^: #2"

        cleaned = _postprocess_ocr_text(raw)

        assert "p ." not in cleaned
        assert "СОДЕРЖАЩАЯ ГЛУБОКОЕ исследование предмета" in cleaned
        assert "#2" not in cleaned

    def test_postprocess_ocr_text_removes_inline_pipe_noise_before_dialogue(self) -> None:
        raw = (
            "Он нахватался зайчиков. Го | Фаланга пошла.\n"
            "Песок: о РЕ Г | — Гера, ты помнишь?\n"
            "воины под.при- | крытием щитов"
        )

        cleaned = _postprocess_ocr_text(raw)

        assert "Го |" not in cleaned
        assert "РЕ Г |" not in cleaned
        assert "Он нахватался зайчиков. Фаланга пошла." in cleaned
        assert "Песок: — Гера, ты помнишь?" in cleaned
        assert "под прикрытием" in cleaned

    def test_postprocess_ocr_text_removes_glued_page_numbers(self) -> None:
        raw = (
            "снежный ком. | 5\n"
            "Сергей представил себе картину битвы."
        )

        cleaned = _postprocess_ocr_text(raw)

        assert "| 5" not in cleaned
        assert "ком. Сергей" in cleaned
        assert "ком. 5 Сергей" not in cleaned

    def test_postprocess_ocr_text_drops_short_debris_paragraphs(self) -> None:
        raw = (
            "Сергей открыл дверь. ^ й В по\n\n"
            "и. = т р. НН: | с.\n\n"
            "Затем он вернулся на кухню."
        )

        cleaned = _postprocess_ocr_text(raw)

        assert "^ й В по" not in cleaned
        assert "НН:" not in cleaned
        assert "Сергей открыл дверь." in cleaned
        assert "Затем он вернулся на кухню." in cleaned

    def test_postprocess_ocr_text_removes_inline_symbol_clusters(self) -> None:
        raw = (
            "Это же Геркулес, - закричали воины. ^ г: Сергей поднялся.\n"
            "Он за него возьмусь. ^ :` | Гроза началась."
        )

        cleaned = _postprocess_ocr_text(raw)

        assert "^" not in cleaned
        assert "|" not in cleaned
        assert "воины. Сергей поднялся" in cleaned
        assert "возьмусь. Гроза началась" in cleaned

    def test_postprocess_ocr_text_uses_backtick_as_word_boundary(self) -> None:
        raw = "Сергей`поднял руку. Герасим меж ТЕМ‘трансформировал облик."

        cleaned = _postprocess_ocr_text(raw)

        assert "Сергей поднял" in cleaned
        assert "ТЕМ трансформировал" in cleaned

    def test_postprocess_ocr_text_removes_short_token_runs(self) -> None:
        raw = "Уходите, там смерть, туда нельзя, — крикнул он; 2 3 КО и СР НЕ Воспоминание окончилось."

        cleaned = _postprocess_ocr_text(raw)

        assert "2 3" not in cleaned
        assert "СР НЕ" not in cleaned
        assert "он. Воспоминание" in cleaned

    def test_postprocess_ocr_text_removes_leftover_forbidden_symbols(self) -> None:
        raw = (
            "Льготы? — переспросил старший монах. |!\n\n"
            "Сатисфакции? ®› и. Нет мадам.\n\n"
            "Ответил Сергей с. 7:\n\n"
            "Подземных {сооружений и церквей №.\n\n"
            "Конец первой части & ^ © ° < > и:\n\n"
            "страница 7:"
        )

        cleaned = _postprocess_ocr_text(raw)

        assert "|" not in cleaned
        assert "^" not in cleaned
        assert "&" not in cleaned
        assert "®" not in cleaned
        assert "№" not in cleaned
        assert "{" not in cleaned
        assert "©" not in cleaned
        assert "страница 7" not in cleaned
        assert "с. 7" not in cleaned
        assert "Льготы? — переспросил старший монах." in cleaned
        assert "Ответил Сергей" in cleaned
        assert "Конец первой части" in cleaned
        assert "части и:" not in cleaned

    def test_postprocess_ocr_text_removes_short_noisy_fragments(self) -> None:
        raw = (
            "Герасим меж ТЕМ‘трансформировал облик. ««- 1. тЫ РИ. - Это же Геркулес.\n"
            "Рыжую шевелюру.“ —.. и . — Феб здесь.: Сергей`поднял руку.\n"
            "Габриель, деточка, разберись с этими жуликами. Бет а\n"
            "Ангел появился с мечом. . . И у. ЕО С ЕЁ\n"
            "дей ии р один р: к « Н к,. + Вы больше не требуете сатисфакции?\n"
            "Нет мадам, совершенно точно нет. „ — . .# г о . Из разговора.\n"
            "Уходите, там смерть, туда нельзя, — крикнул он; Воспоминание окончилось.\n"
            "Он спросил. — Да. Она ответила."
        )

        cleaned = _postprocess_ocr_text(raw)

        assert "тЫ РИ" not in cleaned
        assert "—.." not in cleaned
        assert "Бет а" not in cleaned
        assert "ЕО С ЕЁ" not in cleaned
        assert "дей ии" not in cleaned
        assert "# г о" not in cleaned
        assert "жуликами. Ангел появился" in cleaned
        assert "Вы больше не требуете сатисфакции?" in cleaned
        assert "нет. Из разговора" in cleaned
        assert "здесь. Сергей поднял" in cleaned
        assert "крикнул он. Воспоминание" in cleaned
        assert "Он спросил. — Да. Она ответила." in cleaned

    def test_postprocess_ocr_text_fixes_common_digit_hyphen_glitch(self) -> None:
        raw = "Ночь влекла вперед к новым 32-\nботам."

        cleaned = _postprocess_ocr_text(raw)

        assert "новым заботам" in cleaned
        assert "32" not in cleaned

    def test_repair_ocr_cross_segment_breaks_joins_split_words(self) -> None:
        raw = "Электричество, скопивш\n\nееся в атмосфере.\n\nОн держал при-\n\nкрытие."

        cleaned = _repair_ocr_cross_segment_breaks(raw)

        assert "скопившееся в атмосфере" in cleaned
        assert "прикрытие" in cleaned
        assert "скопивш\n\nееся" not in cleaned
        assert "при-\n\nкрытие" not in cleaned

    def test_postprocess_ocr_text_keeps_chapter_heading_separate(self) -> None:
        raw = (
            "_ Веревка есть вервие простое\n"
            "Из учебного наставления для палачей\n"
            "ГЛАВА ПЕРВАЯ О\n"
            "ПОВЕСТВУЮЩАЯ, В ОБЩЕМ-ТО, НИ О ЧЕМ\n"
            "Сергей сидел за столом."
        )

        cleaned = _postprocess_ocr_text(raw)

        assert cleaned.split("\n\n") == [
            "Веревка есть вервие простое Из учебного наставления для палачей",
            "ГЛАВА ПЕРВАЯ О",
            "ПОВЕСТВУЮЩАЯ, В ОБЩЕМ-ТО, НИ О ЧЕМ Сергей сидел за столом.",
        ]

    def test_postprocess_ocr_text_splits_inline_chapter_heading(self) -> None:
        raw = (
            "Из библии для чиновников ГЛАВА ТРЕТЬЯ -. "
            "СОБЫТИЯ В КОТОРОЙ РАЗВИВАЮТСЯ ВО СНЕ"
        )

        cleaned = _postprocess_ocr_text(raw)

        assert cleaned.split("\n\n") == [
            "Из библии для чиновников",
            "ГЛАВА ТРЕТЬЯ",
            "СОБЫТИЯ В КОТОРОЙ РАЗВИВАЮТСЯ ВО СНЕ",
        ]

    def test_should_keep_ocr_text_rejects_title_page_debris(self) -> None:
        debris = (
            "Б. М. Моносов Часть первая ‚ИТ о о ИТ ‚аа ся к о УЗО у о ВОт ли "
            "Кр а О р о Я к а с ы т два че У ть Ре ФЕ с Л Я ВЫ три процента "
            "Санкт-Петербург две тысячи шесть"
        )
        body = (
            "Сергей сидел за столом и пил чай с малиновым вареньем. "
            "Состояние было весьма тоскливым. Болели старые раны, знаменуя "
            "собой приближение грозы. С улицы парило через открытое окно."
        )

        assert _should_keep_ocr_text(debris) is False
        assert _should_keep_ocr_text(body) is True

    def test_should_keep_ocr_text_rejects_toc_blocks(self) -> None:
        toc = (
            "Содержание\n"
            "ГЛАВА ПЕРВАЯ ................................ 3\n"
            "ГЛАВА ВТОРАЯ ................................ 7\n"
            "ГЛАВА ТРЕТЬЯ ................................ 10\n"
        )

        assert _looks_like_toc(toc) is True
        assert _should_keep_ocr_text(toc) is False
