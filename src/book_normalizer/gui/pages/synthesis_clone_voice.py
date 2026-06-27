"""Voice clone row widget for the synthesis page."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from book_normalizer.gui.i18n import t
from book_normalizer.gui.ui_scaler import apply_combo_content_width


def _make_combo_compact(combo: QComboBox, min_chars: int = 18) -> None:
    """Keep combo width tied to its own items instead of the parent row."""
    apply_combo_content_width(combo, empty_min_chars=min_chars)
    if combo.isEditable():
        line_edit = combo.lineEdit()
        if line_edit is not None:
            line_edit.setAlignment(line_edit.alignment() | Qt.AlignmentFlag.AlignVCenter)
            line_edit.setMinimumHeight(0)


class _CloneVoiceRow(QWidget):
    """A single voice clone entry: voice_id selector + WAV path + transcript."""

    # Emitted just before the widget is destroyed so the parent can update its list.
    about_to_remove: pyqtSignal = pyqtSignal(object)

    def __init__(self, voice_ids: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui(voice_ids)
        self.retranslate()

    def _build_ui(self, voice_ids: list[str]) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(4)

        # Row 1: voice selector + WAV picker.
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        self._voice_combo = QComboBox()
        self._voice_combo.addItems(voice_ids)
        self._voice_combo.setMinimumWidth(128)
        _make_combo_compact(self._voice_combo, min_chars=14)
        row1.addWidget(self._voice_combo)

        self._wav_edit = QLineEdit()
        self._wav_edit.setPlaceholderText("reference.wav")
        self._wav_edit.setReadOnly(True)
        self._wav_edit.setStyleSheet(
            "color: #1e293b; font-size: 11px; padding: 4px 6px;"
            "background: rgba(255,255,255,0.92); border-radius: 6px;"
            "border: 1px solid rgba(91,115,142,0.18);",
        )
        row1.addWidget(self._wav_edit, stretch=1)

        self._btn_wav = QPushButton()
        self._btn_wav.setMaximumWidth(92)
        self._btn_wav.clicked.connect(self._browse_wav)
        row1.addWidget(self._btn_wav)

        self._btn_remove = QPushButton()
        self._btn_remove.setMaximumWidth(34)
        self._btn_remove.setStyleSheet(
            "QPushButton { color: #b91c1c; font-weight: 700;"
            "background: rgba(254,226,226,0.82); border: 1px solid rgba(248,113,113,0.24);"
            "border-radius: 7px; padding: 2px; }"
            "QPushButton:hover { color: #7f1d1d; background: rgba(254,202,202,0.96); }",
        )
        self._btn_remove.clicked.connect(self._on_remove)
        row1.addWidget(self._btn_remove)

        layout.addLayout(row1)

        # Row 2: transcript text field.
        self._transcript = QLineEdit()
        self._transcript.setStyleSheet(
            "color: #1e293b; font-size: 11px; padding: 4px 6px;"
            "background: rgba(255,255,255,0.92); border-radius: 6px;"
            "border: 1px solid rgba(91,115,142,0.18);",
        )
        layout.addWidget(self._transcript)

    def _browse_wav(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("synth.select_reference_audio"),
            "",
            "Audio (*.wav *.mp3 *.flac *.ogg);;All (*)",
        )
        if path:
            self._wav_edit.setText(path)

    def _on_remove(self) -> None:
        # Notify parent page to remove this row from its tracking list
        # BEFORE setParent(None) destroys the C++ object reference.
        self.about_to_remove.emit(self)
        self.setParent(None)  # type: ignore[arg-type]
        self.deleteLater()

    def get_voice_id(self) -> str:
        """Return the selected voice preset ID."""
        return self._voice_combo.currentText()

    def get_wav_path(self) -> str:
        """Return the selected WAV file path."""
        return self._wav_edit.text().strip()

    def get_transcript(self) -> str:
        """Return the reference transcript."""
        return self._transcript.text().strip()

    def is_valid(self) -> bool:
        """Return True when both WAV path and transcript are filled in."""
        return bool(self.get_wav_path() and self.get_transcript())

    def retranslate(self) -> None:
        """Update translatable placeholder text."""
        self._btn_wav.setText(t("synth.choose_file"))
        self._btn_remove.setText("x")
        self._btn_remove.setToolTip(t("synth.clone_remove_voice"))
        self._transcript.setPlaceholderText(t("synth.clone_transcript_ph"))
