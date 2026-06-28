"""Tests for GUI normalization worker helpers."""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from book_normalizer.config import OcrMode
from book_normalizer.gui.i18n import get_language, set_language
from book_normalizer.gui.workers.normalize_worker import (
    NormalizeWorker,
    _apply_selected_book_language,
    _effective_pdf_extraction_mode,
    _ensure_pdf_selection_is_usable,
    _native_ocr_install_hint,
)
from book_normalizer.llm.model_router import FALLBACK_QWEN3_MODEL, PRIMARY_QWEN3_MODEL
from book_normalizer.models.book import Book, Chapter, Metadata, Paragraph


def _readable_english_text() -> str:
    return (
        "This native PDF text is already readable and complete enough for the "
        "normalization worker to use without invoking expensive full page OCR. "
    ) * 4


def test_gui_pdf_auto_falls_back_without_tesseract() -> None:
    mode = _effective_pdf_extraction_mode(
        OcrMode.AUTO,
        tesseract_available=False,
    )

    assert mode == OcrMode.OFF


def test_gui_pdf_compare_falls_back_without_tesseract() -> None:
    mode = _effective_pdf_extraction_mode(
        OcrMode.COMPARE,
        tesseract_available=False,
    )

    assert mode == OcrMode.OFF


def test_gui_pdf_force_requires_tesseract() -> None:
    with pytest.raises(RuntimeError, match="Tesseract"):
        _effective_pdf_extraction_mode(
            OcrMode.FORCE,
            tesseract_available=False,
        )


def test_gui_pdf_image_requires_tesseract() -> None:
    with pytest.raises(RuntimeError, match="Tesseract"):
        _effective_pdf_extraction_mode(
            OcrMode.IMAGE,
            tesseract_available=False,
        )


def test_gui_pdf_keeps_requested_mode_when_tesseract_available() -> None:
    assert (
        _effective_pdf_extraction_mode(
            OcrMode.FORCE,
            tesseract_available=True,
        )
        == OcrMode.FORCE
    )


def test_native_ocr_install_hint_uses_host_os(monkeypatch) -> None:
    monkeypatch.setattr(
        "book_normalizer.gui.workers.normalize_worker.platform.system",
        lambda: "Windows",
    )
    assert _native_ocr_install_hint() == "install.bat --interactive --install-system-tools --download-tessdata"

    monkeypatch.setattr(
        "book_normalizer.gui.workers.normalize_worker.platform.system",
        lambda: "Linux",
    )
    assert _native_ocr_install_hint() == "./install.sh --interactive --install-system-tools --download-tessdata"


def test_gui_pdf_missing_tesseract_error_points_to_native_installer(monkeypatch) -> None:
    set_language("ru")
    monkeypatch.setattr(
        "book_normalizer.gui.workers.normalize_worker.platform.system",
        lambda: "Windows",
    )

    with pytest.raises(RuntimeError) as exc_info:
        _effective_pdf_extraction_mode(
            OcrMode.FORCE,
            tesseract_available=False,
        )

    message = str(exc_info.value)
    assert "install.bat --interactive --install-system-tools --download-tessdata" in message
    assert "wsl" not in message.lower()


def test_gui_pdf_rejects_broken_native_without_tesseract() -> None:
    set_language("en")
    with pytest.raises(RuntimeError) as exc_info:
        _ensure_pdf_selection_is_usable(
            OcrMode.AUTO,
            {"native_unreadable": True, "ocr_unreadable": True},
            tesseract_available=False,
        )
    message = str(exc_info.value)
    assert _native_ocr_install_hint() in message
    assert "wsl" not in message.lower()


def test_gui_pdf_rejects_unreadable_ocr_when_native_is_broken() -> None:
    with pytest.raises(RuntimeError, match="OCR"):
        _ensure_pdf_selection_is_usable(
            OcrMode.AUTO,
            {"native_unreadable": True, "ocr_unreadable": True},
            tesseract_available=True,
        )


def test_apply_selected_book_language_overrides_loader_metadata() -> None:
    book = Book(metadata=Metadata(language="ru"))

    result = _apply_selected_book_language(book, "en-US")

    assert result is book
    assert book.metadata.language == "en"
    assert book.audit_trail[-1]["details"] == "language=en"


def test_llm_normalize_marks_book_for_smart_voice_markup(tmp_path, monkeypatch) -> None:
    captured: dict = {}

    class _FakeNormalizer:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def normalize_book(self, book, progress_callback=None):  # noqa: ANN001
            if progress_callback is not None:
                progress_callback(1, 1, 1, 0)
            return (1, 0)

    monkeypatch.setattr("book_normalizer.normalization.llm_normalizer.LlmNormalizer", _FakeNormalizer)
    book = Book(
        metadata=Metadata(language="uz"),
        chapters=[
            Chapter(
                index=0,
                paragraphs=[Paragraph(raw_text="Salom.", normalized_text="Salom.", index_in_chapter=0)],
            ),
        ],
    )
    worker = NormalizeWorker(
        input_path=tmp_path / "book.txt",
        llm_model="gemma3:4b",
        book_language="uz",
    )

    result = worker._llm_normalize_with_progress(book)

    assert result is book
    assert captured["language"] == "uz"
    assert captured["model"] == "gemma3:4b"
    assert "llm_norm_reviews" in str(captured["review_report_path"])
    assert book.metadata.extra["llm_processing_enabled"] is True
    assert book.metadata.extra["llm_language"] == "uz"
    assert book.metadata.extra["llm_model_candidates"] == [
        PRIMARY_QWEN3_MODEL,
        FALLBACK_QWEN3_MODEL,
    ]


