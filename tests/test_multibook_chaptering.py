"""Tests for multi-work structure detection."""

from __future__ import annotations

from book_normalizer.chaptering.detector import ChapterDetector, _HeadingHit
from book_normalizer.chaptering.patterns import match_chapter_heading, match_work_heading
from book_normalizer.models.book import Book, Chapter, Paragraph


def _book(texts: list[str]) -> Book:
    paragraphs = [
        Paragraph(raw_text=text, index_in_chapter=index)
        for index, text in enumerate(texts)
    ]
    return Book(chapters=[Chapter(title="Full Text", index=0, paragraphs=paragraphs)])


def test_multibook_repeated_chapter_numbers_are_preserved() -> None:
    """Repeated chapter names across detected works must not be deduplicated."""
    book = _book([
        "Книга первая",
        "Глава 1",
        "Текст первой книги, первой главы.",
        "Глава 2",
        "Текст первой книги, второй главы.",
        "Книга вторая",
        "Глава 1",
        "Текст второй книги, первой главы.",
        "Глава 2",
        "Текст второй книги, второй главы.",
    ])

    result = ChapterDetector().detect_and_split(book)

    assert len(result.chapters) == 4
    assert [chapter.work_title for chapter in result.chapters] == [
        "Книга первая",
        "Книга первая",
        "Книга вторая",
        "Книга вторая",
    ]
    assert result.chapters[0].title == "Книга первая - Глава 1"
    assert result.chapters[2].title == "Книга вторая - Глава 1"
    assert result.metadata.extra["structure"]["work_count"] == 2
    assert result.metadata.extra["structure"]["needs_review"] is True


def test_multibook_without_chapters_creates_one_section_per_work() -> None:
    """A collection can contain works without explicit chapters."""
    book = _book([
        "Book One",
        "A standalone novella without chapter headings.",
        "More text from the first novella.",
        "Book Two",
        "Another standalone novella without chapter headings.",
        "More text from the second novella.",
    ])

    result = ChapterDetector().detect_and_split(book)

    assert len(result.chapters) == 2
    assert result.chapters[0].title == "Book One"
    assert result.chapters[1].title == "Book Two"
    assert result.chapters[0].work_title == "Book One"
    assert result.chapters[1].work_title == "Book Two"


def test_large_work_without_glava_splits_at_internal_section_titles() -> None:
    """Large standalone works often use named sections instead of "Глава" headings."""
    long_body = " ".join(["Текст большого раздела."] * 700)
    book = _book([
        "Book One",
        "Параграф 1, пункт десять космического уложения Империи.",
        f"Мы все умрём\n{long_body}",
        f"Посылка сообщения\n{long_body}",
        f"Помощь извне\n{long_body}",
        "Book Two",
        f"Включения\n{long_body}",
        f"Восход Солнца\n{long_body}",
        f"Старый город\n{long_body}",
    ])

    result = ChapterDetector().detect_and_split(book)

    assert [chapter.title for chapter in result.chapters] == [
        "Book One - Preamble",
        "Book One - Мы все умрём",
        "Book One - Посылка сообщения",
        "Book One - Помощь извне",
        "Book Two - Включения",
        "Book Two - Восход Солнца",
        "Book Two - Старый город",
    ]
    assert result.metadata.extra["structure"]["work_count"] == 2


def test_large_late_numbered_work_splits_past_work_title_hit() -> None:
    """Late numeric work boundaries can also be chapter hits; split inside them."""
    long_body = " ".join(["Текст большого раздела."] * 700)
    book = _book([
        "1. вход в спираль",
        "Глава первая,",
        "Текст первой книги.",
        "Глава вторая,",
        "Продолжение первой книги.",
        "2. наследники сета",
        "Глава первая,",
        "Текст второй книги.",
        "Глава вторая,",
        "Продолжение второй книги.",
        "Глава третья,",
        "Еще текст второй книги.",
        "Глава четвертая,",
        "Еще текст второй книги.",
        "Глава пятая,",
        "Еще текст второй книги.",
        "Глава шестая,",
        "Еще текст второй книги.",
        "Глава седьмая,",
        "Еще текст второй книги.",
        "Глава восьмая,",
        "Еще текст второй книги.",
        "2. Спасательная экспедиция",
        f"Мы все умрём\n{long_body}",
        f"Посылка сообщения\n{long_body}",
        f"Помощь извне\n{long_body}",
    ])

    result = ChapterDetector().detect_and_split(book)

    assert [chapter.title for chapter in result.chapters[-3:]] == [
        "2. Спасательная экспедиция - Мы все умрём",
        "2. Спасательная экспедиция - Посылка сообщения",
        "2. Спасательная экспедиция - Помощь извне",
    ]


