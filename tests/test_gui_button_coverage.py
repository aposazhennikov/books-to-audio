"""Real click coverage for GUI buttons that should stay interactive."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tests.gui.helpers import qapp as make_qapp
from tests.gui.helpers import render_widget

QtCore = pytest.importorskip("PyQt6.QtCore")
QtGui = pytest.importorskip("PyQt6.QtGui")
QtWidgets = pytest.importorskip("PyQt6.QtWidgets")

assembly_page = pytest.importorskip("book_normalizer.gui.pages.assembly_page")
normalize_page = pytest.importorskip("book_normalizer.gui.pages.normalize_page")
synthesis_page = pytest.importorskip("book_normalizer.gui.pages.synthesis_page")
voice_preview = pytest.importorskip("book_normalizer.gui.widgets.voice_preview")

AssemblyPage = assembly_page.AssemblyPage
NormalizePage = normalize_page.NormalizePage
SynthesisPage = synthesis_page.SynthesisPage
VoicePreviewPanel = voice_preview.VoicePreviewPanel
VoiceTableWidget = pytest.importorskip(
    "book_normalizer.gui.widgets.voice_table",
).VoiceTableWidget


@pytest.fixture
def qapp():
    return make_qapp()


class _Signal:
    def __init__(self) -> None:
        self.callbacks = []

    def connect(self, callback):  # noqa: ANN001
        self.callbacks.append(callback)

    def emit(self, *args):  # noqa: ANN002
        for callback in self.callbacks:
            callback(*args)


def _manifest_payload() -> dict:
    return {
        "version": 2,
        "book_title": "Button Coverage",
        "chapters": [
            {
                "chapter_index": 0,
                "chunks": [
                    {
                        "chapter_index": 0,
                        "chunk_index": 0,
                        "voice_id": "narrator_calm",
                        "text": "Alpha beta gamma.",
                    },
                    {
                        "chapter_index": 0,
                        "chunk_index": 1,
                        "voice_id": "male_confident",
                        "text": "Second line.",
                    },
                ],
            }
        ],
    }


def _write_manifest(path: Path) -> Path:
    path.write_text(
        json.dumps(_manifest_payload(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def test_normalize_browse_button_selects_file_and_enables_run(
    qapp,
    qtbot,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    book_path = tmp_path / "book.txt"
    book_path.write_text("Hello.", encoding="utf-8")
    monkeypatch.setattr(
        normalize_page.QFileDialog,
        "getOpenFileName",
        lambda *_args, **_kwargs: (str(book_path), "TXT"),
    )
    page = NormalizePage()
    qtbot.addWidget(page)

    qtbot.mouseClick(page._btn_browse, QtCore.Qt.MouseButton.LeftButton)

    assert page._selected_path == str(book_path)
    assert page._path_label.text() == str(book_path)
    assert page._btn_run.isEnabled()


def test_assembly_browse_and_run_buttons_start_worker(
    qapp,
    qtbot,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected_dir = tmp_path / "audio_chunks"
    selected_dir.mkdir()
    captured: dict = {}

    class _FakeAssemblyWorker:
        def __init__(self, audio_dir, output_dir, pause_same, pause_change, **kwargs):
            captured.update(
                {
                    "audio_dir": audio_dir,
                    "output_dir": output_dir,
                    "pause_same": pause_same,
                    "pause_change": pause_change,
                    "manifest_path": kwargs.get("manifest_path"),
                }
            )
            self.progress = _Signal()
            self.finished = _Signal()
            self.error = _Signal()

        def start(self) -> None:
            self.finished.emit("Chapter 1: 2 chunks -> 3.5s")

    monkeypatch.setattr(
        assembly_page.QFileDialog,
        "getExistingDirectory",
        lambda *_args, **_kwargs: str(selected_dir),
    )
    monkeypatch.setattr(assembly_page, "AssemblyWorker", _FakeAssemblyWorker)
    page = AssemblyPage()
    qtbot.addWidget(page)

    qtbot.mouseClick(page._btn_browse, QtCore.Qt.MouseButton.LeftButton)
    assert page._btn_run.isEnabled()
    qtbot.mouseClick(page._btn_run, QtCore.Qt.MouseButton.LeftButton)

    assert captured["audio_dir"] == selected_dir
    assert captured["output_dir"] == selected_dir.parent
    assert captured["manifest_path"] is None
    assert "3.5" in page._output_label.text()
    assert page._btn_run.isEnabled()


def test_voice_preview_directory_selection_and_bulk_buttons(
    qapp,
    qtbot,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preview_dir = tmp_path / "previews"
    preview_dir.mkdir()
    monkeypatch.setattr(
        voice_preview.QFileDialog,
        "getExistingDirectory",
        lambda *_args, **_kwargs: str(preview_dir),
    )
    panel = VoicePreviewPanel()
    qtbot.addWidget(panel)

    qtbot.mouseClick(panel._btn_select_none, QtCore.Qt.MouseButton.LeftButton)
    assert not any(card.is_selected for card in panel._cards)

    qtbot.mouseClick(panel._btn_select_all, QtCore.Qt.MouseButton.LeftButton)
    assert all(card.is_selected for card in panel._cards)

    qtbot.mouseClick(panel._btn_browse, QtCore.Qt.MouseButton.LeftButton)
    assert panel._dir_input.text() == str(preview_dir)

    qtbot.mouseClick(panel._btn_refresh, QtCore.Qt.MouseButton.LeftButton)
    assert panel._status_label.text()


def test_voice_table_bulk_editor_and_retry_buttons_click_through(
    qapp,
    qtbot,
    tmp_path: Path,
) -> None:
    table = VoiceTableWidget()
    qtbot.addWidget(table)
    table.set_segments(
        [
            {
                "segment_index": 0,
                "chapter_index": 0,
                "role": "narrator",
                "voice_id": "narrator_calm",
                "intonation": "calm",
                "is_dialogue": False,
                "text": "First half. Second half.",
            },
            {
                "segment_index": 1,
                "chapter_index": 0,
                "role": "male",
                "voice_id": "male_confident",
                "intonation": "firm",
                "is_dialogue": True,
                "text": "Dialogue line.",
            },
            {
                "segment_index": 2,
                "chapter_index": 0,
                "role": "narrator",
                "voice_id": "narrator_calm",
                "intonation": "neutral",
                "is_dialogue": False,
                "text": "",
            },
        ]
    )
    render_widget(table, 980, 520, scale=1.0)

    qtbot.mouseClick(table._btn_all_male, QtCore.Qt.MouseButton.LeftButton)
    assert {segment["voice_id"] for segment in table.get_segments()} == {"male_confident"}

    qtbot.mouseClick(table._btn_all_female, QtCore.Qt.MouseButton.LeftButton)
    assert {segment["voice_id"] for segment in table.get_segments()} == {"female_warm"}

    qtbot.mouseClick(table._btn_all_narrator, QtCore.Qt.MouseButton.LeftButton)
    assert {segment["voice_id"] for segment in table.get_segments()} == {"narrator_calm"}

    table.get_segments()[1]["role"] = "male"
    table.get_segments()[1]["is_dialogue"] = True
    table._populate_table()
    table._quick_combo.setCurrentIndex(table._quick_combo.findData("female_warm"))
    qtbot.mouseClick(table._btn_apply_dialogue, QtCore.Qt.MouseButton.LeftButton)
    assert table.get_segments()[1]["voice_id"] == "female_warm"
    assert table.get_segments()[0]["voice_id"] == "narrator_calm"

    table._quick_combo.setCurrentIndex(table._quick_combo.findData("male_confident"))
    qtbot.mouseClick(table._btn_apply_narrator, QtCore.Qt.MouseButton.LeftButton)
    assert table.get_segments()[0]["voice_id"] == "male_confident"

    table.get_segments()[0]["role"] = "narrator"
    table.get_segments()[0]["is_dialogue"] = False
    table.get_segments()[1]["role"] = "male"
    table.get_segments()[1]["is_dialogue"] = True
    table._populate_table()
    qtbot.mouseClick(table._btn_auto, QtCore.Qt.MouseButton.LeftButton)
    assert table.get_segments()[0]["voice_id"] == "narrator_calm"
    assert table.get_segments()[1]["voice_id"] == "male_young"

    table._table.setCurrentCell(0, 3)
    cursor = table._segment_editor.textCursor()
    cursor.setPosition(len("First half."))
    table._segment_editor.setTextCursor(cursor)
    qtbot.mouseClick(table._btn_segment_split, QtCore.Qt.MouseButton.LeftButton)
    assert [segment["text"] for segment in table.get_segments()[:2]] == [
        "First half.",
        "Second half.",
    ]

    table._select_segment_index(0)
    qtbot.mouseClick(table._btn_segment_merge, QtCore.Qt.MouseButton.LeftButton)
    assert table.get_segments()[0]["text"] == "First half. Second half."

    table._select_segment_index(len(table.get_segments()) - 1)
    qtbot.mouseClick(table._btn_segment_delete_empty, QtCore.Qt.MouseButton.LeftButton)
    assert all(segment["text"] for segment in table.get_segments())

    table._select_segment_index(0)
    qtbot.mouseClick(table._btn_segment_delete, QtCore.Qt.MouseButton.LeftButton)
    assert table.get_segments()[0]["deleted"] is True
    qtbot.mouseClick(table._btn_segment_restore, QtCore.Qt.MouseButton.LeftButton)
    assert table.get_segments()[0]["deleted"] is False

    qtbot.mouseClick(table._btn_full_refresh, QtCore.Qt.MouseButton.LeftButton)
    table._full_text_editor.setPlainText("One.\n\nTwo.\n\nThree.")
    qtbot.mouseClick(table._btn_full_apply, QtCore.Qt.MouseButton.LeftButton)
    assert [segment["text"] for segment in table.get_segments()] == ["One.", "Two.", "Three."]

    manifest_path = _write_manifest(tmp_path / "chunks_manifest_v2.json")
    table.load_manifest(manifest_path)
    retry_button = table._table.cellWidget(0, 8)
    assert retry_button is not None and retry_button.isEnabled()
    qtbot.mouseClick(retry_button, QtCore.Qt.MouseButton.LeftButton)
    assert table.get_segments()[0]["failed"] is True


def test_synthesis_manifest_directory_and_chunk_buttons_click_through(
    qapp,
    qtbot,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path = _write_manifest(tmp_path / "chunks_manifest_v2.json")
    output_dir = tmp_path / "out"
    sample_audio = tmp_path / "sample.wav"
    sample_audio.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt ")
    directory_choices = iter([
        str(output_dir),
        str(tmp_path / "models"),
        str(tmp_path / "voices"),
    ])

    monkeypatch.setattr(
        synthesis_page.QFileDialog,
        "getOpenFileName",
        lambda *_args, **_kwargs: (str(manifest_path), "JSON"),
    )
    monkeypatch.setattr(
        synthesis_page.QFileDialog,
        "getExistingDirectory",
        lambda *_args, **_kwargs: next(directory_choices),
    )
    monkeypatch.setattr(synthesis_page, "missing_tts_model_ids", lambda *_args, **_kwargs: [])

    page = SynthesisPage()
    qtbot.addWidget(page)
    render_widget(page, 1180, 760, scale=1.0)

    qtbot.mouseClick(page._btn_load, QtCore.Qt.MouseButton.LeftButton)
    assert page._manifest_path == manifest_path
    assert page._btn_start.isEnabled()
    assert page._btn_test.isEnabled()

    page._test_chunk_preview.setPlainText("Edited alpha beta.")
    qtbot.mouseClick(page._btn_save_chunk_text, QtCore.Qt.MouseButton.LeftButton)
    saved = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert saved["chapters"][0]["chunks"][0]["text"] == "Edited alpha beta."

    cursor = page._test_chunk_preview.textCursor()
    cursor.setPosition(len("Edited alpha"))
    page._test_chunk_preview.setTextCursor(cursor)
    qtbot.mouseClick(page._btn_split_chunk, QtCore.Qt.MouseButton.LeftButton)
    split_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(split_manifest["chapters"][0]["chunks"]) == 3

    qtbot.mouseClick(page._btn_merge_chunk, QtCore.Qt.MouseButton.LeftButton)
    merged_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(merged_manifest["chapters"][0]["chunks"]) == 2

    page._mode_tabs.setCurrentIndex(0)
    monkeypatch.setattr(
        synthesis_page.QFileDialog,
        "getOpenFileName",
        lambda *_args, **_kwargs: (str(sample_audio), "WAV"),
    )
    qtbot.mouseClick(page._btn_sample_audio, QtCore.Qt.MouseButton.LeftButton)
    assert page._sample_audio_edit.text() == str(sample_audio)
    assert page._btn_sample_play.isEnabled()

    qtbot.mouseClick(page._btn_save_sample_voice, QtCore.Qt.MouseButton.LeftButton)
    assert page._sample_status.text()

    qtbot.mouseClick(page._voice_tuning_toggle, QtCore.Qt.MouseButton.LeftButton)
    assert page._voice_tuning_panel.isVisible()

    page._mode_tabs.setCurrentIndex(2)
    qtbot.mouseClick(page._btn_output_dir, QtCore.Qt.MouseButton.LeftButton)
    assert page._output_dir_edit.text() == str(output_dir)
    qtbot.mouseClick(page._btn_models_dir, QtCore.Qt.MouseButton.LeftButton)
    assert page._models_dir_edit.text() == str(tmp_path / "models")
    qtbot.mouseClick(page._btn_voice_library_dir, QtCore.Qt.MouseButton.LeftButton)
    assert page._voice_library_dir_edit.text() == str(tmp_path / "voices")

    qtbot.mouseClick(page._btn_install_models, QtCore.Qt.MouseButton.LeftButton)
    assert str(tmp_path / "models") in page._status.text()


def test_synthesis_run_buttons_use_worker_wiring_without_real_tts(
    qapp,
    qtbot,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path = _write_manifest(tmp_path / "chunks_manifest_v2.json")
    captured: list[dict] = []

    class _FakeTTSWorker:
        def __init__(self, **kwargs):
            captured.append(kwargs)
            self.progress = _Signal()
            self.status = _Signal()
            self.log_line = _Signal()
            self.finished = _Signal()
            self.error = _Signal()
            self.cancelled = False

        def start(self) -> None:
            self.finished.emit(str(captured[-1]["output_dir"]), 1, 0)

        def cancel(self) -> None:
            self.cancelled = True

    monkeypatch.setattr(synthesis_page, "TTSSynthesisWorker", _FakeTTSWorker)
    page = SynthesisPage()
    qtbot.addWidget(page)
    page.set_manifest(manifest_path, tmp_path / "out")
    page._mode_tabs.setCurrentIndex(1)

    qtbot.mouseClick(page._btn_test, QtCore.Qt.MouseButton.LeftButton)
    assert captured[-1]["batch_size"] == 1
    assert captured[-1]["merge_chapters"] is False

    qtbot.mouseClick(page._btn_start, QtCore.Qt.MouseButton.LeftButton)
    assert captured[-1]["manifest_path"] == manifest_path
    assert captured[-1]["output_dir"] == tmp_path / "out"

    class _BlockingTTSWorker(_FakeTTSWorker):
        def start(self) -> None:
            return None

    monkeypatch.setattr(synthesis_page, "TTSSynthesisWorker", _BlockingTTSWorker)
    qtbot.mouseClick(page._btn_start, QtCore.Qt.MouseButton.LeftButton)
    worker = page._worker
    assert worker is not None
    assert page._btn_stop.isEnabled()
    qtbot.mouseClick(page._btn_stop, QtCore.Qt.MouseButton.LeftButton)
    assert worker.cancelled is True
