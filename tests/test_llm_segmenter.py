from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from book_normalizer.chunking.llm_segmenter import LlmSegmentationError, LlmVoiceSegmenter
from book_normalizer.llm.model_router import FALLBACK_QWEN3_MODEL, PRIMARY_QWEN3_MODEL
from book_normalizer.llm.ollama_client import OllamaChatAttempt
from book_normalizer.models.book import Book, Chapter, Metadata, Paragraph

_MOJIBAKE_FRAGMENTS = ("Рў", "Рџ", "Рњ", "вЂ", "дЅ", "Т›", "У©")


def _joined_segment_text(rows: list[dict[str, Any]]) -> str:
    from book_normalizer.chunking.llm_segmenter import _canonical_for_preservation

    return _canonical_for_preservation(" ".join(row["text"] for row in rows))


def _source_text(text: str) -> str:
    from book_normalizer.chunking.llm_segmenter import _canonical_for_preservation

    return _canonical_for_preservation(text.replace("\n\n", " "))


class _FakeClient:
    def __init__(self, responses: dict[str, Any]) -> None:
        self.responses = responses
        self.calls: list[str] = []
        self.messages: list[list[dict[str, str]]] = []
        self.unloaded: list[str] = []
        self.unloaded_batches: list[tuple[str, ...]] = []

    def chat_json_with_fallback(self, *, models: list[str], **kwargs: Any) -> OllamaChatAttempt:
        model = models[0]
        self.calls.append(model)
        self.messages.append(kwargs["messages"])
        response = self.responses[model]
        if isinstance(response, list):
            response = response.pop(0)
        if isinstance(response, Exception):
            raise response
        return OllamaChatAttempt(model=model, content=json.dumps(response), data=response)

    def unload_model(self, model: str) -> None:
        self.unloaded.append(model)

    def unload_models(self, models: tuple[str, ...]) -> None:
        self.unloaded_batches.append(tuple(models))


def _book(text: str, language: str = "ru") -> Book:
    return Book(
        metadata=Metadata(language=language),
        chapters=[
            Chapter(
                title="Ch",
                index=0,
                paragraphs=[Paragraph(raw_text=text, normalized_text=text, index_in_chapter=0)],
            ),
        ],
    )


def test_llm_voice_segmenter_prompts_are_readable_and_retry_is_strict() -> None:
    from book_normalizer.chunking.llm_segmenter import (
        _system_prompt_for_language,
        _user_prompt_for_window,
    )

    prompts = {
        language: _system_prompt_for_language(language)
        for language in ("ru", "en", "zh", "kk", "uz")
    }

    assert "режиссёр" in prompts["ru"]
    assert "中文" in prompts["zh"]
    assert "қазақ" in prompts["kk"].lower()
    for prompt in prompts.values():
        assert not any(fragment in prompt for fragment in _MOJIBAKE_FRAGMENTS)

    retry_prompt = _user_prompt_for_window(
        language="ru",
        chapter_index=0,
        window_index=0,
        window_text="— Привет.",
        previous_issues=["text_preservation_failed"],
    )
    assert "PREVIOUS_OUTPUT_FAILED_VALIDATION" in retry_prompt
    assert "preserve input.text exactly" in retry_prompt


@pytest.mark.parametrize(
    ("language", "text"),
    [
        ("ru", "Он вошел. — Привет."),
        ("en", "He entered. \"Hello.\""),
        ("zh", "他进来了。“你好。”"),
        ("kk", "Ол кірді. — Сәлем."),
        ("uz", "U kirdi. \"Salom.\""),
    ],
)
def test_llm_voice_segmenter_outputs_manifest_for_all_languages(language: str, text: str) -> None:
    segmenter = LlmVoiceSegmenter(language=language)
    fake = _FakeClient({
        PRIMARY_QWEN3_MODEL: {
            "segments": [
                {"role": "narrator", "text": text, "intonation": "calm"},
            ],
        },
    })
    segmenter._client = fake

    rows = segmenter.segment_book(_book(text, language=language))

    assert rows[0]["language"] == language
    assert rows[0]["role"] == "narrator"
    assert rows[0]["voice_id"] == "narrator_calm"
    assert _joined_segment_text(rows) == _source_text(text)
    assert rows[-1]["boundary_after"] == "chapter"
    assert rows[-1]["pause_after_ms"] == 1500
    assert fake.calls == [PRIMARY_QWEN3_MODEL]
    assert fake.unloaded_batches == [(PRIMARY_QWEN3_MODEL, FALLBACK_QWEN3_MODEL)]


def test_llm_voice_segmenter_reports_progress_before_first_model_call() -> None:
    text = "First paragraph."
    events: list[tuple[int, int, str]] = []

    class _ProgressAwareClient(_FakeClient):
        def chat_json_with_fallback(self, **kwargs: Any) -> OllamaChatAttempt:
            assert events == [(0, 1, "1:1/1")]
            return super().chat_json_with_fallback(**kwargs)

    segmenter = LlmVoiceSegmenter(language="en")
    segmenter._client = _ProgressAwareClient({
        PRIMARY_QWEN3_MODEL: {
            "segments": [
                {"role": "narrator", "text": text, "intonation": "calm"},
            ],
        },
    })

    segmenter.segment_book(
        _book(text, language="en"),
        progress_callback=lambda done, total, label: events.append((done, total, label)),
    )

    assert events == [(0, 1, "1:1/1"), (1, 1, "1:1/1")]