def test_internal_section_titles_ignore_dialogue_and_trailing_toc() -> None:
    """Fallback section headings must not turn dialogue or contents into chapters."""
    long_body = " ".join(["Текст большого раздела."] * 700)
    paragraphs = [
        Paragraph(raw_text=text, index_in_chapter=index)
        for index, text in enumerate(
            [
                f"Включения\n{long_body}",
                f"Восход Солнца\n{long_body}",
                "— Смотрите, капитан. Это «Замок Ледяных Кукол». Я когда-то был там.",
                "Кульминация\nФинальный текст.",
                "Содержание",
                "Вход в спираль",
                "Наследники Сета",
            ]
        )
    ]

    hits = ChapterDetector._infer_internal_section_headings(paragraphs)

    assert [hit.heading_text for hit in hits] == ["Включения", "Восход Солнца", "Кульминация"]


def test_dialogue_like_heading_hit_is_ignored_inside_work() -> None:
    """A false heading inside direct speech must not become a chapter title."""
    book = _book([
        "Book One",
        "Глава 1",
        "Prelude text.",
        "Book Two",
        "Загадочные обстоятельства",
        "Основной текст.",
        "— Смотрите, капитан. Это «Замок Ледяных Кукол». Я когда(\nто был там.",
        "Кульминация",
        "Финал.",
    ])
    result = ChapterDetector().detect_and_split(book)

    assert all("Замок Ледяных Кукол" not in chapter.title for chapter in result.chapters)


def test_heading_line_prefers_title_start_over_earlier_mention() -> None:
    """When a heading title is mentioned in dialogue, split at the real heading line."""
    paragraphs = [
        Paragraph(
            raw_text=(
                "— Смотрите, капитан. Это «Замок Ледяных Кукол».\n"
                "Замок Ледяных Кукол\n"
                "Описание замка."
            ),
            index_in_chapter=0,
        )
    ]
    chapters = ChapterDetector()._split_at_headings(
        paragraphs,
        [_HeadingHit(0, "Замок Ледяных Кукол", "internal_section_title")],
    )

    assert chapters[0].title == "Замок Ледяных Кукол"
    assert chapters[0].paragraphs[0].raw_text.startswith("Замок Ледяных Кукол")


def test_multibook_can_be_inferred_from_restarted_first_chapters() -> None:
    book = _book([
        "1. вход в спираль",
        "Веревка есть вервие простое. Из учебного наставления для палачей",
        "Глава первая,",
        "Текст первой книги.",
        "Глава вторая,",
        "Продолжение первой книги.",
        "2. наследники сета",
        "Вы неправильную порчу наводите! Из древней рекламации",
        "Глава первая,",
        "Текст второй книги.",
    ])

    result = ChapterDetector().detect_and_split(book)

    assert [chapter.work_title for chapter in result.chapters] == [
        "1. вход в спираль",
        "1. вход в спираль",
        "2. наследники сета",
    ]
    assert result.metadata.extra["structure"]["work_count"] == 2


def test_multibook_infers_short_numbered_work_title_before_reset() -> None:
    book = _book([
        "3. темный обелиск",
        "Глава первая,",
        "Текст третьей книги.",
        "Глава вторая,",
        "Продолжение третьей книги.",
        "4. троя",
        "Глава первая,",
        "Текст четвертой книги.",
    ])

    result = ChapterDetector().detect_and_split(book)

    assert result.metadata.extra["structure"]["work_titles"] == [
        "3. темный обелиск",
        "4. троя",
    ]
    assert result.chapters[-1].work_title == "4. троя"
    assert result.chapters[-1].title == "4. троя - Глава первая,"


