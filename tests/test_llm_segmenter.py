from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from book_normalizer.chunking.llm_segmenter import LlmSegmentationError, LlmVoiceSegmenter
from book_normalizer.llm.model_router import FALLBACK_QWEN3_MODEL, PRIMARY_QWEN3_MODEL
from book_normalizer.llm.ollama_client import OllamaChatAttempt
from book_normalizer.models.book import Book, Chapter, Metadata, Paragraph


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
    assert rows[0]["text"] == text
    assert rows[-1]["boundary_after"] == "chapter"
    assert rows[-1]["pause_after_ms"] == 1500
    assert fake.calls == [PRIMARY_QWEN3_MODEL]
    assert fake.unloaded_batches == [(PRIMARY_QWEN3_MODEL, FALLBACK_QWEN3_MODEL)]


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
    assert fake.calls == [PRIMARY_QWEN3_MODEL, FALLBACK_QWEN3_MODEL]
    assert PRIMARY_QWEN3_MODEL in fake.unloaded


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

    assert " ".join(row["text"] for row in rows).replace(" \n", "\n") == text.replace("\n\n", " ")
    assert [row["speaker"] for row in rows] == ["Цыганка", "Сергей", "Цыганка", "Сергей"]
    assert [row["role"] for row in rows] == ["female", "male", "female", "male"]
    assert [row["voice_id"] for row in rows] == [
        "female_warm",
        "male_young",
        "female_warm",
        "male_young",
    ]
    assert all(row["section_kind"] == "dialogue" for row in rows)
    assert all(row["is_dialogue"] is True for row in rows)


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

    assert [row["text"] for row in rows] == parts
    assert [row["speaker"] for row in rows] == expected_speakers
    assert all(row["role"] == "unknown" for row in rows)
    assert all(row["voice_id"] == "narrator_calm" for row in rows)
    assert all(row["section_kind"] == "dialogue" for row in rows)
    assert all(row["is_dialogue"] is True for row in rows)


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

    assert rows[0]["text"] == text
    assert rows[0]["role"] == expected_role
    assert rows[0]["voice_id"] == expected_voice
    assert rows[0]["section_kind"] == "dialogue"
    assert rows[0]["is_dialogue"] is True


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
    assert rows[1]["is_dialogue"] is True


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
    assert len(report["failures"]) == 2