def test_llm_voice_segmenter_sends_quoted_source_as_json_input() -> None:
    text = 'Sergey eshikni ochdi. "U yerda kim bor?" deb so\'radi u.'
    segmenter = LlmVoiceSegmenter(language="uz")
    fake = _FakeClient({
        PRIMARY_QWEN3_MODEL: {
            "segments": [
                {"role": "narrator", "text": text, "intonation": "calm"},
            ],
        },
    })
    segmenter._client = fake

    segmenter.segment_book(_book(text, language="uz"))

    user_content = fake.messages[0][1]["content"]
    payload = json.loads(user_content.split("INPUT_JSON:\n", 1)[1])
    assert payload["language"] == "Uzbek"
    assert payload["text"] == text


def test_llm_voice_segmenter_falls_back_when_primary_loses_text() -> None:
    text = "Alpha beta gamma."
    segmenter = LlmVoiceSegmenter(language="en")
    fake = _FakeClient({
        PRIMARY_QWEN3_MODEL: {
            "segments": [{"role": "narrator", "text": "Alpha beta.", "intonation": "calm"}],
        },
        FALLBACK_QWEN3_MODEL: {
            "segments": [{"role": "narrator", "text": text, "intonation": "calm"}],
        },
    })
    segmenter._client = fake

    rows = segmenter.segment_book(_book(text, language="en"))

    assert " ".join(row["text"] for row in rows) == text
    assert fake.calls == [PRIMARY_QWEN3_MODEL, PRIMARY_QWEN3_MODEL, FALLBACK_QWEN3_MODEL]
    assert PRIMARY_QWEN3_MODEL in fake.unloaded


def test_llm_voice_segmenter_retries_primary_before_fallback_on_text_loss() -> None:
    text = "Alpha beta gamma."
    segmenter = LlmVoiceSegmenter(language="en")
    fake = _FakeClient({
        PRIMARY_QWEN3_MODEL: [
            {"segments": [{"role": "narrator", "text": "Alpha beta.", "intonation": "calm"}]},
            {"segments": [{"role": "narrator", "text": text, "intonation": "calm"}]},
        ],
        FALLBACK_QWEN3_MODEL: {
            "segments": [{"role": "narrator", "text": text, "intonation": "calm"}],
        },
    })
    segmenter._client = fake

    rows = segmenter.segment_book(_book(text, language="en"))

    assert " ".join(row["text"] for row in rows) == text
    assert fake.calls == [PRIMARY_QWEN3_MODEL, PRIMARY_QWEN3_MODEL]
    assert "PREVIOUS_OUTPUT_FAILED_VALIDATION" in fake.messages[1][1]["content"]


def test_llm_voice_segmenter_restores_source_quotes_from_model_boundaries() -> None:
    text = "谢尔盖打开了门。\n\n“谁在那里？”他问。"
    segmenter = LlmVoiceSegmenter(language="zh")
    fake = _FakeClient({
        PRIMARY_QWEN3_MODEL: {
            "segments": [
                {"role": "narrator", "text": "谢尔盖打开了门。", "intonation": "calm"},
                {"role": "male", "text": "谁在那里？", "intonation": "tense"},
                {"role": "narrator", "text": "他问。", "intonation": "calm"},
            ],
        },
    })
    segmenter._client = fake

    rows = segmenter.segment_book(_book(text, language="zh"))

    assert [row["text"] for row in rows] == ["谢尔盖打开了门。", "“谁在那里？”", "他问。"]
    assert fake.calls == [PRIMARY_QWEN3_MODEL]


def test_llm_voice_segmenter_restores_source_dialogue_dash_from_model_boundaries() -> None:
    text = "Он вошел.\n\n— Привет."
    segmenter = LlmVoiceSegmenter(language="ru")
    fake = _FakeClient({
        PRIMARY_QWEN3_MODEL: {
            "segments": [
                {"role": "narrator", "text": "Он вошел.", "intonation": "calm"},
                {"role": "male", "text": "Привет.", "intonation": "cheerful"},
            ],
        },
    })
    segmenter._client = fake

    rows = segmenter.segment_book(_book(text, language="ru"))

    assert [row["text"] for row in rows] == ["Он вошел.", "— Привет."]
    assert fake.calls == [PRIMARY_QWEN3_MODEL]


