from __future__ import annotations

from PyQt6.QtWidgets import QApplication

from book_normalizer.gui.main_window import MainWindow
from book_normalizer.gui.resources import application_icon, asset_path


def test_application_icon_asset_loads(qapp) -> None:
    svg_icon_path = asset_path("icon.svg")
    ico_icon_path = asset_path("icon.ico")

    assert svg_icon_path.exists()
    assert ico_icon_path.exists()
    assert not application_icon().pixmap(64, 64).isNull()


def test_application_and_main_window_use_book_icon(qapp, qtbot) -> None:
    app = QApplication.instance()
    assert app is not None
    app.setWindowIcon(application_icon())

    window = MainWindow()
    qtbot.addWidget(window)

    assert not app.windowIcon().pixmap(64, 64).isNull()
    assert not window.windowIcon().pixmap(64, 64).isNull()