def test_multibook_promotes_late_numbered_sections_after_known_works() -> None:
    book = _book([
        "1. вход в спираль",
        "Глава первая,",
        "Текст первой книги.",
        "Глава вторая,",
        "Продолжение первой книги.",
        "2. наследники сета",
        "Глава первая,",
        "Текст второй книги.",
        "Глава вторая,",
        "Продолжение второй книги.",
        "Глава третья,",
        "Еще текст второй книги.",
        "Глава четвертая,",
        "Еще текст второй книги.",
        "Глава пятая,",
        "Еще текст второй книги.",
        "Глава шестая,",
        "Еще текст второй книги.",
        "Глава седьмая,",
        "Еще текст второй книги.",
        "Глава восьмая,",
        "Еще текст второй книги.",
        "2. Спасательная экспедиция",
        "Самостоятельная поздняя повесть.",
        "7. В поисках силы",
        "Еще одна поздняя повесть.",
    ])

    result = ChapterDetector().detect_and_split(book)

    assert result.metadata.extra["structure"]["work_titles"] == [
        "1. вход в спираль",
        "2. наследники сета",
        "2. Спасательная экспедиция",
        "7. В поисках силы",
    ]
    assert result.chapters[-2].work_title == "2. Спасательная экспедиция"
    assert result.chapters[-1].work_title == "7. В поисках силы"


def test_toc_work_titles_promote_standalone_title_pages() -> None:
    toc = "\u0421\u043e\u0434\u0435\u0440\u0436\u0430\u043d\u0438\u0435"
    book_label = "\u041a\u043d\u0438\u0433\u0430"
    title_1 = "\u0412\u0445\u043e\u0434 \u0432 \u0441\u043f\u0438\u0440\u0430\u043b\u044c"
    title_2 = "\u041d\u0430\u0441\u043b\u0435\u0434\u043d\u0438\u043a\u0438 \u0421\u0435\u0442\u0430"
    title_3 = (
        "\u0417\u0430\u0442\u0435\u0440\u044f\u043d\u043d\u044b\u0435 "
        "\u0432 \u043a\u043e\u0441\u043c\u043e\u0441\u0435"
    )
    title_3_ocr = "\u0417\u0410\u0422\u0415\u0420\u042f\u041d\u041d\u042b\u0415"
    chapter_1 = "\u0413\u043b\u0430\u0432\u0430 \u043f\u0435\u0440\u0432\u0430\u044f,"
    chapter_2 = "\u0413\u043b\u0430\u0432\u0430 \u0432\u0442\u043e\u0440\u0430\u044f,"
    section_1 = (
        "\u0413\u0435\u043d\u0435\u0442\u0438\u0447\u0435\u0441\u043a\u0430\u044f "
        "\u043f\u0430\u043c\u044f\u0442\u044c"
    )
    section_2 = (
        "\u0412\u043e\u0437\u0432\u0440\u0430\u0449\u0430\u043b\u043a\u0430 "
        "\u0440\u0430\u0437\u0443\u043c\u0430"
    )
    book = _book([
        toc,
        f"{book_label} 1",
        title_1,
        "1",
        f"{book_label} 2",
        title_2,
        "120",
        f"{book_label} 3",
        title_3,
        "240",
        title_1,
        chapter_1,
        "\u0422\u0435\u043a\u0441\u0442 "
        "\u043f\u0435\u0440\u0432\u043e\u0439 \u043a\u043d\u0438\u0433\u0438.",
        chapter_2,
        "\u041f\u0440\u043e\u0434\u043e\u043b\u0436\u0435\u043d\u0438\u0435 "
        "\u043f\u0435\u0440\u0432\u043e\u0439 \u043a\u043d\u0438\u0433\u0438.",
        title_2,
        chapter_1,
        "\u0422\u0435\u043a\u0441\u0442 "
        "\u0432\u0442\u043e\u0440\u043e\u0439 \u043a\u043d\u0438\u0433\u0438.",
        chapter_2,
        "\u041f\u0440\u043e\u0434\u043e\u043b\u0436\u0435\u043d\u0438\u0435 "
        "\u0432\u0442\u043e\u0440\u043e\u0439 \u043a\u043d\u0438\u0433\u0438.",
        title_3_ocr,
        section_1,
        (
            "\u0411\u043e\u043b\u044c\u0448\u043e\u0439 "
            "\u0441\u0430\u043c\u043e\u0441\u0442\u043e\u044f\u0442\u0435\u043b\u044c\u043d\u044b\u0439 "
            "\u0440\u0430\u0437\u0434\u0435\u043b "
            "\u0442\u0440\u0435\u0442\u044c\u0435\u0439 "
            "\u043a\u043d\u0438\u0433\u0438. "
        ) * 900,
        section_2,
        (
            "\u0415\u0449\u0435 \u043e\u0434\u0438\u043d "
            "\u0441\u0430\u043c\u043e\u0441\u0442\u043e\u044f\u0442\u0435\u043b\u044c\u043d\u044b\u0439 "
            "\u0440\u0430\u0437\u0434\u0435\u043b "
            "\u0442\u0440\u0435\u0442\u044c\u0435\u0439 "
            "\u043a\u043d\u0438\u0433\u0438. "
        ) * 900,
    ])

    result = ChapterDetector().detect_and_split(book)

    assert result.metadata.extra["structure"]["work_titles"] == [
        f"1. {title_1}",
        f"2. {title_2}",
        f"3. {title_3}",
    ]
    assert result.chapters[-2].work_title == f"3. {title_3}"
    assert result.chapters[-2].title == f"3. {title_3} - {section_1}"
    assert result.chapters[-1].title == f"3. {title_3} - {section_2}"


