from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from book_normalizer.gui import role_cache
from book_normalizer.gui.i18n import set_language, t
from book_normalizer.models.book import Book, Chapter, Metadata, Paragraph

QtWidgets = pytest.importorskip("PyQt6.QtWidgets")
QtCore = pytest.importorskip("PyQt6.QtCore")
QApplication = QtWidgets.QApplication
roles_page = pytest.importorskip("book_normalizer.gui.pages.roles_page")
RolesPage = roles_page.RolesPage


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def isolate_role_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(role_cache, "CACHE_ROOT", tmp_path / "role_cache")


class _Signal:
    def __init__(self) -> None:
        self.callbacks = []

    def connect(self, callback):  # noqa: ANN001
        self.callbacks.append(callback)

    def emit(self, *args):  # noqa: ANN002
        for callback in self.callbacks:
            callback(*args)


def _sample_book() -> Book:
    return Book(
        metadata=Metadata(language="ru"),
        chapters=[
            Chapter(
                index=0,
                paragraphs=[
                    Paragraph(raw_text="Привет.", normalized_text="Привет."),
                ],
            )
        ],
    )


def _segments_payload(speaker: str = "Alice") -> list[dict[str, object]]:
    return [
        {
            "segment_index": 0,
            "chapter_index": 0,
            "language": "ru",
            "role": "female",
            "speaker": speaker,
            "character_description": "Lead character.",
            "is_dialogue": True,
            "emotion": "calm",
            "intonation": "calm",
            "text": "Hello.",
        }
    ]


def _roles_inventory(display_name: str = "Alice") -> dict[str, object]:
    return {
        "roles": [
            {
                "display_name": display_name,
                "description": "Cached lead.",
                "direct_speech_count": 1,
                "emotions": [{"emotion": "calm", "count": 1}],
                "segment_count": 1,
            }
        ],
        "total_direct_speech": 1,
        "total_segments": 1,
    }


def _write_cached_role_inputs(path: Path) -> tuple[Path, Path]:
    path.mkdir(parents=True, exist_ok=True)
    segments_path = path / "segments_manifest.json"
    roles_path = path / "roles_manifest.json"
    segments_path.write_text(
        json.dumps(_segments_payload(), ensure_ascii=False),
        encoding="utf-8",
    )
    roles_path.write_text(
        json.dumps(_roles_inventory("Cached Alice"), ensure_ascii=False),
        encoding="utf-8",
    )
    return segments_path, roles_path


