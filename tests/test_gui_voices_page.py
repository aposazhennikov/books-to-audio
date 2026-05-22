from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from book_normalizer.llm.model_router import PRIMARY_QWEN3_MODEL
from book_normalizer.models.book import Book, Metadata

QtWidgets = pytest.importorskip("PyQt6.QtWidgets")
QApplication = QtWidgets.QApplication
voices_page = pytest.importorskip("book_normalizer.gui.pages.voices_page")
VoicesPage = voices_page.VoicesPage


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_voices_page_defaults_to_llm_when_normalization_used(qapp, tmp_path) -> None:
    book = Book(
        metadata=Metadata(
            language="kk",
            extra={
                "llm_processing_enabled": True,
                "llm_model_candidates": [PRIMARY_QWEN3_MODEL, "fallback"],
            },
        ),
    )
    page = VoicesPage()

    page.set_book(book, tmp_path)

    assert page._speaker_mode.currentData() == "llm"
    assert page._llm_model.text() == PRIMARY_QWEN3_MODEL
    page.deleteLater()
