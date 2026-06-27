"""Real click coverage for GUI buttons that should stay interactive."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from book_normalizer.gui import normalization_cache, role_cache
from book_normalizer.gui.i18n import t
from book_normalizer.models.book import Book, Chapter, Metadata, Paragraph
from tests.gui.helpers import qapp as make_qapp
from tests.gui.helpers import render_widget

QtCore = pytest.importorskip("PyQt6.QtCore")
QtGui = pytest.importorskip("PyQt6.QtGui")
QtWidgets = pytest.importorskip("PyQt6.QtWidgets")

cli = pytest.importorskip("book_normalizer.cli")
main_window = pytest.importorskip("book_normalizer.gui.main_window")
assembly_page = pytest.importorskip("book_normalizer.gui.pages.assembly_page")
normalize_page = pytest.importorskip("book_normalizer.gui.pages.normalize_page")
roles_page = pytest.importorskip("book_normalizer.gui.pages.roles_page")
synthesis_page = pytest.importorskip("book_normalizer.gui.pages.synthesis_page")
voices_page = pytest.importorskip("book_normalizer.gui.pages.voices_page")
voice_preview = pytest.importorskip("book_normalizer.gui.widgets.voice_preview")

AssemblyPage = assembly_page.AssemblyPage
MainWindow = main_window.MainWindow
NormalizePage = normalize_page.NormalizePage
SynthesisPage = synthesis_page.SynthesisPage
VoicesPage = voices_page.VoicesPage
VoicePreviewPanel = voice_preview.VoicePreviewPanel
VoiceTableWidget = pytest.importorskip(
    "book_normalizer.gui.widgets.voice_table",
).VoiceTableWidget


@pytest.fixture
def qapp():
    return make_qapp()


@pytest.fixture(autouse=True)
def isolate_normalization_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(normalization_cache, "CACHE_ROOT", tmp_path / "normalization_cache")
    monkeypatch.setattr(role_cache, "CACHE_ROOT", tmp_path / "role_cache")


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


def test_main_window_llm_workflow_clicks_normalize_roles_and_loads_chunks(
    qapp,
    qtbot,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    book_path = tmp_path / "workflow.txt"
    book_path.write_text("Маргарита сказала: «Здравствуйте!»", encoding="utf-8")
    output_dir = tmp_path / "audio_out"
    captured_normalize: dict = {}
    captured_segments: dict = {}

    class _FakeNormalizeWorker:
        def __init__(self, **kwargs):
            captured_normalize.update(kwargs)
            self.progress = _Signal()
            self.progress_pct = _Signal()
            self.finished = _Signal()
            self.error = _Signal()

        def start(self) -> None:
            book = Book(
                metadata=Metadata(
                    language=captured_normalize["book_language"],
                    extra={
                        "llm_processing_enabled": captured_normalize["llm_normalize"],
                        "llm_model_candidates": [captured_normalize["llm_model"]],
                    },
                ),
                chapters=[
                    Chapter(
                        title="Глава 1",
                        index=0,
                        paragraphs=[
                            Paragraph(
                                raw_text="Маргарита сказала: «Здравствуйте!»",
                                normalized_text="Маргарита сказала: «Здравствуйте!»",
                            ),
                        ],
                    ),
                ],
            )
            self.finished.emit(book)

    class _FakeExportSegmentsWorker:
        def __init__(self, **kwargs):
            captured_segments.update(kwargs)
            self.progress = _Signal()
            self.finished = _Signal()
            self.error = _Signal()

        def start(self) -> None:
            manifest_path = captured_segments["output_dir"] / "segments_manifest.json"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(
                json.dumps(
                    [
                        {
                            "segment_index": 0,
                            "chapter_index": 0,
                            "language": "ru",
                            "role": "margarita",
                            "speaker": "Маргарита",
                            "character_description": "Смелая, теплая, прямая.",
                            "is_dialogue": True,
                            "emotion": "warm",
                            "intonation": "warm",
                            "voice_id": "female_warm",
                            "text": "Здравствуйте!",
                            "pause_after_ms": 260,
                            "boundary_after": "sentence",
                        }
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            self.finished.emit(str(manifest_path))

    monkeypatch.setattr(
        normalize_page.QFileDialog,
        "getOpenFileName",
        lambda *_args, **_kwargs: (str(book_path), "TXT"),
    )
    monkeypatch.setattr(normalize_page, "NormalizeWorker", _FakeNormalizeWorker)
    monkeypatch.setattr(roles_page, "ExportSegmentsWorker", _FakeExportSegmentsWorker)
    monkeypatch.setattr(cli, "_build_output_dir", lambda *_args, **_kwargs: output_dir)

    window = MainWindow()
    qtbot.addWidget(window)
    render_widget(window, 1180, 760, scale=1.0)

    qtbot.mouseClick(window._normalize_page._btn_browse, QtCore.Qt.MouseButton.LeftButton)
    window._normalize_page._llm_normalize.setChecked(True)
    qtbot.mouseClick(window._normalize_page._btn_run, QtCore.Qt.MouseButton.LeftButton)

    assert window._tabs.currentIndex() == 1
    assert captured_normalize["llm_normalize"] is True
    assert captured_normalize["book_language"] == "ru"
    assert "wsl" not in captured_normalize["llm_endpoint"].lower()
    assert window._roles_page._btn_extract.isEnabled()
    assert window._roles_page._llm_model.text() == captured_normalize["llm_model"]

    qtbot.mouseClick(window._roles_page._btn_extract, QtCore.Qt.MouseButton.LeftButton)

    assert captured_segments["speaker_mode"] == "llm"
    assert captured_segments["output_dir"] == output_dir
    assert "wsl" not in captured_segments["llm_endpoint"].lower()
    assert window._tabs.currentIndex() == 2
    assert window._roles_page._table.rowCount() == 1
    assert window._voices_page._voice_table.get_segments()[0]["speaker"] == "Маргарита"
    assert (output_dir / "roles_manifest.json").exists()


def test_main_window_auto_pipeline_runs_all_steps_with_quality_settings(
    qapp,
    qtbot,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    book_path = tmp_path / "overnight.txt"
    book_path.write_text("Alice said hello.", encoding="utf-8")
    output_dir = tmp_path / "overnight_out"
    captured_normalize: dict = {}
    captured_roles: dict = {}
    captured_tts: dict = {}
    captured_assembly: dict = {}
    captured_production: dict = {}

    class _FakeNormalizeWorker:
        def __init__(self, **kwargs):
            captured_normalize.update(kwargs)
            self.progress = _Signal()
            self.progress_pct = _Signal()
            self.finished = _Signal()
            self.error = _Signal()

        def start(self) -> None:
            book = Book(
                metadata=Metadata(
                    language=captured_normalize["book_language"],
                    extra={
                        "llm_processing_enabled": True,
                        "llm_model_candidates": [captured_normalize["llm_model"]],
                    },
                ),
                chapters=[
                    Chapter(
                        title="Chapter 1",
                        index=0,
                        paragraphs=[
                            Paragraph(
                                raw_text="Alice said hello.",
                                normalized_text="Alice said hello.",
                            ),
                        ],
                    ),
                ],
            )
            self.finished.emit(book)

    class _FakeExportSegmentsWorker:
        def __init__(self, **kwargs):
            captured_roles.update(kwargs)
            self.progress = _Signal()
            self.finished = _Signal()
            self.error = _Signal()

        def start(self) -> None:
            manifest_path = captured_roles["output_dir"] / "segments_manifest.json"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(
                json.dumps(
                    [
                        {
                            "segment_index": 0,
                            "chapter_index": 0,
                            "language": "en",
                            "role": "alice",
                            "speaker": "Alice",
                            "character_description": "Main speaker.",
                            "is_dialogue": True,
                            "emotion": "calm",
                            "intonation": "calm",
                            "voice_id": "female_warm",
                            "text": "Alice said hello.",
                        }
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            self.finished.emit(str(manifest_path))

    class _FakeTTSWorker:
        def __init__(self, **kwargs):
            captured_tts.update(kwargs)
            self.progress = _Signal()
            self.status = _Signal()
            self.log_line = _Signal()
            self.finished = _Signal()
            self.error = _Signal()
            self.cancelled = False

        def start(self) -> None:
            audio_dir = captured_tts["output_dir"] / "audio_chunks"
            audio_dir.mkdir(parents=True, exist_ok=True)
            audio_path = audio_dir / "chapter_001" / "chunk_001_narrator.wav"
            audio_path.parent.mkdir(parents=True, exist_ok=True)
            audio_path.write_bytes(b"RIFF$\x00\x00\x00WAVEfmt ")
            manifest_path = captured_tts["manifest_path"]
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            chunk = manifest["chapters"][0]["chunks"][0]
            chunk["synthesized"] = True
            chunk["audio_file"] = str(audio_path)
            chunk["asr_qa"] = {"status": "passed"}
            chunk["qa_status"] = "passed"
            chunk["perceptual_qa"] = {"status": "passed"}
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            self.finished.emit(str(audio_dir), 1, 0)

        def cancel(self) -> None:
            self.cancelled = True

    class _FakeAssemblyWorker:
        def __init__(
            self,
            audio_dir,
            output_dir,
            pause_same,
            pause_change,
            manifest_path=None,
            parent=None,
        ):
            captured_assembly.update(
                {
                    "audio_dir": audio_dir,
                    "output_dir": output_dir,
                    "pause_same": pause_same,
                    "pause_change": pause_change,
                    "manifest_path": manifest_path,
                    "parent": parent,
                }
            )
            self.progress = _Signal()
            self.finished = _Signal()
            self.error = _Signal()

        def start(self) -> None:
            (captured_assembly["output_dir"] / "chapter_001.wav").write_bytes(b"RIFF$\x00\x00\x00WAVEfmt ")
            self.finished.emit("Chapter 001: 1 chunks -> 1.0s")

    class _FakeProductionWorker:
        def __init__(self, manifest_path, output_dir, **kwargs):  # noqa: ANN001
            captured_production.update(
                {
                    "manifest_path": manifest_path,
                    "output_dir": output_dir,
                    **kwargs,
                }
            )
            self.progress = _Signal()
            self.finished = _Signal()
            self.error = _Signal()

        def start(self) -> None:
            self.finished.emit("Production report: done")

    monkeypatch.setattr(normalize_page, "NormalizeWorker", _FakeNormalizeWorker)
    monkeypatch.setattr(roles_page, "ExportSegmentsWorker", _FakeExportSegmentsWorker)
    monkeypatch.setattr(synthesis_page, "TTSSynthesisWorker", _FakeTTSWorker)
    monkeypatch.setattr(assembly_page, "AssemblyWorker", _FakeAssemblyWorker)
    monkeypatch.setattr(assembly_page, "ProductionPreflightWorker", _FakeProductionWorker)
    monkeypatch.setattr(cli, "_build_output_dir", lambda *_args, **_kwargs: output_dir)

    window = MainWindow()
    qtbot.addWidget(window)
    render_widget(window, 1180, 760, scale=1.0)
    window._normalize_page._selected_path = str(book_path)
    window._normalize_page._path_label.setText(str(book_path))
    window._normalize_page._btn_run.setEnabled(True)
    monkeypatch.setattr(window, "_ask_auto_pipeline_cache_choice", lambda _source: "restore")

    qtbot.mouseClick(window._btn_auto_pipeline, QtCore.Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: not window._auto_pipeline_active, timeout=2000)

    assert captured_normalize["llm_normalize"] is True
    assert captured_normalize["ocr_mode"] == "compare"
    assert captured_normalize["ocr_dpi"] == 600
    assert captured_normalize["ocr_psm"] == 6
    assert captured_roles["speaker_mode"] == "llm"
    assert captured_roles["stress_mode"] == "double_vowel"

    chunks_manifest = json.loads(
        (output_dir / "chunks_manifest_v2.json").read_text(encoding="utf-8")
    )
    assert chunks_manifest["max_chunk_chars"] == 400
    assert chunks_manifest["chapters"][0]["chunks"][0]["text"] == "Alice said hello."

    assert captured_tts["manifest_path"] == output_dir / "chunks_manifest_v2.json"
    assert captured_tts["model"] == "qwen3-customvoice-1.7b"
    assert captured_tts["batch_size"] == 1
    assert captured_tts["chunk_timeout"] == 900
    assert captured_tts["merge_chapters"] is True
    assert captured_tts["output_format"] == "wav"
    assert captured_tts["max_new_tokens"] == 4096
    assert captured_tts["asr_qa_after_synthesis"] is True

    assert captured_assembly["manifest_path"] == output_dir / "chunks_manifest_v2.json"
    assert captured_assembly["output_dir"] == output_dir
    assert captured_assembly["pause_same"] == 300
    assert captured_assembly["pause_change"] == 600
    assert captured_production["manifest_path"] == output_dir / "chunks_manifest_v2.json"
    assert captured_production["output_dir"] == output_dir
    assert captured_production["package_outputs"] is True
    assert captured_production["chapter_audio_dir"] == output_dir
    assert captured_production["dry_run_package"] is False
    assert captured_production["allow_review_package"] is False
    assert window._tabs.currentIndex() == 4
    assert window._btn_auto_pipeline.isEnabled()
    assert window.statusBar().currentMessage() == t("auto.complete")


def test_main_window_auto_pipeline_reuses_cached_chunks_manifest(
    qapp,
    qtbot,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "cached_out"
    output_dir.mkdir()
    audio_path = output_dir / "audio_chunks" / "chapter_001" / "chunk_001_narrator.wav"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"RIFF$\x00\x00\x00WAVEfmt ")
    segments_path = output_dir / "segments_manifest.json"
    roles_path = output_dir / "roles_manifest.json"
    segments_path.write_text(
        json.dumps(
            [
                {
                    "segment_index": 0,
                    "chapter_index": 0,
                    "role": "narrator",
                    "voice_id": "narrator_calm",
                    "text": "Cached line.",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    roles_path.write_text('{"roles": []}', encoding="utf-8")
    chunks_path = output_dir / "chunks_manifest_v2.json"
    chunks_path.write_text(
        json.dumps(
            {
                "version": 2,
                "book_title": "Cached",
                "language": "en",
                "chapters": [
                    {
                        "chapter_index": 0,
                        "chunks": [
                            {
                                "chapter_index": 0,
                                "chunk_index": 0,
                                "voice_label": "narrator",
                                "voice_id": "narrator_calm",
                                "text": "Cached line.",
                                "synthesized": True,
                                "audio_file": str(audio_path),
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    captured_assembly: dict = {}
    captured_production: dict = {}
    captured_quality: dict = {}

    class _FakeAssemblyWorker:
        def __init__(
            self,
            audio_dir,
            output_dir,
            pause_same,
            pause_change,
            manifest_path=None,
            parent=None,
        ):
            captured_assembly.update(
                {
                    "audio_dir": audio_dir,
                    "output_dir": output_dir,
                    "pause_same": pause_same,
                    "pause_change": pause_change,
                    "manifest_path": manifest_path,
                    "parent": parent,
                }
            )
            self.progress = _Signal()
            self.finished = _Signal()
            self.error = _Signal()

        def start(self) -> None:
            (captured_assembly["output_dir"] / "chapter_001.wav").write_bytes(b"RIFF$\x00\x00\x00WAVEfmt ")
            self.finished.emit("Chapter 001: 1 chunks -> 1.0s")

    class _FakeProductionWorker:
        def __init__(self, manifest_path, output_dir, **kwargs):  # noqa: ANN001
            captured_production.update(
                {
                    "manifest_path": manifest_path,
                    "output_dir": output_dir,
                    **kwargs,
                }
            )
            self.progress = _Signal()
            self.finished = _Signal()
            self.error = _Signal()

        def start(self) -> None:
            self.finished.emit("Production report: done")

    monkeypatch.setattr(assembly_page, "AssemblyWorker", _FakeAssemblyWorker)
    monkeypatch.setattr(assembly_page, "ProductionPreflightWorker", _FakeProductionWorker)

    window = MainWindow()
    qtbot.addWidget(window)
    window._output_dir = output_dir
    window._auto_pipeline_active = True
    window._btn_auto_pipeline.setEnabled(False)
    monkeypatch.setattr(
        window._voices_page,
        "_build_tts_chunks",
        lambda: (_ for _ in ()).throw(AssertionError("chunks should come from cache")),
    )
    monkeypatch.setattr(
        window._synthesis_page,
        "_start_synthesis",
        lambda: (_ for _ in ()).throw(AssertionError("complete cached audio should skip synthesis")),
    )

    def fake_start_asr_qa_worker(pending_finish=None):  # noqa: ANN001
        captured_quality["pending_finish"] = pending_finish
        manifest = json.loads(chunks_path.read_text(encoding="utf-8"))
        chunk = manifest["chapters"][0]["chunks"][0]
        chunk["asr_qa"] = {"status": "passed"}
        chunk["qa_status"] = "passed"
        chunk["perceptual_qa"] = {"status": "passed"}
        chunks_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        if pending_finish is not None:
            window._synthesis_page.synthesis_finished.emit(*pending_finish)

    monkeypatch.setattr(
        window._synthesis_page,
        "_start_asr_qa_worker",
        fake_start_asr_qa_worker,
    )

    window._on_roles_segments_ready(str(segments_path), str(roles_path))
    qtbot.waitUntil(lambda: not window._auto_pipeline_active, timeout=2000)

    assert captured_quality["pending_finish"] == (str(output_dir / "audio_chunks"), 0, 0)
    assert captured_assembly["manifest_path"] == chunks_path
    assert captured_assembly["output_dir"] == output_dir
    assert captured_production["manifest_path"] == chunks_path
    assert captured_production["output_dir"] == output_dir
    assert captured_production["package_outputs"] is True
    assert captured_production["dry_run_package"] is False
    assert captured_production["allow_review_package"] is False
    assert window.statusBar().currentMessage() == t("auto.complete")
    cached_manifest = json.loads(chunks_path.read_text(encoding="utf-8"))
    assert cached_manifest["chapters"][0]["chunks"][0]["audio_file"] == str(audio_path)


def test_main_window_auto_pipeline_fresh_choice_ignores_cached_chunks_manifest(
    qapp,
    qtbot,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "cached_out"
    output_dir.mkdir()
    segments_path = output_dir / "segments_manifest.json"
    roles_path = output_dir / "roles_manifest.json"
    segments_path.write_text(
        json.dumps(
            [
                {
                    "segment_index": 0,
                    "chapter_index": 0,
                    "role": "narrator",
                    "voice_id": "narrator_calm",
                    "text": "Cached line.",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    roles_path.write_text('{"roles": []}', encoding="utf-8")
    (output_dir / "chunks_manifest_v2.json").write_text(
        json.dumps(
            {
                "version": 2,
                "book_title": "Cached",
                "language": "en",
                "chapters": [{"chapter_index": 0, "chunks": []}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    built: dict[str, bool] = {}

    window = MainWindow()
    qtbot.addWidget(window)
    window._output_dir = output_dir
    window._auto_pipeline_active = True
    window._auto_pipeline_cache_choice = "fresh"
    monkeypatch.setattr(
        window._voices_page,
        "_build_tts_chunks",
        lambda: built.update({"called": True}),
    )

    window._on_roles_segments_ready(str(segments_path), str(roles_path))

    assert built["called"] is True


def test_main_window_auto_pipeline_requires_selected_book(qapp, qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    qtbot.mouseClick(window._btn_auto_pipeline, QtCore.Qt.MouseButton.LeftButton)

    assert window.statusBar().currentMessage() == t("auto.need_file")
    assert window._normalize_page._btn_browse.property("attention") is True
    qtbot.waitUntil(
        lambda: window._normalize_page._btn_browse.property("attention") is False,
        timeout=2000,
    )
    assert not window._auto_pipeline_active


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


def test_voice_save_and_build_actions_report_completion(
    qapp,
    qtbot,
    tmp_path: Path,
) -> None:
    manifest_path = _write_manifest(tmp_path / "segments_manifest.json")
    output_dir = tmp_path / "out"
    book = Book(
        chapters=[
            Chapter(
                title="Chapter 1",
                paragraphs=[
                    Paragraph(
                        raw_text="Alpha beta gamma.",
                        normalized_text="Alpha beta gamma.",
                    ),
                ],
                index=0,
            )
        ],
        metadata=Metadata(title="Button Coverage", language="en"),
    )

    page = VoicesPage()
    qtbot.addWidget(page)
    page.set_book(book, output_dir)
    page.load_segments_manifest(manifest_path)
    render_widget(page, 1180, 760, scale=1.0)

    qtbot.mouseClick(page._btn_save, QtCore.Qt.MouseButton.LeftButton)
    assert not page._btn_save.isEnabled()
    qtbot.waitUntil(lambda: page._save_worker is None, timeout=5000)
    assert t("voice.saved", path=str(manifest_path)) in page._action_status.text()
    assert page._action_status.isVisible()

    built: list[str] = []
    page.chunks_built.connect(built.append)
    qtbot.mouseClick(page._btn_build, QtCore.Qt.MouseButton.LeftButton)
    assert not page._btn_build.isEnabled()
    qtbot.waitUntil(lambda: page._build_worker is None, timeout=5000)

    chunks_path = output_dir / "chunks_manifest_v2.json"
    assert built == [str(chunks_path)]
    assert chunks_path.exists()
    assert "TTS" in page._action_status.text()
    assert str(chunks_path) in page._action_status.text()


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
