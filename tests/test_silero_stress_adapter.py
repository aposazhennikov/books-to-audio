"""Tests for external stress mark conversion and model integration."""

from __future__ import annotations

from pathlib import Path

from book_normalizer.memory.stress_store import StressStore
from book_normalizer.models.book import Book, Chapter, Paragraph
from book_normalizer.models.memory import StressMemoryEntry
from book_normalizer.stress.annotator import StressAnnotator
from book_normalizer.stress.dictionary import COMBINING_ACUTE, StressDictionary
from book_normalizer.stress.silero import convert_external_stress_marks


class FakePredictor:
    def __init__(self, accented: str) -> None:
        self._accented = accented

    def accent_text(self, _text: str) -> str:
        return convert_external_stress_marks(self._accented)


def test_plus_stress_is_converted_to_combining_acute() -> None:
    assert convert_external_stress_marks("зам+ок") == "замо" + COMBINING_ACUTE + "к"


def test_apostrophe_stress_is_converted_to_combining_acute() -> None:
    assert convert_external_stress_marks("замо'к") == "замо" + COMBINING_ACUTE + "к"


def test_stress_annotator_uses_paragraph_prediction_for_homograph() -> None:
    para = Paragraph(raw_text="Он открыл замок.", normalized_text="Он открыл замок.")
    book = Book(chapters=[Chapter(title="Test", index=0, paragraphs=[para])])
    dictionary = StressDictionary(predictor=FakePredictor("Он откр+ыл зам+ок."))

    result = StressAnnotator(dictionary).annotate_book(book)

    assert result.predicted_words >= 2
    assert any(seg.text == "замок" and seg.stress_form == "замо" + COMBINING_ACUTE + "к" for seg in para.segments)


def test_user_override_wins_over_model(tmp_path: Path) -> None:
    store = StressStore(tmp_path / "stress.json")
    store.add(
        StressMemoryEntry(
            word="замок",
            normalized_word="замок",
            stressed_form="за" + COMBINING_ACUTE + "мок",
            confirmed=True,
        )
    )
    dictionary = StressDictionary(store=store, predictor=FakePredictor("зам+ок"))

    assert dictionary.lookup("замок") == "за" + COMBINING_ACUTE + "мок"