def test_compact_trailing_toc_extracts_implicit_work_numbers() -> None:
    lines = [
        "\u0421\u043e\u0434\u0435\u0440\u0436\u0430\u043d\u0438\u0435",
        "\u041a\u043d\u0438\u0433\u0430 1 "
        "\u0412\u0445\u043e\u0434 \u0432 \u0441\u043f\u0438\u0440\u0430\u043b\u044c",
        "\u041d\u0430\u0441\u043b\u0435\u0434\u043d\u0438\u043a\u0438 \u0421\u0435\u0442\u0430",
        "\u0422\u0435\u043c\u043d\u044b\u0439 \u043e\u0431\u0435\u043b\u0438\u0441\u043a",
        "\u041a\u043d\u0438\u0433\u0430 4 \u0422\u0440\u043e\u044f",
        "\u041a\u043d\u0438\u0433\u0430 5 "
        "\u041c\u0430\u043b\u044c\u0442\u0438\u0439\u0441\u043a\u0438\u0439 "
        "\u044f\u0441\u0442\u0440\u0435\u0431",
        "\u0417\u0430\u0442\u0435\u0440\u044f\u043d\u043d\u044b\u0435 "
        "\u0432 \u043a\u043e\u0441\u043c\u043e\u0441\u0435",
        "\u0412 \u043f\u043e\u0438\u0441\u043a\u0430\u0445 \u0441\u0438\u043b\u044b",
    ]

    titles = ChapterDetector._extract_compact_toc_work_titles(lines)

    assert titles == {
        1: "\u0031\u002e \u0412\u0445\u043e\u0434 \u0432 \u0441\u043f\u0438\u0440\u0430\u043b\u044c",
        2: "\u0032\u002e \u041d\u0430\u0441\u043b\u0435\u0434\u043d\u0438\u043a\u0438 \u0421\u0435\u0442\u0430",
        3: "\u0033\u002e \u0422\u0435\u043c\u043d\u044b\u0439 \u043e\u0431\u0435\u043b\u0438\u0441\u043a",
        4: "\u0034\u002e \u0422\u0440\u043e\u044f",
        5: (
            "\u0035\u002e "
            "\u041c\u0430\u043b\u044c\u0442\u0438\u0439\u0441\u043a\u0438\u0439 "
            "\u044f\u0441\u0442\u0440\u0435\u0431"
        ),
        6: (
            "\u0036\u002e "
            "\u0417\u0430\u0442\u0435\u0440\u044f\u043d\u043d\u044b\u0435 "
            "\u0432 \u043a\u043e\u0441\u043c\u043e\u0441\u0435"
        ),
        7: "\u0037\u002e \u0412 \u043f\u043e\u0438\u0441\u043a\u0430\u0445 \u0441\u0438\u043b\u044b",
    }


def test_supported_language_heading_patterns() -> None:
    assert match_chapter_heading("Chapter One") is not None
    assert match_chapter_heading("Chapter IV") is not None
    assert match_chapter_heading("第一章") is not None
    assert match_chapter_heading("Bob 1") is not None
    assert match_chapter_heading("Тарау 1") is not None
    assert match_work_heading("Book Two") is not None
    assert match_work_heading("第二部") is not None
    assert match_work_heading("книга лежала на столе рейхсфюрера") is None