def test_llm_voice_segmenter_moves_orphan_quote_and_splits_author_tag() -> None:
    text = (
        "И тут, когда дева моей мечты была уже почти готова, вновь появился злой бог Сет. "
        "«Что-то сдохло?» - спросил потянув носом воздух. "
        "Но увидев сию деву, бог явственно вздрогнул."
    )
    segmenter = LlmVoiceSegmenter(language="ru")
    fake = _FakeClient({
        PRIMARY_QWEN3_MODEL: {
            "segments": [
                {
                    "role": "narrator",
                    "text": "И тут, когда дева моей мечты была уже почти готова, вновь появился злой бог Сет. «",
                    "intonation": "calm",
                },
                {
                    "role": "male",
                    "section_kind": "dialogue",
                    "text": "Что-то сдохло?» - спросил потянув носом воздух.",
                    "intonation": "tense",
                },
                {
                    "role": "male",
                    "section_kind": "dialogue",
                    "text": "Но увидев сию деву, бог явственно вздрогнул.",
                    "intonation": "tense",
                },
            ],
        },
    })
    segmenter._client = fake

    rows = segmenter.segment_book(_book(text, language="ru"))

    assert [row["text"] for row in rows] == [
        "И тут, когда дева моей мечты была уже почти готова, вновь появился злой бог Сет.",
        "«Что-то сдохло?»",
        "- спросил потянув носом воздух.",
        "Но увидев сию деву, бог явственно вздрогнул.",
    ]
    assert [row["role"] for row in rows] == ["narrator", "male", "narrator", "narrator"]
    assert rows[1]["speaker"] == ""
    assert [row["voice_id"] for row in rows] == [
        "narrator_calm",
        "male_young",
        "narrator_calm",
        "narrator_calm",
    ]
    assert [row["section_kind"] for row in rows] == [
        "narration",
        "dialogue",
        "narration",
        "narration",
    ]


def test_llm_voice_segmenter_splits_dash_dialogue_from_author_tags() -> None:
    text = "- Что это? - спросил он, наконец, дрогнувшим голосом. - Моя невеста, - гордо ответил я."
    segmenter = LlmVoiceSegmenter(language="ru")
    fake = _FakeClient({
        PRIMARY_QWEN3_MODEL: {
            "segments": [
                {
                    "role": "male",
                    "section_kind": "dialogue",
                    "text": "- Что это? - спросил он, наконец, дрогнувшим голосом. -",
                    "intonation": "tense",
                },
                {
                    "role": "male",
                    "section_kind": "dialogue",
                    "text": "Моя невеста, - гордо ответил я.",
                    "intonation": "calm",
                },
            ],
        },
    })
    segmenter._client = fake

    rows = segmenter.segment_book(_book(text, language="ru"))

    assert [row["text"] for row in rows] == [
        "- Что это?",
        "- спросил он, наконец, дрогнувшим голосом.",
        "- Моя невеста,",
        "- гордо ответил я.",
    ]
    assert [row["role"] for row in rows] == ["male", "narrator", "male", "narrator"]
    assert [row["section_kind"] for row in rows] == [
        "dialogue",
        "narration",
        "dialogue",
        "narration",
    ]


def test_llm_voice_segmenter_repairs_dash_dialogue_inside_narrator_segment() -> None:
    text = (
        "- Что это? - спросил он, наконец, дрогнувшим голосом. - "
        "Моя невеста, - гордо ответил я тёмному божеству. Он глубоко вздохнул "
        "и схватил прекрасную деву, грациозно покачивающуюся в воздухе, за ногу."
    )
    segmenter = LlmVoiceSegmenter(language="ru")
    fake = _FakeClient({
        PRIMARY_QWEN3_MODEL: {
            "segments": [
                {
                    "role": "narrator",
                    "section_kind": "narration",
                    "text": text,
                    "intonation": "calm",
                },
            ],
        },
    })
    segmenter._client = fake

    rows = segmenter.segment_book(_book(text, language="ru"))

    assert [row["text"] for row in rows] == [
        "- Что это?",
        "- спросил он, наконец, дрогнувшим голосом.",
        "- Моя невеста,",
        (
            "- гордо ответил я тёмному божеству. Он глубоко вздохнул и схватил "
            "прекрасную деву, грациозно покачивающуюся в воздухе, за ногу."
        ),
    ]
    assert [row["role"] for row in rows] == ["male", "narrator", "male", "narrator"]
    assert [row["section_kind"] for row in rows] == [
        "dialogue",
        "narration",
        "dialogue",
        "narration",
    ]


def test_repaired_narrator_tags_stay_narrator_when_chunk_builder_repairs_again() -> None:
    from book_normalizer.chunking.llm_segmenter import repair_segment_dialogue_boundaries
    from book_normalizer.chunking.voice_splitter import build_chunks_from_segments

    text = (
        "- Что это? - спросил он, наконец, дрогнувшим голосом. - "
        "Моя невеста, - гордо ответил я тёмному божеству."
    )
    rows = [
        {
            "chapter_index": 0,
            "segment_index": 0,
            "language": "ru",
            "role": "narrator",
            "voice_id": "narrator_calm",
            "section_kind": "narration",
            "text": text,
            "intonation": "calm",
        }
    ]

    repaired = repair_segment_dialogue_boundaries(rows, language="ru")
    chunks = build_chunks_from_segments(repaired, max_chunk_chars=400)

    assert [chunk["text"] for chunk in chunks] == [
        "- Что это?",
        "- спросил он, наконец, дрогнувшим голосом.",
        "- Моя невеста,",
        "- гордо ответил я тёмному божеству.",
    ]
    assert [chunk["role"] for chunk in chunks] == [
        "male",
        "narrator",
        "male",
        "narrator",
    ]