def test_llm_normalize_records_review_report_for_rejected_paragraphs(tmp_path, monkeypatch) -> None:
    class _FakeNormalizer:
        def __init__(self, **kwargs):
            self.review_report_path = kwargs["review_report_path"]

        def normalize_book(self, book, progress_callback=None):  # noqa: ANN001
            self.review_report_path.parent.mkdir(parents=True, exist_ok=True)
            self.review_report_path.write_text("{}", encoding="utf-8")
            if progress_callback is not None:
                progress_callback(1, 1, 0, 1)
            return (0, 1)

    monkeypatch.setattr("book_normalizer.normalization.llm_normalizer.LlmNormalizer", _FakeNormalizer)
    book = Book(
        metadata=Metadata(language="en"),
        chapters=[
            Chapter(
                index=0,
                paragraphs=[Paragraph(raw_text="Alpha.", normalized_text="Alpha.", index_in_chapter=0)],
            ),
        ],
    )
    worker = NormalizeWorker(input_path=tmp_path / "book.txt", book_language="en")

    worker._llm_normalize_with_progress(book)

    report_path = book.metadata.extra["llm_normalization_review_report"]
    assert "llm_norm_reviews" in report_path


def test_gui_ocr_progress_uses_native_tesseract_runtime(tmp_path, monkeypatch) -> None:
    from book_normalizer.loaders import pdf_loader

    class _FakePixmap:
        width = 1
        height = 1
        samples = b"\x00"

    class _FakePage:
        def get_pixmap(self, **_kwargs):  # noqa: ANN001
            return _FakePixmap()

    class _FakeDoc:
        def __enter__(self):
            return self

        def __exit__(self, *_args):  # noqa: ANN001
            return False

        def __len__(self):
            return 1

        def __getitem__(self, index):  # noqa: ANN001
            assert index == 0
            return _FakePage()

    fake_fitz = SimpleNamespace(
        Matrix=lambda *_args: object(),
        csGRAY=object(),
        open=lambda _path: _FakeDoc(),
    )
    monkeypatch.setitem(sys.modules, "fitz", fake_fitz)
    monkeypatch.setattr(pdf_loader, "_load_tesseract_runtime", lambda: ("cli", None))
    monkeypatch.setattr(pdf_loader, "_prepare_ocr_page_images", lambda _img: ["segment"])
    monkeypatch.setattr(
        pdf_loader,
        "_postprocess_ocr_text",
        lambda text, **_kwargs: text,
    )
    monkeypatch.setattr(pdf_loader, "_should_keep_ocr_text", lambda _text, _language: True)
    monkeypatch.setattr(pdf_loader, "_repair_ocr_cross_segment_breaks", lambda text: text)
    monkeypatch.setattr(pdf_loader, "remove_repeated_headers", lambda text, **_kwargs: text)
    calls: list[dict[str, object]] = []

    def fake_ocr(_img, *, lang, psm, preprocess, runtime, pytesseract_module):  # noqa: ANN001
        calls.append({
            "lang": lang,
            "psm": psm,
            "preprocess": preprocess,
            "runtime": runtime,
            "pytesseract_module": pytesseract_module,
        })
        return "Распознанный текст"

    monkeypatch.setattr(pdf_loader, "_ocr_pil_image_with_tesseract", fake_ocr)
    worker = NormalizeWorker(input_path=tmp_path / "scan.pdf", book_language="ru")
    old_language = get_language()
    set_language("en")
    messages: list[str] = []
    progress: list[tuple[int, int, str]] = []
    worker.progress.connect(messages.append)
    worker.progress_pct.connect(
        lambda current, total, eta: progress.append((current, total, eta))
    )

    try:
        text = worker._ocr_with_progress(tmp_path / "scan.pdf", OcrMode.AUTO, dpi=72, psm=6)
    finally:
        set_language(old_language)

    assert text == "Распознанный текст"
    assert any("OCR will process 1 page" in msg for msg in messages)
    assert any("rendering page 1/1" in msg for msg in messages)
    assert any("recognizing page 1/1, segment 1/1" in msg for msg in messages)
    assert progress[0] == (0, 1, "")
    assert progress[-1][0:2] == (1, 1)
    assert calls == [
        {
            "lang": "rus",
            "psm": 6,
            "preprocess": True,
            "runtime": "cli",
            "pytesseract_module": None,
        }
    ]


def test_gui_pdf_auto_uses_readable_native_without_full_ocr(tmp_path, monkeypatch) -> None:
    from book_normalizer.loaders import pdf_loader

    pdf_file = tmp_path / "native.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 dummy")

    monkeypatch.setattr(pdf_loader, "_tesseract_available", lambda: True)
    monkeypatch.setattr(
        pdf_loader.PdfLoader,
        "_extract_text",
        staticmethod(lambda _path: _readable_english_text()),
    )

    worker = NormalizeWorker(
        input_path=pdf_file,
        ocr_mode="auto",
        book_language="en",
        skip_stress=True,
    )

    def fail_ocr(*_args, **_kwargs):  # noqa: ANN002
        raise AssertionError("AUTO should not run full-page OCR for readable native text")

    monkeypatch.setattr(worker, "_ocr_with_progress", fail_ocr)
    results: list[Book] = []
    errors: list[str] = []
    worker.finished.connect(results.append)
    worker.error.connect(errors.append)

    worker.run()

    assert errors == []
    assert results
    assert results[0].metadata.extra["pdf_text_variant"] == "native"
