from __future__ import annotations

import os

import pytest

from tests.gui.helpers import assert_layout_sane, render_widget

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from book_normalizer.gui.i18n import SUPPORTED_LANGUAGES, set_language, t
from book_normalizer.models.book import Book, Chapter, Paragraph

QtWidgets = pytest.importorskip("PyQt6.QtWidgets")
QtCore = pytest.importorskip("PyQt6.QtCore")
QApplication = QtWidgets.QApplication
normalize_page = pytest.importorskip("book_normalizer.gui.pages.normalize_page")
_book_preview_lines = normalize_page._book_preview_lines
_native_ocr_install_display_command = normalize_page._native_ocr_install_display_command
_native_ocr_installer_command = normalize_page._native_ocr_installer_command
NormalizePage = normalize_page.NormalizePage


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_book_preview_default_is_not_truncated() -> None:
    book = Book(chapters=[
        Chapter(
            title="Long Chapter",
            index=0,
            paragraphs=[
                Paragraph(raw_text=f"Paragraph {idx}", normalized_text=f"Paragraph {idx}")
                for idx in range(35)
            ],
        ),
    ])

    raw_lines, norm_lines = _book_preview_lines(book)

    assert "Paragraph 34" in raw_lines
    assert norm_lines == raw_lines


def test_normalize_page_hides_ocr_help_until_pdf_selected(qapp) -> None:
    page = NormalizePage()

    assert page._ocr_mode_label_wrap.isHidden()
    assert page._ocr_dpi_label_wrap.isHidden()
    assert page._ocr_psm_label_wrap.isHidden()
    assert page._ocr_psm_field.isHidden()

    page._selected_path = "book.fb2"
    page._update_ocr_visibility()

    assert page._ocr_mode_label_wrap.isHidden()
    assert page._ocr_dpi_label_wrap.isHidden()
    assert page._ocr_psm_label_wrap.isHidden()
    assert page._ocr_psm_field.isHidden()
    assert not page._ocr_not_applicable_label.isHidden()

    page._selected_path = "book.pdf"
    page._update_ocr_visibility()

    assert not page._ocr_mode_label_wrap.isHidden()
    assert not page._ocr_dpi_label_wrap.isHidden()
    assert not page._ocr_psm_label_wrap.isHidden()
    assert not page._ocr_psm_field.isHidden()
    assert page._ocr_not_applicable_label.isHidden()

    page.deleteLater()


def test_normalize_page_prompts_native_ocr_install_when_tesseract_missing(
    qapp,
    monkeypatch,
) -> None:
    monkeypatch.setattr(normalize_page, "tesseract_available", lambda: False)
    monkeypatch.setattr(normalize_page.platform, "system", lambda: "Windows")
    set_language("ru")
    page = NormalizePage()

    page._selected_path = "book.pdf"
    page._update_ocr_visibility()

    assert not page._ocr_install_panel.isHidden()
    assert "install.bat --interactive --install-system-tools --download-tessdata" in page._ocr_install_label.text()
    assert page._btn_install_ocr_tools.text() == "Установить OCR"
    assert "wsl" not in page._ocr_install_label.text().lower()

    page.deleteLater()


def test_normalize_page_hides_native_ocr_install_when_tesseract_available(
    qapp,
    monkeypatch,
) -> None:
    monkeypatch.setattr(normalize_page, "tesseract_available", lambda: True)
    monkeypatch.setattr(normalize_page, "tesseract_language_available", lambda _lang: True)
    page = NormalizePage()

    page._selected_path = "book.pdf"
    page._update_ocr_visibility()

    assert page._ocr_install_panel.isHidden()
    page.deleteLater()


def test_normalize_page_prompts_when_tesseract_language_pack_missing(
    qapp,
    monkeypatch,
) -> None:
    monkeypatch.setattr(normalize_page, "tesseract_available", lambda: True)
    monkeypatch.setattr(normalize_page, "tesseract_language_available", lambda _lang: False)
    monkeypatch.setattr(normalize_page.platform, "system", lambda: "Windows")
    set_language("ru")
    page = NormalizePage()

    page._selected_path = "book.pdf"
    page._update_ocr_visibility()

    assert not page._ocr_install_panel.isHidden()
    assert "rus" in page._ocr_install_label.text()
    assert "языкового пакета" in page._ocr_install_label.text()
    assert "install.bat --interactive --install-system-tools --download-tessdata" in page._ocr_install_label.text()
    assert "wsl" not in page._ocr_install_label.text().lower()

    page.deleteLater()