def test_short_quoted_terms_are_not_repaired_as_dialogue() -> None:
    from book_normalizer.chunking.llm_segmenter import repair_segment_dialogue_boundaries
    from book_normalizer.chunking.voice_splitter import build_chunks_from_segments

    text = "Они называли этот сбой «Глюк» и потом долго спорили о «Скарабее»."
    rows = [
        {
            "chapter_index": 0,
            "segment_index": 0,
            "language": "ru",
            "role": "narrator",
            "voice_id": "narrator_calm",
            "section_kind": "narration",
            "text": text,
            "intonation": "calm",
        }
    ]

    chunks = build_chunks_from_segments(
        repair_segment_dialogue_boundaries(rows, language="ru"),
        max_chunk_chars=400,
    )

    assert [chunk["text"] for chunk in chunks] == [text]
    assert [chunk["role"] for chunk in chunks] == ["narrator"]


def test_quoted_term_with_explanatory_dash_stays_narrator() -> None:
    from book_normalizer.chunking.llm_segmenter import repair_segment_dialogue_boundaries
    from book_normalizer.chunking.voice_splitter import build_chunks_from_segments

    text = "Несколько раз произносилось название «Вольфшанце» — волчье логово."
    rows = [
        {
            "chapter_index": 0,
            "segment_index": 0,
            "language": "ru",
            "role": "narrator",
            "voice_id": "narrator_calm",
            "section_kind": "narration",
            "text": text,
            "intonation": "calm",
        }
    ]

    chunks = build_chunks_from_segments(
        repair_segment_dialogue_boundaries(rows, language="ru"),
        max_chunk_chars=400,
    )

    assert [chunk["text"] for chunk in chunks] == [text]
    assert [chunk["role"] for chunk in chunks] == ["narrator"]


def test_dash_dialogue_splits_before_attribution_without_space_after_punctuation() -> None:
    from book_normalizer.chunking.llm_segmenter import repair_segment_dialogue_boundaries

    text = "- Тварь!- закричал наставник отскочив от моего питомца."
    rows = [
        {
            "chapter_index": 0,
            "segment_index": 0,
            "language": "ru",
            "role": "narrator",
            "voice_id": "narrator_calm",
            "section_kind": "narration",
            "text": text,
            "intonation": "calm",
        }
    ]

    repaired = repair_segment_dialogue_boundaries(rows, language="ru")

    assert [row["text"] for row in repaired] == [
        "- Тварь!",
        "- закричал наставник отскочив от моего питомца.",
    ]
    assert [row["role"] for row in repaired] == ["male", "narrator"]


def test_narrator_tag_can_contain_next_dash_dialogue() -> None:
    from book_normalizer.chunking.llm_segmenter import repair_segment_dialogue_boundaries

    text = "- Я пришёл, - признался - Ой, как все запущено, - сказал мужчина."
    rows = [
        {
            "chapter_index": 0,
            "segment_index": 0,
            "language": "ru",
            "role": "narrator",
            "voice_id": "narrator_calm",
            "section_kind": "narration",
            "text": text,
            "intonation": "calm",
        }
    ]

    repaired = repair_segment_dialogue_boundaries(rows, language="ru")

    assert [row["text"] for row in repaired] == [
        "- Я пришёл,",
        "- признался",
        "- Ой, как все запущено,",
        "- сказал мужчина.",
    ]
    assert [row["role"] for row in repaired] == ["male", "narrator", "male", "narrator"]


def test_dash_dialogue_splits_before_following_dash_dialogue() -> None:
    from book_normalizer.chunking.llm_segmenter import repair_segment_dialogue_boundaries

    text = "- Вы согласны? - А что у нас с планом? - переспросил мужчина."
    rows = [
        {
            "chapter_index": 0,
            "segment_index": 0,
            "language": "ru",
            "role": "narrator",
            "voice_id": "narrator_calm",
            "section_kind": "narration",
            "text": text,
            "intonation": "calm",
        }
    ]

    repaired = repair_segment_dialogue_boundaries(rows, language="ru")

    assert [row["text"] for row in repaired] == [
        "- Вы согласны?",
        "- А что у нас с планом?",
        "- переспросил мужчина.",
    ]
    assert [row["role"] for row in repaired] == ["unknown", "male", "narrator"]


def test_plain_narration_splits_before_colon_introduced_dash_dialogue() -> None:
    from book_normalizer.chunking.llm_segmenter import repair_segment_dialogue_boundaries

    text = "Женщина спросила, и мужчина сразу ответил: - Конечно, вижу."
    rows = [
        {
            "chapter_index": 0,
            "segment_index": 0,
            "language": "ru",
            "role": "narrator",
            "voice_id": "narrator_calm",
            "section_kind": "narration",
            "text": text,
            "intonation": "calm",
        }
    ]

    repaired = repair_segment_dialogue_boundaries(rows, language="ru")

    assert [row["text"] for row in repaired] == [
        "Женщина спросила, и мужчина сразу ответил:",
        "- Конечно, вижу.",
    ]
    assert [row["role"] for row in repaired] == ["narrator", "male"]


