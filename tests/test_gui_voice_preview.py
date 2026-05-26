from __future__ import annotations

import os
import sys
import wave
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

QtCore = pytest.importorskip("PyQt6.QtCore")
QtWidgets = pytest.importorskip("PyQt6.QtWidgets")
voice_preview = pytest.importorskip("book_normalizer.gui.widgets.voice_preview")
GeneratePreviewsWorker = voice_preview.GeneratePreviewsWorker
VoicePreviewPanel = voice_preview.VoicePreviewPanel


@pytest.fixture
def qapp():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app


class _Signal:
    def __init__(self) -> None:
        self.callbacks = []

    def connect(self, callback):  # noqa: ANN001
        self.callbacks.append(callback)

    def emit(self, *args):  # noqa: ANN002
        for callback in self.callbacks:
            callback(*args)


def _install_fake_tts_modules(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict:
    captured: dict = {}

    torch_mod = ModuleType("torch")
    torch_mod.bfloat16 = "bfloat16"
    torch_mod.float32 = "float32"
    torch_mod.cuda = SimpleNamespace(is_available=lambda: False)

    sf_mod = ModuleType("soundfile")

    def fake_write(path: str, _samples, sample_rate: int) -> None:  # noqa: ANN001
        with wave.open(path, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(b"\x00\x00" * 120)

    sf_mod.write = fake_write

    qwen_mod = ModuleType("qwen_tts")

    class _FakeModel:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):  # noqa: ANN002, ANN003
            captured["from_pretrained"] = {"args": args, "kwargs": kwargs}
            return cls()

        def generate_custom_voice(self, **kwargs):  # noqa: ANN003
            captured.setdefault("generated", []).append(kwargs)
            return [[0.0] * 120], 24000

    qwen_mod.Qwen3TTSModel = _FakeModel

    monkeypatch.setitem(sys.modules, "torch", torch_mod)
    monkeypatch.setitem(sys.modules, "soundfile", sf_mod)
    monkeypatch.setitem(sys.modules, "qwen_tts", qwen_mod)
    monkeypatch.setattr(voice_preview, "check_tts_python", lambda: (True, sys.executable))
    monkeypatch.setattr(voice_preview, "default_comfyui_models_dir", lambda: tmp_path / "models")
    monkeypatch.setattr(
        voice_preview,
        "describe_model_resolution",
        lambda model, *, models_dir: (str(models_dir / model.replace("/", "_")), True),
    )
    return captured


def test_voice_preview_worker_generates_inside_app_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = Path("src/book_normalizer/gui/widgets/voice_preview.py").read_text(
        encoding="utf-8"
    )
    assert "subprocess" not in source
    assert "generate_voice_previews.py" not in source

    captured = _install_fake_tts_modules(monkeypatch, tmp_path)
    worker = GeneratePreviewsWorker(
        tmp_path / "previews",
        "Preview text.",
        ["narrator_calm"],
        model="Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    )
    progress: list[str] = []
    done: list[str] = []
    finished: list[tuple[int, int, str]] = []
    errors: list[str] = []
    worker.progress_line.connect(progress.append)
    worker.voice_done.connect(done.append)
    worker.finished_ok.connect(lambda generated, total, elapsed: finished.append((generated, total, elapsed)))
    worker.error.connect(errors.append)

    worker.run()

    assert errors == []
    assert done == ["narrator_calm"]
    assert finished and finished[0][:2] == (1, 1)
    assert (tmp_path / "previews" / "narrator_calm.wav").exists()
    assert captured["from_pretrained"]["kwargs"]["device_map"] == "cpu"
    generated = captured["generated"][0]
    assert generated["text"] == "Preview text."
    assert generated["speaker"] == "Aiden"
    assert "Спокойный" in generated["instruct"]
    assert any("1/1" in line for line in progress)


def test_voice_preview_worker_reports_missing_runtime(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        voice_preview,
        "check_tts_python",
        lambda: (False, "missing Python packages: qwen_tts"),
    )
    worker = GeneratePreviewsWorker(tmp_path, "Text", ["narrator_calm"])
    errors: list[str] = []
    worker.error.connect(errors.append)

    worker.run()

    assert errors == ["missing Python packages: qwen_tts"]


def test_voice_preview_panel_generate_button_starts_worker(
    qapp,
    qtbot,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    class _FakeWorker:
        def __init__(self, out_dir, text, voice_ids, model="", parent=None):  # noqa: ANN001
            captured.update(
                {
                    "out_dir": out_dir,
                    "text": text,
                    "voice_ids": voice_ids,
                    "model": model,
                    "parent": parent,
                }
            )
            self.progress_line = _Signal()
            self.progress_pct = _Signal()
            self.voice_done = _Signal()
            self.finished_ok = _Signal()
            self.attn_info = _Signal()
            self.error = _Signal()

        def start(self) -> None:
            self.finished_ok.emit(1, 1, "0s")

    monkeypatch.setattr(voice_preview, "GeneratePreviewsWorker", _FakeWorker)
    panel = VoicePreviewPanel()
    qtbot.addWidget(panel)
    panel._dir_input.setText(str(tmp_path / "previews"))
    panel._phrase_input.setPlainText("Hello preview.")
    for card in panel._cards:
        card._checkbox.setChecked(False)
    panel._cards[0]._checkbox.setChecked(True)

    qtbot.mouseClick(panel._btn_generate, QtCore.Qt.MouseButton.LeftButton)

    assert captured["out_dir"] == tmp_path / "previews"
    assert captured["text"] == "Hello preview."
    assert captured["voice_ids"] == [panel._cards[0].preset.id]
    assert panel._btn_generate.isEnabled()
