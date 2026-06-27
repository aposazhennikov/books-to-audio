from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

QtWidgets = pytest.importorskip("PyQt6.QtWidgets")
QApplication = QtWidgets.QApplication

progress_widget = pytest.importorskip("book_normalizer.gui.widgets.progress_widget")
i18n = pytest.importorskip("book_normalizer.gui.i18n")

ProgressWidget = progress_widget.ProgressWidget
set_language = i18n.set_language


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def reset_language():
    set_language("ru")
    yield
    set_language("ru")


@pytest.mark.parametrize("lang", ["ru", "en", "zh", "kk", "uz"])
def test_progress_widget_shows_elapsed_eta_and_remaining_in_all_locales(
    qapp,
    monkeypatch,
    lang: str,
) -> None:
    now = {"value": 100.0}
    monkeypatch.setattr(progress_widget, "monotonic", lambda: now["value"])
    set_language(lang)
    widget = ProgressWidget()

    widget.set_progress(2, 10, "1m 20s")

    assert progress_widget._ELAPSED_LABELS[lang] in widget._eta.text()
    assert progress_widget._ETA_LABELS[lang] in widget._eta.text()
    assert "0" in widget._eta.text()
    assert "1m 20s" in widget._eta.text()
    assert progress_widget._remaining_chunks_text(8) in widget._status.text()

    widget.deleteLater()


def test_progress_widget_elapsed_clock_keeps_running_in_busy_mode(
    qapp,
    monkeypatch,
) -> None:
    now = {"value": 100.0}
    monkeypatch.setattr(progress_widget, "monotonic", lambda: now["value"])
    set_language("en")
    widget = ProgressWidget()

    widget.set_busy("Waiting for local LLM")
    assert widget._eta.text() == "Elapsed: 0s"

    now["value"] = 165.0
    widget._refresh_time_label()

    assert widget._eta.text() == "Elapsed: 1m 05s"
    assert widget._bar.maximum() == 0

    widget.set_status("Done")
    assert widget._eta.text() == ""
    assert not widget._bar_row.isVisible()

    widget.deleteLater()


def test_progress_widget_status_updates_do_not_reset_determinate_progress(
    qapp,
    monkeypatch,
) -> None:
    now = {"value": 100.0}
    monkeypatch.setattr(progress_widget, "monotonic", lambda: now["value"])
    widget = ProgressWidget()

    widget.set_progress(4, 142, "10m 00s")
    widget.set_busy("OCR: recognizing page 5/142, segment 1/1...")

    assert widget._status.text() == "OCR: recognizing page 5/142, segment 1/1..."
    assert widget._bar.maximum() == 142
    assert widget._bar.value() == 4
    assert "10m 00s" in widget._eta.text()

    widget.deleteLater()