def test_lowercase_ocr_dash_question_stays_dialogue_before_narration_intro() -> None:
    from book_normalizer.chunking.llm_segmenter import repair_segment_dialogue_boundaries

    text = "- вы подскажете куда нам идти? Мужчина открыл глаза: - Идите прямо."
    rows = [
        {
            "chapter_index": 0,
            "segment_index": 0,
            "language": "ru",
            "role": "narrator",
            "voice_id": "narrator_calm",
            "section_kind": "narration",
            "text": text,
            "intonation": "calm",
        }
    ]

    repaired = repair_segment_dialogue_boundaries(rows, language="ru")

    assert [row["text"] for row in repaired] == [
        "- вы подскажете куда нам идти?",
        "Мужчина открыл глаза:",
        "- Идите прямо.",
    ]
    assert [row["section_kind"] for row in repaired] == ["dialogue", "narration", "dialogue"]


def test_dash_speech_with_closing_quote_splits_before_following_narration() -> None:
    from book_normalizer.chunking.llm_segmenter import repair_segment_dialogue_boundaries

    text = "— Что я скажу?». Он стал вспоминать инструкцию."
    rows = [
        {
            "chapter_index": 0,
            "segment_index": 0,
            "language": "ru",
            "role": "narrator",
            "voice_id": "narrator_calm",
            "section_kind": "narration",
            "text": text,
            "intonation": "calm",
        }
    ]

    repaired = repair_segment_dialogue_boundaries(rows, language="ru")

    assert [row["text"] for row in repaired] == [
        "— Что я скажу?».",
        "Он стал вспоминать инструкцию.",
    ]
    assert [row["section_kind"] for row in repaired] == ["dialogue", "narration"]


def test_narrator_tag_splits_before_lowercase_resumed_dash_dialogue() -> None:
    from book_normalizer.chunking.llm_segmenter import repair_segment_dialogue_boundaries

    text = "- ответил мужчина, - я просто чародей."
    rows = [
        {
            "chapter_index": 0,
            "segment_index": 0,
            "language": "ru",
            "role": "narrator",
            "voice_id": "narrator_calm",
            "section_kind": "narration",
            "text": text,
            "intonation": "calm",
        }
    ]

    repaired = repair_segment_dialogue_boundaries(rows, language="ru")

    assert [row["text"] for row in repaired] == [
        "- ответил мужчина,",
        "- я просто чародей.",
    ]
    assert [row["role"] for row in repaired] == ["narrator", "male"]


def test_dash_started_narration_splits_later_direct_speech() -> None:
    from book_normalizer.chunking.llm_segmenter import repair_segment_dialogue_boundaries

    text = (
        "— вставная авторская часть закончилась. Герой посмотрел на дверь. "
        "— Ты меня обманул,, сказал он. — Я своё обещание выполнил?"
    )
    rows = [
        {
            "chapter_index": 0,
            "segment_index": 0,
            "language": "ru",
            "role": "narrator",
            "voice_id": "narrator_calm",
            "section_kind": "narration",
            "text": text,
            "intonation": "calm",
        }
    ]

    repaired = repair_segment_dialogue_boundaries(rows, language="ru")

    assert [row["text"] for row in repaired] == [
        "— вставная авторская часть закончилась. Герой посмотрел на дверь.",
        "— Ты меня обманул,,",
        "сказал он.",
        "— Я своё обещание выполнил?",
    ]
    assert [row["section_kind"] for row in repaired] == [
        "narration",
        "dialogue",
        "narration",
        "dialogue",
    ]


def test_dash_dialogue_splits_ocr_inline_attribution_without_second_dash() -> None:
    from book_normalizer.chunking.llm_segmenter import repair_segment_dialogue_boundaries

    text = "— Да,, сквозь зубы процедила цыганка."
    rows = [
        {
            "chapter_index": 0,
            "segment_index": 0,
            "language": "ru",
            "role": "narrator",
            "voice_id": "narrator_calm",
            "section_kind": "narration",
            "text": text,
            "intonation": "calm",
        }
    ]

    repaired = repair_segment_dialogue_boundaries(rows, language="ru")

    assert [row["text"] for row in repaired] == [
        "— Да,,",
        "сквозь зубы процедила цыганка.",
    ]
    assert [row["role"] for row in repaired] == ["female", "narrator"]


def test_quoted_thought_splits_from_thought_attribution() -> None:
    from book_normalizer.chunking.llm_segmenter import repair_segment_dialogue_boundaries

    text = "«Придётся идти»,, обречено подумал Сергей."
    rows = [
        {
            "chapter_index": 0,
            "segment_index": 0,
            "language": "ru",
            "role": "narrator",
            "voice_id": "narrator_calm",
            "section_kind": "narration",
            "text": text,
            "intonation": "calm",
        }
    ]

    repaired = repair_segment_dialogue_boundaries(rows, language="ru")

    assert [row["text"] for row in repaired] == [
        "«Придётся идти»,,",
        "обречено подумал Сергей.",
    ]
    assert [row["role"] for row in repaired] == ["male", "narrator"]


def test_short_quoted_terms_from_llm_dialogue_are_demoted_to_narrator() -> None:
    from book_normalizer.chunking.llm_segmenter import repair_segment_dialogue_boundaries

    rows = [
        {
            "chapter_index": 0,
            "segment_index": 0,
            "language": "ru",
            "role": "male",
            "voice_id": "male_young",
            "section_kind": "dialogue",
            "text": "«Глюк»",
            "intonation": "calm",
        }
    ]

    repaired = repair_segment_dialogue_boundaries(rows, language="ru")

    assert [row["text"] for row in repaired] == ["«Глюк»"]
    assert [row["role"] for row in repaired] == ["narrator"]
    assert [row["section_kind"] for row in repaired] == ["narration"]