def test_native_ocr_installer_command_uses_host_os_without_wsl(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(normalize_page.platform, "system", lambda: "Windows")
    command, args, cwd = _native_ocr_installer_command(tmp_path)
    flattened = " ".join([command, *args])

    assert command == "cmd.exe"
    assert str(tmp_path / "install.bat") in args
    assert cwd == tmp_path.resolve()
    assert "wsl" not in flattened.lower()
    assert (
        _native_ocr_install_display_command()
        == "install.bat --interactive --install-system-tools --download-tessdata"
    )

    monkeypatch.setattr(normalize_page.platform, "system", lambda: "Linux")
    command, args, cwd = _native_ocr_installer_command(tmp_path)
    flattened = " ".join([command, *args])

    assert command == str((tmp_path / "install.sh").resolve())
    assert args == ["--interactive", "--install-system-tools", "--download-tessdata"]
    assert cwd == tmp_path.resolve()
    assert "wsl" not in flattened.lower()
    assert (
        _native_ocr_install_display_command()
        == "./install.sh --interactive --install-system-tools --download-tessdata"
    )


def test_normalize_page_install_ocr_button_launches_native_installer(
    qapp,
    qtbot,
    tmp_path,
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeProcess:
        @staticmethod
        def startDetached(command, args, cwd) -> bool:  # noqa: ANN001, N802
            captured["command"] = command
            captured["args"] = list(args)
            captured["cwd"] = cwd
            return True

    monkeypatch.setattr(normalize_page.platform, "system", lambda: "Windows")
    monkeypatch.setattr(normalize_page, "_project_root", lambda: tmp_path)
    monkeypatch.setattr(normalize_page, "QProcess", FakeProcess)
    set_language("ru")
    page = NormalizePage()
    qtbot.addWidget(page)

    qtbot.mouseClick(page._btn_install_ocr_tools, QtCore.Qt.MouseButton.LeftButton)

    flattened = " ".join([captured["command"], *captured["args"]])
    assert captured["command"] == "cmd.exe"
    assert str(tmp_path / "install.bat") in captured["args"]
    assert captured["cwd"] == str(tmp_path.resolve())
    assert "wsl" not in flattened.lower()
    assert "нативный установщик OCR" in page._progress._status.text()
    assert "install.bat --interactive --install-system-tools --download-tessdata" in page._progress._status.text()


def test_normalize_page_defaults_book_language_to_russian(qapp) -> None:
    page = NormalizePage()

    assert page._book_language.currentData() == "ru"
    assert [
        page._book_language.itemData(index)
        for index in range(page._book_language.count())
    ] == ["ru", "en", "zh", "kk", "uz"]

    page.deleteLater()


def test_normalize_page_passes_selected_book_language_to_worker(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    captured: dict = {}

    class _Signal:
        def connect(self, _callback):  # noqa: ANN001
            return None

    class _FakeWorker:
        progress = _Signal()
        progress_pct = _Signal()
        finished = _Signal()
        error = _Signal()

        def __init__(self, **kwargs):
            captured.update(kwargs)

        def start(self) -> None:
            return None

    monkeypatch.setattr(normalize_page, "NormalizeWorker", _FakeWorker)

    book_path = tmp_path / "book.txt"
    book_path.write_text("Hello world.", encoding="utf-8")
    page = NormalizePage()
    page._selected_path = str(book_path)
    page._path_label.setText(str(book_path))
    page._btn_run.setEnabled(True)
    page._book_language.setCurrentIndex(page._book_language.findData("en"))
    page._ocr_psm.setCurrentIndex(page._ocr_psm.findData(11))

    page._run_normalization()

    assert captured["input_path"] == book_path
    assert captured["book_language"] == "en"
    assert captured["ocr_psm"] == 11
    assert not page._progress._bar_row.isHidden()
    assert page._progress._bar.maximum() == 0
    assert page._progress._status.text() == t("norm.starting")
    page.deleteLater()


def test_normalize_page_run_button_starts_worker(qapp, qtbot, tmp_path, monkeypatch) -> None:
    captured: dict = {}

    class _Signal:
        def __init__(self) -> None:
            self.callbacks = []

        def connect(self, callback):  # noqa: ANN001
            self.callbacks.append(callback)

        def emit(self, *args):  # noqa: ANN002
            for callback in self.callbacks:
                callback(*args)

    class _FakeWorker:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.progress = _Signal()
            self.progress_pct = _Signal()
            self.finished = _Signal()
            self.error = _Signal()

        def start(self) -> None:
            book = Book(
                chapters=[
                    Chapter(
                        index=0,
                        paragraphs=[
                            Paragraph(
                                raw_text="Hello.",
                                normalized_text="Hello.",
                                index_in_chapter=0,
                            ),
                        ],
                    )
                ],
            )
            self.finished.emit(book)

    monkeypatch.setattr(normalize_page, "NormalizeWorker", _FakeWorker)
    book_path = tmp_path / "book.txt"
    book_path.write_text("Hello.", encoding="utf-8")
    page = NormalizePage()
    qtbot.addWidget(page)
    page._selected_path = str(book_path)
    page._path_label.setText(str(book_path))
    page._btn_run.setEnabled(True)
    page._book_language.setCurrentIndex(page._book_language.findData("en"))

    qtbot.mouseClick(page._btn_run, QtCore.Qt.MouseButton.LeftButton)

    assert captured["input_path"] == book_path
    assert captured["book_language"] == "en"
    assert page._book is not None
    assert page._raw_text.toPlainText() == "Hello."


def test_normalize_page_shows_worker_preview_before_finished(
    qapp,
    tmp_path,
    monkeypatch,
) -> None:
    class _Signal:
        def __init__(self) -> None:
            self.callbacks = []

        def connect(self, callback):  # noqa: ANN001
            self.callbacks.append(callback)

        def emit(self, *args):  # noqa: ANN002
            for callback in self.callbacks:
                callback(*args)

    class _FakeWorker:
        def __init__(self, **_kwargs):
            self.progress = _Signal()
            self.progress_pct = _Signal()
            self.preview_ready = _Signal()
            self.finished = _Signal()
            self.error = _Signal()

        def start(self) -> None:
            self.preview_ready.emit(
                Book(
                    chapters=[
                        Chapter(
                            index=0,
                            paragraphs=[
                                Paragraph(
                                    raw_text="Raw preview.",
                                    normalized_text="Normalized preview.",
                                    index_in_chapter=0,
                                ),
                            ],
                        ),
                    ],
                )
            )

    monkeypatch.setattr(normalize_page, "NormalizeWorker", _FakeWorker)
    book_path = tmp_path / "book.txt"
    book_path.write_text("Raw preview.", encoding="utf-8")
    page = NormalizePage()
    page._selected_path = str(book_path)
    page._path_label.setText(str(book_path))
    page._btn_run.setEnabled(True)

    page._run_normalization()

    assert page._raw_text.toPlainText() == "Raw preview."
    assert page._norm_text.toPlainText() == "Normalized preview."
    assert page._book is None
    assert not page._btn_run.isEnabled()
    assert page._btn_apply_norm_edits.isHidden()


def test_normalize_page_hides_llm_field_help_until_enabled(qapp) -> None:
    page = NormalizePage()

    assert page._llm_endpoint_label_wrap.isHidden()
    assert page._llm_model_label_wrap.isHidden()

    page._llm_normalize.setChecked(True)

    assert not page._llm_endpoint_label_wrap.isHidden()
    assert not page._llm_model_label_wrap.isHidden()

    page._llm_normalize.setChecked(False)

    assert page._llm_endpoint_label_wrap.isHidden()
    assert page._llm_model_label_wrap.isHidden()

    page.deleteLater()


def test_normalize_page_uses_readable_psm_options_and_centered_dpi(qapp) -> None:
    set_language("en")
    page = NormalizePage()

    assert page._ocr_dpi.alignment() & QtCore.Qt.AlignmentFlag.AlignHCenter
    assert page._ocr_dpi.alignment() & QtCore.Qt.AlignmentFlag.AlignVCenter
    assert page._ocr_dpi.lineEdit().alignment() & QtCore.Qt.AlignmentFlag.AlignHCenter
    assert page._ocr_dpi.lineEdit().alignment() & QtCore.Qt.AlignmentFlag.AlignVCenter
    assert page._ocr_dpi.buttonSymbols() == QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons
    assert page._ocr_dpi.height() == 38
    assert page._ocr_dpi.width() <= 160
    assert [
        page._ocr_psm.itemData(index)
        for index in range(page._ocr_psm.count())
    ] == [3, 4, 6, 11, 13]
    current_text = page._ocr_psm.itemText(page._ocr_psm.findData(6)).lower()
    assert "6" in current_text
    assert "cropped body text" in current_text
    assert "selected text block" in current_text
    psm_help = page._ocr_psm.toolTip().lower()
    assert "normal book page" in psm_help
    assert "reading order may need review" in psm_help
    assert "do not use for full pages" in psm_help
    assert page._ocr_psm_summary.text() == t("norm.ocr_psm_summary_6")
    page._ocr_psm.setCurrentIndex(page._ocr_psm.findData(4))
    assert page._ocr_psm_summary.text() == t("norm.ocr_psm_summary_4")
    assert page._raw_label.text() == "Original text"
    assert page._norm_label.text() == "After normalization"

    page.deleteLater()
    set_language("ru")

    ru_page = NormalizePage()
    ru_texts = [
        ru_page._ocr_psm.itemText(index)
        for index in range(ru_page._ocr_psm.count())
    ]
    assert any("Обычная страница книги" in text for text in ru_texts)
    assert any("Разбросанные фрагменты" in text for text in ru_texts)
    assert "порядок чтения надо проверить" in ru_page._ocr_psm.toolTip()
    assert "не использовать для полной страницы" in ru_page._ocr_psm.toolTip()
    assert "обрезанного прямоугольника" in ru_page._ocr_psm_summary.text()
    ru_page.deleteLater()


def test_normalize_page_pdf_controls_stay_compact_and_help_centered(qapp) -> None:
    set_language("ru")
    page = NormalizePage()
    page._selected_path = "book.pdf"
    page._update_ocr_visibility()

    render_widget(page, 1180, 760, scale=1.0)

    assert page._book_language.maximumWidth() == 360
    assert page._ocr_mode.width() == 180
    assert page._ocr_mode.maximumWidth() == 180
    assert page._ocr_dpi.width() == 128
    assert page._ocr_psm.maximumWidth() == 360
    assert page._ocr_psm_field.maximumWidth() == 380

    dpi_help = page._help_buttons["norm.ocr_dpi_tip"]
    label_center = page._ocr_dpi_label.mapTo(page, page._ocr_dpi_label.rect().center()).y()
    help_center = dpi_help.mapTo(page, dpi_help.rect().center()).y()
    assert abs(label_center - help_center) <= 3

    page.deleteLater()


def test_normalize_page_hides_psm_summary_in_compact_pdf_layout(qapp) -> None:
    set_language("ru")
    page = NormalizePage()
    page._selected_path = "book.pdf"
    page._path_label.setText("book.pdf")
    page._compact_mode = True
    page._populate_psm_combo()
    page._apply_action_labels()
    page._update_ocr_visibility()

    assert page._compact_mode is True
    assert page._ocr_psm_summary.isHidden()
    assert page._llm_normalize.text() == "Локальная LLM"
    assert page._ocr_psm.itemText(page._ocr_psm.findData(6)) == "6 - Обрезанный текст"
    page.deleteLater()


def test_normalize_page_retranslates_psm_options_for_all_languages(qapp) -> None:
    vague_fragments = {
        "single column",
        "sparse text",
        "один столбец",
        "редкий текст",
        "разреженный текст",
        "单列",
        "稀疏",
        "үздіксіз мәтін бағаны",
        "uzluksiz matn ustuni",
    }
    for code, _label in SUPPORTED_LANGUAGES:
        set_language(code)
        page = NormalizePage()
        page.retranslate()

        texts = [page._ocr_psm.itemText(index) for index in range(page._ocr_psm.count())]
        page._compact_mode = True
        page._populate_psm_combo()
        compact_texts = [page._ocr_psm.itemText(index) for index in range(page._ocr_psm.count())]
        page._compact_mode = False
        page._populate_psm_combo()
        summaries = []
        for value in (3, 4, 6, 11, 13):
            page._ocr_psm.setCurrentIndex(page._ocr_psm.findData(value))
            summaries.append(page._ocr_psm_summary.text())
        all_help = "\n".join(texts + compact_texts + summaries + [page._ocr_psm.toolTip()]).lower()
        assert [page._ocr_psm.itemData(index) for index in range(page._ocr_psm.count())] == [
            3,
            4,
            6,
            11,
            13,
        ]
        assert all(text.strip() for text in texts)
        assert all(text.strip() for text in compact_texts)
        assert all(summary.strip() for summary in summaries)
        assert all("??" not in text for text in texts)
        assert all("??" not in text for text in compact_texts)
        assert all("??" not in summary for summary in summaries)
        assert "??" not in page._ocr_psm.toolTip()
        assert "\ufffd" not in page._ocr_psm.toolTip()
        assert not any(fragment.lower() in all_help for fragment in vague_fragments)
        page._ocr_psm.setCurrentIndex(page._ocr_psm.findData(6))
        assert page._ocr_psm.currentData() == 6
        assert page._ocr_psm_summary.text() == t("norm.ocr_psm_summary_6")
        page.deleteLater()

    set_language("ru")


def test_normalize_page_allows_manual_normalized_text_edits(qapp, qtbot) -> None:
    page = NormalizePage()
    qtbot.addWidget(page)
    book = Book(
        chapters=[
            Chapter(
                title="Chapter",
                index=0,
                paragraphs=[
                    Paragraph(raw_text="Raw one.", normalized_text="Norm one."),
                    Paragraph(raw_text="Raw two.", normalized_text="Norm two."),
                ],
            )
        ]
    )

    page._on_finished(book)
    assert not page._norm_text.isReadOnly()
    assert not page._btn_apply_norm_edits.isHidden()
    assert page._btn_apply_norm_edits.isEnabled()

    page._norm_text.setPlainText("=== Chapter ===\n\nEdited one.\n\nEdited two.")
    qtbot.mouseClick(page._btn_apply_norm_edits, QtCore.Qt.MouseButton.LeftButton)

    assert book.chapters[0].paragraphs[0].normalized_text == "Edited one."
    assert book.chapters[0].paragraphs[1].normalized_text == "Edited two."

    page.deleteLater()


def test_normalize_page_hides_manual_apply_until_text_exists(qapp, qtbot) -> None:
    page = NormalizePage()
    qtbot.addWidget(page)

    assert page._btn_apply_norm_edits.isHidden()
    assert not page._btn_apply_norm_edits.isEnabled()

    page._on_finished(
        Book(
            chapters=[
                Chapter(
                    index=0,
                    paragraphs=[
                        Paragraph(raw_text="Raw.", normalized_text="Normalized."),
                    ],
                )
            ]
        )
    )
    assert not page._btn_apply_norm_edits.isHidden()
    assert page._btn_apply_norm_edits.isEnabled()

    page._set_manual_edit_available(False)
    assert page._btn_apply_norm_edits.isHidden()
    assert not page._btn_apply_norm_edits.isEnabled()

    page.deleteLater()


def test_normalize_page_pdf_layout_stays_sane_at_small_size(qapp) -> None:
    page = NormalizePage()
    page._selected_path = "book.pdf"
    page._update_ocr_visibility()

    render_widget(page, 760, 520, scale=1.0)
    assert_layout_sane(page)
    assert not page.findChildren(QtWidgets.QSplitter)
    for editor in (page._raw_text, page._norm_text):
        assert editor.horizontalScrollBarPolicy() == QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        assert editor.verticalScrollBarPolicy() == QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        assert not editor.horizontalScrollBar().isVisible()
        assert not editor.verticalScrollBar().isVisible()

    def page_rect(widget):
        top_left = widget.mapTo(page, widget.rect().topLeft())
        return QtCore.QRect(top_left, widget.size()).adjusted(0, 0, -1, -1)

    raw_label = page_rect(page._raw_label)
    raw_text = page_rect(page._raw_text)
    norm_label = page_rect(page._norm_label)
    norm_text = page_rect(page._norm_text)

    assert raw_label.bottom() < raw_text.top()
    assert norm_label.bottom() < norm_text.top()
    assert raw_text.right() < norm_text.left()

    page.deleteLater()


def test_book_preview_continues_after_short_preamble() -> None:
    book = Book(chapters=[
        Chapter(
            title="Preamble",
            index=0,
            paragraphs=[
                Paragraph(raw_text="Верёвка есть вервие простое.", normalized_text="Верёвка есть вервие простое."),
            ],
        ),
        Chapter(
            title="ГЛАВА 1",
            index=1,
            paragraphs=[
                Paragraph(raw_text="Сергей сидел за столом.", normalized_text="Сергей сидел за столом."),
                Paragraph(raw_text="Гроза началась.", normalized_text="Гроза началась."),
            ],
        ),
    ])

    raw_lines, norm_lines = _book_preview_lines(book, limit=3)

    assert "Preamble" in raw_lines[0]
    assert "Верёвка есть вервие простое." in raw_lines
    assert "=== ГЛАВА 1 ===" in raw_lines
    assert "Сергей сидел за столом." in raw_lines
    assert norm_lines == raw_lines