def test_roles_page_runs_llm_segments_and_writes_inventory(
    qapp,
    qtbot,
    tmp_path: Path,
    monkeypatch,
) -> None:
    captured: dict = {}

    class _FakeWorker:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.progress = _Signal()
            self.finished = _Signal()
            self.error = _Signal()

        def start(self) -> None:
            manifest_path = captured["output_dir"] / "segments_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    [
                        {
                            "segment_index": 0,
                            "chapter_index": 0,
                            "language": "ru",
                            "role": "female",
                            "speaker": "Маргарита",
                            "character_description": "Смелая.",
                            "is_dialogue": True,
                            "emotion": "joyful",
                            "intonation": "joyful",
                            "text": "Привет.",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            self.finished.emit(str(manifest_path))

    monkeypatch.setattr(roles_page, "ExportSegmentsWorker", _FakeWorker)
    page = RolesPage()
    qtbot.addWidget(page)
    page.set_book(_sample_book(), tmp_path)

    emitted: list[tuple[str, str]] = []
    page.segments_ready.connect(lambda segments, roles: emitted.append((segments, roles)))
    qtbot.mouseClick(page._btn_extract, QtCore.Qt.MouseButton.LeftButton)

    assert captured["speaker_mode"] == "llm"
    assert captured["output_dir"] == tmp_path
    assert emitted == [
        (
            str(tmp_path / "segments_manifest.json"),
            str(tmp_path / "roles_manifest.json"),
        )
    ]
    inventory = json.loads((tmp_path / "roles_manifest.json").read_text(encoding="utf-8"))
    assert inventory["roles"][0]["display_name"] == "Маргарита"
    assert page._table.rowCount() == 1

    page.deleteLater()


def test_roles_page_restores_completed_roles_from_cache(
    qapp,
    qtbot,
    tmp_path: Path,
    monkeypatch,
) -> None:
    class _UnexpectedWorker:
        def __init__(self, **_kwargs):
            raise AssertionError("worker should not start when role cache is restored")

    book = _sample_book()
    output_dir = tmp_path / "output"
    source_segments, source_roles = _write_cached_role_inputs(tmp_path / "cache_source")
    page = RolesPage()
    qtbot.addWidget(page)
    page.set_book(book, output_dir)
    role_cache.save_role_cache(
        book,
        page._role_cache_settings(),
        source_segments,
        source_roles,
    )
    monkeypatch.setattr(page, "_ask_cached_roles", lambda: "restore")
    monkeypatch.setattr(roles_page, "ExportSegmentsWorker", _UnexpectedWorker)
    set_language("en")

    emitted: list[tuple[str, str]] = []
    page.segments_ready.connect(lambda segments, roles: emitted.append((segments, roles)))
    page._run_role_extraction()

    restored_roles = json.loads(
        (output_dir / "roles_manifest.json").read_text(encoding="utf-8")
    )
    assert restored_roles["roles"][0]["display_name"] == "Cached Alice"
    assert page._table.item(0, 0).text() == "Cached Alice"
    assert emitted == [
        (
            str(output_dir / "segments_manifest.json"),
            str(output_dir / "roles_manifest.json"),
        )
    ]
    assert page._progress._status.text() == t("roles.cache_restored", n=1)
    assert page._btn_extract.isEnabled()
    set_language("ru")
    page.deleteLater()


def test_roles_page_can_extract_again_when_role_cache_exists(
    qapp,
    qtbot,
    tmp_path: Path,
    monkeypatch,
) -> None:
    started: list[bool] = []

    class _FakeWorker:
        def __init__(self, **kwargs):
            self.output_dir = kwargs["output_dir"]
            self.progress = _Signal()
            self.progress_pct = _Signal()
            self.finished = _Signal()
            self.error = _Signal()

        def start(self) -> None:
            started.append(True)
            manifest_path = self.output_dir / "segments_manifest.json"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(
                json.dumps(_segments_payload("Fresh Alice"), ensure_ascii=False),
                encoding="utf-8",
            )
            self.finished.emit(str(manifest_path))

    book = _sample_book()
    output_dir = tmp_path / "output"
    source_segments, source_roles = _write_cached_role_inputs(tmp_path / "cache_source")
    page = RolesPage()
    qtbot.addWidget(page)
    page.set_book(book, output_dir)
    role_cache.save_role_cache(
        book,
        page._role_cache_settings(),
        source_segments,
        source_roles,
    )
    monkeypatch.setattr(page, "_ask_cached_roles", lambda: "fresh")
    monkeypatch.setattr(roles_page, "ExportSegmentsWorker", _FakeWorker)

    page._run_role_extraction()

    assert started == [True]
    assert page._table.item(0, 0).text() == "Fresh Alice"
    assert page._progress._status.text() == roles_page.t("roles.done", n=1)
    page.deleteLater()


def test_roles_page_can_cancel_when_role_cache_exists(
    qapp,
    qtbot,
    tmp_path: Path,
    monkeypatch,
) -> None:
    class _UnexpectedWorker:
        def __init__(self, **_kwargs):
            raise AssertionError("worker should not start when role cache prompt is cancelled")

    book = _sample_book()
    source_segments, source_roles = _write_cached_role_inputs(tmp_path / "cache_source")
    page = RolesPage()
    qtbot.addWidget(page)
    page.set_book(book, tmp_path / "output")
    role_cache.save_role_cache(
        book,
        page._role_cache_settings(),
        source_segments,
        source_roles,
    )
    monkeypatch.setattr(page, "_ask_cached_roles", lambda: "cancel")
    monkeypatch.setattr(roles_page, "ExportSegmentsWorker", _UnexpectedWorker)

    page._run_role_extraction()

    assert page._segments_path is None
    assert page._btn_extract.isEnabled()
    page.deleteLater()


@pytest.mark.parametrize(
    ("clicked_key", "expected"),
    [
        ("roles.cache_restore_button", "restore"),
        ("roles.cache_run_fresh_button", "fresh"),
        ("roles.cache_cancel_button", "cancel"),
    ],
)
def test_roles_page_cache_prompt_uses_localized_copy(
    qapp,
    monkeypatch,
    clicked_key: str,
    expected: str,
) -> None:
    seen: dict[str, object] = {}

    class _FakeMessageBox:
        class Icon:
            Question = object()

        class ButtonRole:
            AcceptRole = object()
            ActionRole = object()
            RejectRole = object()

        clicked_text = ""

        def __init__(self, parent):  # noqa: ANN001
            seen["parent"] = parent
            seen["buttons"] = []
            self._buttons: dict[str, object] = {}

        def setIcon(self, icon):  # noqa: ANN001, N802
            seen["icon"] = icon

        def setWindowTitle(self, title):  # noqa: ANN001, N802
            seen["title"] = title

        def setText(self, text):  # noqa: ANN001, N802
            seen["text"] = text

        def setInformativeText(self, text):  # noqa: ANN001, N802
            seen["informative"] = text

        def addButton(self, text, role):  # noqa: ANN001, N802
            button = object()
            self._buttons[text] = button
            seen["buttons"].append((text, role))
            return button

        def setDefaultButton(self, button):  # noqa: ANN001, N802
            seen["default"] = button

        def setEscapeButton(self, button):  # noqa: ANN001, N802
            seen["escape"] = button

        def exec(self) -> None:
            return None

        def clickedButton(self):  # noqa: N802
            return self._buttons[self.clicked_text]

    set_language("en")
    _FakeMessageBox.clicked_text = t(clicked_key)
    monkeypatch.setattr(roles_page, "QMessageBox", _FakeMessageBox)
    page = RolesPage()

    assert page._ask_cached_roles() == expected
    assert seen["title"] == t("roles.cache_dialog_title")
    assert seen["text"] == t("roles.cache_dialog_text")
    assert seen["informative"] == t("roles.cache_dialog_informative")
    assert {text for text, _role in seen["buttons"]} == {
        t("roles.cache_restore_button"),
        t("roles.cache_run_fresh_button"),
        t("roles.cache_cancel_button"),
    }
    set_language("ru")
    page.deleteLater()


def test_roles_page_shows_busy_feedback_before_first_llm_window(
    qapp,
    qtbot,
    tmp_path: Path,
    monkeypatch,
) -> None:
    class _FakeWorker:
        def __init__(self, **_kwargs):
            self.progress = _Signal()
            self.progress_pct = _Signal()
            self.finished = _Signal()
            self.error = _Signal()

        def start(self) -> None:
            return

    monkeypatch.setattr(roles_page, "ExportSegmentsWorker", _FakeWorker)
    page = RolesPage()
    qtbot.addWidget(page)
    page.set_book(_sample_book(), tmp_path)

    qtbot.mouseClick(page._btn_extract, QtCore.Qt.MouseButton.LeftButton)

    assert not page._btn_extract.isEnabled()
    assert page._progress._status.text() == roles_page.t("roles.extracting")
    assert page._progress._bar.maximum() == 0

    page._worker.progress.emit("Waiting for local LLM")
    assert page._progress._status.text() == "Waiting for local LLM"
    assert page._progress._bar.maximum() == 0

    page._worker.progress_pct.emit(2, 10, "1m 20s")
    assert page._progress._bar.maximum() == 10
    assert page._progress._bar.value() == 2
    assert "1m 20s" in page._progress._eta.text()

    page.deleteLater()


def test_roles_page_warns_when_review_report_was_written(qapp, tmp_path: Path) -> None:
    page = RolesPage()
    page.set_book(_sample_book(), tmp_path)
    manifest_path = tmp_path / "segments_manifest.json"
    manifest_path.write_text(
        json.dumps(
            [
                {
                    "segment_index": 0,
                    "chapter_index": 0,
                    "language": "ru",
                    "role": "narrator",
                    "text": "РџСЂРёРІРµС‚.",
                    "intonation": "calm",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (tmp_path / "llm_voice_review_report.json").write_text(
        '{"requires_human_review": true}',
        encoding="utf-8",
    )

    page.load_segments_manifest(manifest_path)

    assert "llm_voice_review_report.json" in page._progress._status.text()

    page.deleteLater()


def test_roles_page_labels_llm_fields_and_shows_endpoint_start(qapp) -> None:
    page = RolesPage()

    assert page._llm_endpoint_label.text()
    assert page._llm_model_label.text()
    assert page._llm_endpoint.cursorPosition() == 0
    assert page._llm_model.cursorPosition() == 0
    assert page._llm_endpoint.minimumWidth() >= 318
    assert page._llm_endpoint.maximumWidth() <= 340
    assert page._btn_extract.maximumWidth() <= 340

    page.deleteLater()