def test_llm_voice_segmenter_repairs_quoted_and_unquoted_speech_inside_narrator_segment() -> None:
    text = (
        "«Нарушена техника безопасности при работе с монстрами», - сказал Сет и потащил мою женщину с собой в ад. "
        "Себя бы посмотрел, животное неизвестное, - прошептал ему вслед. "
        "Так вот я и остался сегодня без женщины, зато Годзилла сразу же вернулся (или вернулась?)."
    )
    segmenter = LlmVoiceSegmenter(language="ru")
    fake = _FakeClient({
        PRIMARY_QWEN3_MODEL: {
            "segments": [
                {
                    "role": "narrator",
                    "section_kind": "narration",
                    "text": text,
                    "intonation": "calm",
                },
            ],
        },
    })
    segmenter._client = fake

    rows = segmenter.segment_book(_book(text, language="ru"))

    assert [row["text"] for row in rows] == [
        "«Нарушена техника безопасности при работе с монстрами»,",
        "- сказал Сет и потащил мою женщину с собой в ад.",
        "Себя бы посмотрел, животное неизвестное,",
        (
            "- прошептал ему вслед. Так вот я и остался сегодня без женщины, "
            "зато Годзилла сразу же вернулся (или вернулась?)."
        ),
    ]
    assert [row["role"] for row in rows] == ["male", "narrator", "male", "narrator"]
    assert all(row["voice_id"] != "narrator_calm" for row in (rows[0], rows[2]))


def test_llm_voice_segmenter_keeps_character_metadata_for_roles() -> None:
    text = "Маргарита сказала: «Я вернулась»."
    segmenter = LlmVoiceSegmenter(language="ru")
    fake = _FakeClient({
        PRIMARY_QWEN3_MODEL: {
            "segments": [
                {"role": "narrator", "text": "Маргарита сказала:", "intonation": "calm"},
                {
                    "role": "female",
                    "speaker": "Маргарита",
                    "character_description": "Решительная и резкая.",
                    "emotion": "joyful",
                    "text": "«Я вернулась».",
                    "intonation": "joyful",
                },
            ],
        },
    })
    segmenter._client = fake

    rows = segmenter.segment_book(_book(text, language="ru"))

    assert rows[1]["speaker"] == "Маргарита"
    assert rows[1]["character_description"] == "Решительная и резкая."
    assert rows[1]["emotion"] == "joyful"
    assert rows[1]["section_kind"] == "dialogue"


def test_llm_voice_segmenter_repairs_narrator_dialogue_from_bad_llm_output() -> None:
    text = "\n\n".join([
        "— Да, — сквозь зубы процедила цыганка.",
        "— Ты зачем пришла? — спросил Сергей у совершенно каменной статуи.",
        "— Меня к тебе по делу прислали.",
        "— Кто прислал? — спросил Сергей.",
    ])
    segmenter = LlmVoiceSegmenter(language="ru")
    fake = _FakeClient({
        PRIMARY_QWEN3_MODEL: {
            "segments": [
                {"role": "narrator", "section_kind": "narration", "text": part, "intonation": "calm"}
                for part in text.split("\n\n")
            ],
        },
    })
    segmenter._client = fake

    rows = segmenter.segment_book(_book(text, language="ru"))

    assert _joined_segment_text(rows) == _source_text(text)
    dialogue_rows = [row for row in rows if row["is_dialogue"]]
    assert [row["text"] for row in dialogue_rows] == [
        "— Да,",
        "— Ты зачем пришла?",
        "— Меня к тебе по делу прислали.",
        "— Кто прислал?",
    ]
    assert [row["speaker"] for row in dialogue_rows] == ["Цыганка", "Сергей", "Цыганка", "Сергей"]
    assert [row["role"] for row in dialogue_rows] == ["female", "male", "female", "male"]
    assert all(row["section_kind"] == "dialogue" for row in dialogue_rows)
    assert all(row["section_kind"] == "narration" for row in rows if not row["is_dialogue"])


@pytest.mark.parametrize(
    ("language", "parts", "expected_speakers"),
    [
        (
            "en",
            ['"Come in," Alice said.', '"Now?" Bob asked.'],
            ["Alice", "Bob"],
        ),
        (
            "zh",
            ["“你好，”李雷说。", "“请坐，”王芳回答。"],
            ["李雷", "王芳"],
        ),
        (
            "kk",
            ["— Сәлем, — деді Айгүл.", "— Кел, — деді Ержан."],
            ["Айгүл", "Ержан"],
        ),
        (
            "uz",
            ["— Salom, — dedi Aziz.", "— Kut, — dedi Dilnoza."],
            ["Aziz", "Dilnoza"],
        ),
    ],
)
def test_llm_voice_segmenter_repairs_named_dialogue_for_all_product_languages(
    language: str,
    parts: list[str],
    expected_speakers: list[str],
) -> None:
    text = "\n\n".join(parts)
    segmenter = LlmVoiceSegmenter(language=language)
    fake = _FakeClient({
        PRIMARY_QWEN3_MODEL: {
            "segments": [
                {"role": "narrator", "section_kind": "narration", "text": part, "intonation": "calm"}
                for part in parts
            ],
        },
    })
    segmenter._client = fake

    rows = segmenter.segment_book(_book(text, language=language))

    assert _joined_segment_text(rows) == _source_text(text)
    dialogue_rows = [row for row in rows if row["is_dialogue"]]
    assert [row["speaker"] for row in dialogue_rows] == expected_speakers
    assert all(row["section_kind"] == "dialogue" for row in dialogue_rows)
    assert all(row["section_kind"] == "narration" for row in rows if not row["is_dialogue"])


