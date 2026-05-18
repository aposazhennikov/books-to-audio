"""Tests for rendering stress annotations into TTS hints."""

from __future__ import annotations

from book_normalizer.dialogue.models import (
    AnnotatedChapter,
    AnnotatedParagraph,
    DialogueLine,
    SpeakerRole,
)
from book_normalizer.models.book import Book, Chapter, Paragraph, Segment
from book_normalizer.stress.rendering import (
    double_stressed_vowels,
    render_annotated_chapters_for_tts,
    render_book_for_tts,
    render_stressed_text,
)


def test_double_stressed_vowels_converts_acute_to_vowel_duplication() -> None:
    assert double_stressed_vowels("\u0437\u0430\u0301\u043c\u043e\u043a") == "\u0437\u0430\u0430\u043c\u043e\u043a"
    assert double_stressed_vowels("\u0437\u0430\u043c\u043e\u0301\u043a") == "\u0437\u0430\u043c\u043e\u043e\u043a"


def test_render_stressed_text_can_strip_or_keep_acute() -> None:
    text = "\u0437\u0430\u043c\u043e\u0301\u043a"

    assert render_stressed_text(text, "plain") == "\u0437\u0430\u043c\u043e\u043a"
    assert render_stressed_text(text, "keep_acute") == text


def test_render_book_for_tts_uses_segments_without_mutating_source_book() -> None:
    source = Book(
        chapters=[
            Chapter(
                title="Ch",
                index=0,
                paragraphs=[
                    Paragraph(
                        raw_text="\u0417\u0430\u043c\u043e\u043a.",
                        normalized_text="\u0417\u0430\u043c\u043e\u043a.",
                        segments=[
                            Segment(
                                text="\u0417\u0430\u043c\u043e\u043a",
                                stress_form="\u0437\u0430\u043c\u043e\u0301\u043a",
                            ),
                            Segment(text=".", stress_form=""),
                        ],
                    )
                ],
            )
        ]
    )

    rendered = render_book_for_tts(source, "double_vowel")

    assert source.chapters[0].paragraphs[0].normalized_text == "\u0417\u0430\u043c\u043e\u043a."
    assert rendered.chapters[0].paragraphs[0].normalized_text == "\u0417\u0430\u043c\u043e\u043e\u043a."


def test_render_annotated_chapters_applies_hints_after_detection() -> None:
    text = (
        "\u041e\u043d \u043e\u0442\u043a\u0440\u044b\u043b \u0437\u0430\u043c\u043e\u043a. "
        "\u041f\u043e\u0442\u043e\u043c \u0443\u0448\u0435\u043b."
    )
    paragraph = Paragraph(
        id="p0",
        raw_text=text,
        normalized_text=text,
        segments=[
            Segment(text="\u041e\u043d \u043e\u0442\u043a\u0440\u044b\u043b "),
            Segment(
                text="\u0437\u0430\u043c\u043e\u043a",
                stress_form="\u0437\u0430\u043c\u043e\u0301\u043a",
            ),
            Segment(text=". \u041f\u043e\u0442\u043e\u043c \u0443\u0448\u0435\u043b."),
        ],
    )
    book = Book(chapters=[Chapter(index=0, paragraphs=[paragraph])])
    annotated = [
        AnnotatedChapter(
            chapter_index=0,
            paragraphs=[
                AnnotatedParagraph(
                    paragraph_id="p0",
                    lines=[
                        DialogueLine(
                            text="\u041e\u043d \u043e\u0442\u043a\u0440\u044b\u043b \u0437\u0430\u043c\u043e\u043a.",
                            role=SpeakerRole.NARRATOR,
                        ),
                        DialogueLine(
                            text="\u041f\u043e\u0442\u043e\u043c \u0443\u0448\u0435\u043b.",
                            role=SpeakerRole.NARRATOR,
                        ),
                    ],
                ),
            ],
        ),
    ]

    render_annotated_chapters_for_tts(annotated, book, "double_vowel")

    assert annotated[0].paragraphs[0].lines[0].text.endswith("\u0437\u0430\u043c\u043e\u043e\u043a.")
    assert annotated[0].paragraphs[0].lines[1].text == "\u041f\u043e\u0442\u043e\u043c \u0443\u0448\u0435\u043b."