@pytest.mark.parametrize(
    ("language", "text", "expected_role", "expected_voice"),
    [
        ("en", '"Go now," he said.', "male", "male_young"),
        ("en", '"Stay here," she whispered.', "female", "female_warm"),
        ("zh", "“走吧，”他说。", "male", "male_young"),
        ("zh", "“别怕，”她说。", "female", "female_warm"),
    ],
)
def test_llm_voice_segmenter_repairs_gendered_pronoun_dialogue(
    language: str,
    text: str,
    expected_role: str,
    expected_voice: str,
) -> None:
    segmenter = LlmVoiceSegmenter(language=language)
    fake = _FakeClient({
        PRIMARY_QWEN3_MODEL: {
            "segments": [
                {"role": "narrator", "section_kind": "narration", "text": text, "intonation": "calm"},
            ],
        },
    })
    segmenter._client = fake

    rows = segmenter.segment_book(_book(text, language=language))

    assert _joined_segment_text(rows) == _source_text(text)
    dialogue_rows = [row for row in rows if row["is_dialogue"]]
    assert len(dialogue_rows) == 1
    assert dialogue_rows[0]["role"] == expected_role
    assert dialogue_rows[0]["voice_id"] == expected_voice
    assert dialogue_rows[0]["section_kind"] == "dialogue"


def test_llm_voice_segmenter_marks_dialogue_when_gender_is_unknown() -> None:
    text = "谢尔盖打开了门。\n\n“谁在那里？”问道。"
    segmenter = LlmVoiceSegmenter(language="zh")
    fake = _FakeClient({
        PRIMARY_QWEN3_MODEL: {
            "segments": [
                {"role": "narrator", "text": "谢尔盖打开了门。", "intonation": "calm"},
                    {
                        "role": "narrator",
                        "section_kind": "dialogue",
                        "text": "“谁在那里？”问道。",
                        "intonation": "tense",
                    },
            ],
        },
    })
    segmenter._client = fake

    rows = segmenter.segment_book(_book(text, language="zh"))

    assert rows[0]["is_dialogue"] is False
    assert rows[1]["role"] == "unknown"
    assert rows[1]["voice_id"] == "narrator_calm"
    assert rows[1]["section_kind"] == "dialogue"


def test_repaired_dialogue_uses_speaker_name_gender_for_voice() -> None:
    from book_normalizer.chunking.llm_segmenter import repair_segment_dialogue_boundaries

    rows = [
        {
            "chapter_index": 0,
            "segment_index": 0,
            "language": "ru",
            "role": "unknown",
            "voice_id": "narrator_calm",
            "speaker": "Сергей",
            "section_kind": "dialogue",
            "text": "- Продолжаем.",
            "intonation": "calm",
        },
    ]

    repaired = repair_segment_dialogue_boundaries(rows, language="ru")

    assert repaired[0]["role"] == "male"
    assert repaired[0]["voice_id"].startswith("male_")


def test_ru_speaker_filter_rejects_lowercase_non_person_candidates() -> None:
    from book_normalizer.chunking.llm_segmenter import repair_segment_dialogue_boundaries

    rows = [
        {
            "chapter_index": 0,
            "segment_index": 0,
            "language": "ru",
            "role": "narrator",
            "voice_id": "narrator_calm",
            "section_kind": "narration",
            "text": "- Проверим,, готовиться.",
            "intonation": "calm",
        },
        {
            "chapter_index": 0,
            "segment_index": 1,
            "language": "ru",
            "role": "narrator",
            "voice_id": "narrator_calm",
            "section_kind": "narration",
            "text": "- Проверим,, ответил маркиз.",
            "intonation": "calm",
        },
    ]

    repaired = repair_segment_dialogue_boundaries(rows, language="ru")
    dialogue = [row for row in repaired if row["section_kind"] == "dialogue"]

    assert dialogue[0]["speaker"] == ""
    assert dialogue[1]["speaker"] == "Маркиз"


def test_ru_speaker_filter_rejects_capitalized_non_person_candidates() -> None:
    from book_normalizer.chunking.llm_segmenter import repair_segment_dialogue_boundaries

    rows = [
        {
            "chapter_index": 0,
            "segment_index": 0,
            "language": "ru",
            "role": "narrator",
            "voice_id": "narrator_calm",
            "section_kind": "narration",
            "text": "- Проверим,, спросил Кто.",
            "intonation": "calm",
        },
        {
            "chapter_index": 0,
            "segment_index": 1,
            "language": "ru",
            "role": "narrator",
            "voice_id": "narrator_calm",
            "section_kind": "narration",
            "text": "- Проверим,, ответил Боккардини.",
            "intonation": "calm",
        },
        {
            "chapter_index": 0,
            "segment_index": 2,
            "language": "ru",
            "role": "narrator",
            "voice_id": "narrator_calm",
            "section_kind": "narration",
            "text": "- Проверим,, спросил Медное.",
            "intonation": "calm",
        },
    ]

    repaired = repair_segment_dialogue_boundaries(rows, language="ru")
    dialogue = [row for row in repaired if row["section_kind"] == "dialogue"]

    assert dialogue[0]["speaker"] == ""
    assert dialogue[1]["speaker"] == "Боккардини"
    assert dialogue[2]["speaker"] == ""


def test_llm_provided_ru_speaker_is_filtered_with_same_person_rules() -> None:
    text = "- Проверим."
    segmenter = LlmVoiceSegmenter(language="ru")
    fake = _FakeClient({
        PRIMARY_QWEN3_MODEL: {
            "segments": [
                {
                    "role": "male",
                    "speaker": "Кто",
                    "section_kind": "dialogue",
                    "text": "- Проверим.",
                    "intonation": "calm",
                }
            ],
        },
    })
    segmenter._client = fake

    rows = segmenter.segment_book(_book(text, language="ru"))

    assert rows[0]["speaker"] == ""
    assert rows[0]["section_kind"] == "dialogue"


def test_llm_voice_segmenter_restores_source_punctuation_from_model_boundaries() -> None:
    text = "Посланца..И сделать было нельзя.\n\nСерг"
    segmenter = LlmVoiceSegmenter(language="ru")
    fake = _FakeClient({
        PRIMARY_QWEN3_MODEL: {
            "segments": [
                {
                    "role": "narrator",
                    "text": "Посланца. И сделать было нельзя. Серг",
                    "intonation": "calm",
                },
            ],
        },
    })
    segmenter._client = fake

    rows = segmenter.segment_book(_book(text, language="ru"))

    assert [row["text"] for row in rows] == ["Посланца..И сделать было нельзя. Серг"]
    assert fake.calls == [PRIMARY_QWEN3_MODEL]


def test_llm_voice_segmenter_restores_initial_ellipsis_and_trailing_dot_leader() -> None:
    text = "…И вижу всадника.\n\nОГЛАВЛЕНИЕ\n1. Предисловие ...................."
    segmenter = LlmVoiceSegmenter(language="ru")
    fake = _FakeClient({
        PRIMARY_QWEN3_MODEL: {
            "segments": [
                {"role": "narrator", "text": "И вижу всадника.", "intonation": "calm"},
                {"role": "narrator", "text": "ОГЛАВЛЕНИЕ 1. Предисловие", "intonation": "calm"},
            ],
        },
    })
    segmenter._client = fake

    rows = segmenter.segment_book(_book(text, language="ru"))

    assert [row["text"] for row in rows] == [
        "…И вижу всадника.",
        "ОГЛАВЛЕНИЕ\n1. Предисловие ....................",
    ]


def test_llm_voice_segmenter_writes_review_report_when_all_models_fail(tmp_path: Path) -> None:
    report_path = tmp_path / "review.json"
    segmenter = LlmVoiceSegmenter(language="en", review_report_path=report_path)
    fake = _FakeClient({
        PRIMARY_QWEN3_MODEL: {
            "segments": [{"role": "narrator", "text": "lost", "intonation": "calm"}],
        },
        FALLBACK_QWEN3_MODEL: {
            "segments": [{"role": "narrator", "text": "also lost", "intonation": "calm"}],
        },
    })
    segmenter._client = fake

    with pytest.raises(LlmSegmentationError):
        segmenter.segment_book(_book("Full source text.", language="en"))

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["requires_human_review"] is True
    assert report["models"] == [PRIMARY_QWEN3_MODEL, FALLBACK_QWEN3_MODEL]
    assert len(report["failures"]) == 4
    assert fake.calls == [
        PRIMARY_QWEN3_MODEL,
        PRIMARY_QWEN3_MODEL,
        FALLBACK_QWEN3_MODEL,
        FALLBACK_QWEN3_MODEL,
    ]


def test_llm_voice_segmenter_uses_source_fallback_when_enabled(tmp_path: Path) -> None:
    report_path = tmp_path / "review.json"
    text = "Full source text."
    segmenter = LlmVoiceSegmenter(
        language="en",
        review_report_path=report_path,
        allow_source_fallback=True,
    )
    fake = _FakeClient({
        PRIMARY_QWEN3_MODEL: {
            "segments": [{"role": "narrator", "text": "lost", "intonation": "calm"}],
        },
        FALLBACK_QWEN3_MODEL: {
            "segments": [{"role": "narrator", "text": "also lost", "intonation": "calm"}],
        },
    })
    segmenter._client = fake

    rows = segmenter.segment_book(_book(text, language="en"))

    assert [row["text"] for row in rows] == [text]
    assert rows[0]["role"] == "narrator"
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["requires_human_review"] is True
    assert report["failures"][-1]["model"] == "source-preserving-fallback"
    assert fake.calls == [
        PRIMARY_QWEN3_MODEL,
        PRIMARY_QWEN3_MODEL,
        FALLBACK_QWEN3_MODEL,
        FALLBACK_QWEN3_MODEL,
    ]
