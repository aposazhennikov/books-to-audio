"""Voice preview panel — audition voices with Play buttons."""

from __future__ import annotations

import subprocess
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from book_normalizer.gui.i18n import get_language, t
from book_normalizer.gui.voice_presets import VOICE_PRESETS, VoicePreset

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_SCRIPT_PATH = _PROJECT_ROOT / "scripts" / "generate_voice_previews.py"
_DEFAULT_PREVIEW_DIR = _PROJECT_ROOT / "voice_previews"

_STYLE_STATUS_NORMAL = (
    "color: rgba(255,255,255,0.5); font-size: 11px;"
    "background: transparent; border: none; padding: 2px 0;"
)
_STYLE_STATUS_ACTIVE = (
    "color: rgba(124,92,252,0.8); font-size: 11px;"
    "background: transparent; border: none; padding: 2px 0;"
)
_STYLE_STATUS_OK = (
    "color: rgba(0,184,148,0.9); font-size: 12px;"
    "background: transparent; border: none; padding: 2px 0;"
)
_STYLE_STATUS_ERR = (
    "color: rgba(231,76,60,0.9); font-size: 12px;"
    "background: rgba(231,76,60,0.08);"
    "border: 1px solid rgba(231,76,60,0.2);"
    "border-radius: 6px; padding: 6px 8px;"
)


def _to_wsl(path: Path) -> str:
    """Convert Windows path to WSL path."""
    p = str(path.resolve()).replace("\\", "/")
    if len(p) >= 2 and p[1] == ":":
        drive = p[0].lower()
        p = f"/mnt/{drive}{p[2:]}"
    return p


class GeneratePreviewsWorker(QThread):
    """Background worker — streams WSL TTS output line by line."""

    progress_line = pyqtSignal(str)
    progress_pct = pyqtSignal(int, int, str)
    voice_done = pyqtSignal(str)
    finished_ok = pyqtSignal(int, int, str)
    attn_info = pyqtSignal(str, str)
    error = pyqtSignal(str)

    def __init__(
        self,
        out_dir: Path,
        text: str,
        voice_ids: list[str],
        model: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self._out_dir = out_dir
        self._text = text
        self._voice_ids = voice_ids
        self._model = model or "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"

    def run(self) -> None:
        try:
            wsl_script = _to_wsl(_SCRIPT_PATH)
            wsl_out = _to_wsl(self._out_dir)

            safe_text = self._text.replace("'", "'\\''")
            ids_arg = ",".join(self._voice_ids)
            cmd = [
                "wsl", "-e", "bash", "-c",
                f"source ~/venvs/qwen3tts/bin/activate && "
                f"python '{wsl_script}' "
                f"--out '{wsl_out}' "
                f"--model '{self._model}' "
                f"--ids '{ids_arg}' "
                f"--text '{safe_text}'",
            ]

            self.progress_line.emit(t("voice.gen_loading"))

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            for raw in proc.stdout:
                line = raw.strip()
                if not line:
                    continue

                if line.startswith("PROGRESS|"):
                    self._parse_progress(line)
                elif line.startswith("FINISHED|"):
                    self._parse_finished(line)
                elif line.startswith("LOADING_MODEL"):
                    self.progress_line.emit(t("voice.gen_loading"))
                elif line.startswith("MODEL_READY"):
                    self.progress_line.emit("Model loaded. Generating...")
                elif line.startswith("ATTN_INFO|"):
                    parts = line.split("|")
                    if len(parts) >= 3:
                        self.attn_info.emit(parts[1], parts[2])
                elif line.startswith("ERROR|"):
                    self.error.emit(line[6:])
                    return
                else:
                    self.progress_line.emit(line[:150])

            proc.wait(timeout=30)
            if proc.returncode != 0:
                self.error.emit(
                    f"Process exited with code {proc.returncode}"
                )

        except subprocess.TimeoutExpired:
            self.error.emit("Timeout: generation took too long")
        except Exception as exc:
            self.error.emit(str(exc))

    def _parse_progress(self, line: str) -> None:
        """Parse PROGRESS|done|total|elapsed|name|status."""
        parts = line.split("|")
        if len(parts) < 6:
            return
        done, total = int(parts[1]), int(parts[2])
        elapsed = float(parts[3])
        name = parts[4]
        status = parts[5]

        if done > 0 and elapsed > 0:
            avg = elapsed / done
            remaining = avg * (total - done)
            eta = self._fmt_time(remaining)
        else:
            eta = "..."

        self.progress_pct.emit(done, total, eta)
        self.progress_line.emit(
            t(
                "voice.gen_progress",
                done=done, total=total, name=name, eta=eta,
            )
        )
        if status in ("done", "skipped"):
            self.voice_done.emit(name)

    def _parse_finished(self, line: str) -> None:
        """Parse FINISHED|generated|total|elapsed."""
        parts = line.split("|")
        if len(parts) < 4:
            return
        generated, total = int(parts[1]), int(parts[2])
        elapsed_str = self._fmt_time(float(parts[3]))
        self.finished_ok.emit(generated, total, elapsed_str)

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        """Format seconds as human-readable string."""
        m, s = divmod(int(seconds), 60)
        if m > 0:
            return f"{m}m {s}s"
        return f"{s}s"


class VoiceCard(QWidget):
    """Single voice card with checkbox, status badge, and Play button."""

    def __init__(self, preset: VoicePreset, preview_dir: Path, parent=None):
        super().__init__(parent)
        self.preset = preset
        self._preview_dir = preview_dir
        self._player: QMediaPlayer | None = None
        self._audio_output: QAudioOutput | None = None
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setObjectName("voiceCard")
        self.setStyleSheet(
            "#voiceCard {"
            "  background: rgba(255,255,255,0.04);"
            "  border: 1px solid rgba(255,255,255,0.08);"
            "  border-radius: 10px; padding: 4px;"
            "}"
            "#voiceCard:hover {"
            "  background: rgba(124,92,252,0.08);"
            "  border-color: rgba(124,92,252,0.25);"
            "}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # Checkbox for selection.
        self._checkbox = QCheckBox()
        self._checkbox.setChecked(True)
        self._checkbox.setStyleSheet(
            "QCheckBox::indicator {"
            "  width: 16px; height: 16px; border-radius: 3px;"
            "  border: 1px solid rgba(255,255,255,0.2);"
            "  background: rgba(255,255,255,0.04);"
            "}"
            "QCheckBox::indicator:checked {"
            "  background: rgba(124,92,252,0.6);"
            "  border-color: rgba(124,92,252,0.8);"
            "}"
            "QCheckBox::indicator:hover {"
            "  border-color: rgba(124,92,252,0.5);"
            "}"
        )
        layout.addWidget(self._checkbox)

        # Info block.
        info = QVBoxLayout()
        info.setSpacing(1)

        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        lang = get_language()
        label_text = (
            self.preset.label_ru if lang == "ru" else self.preset.label_en
        )
        self._label = QLabel(label_text)
        self._label.setStyleSheet(
            "font-size: 13px; font-weight: 700; color: #e0e0e0;"
            "background: transparent; border: none;"
        )
        top_row.addWidget(self._label)

        # Status badge.
        self._status_badge = QLabel()
        self._status_badge.setStyleSheet(
            "font-size: 9px; font-weight: 700;"
            "padding: 1px 6px; border-radius: 4px;"
            "background: transparent; border: none;"
        )
        top_row.addWidget(self._status_badge)
        top_row.addStretch()
        info.addLayout(top_row)

        desc = (
            self.preset.description_ru
            if lang == "ru"
            else self.preset.description_en
        )
        self._desc = QLabel(desc)
        self._desc.setStyleSheet(
            "color: rgba(255,255,255,0.35); font-size: 10px;"
            "background: transparent; border: none;"
        )
        self._desc.setWordWrap(True)
        info.addWidget(self._desc)

        self._speaker_lbl = QLabel(f"speaker: {self.preset.speaker}")
        self._speaker_lbl.setStyleSheet(
            "color: rgba(124,92,252,0.55); font-size: 9px;"
            "font-weight: 600; background: transparent; border: none;"
        )
        info.addWidget(self._speaker_lbl)

        layout.addLayout(info, stretch=1)

        # Play button.
        self._btn_play = QPushButton("\u25B6")
        self._btn_play.setFixedSize(32, 32)
        self._btn_play.setObjectName("playBtn")
        self._btn_play.setStyleSheet(
            "#playBtn {"
            "  font-size: 14px; border-radius: 16px;"
            "  background: rgba(124,92,252,0.15); color: #7c5cfc;"
            "  border: 1px solid rgba(124,92,252,0.25);"
            "}"
            "#playBtn:hover {"
            "  background: rgba(124,92,252,0.3); color: #fff;"
            "}"
            "#playBtn:disabled {"
            "  background: rgba(255,255,255,0.02);"
            "  color: rgba(255,255,255,0.12);"
            "  border-color: rgba(255,255,255,0.04);"
            "}"
        )
        self._btn_play.clicked.connect(self._play)
        self._btn_play.setEnabled(False)
        layout.addWidget(self._btn_play)

    @property
    def is_selected(self) -> bool:
        """Whether the checkbox is checked."""
        return self._checkbox.isChecked()

    def set_preview_dir(self, d: Path) -> None:
        """Update the directory where preview WAVs are stored."""
        self._preview_dir = d

    def refresh_status(self) -> None:
        """Update badge and play button based on WAV existence."""
        wav = self._preview_dir / f"{self.preset.id}.wav"
        exists = wav.exists()
        self._btn_play.setEnabled(exists)
        if exists:
            self._status_badge.setText("\u2713")
            self._status_badge.setStyleSheet(
                "font-size: 10px; font-weight: 700;"
                "padding: 1px 6px; border-radius: 4px;"
                "background: rgba(0,184,148,0.15);"
                "color: rgba(0,184,148,0.9);"
                "border: none;"
            )
            self._checkbox.setChecked(False)
        else:
            self._status_badge.setText("\u2014")
            self._status_badge.setStyleSheet(
                "font-size: 10px; font-weight: 700;"
                "padding: 1px 6px; border-radius: 4px;"
                "background: rgba(255,255,255,0.05);"
                "color: rgba(255,255,255,0.25);"
                "border: none;"
            )
            self._checkbox.setChecked(True)

    def retranslate(self) -> None:
        """Update labels for current language."""
        lang = get_language()
        self._label.setText(
            self.preset.label_ru if lang == "ru" else self.preset.label_en
        )
        self._desc.setText(
            self.preset.description_ru
            if lang == "ru"
            else self.preset.description_en
        )

    def _play(self) -> None:
        """Play the preview audio file."""
        wav_path = self._preview_dir / f"{self.preset.id}.wav"
        if not wav_path.exists():
            return

        if self._player is None:
            self._audio_output = QAudioOutput()
            self._player = QMediaPlayer()
            self._player.setAudioOutput(self._audio_output)
            self._player.playbackStateChanged.connect(
                self._on_state_changed,
            )

        playing = (
            self._player.playbackState()
            == QMediaPlayer.PlaybackState.PlayingState
        )
        if playing:
            self._player.stop()
            self._btn_play.setText("\u25B6")
            return

        self._player.setSource(QUrl.fromLocalFile(str(wav_path)))
        self._player.play()
        self._btn_play.setText("\u25A0")

    def _on_state_changed(self, state) -> None:
        if state == QMediaPlayer.PlaybackState.StoppedState:
            self._btn_play.setText("\u25B6")


class VoicePreviewPanel(QWidget):
    """Panel showing all voice presets with checkboxes, Play buttons,
    dir chooser, custom phrase input, and live generation progress."""

    voice_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: list[VoiceCard] = []
        self._card_by_id: dict[str, VoiceCard] = {}
        self._worker: GeneratePreviewsWorker | None = None
        self._preview_dir: Path = _DEFAULT_PREVIEW_DIR
        self._setup_ui()
        self._refresh_all()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        # Output directory row.
        dir_row = QHBoxLayout()
        dir_row.setSpacing(6)
        self._dir_label = QLabel()
        self._dir_label.setStyleSheet(
            "font-weight: 600; font-size: 11px;"
            "color: rgba(255,255,255,0.6);"
            "background: transparent; border: none;"
        )
        dir_row.addWidget(self._dir_label)

        self._dir_input = QLineEdit(str(self._preview_dir))
        self._dir_input.setMinimumHeight(28)
        dir_row.addWidget(self._dir_input, stretch=1)

        self._btn_browse = QPushButton()
        self._btn_browse.setMinimumHeight(28)
        self._btn_browse.clicked.connect(self._browse_dir)
        dir_row.addWidget(self._btn_browse)
        layout.addLayout(dir_row)

        # Preview phrase.
        self._phrase_label = QLabel()
        self._phrase_label.setStyleSheet(
            "font-weight: 600; font-size: 11px;"
            "color: rgba(255,255,255,0.6);"
            "background: transparent; border: none;"
            "padding-top: 2px;"
        )
        layout.addWidget(self._phrase_label)

        self._phrase_input = QTextEdit()
        self._phrase_input.setPlaceholderText(t("voice.default_phrase"))
        self._phrase_input.setMaximumHeight(48)
        self._phrase_input.setStyleSheet(
            "QTextEdit {"
            "  background: rgba(255,255,255,0.04);"
            "  border: 1px solid rgba(255,255,255,0.1);"
            "  border-radius: 6px; color: #d0d0d0;"
            "  font-size: 12px; padding: 4px 6px;"
            "}"
        )
        layout.addWidget(self._phrase_input)

        # Buttons row.
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._btn_generate = QPushButton()
        self._btn_generate.setObjectName("primaryBtn")
        self._btn_generate.setMinimumHeight(34)
        self._btn_generate.clicked.connect(self._generate_previews)
        btn_row.addWidget(self._btn_generate)

        self._btn_select_all = QPushButton()
        self._btn_select_all.setMinimumHeight(34)
        self._btn_select_all.clicked.connect(self._select_all)
        btn_row.addWidget(self._btn_select_all)

        self._btn_select_none = QPushButton()
        self._btn_select_none.setMinimumHeight(34)
        self._btn_select_none.clicked.connect(self._select_none)
        btn_row.addWidget(self._btn_select_none)

        self._btn_refresh = QPushButton()
        self._btn_refresh.setMinimumHeight(34)
        self._btn_refresh.clicked.connect(self._refresh_all)
        btn_row.addWidget(self._btn_refresh)
        layout.addLayout(btn_row)

        # Progress bar.
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setMinimumHeight(16)
        self._progress_bar.setMaximumHeight(16)
        layout.addWidget(self._progress_bar)

        # Status label.
        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet(_STYLE_STATUS_NORMAL)
        layout.addWidget(self._status_label)

        # Category sections + voice cards.
        cat_order = [
            ("narrator", "Narrators",
             "\u0414\u0438\u043a\u0442\u043e\u0440\u044b"),
            ("male", "Male voices",
             "\u041c\u0443\u0436\u0441\u043a\u0438\u0435 "
             "\u0433\u043e\u043b\u043e\u0441\u0430"),
            ("female", "Female voices",
             "\u0416\u0435\u043d\u0441\u043a\u0438\u0435 "
             "\u0433\u043e\u043b\u043e\u0441\u0430"),
        ]

        self._cat_labels: list[tuple[str, QLabel]] = []

        for cat_id, _en, _ru in cat_order:
            cat_label = QLabel()
            cat_label.setStyleSheet(
                "font-weight: 700; font-size: 11px;"
                "color: rgba(124,92,252,0.7);"
                "background: transparent; border: none;"
                "padding: 4px 0 1px 0;"
                "text-transform: uppercase; letter-spacing: 1px;"
            )
            self._cat_labels.append((cat_id, cat_label))
            layout.addWidget(cat_label)

            presets = [p for p in VOICE_PRESETS if p.category == cat_id]
            for preset in presets:
                card = VoiceCard(preset, self._preview_dir)
                layout.addWidget(card)
                self._cards.append(card)
                self._card_by_id[preset.id] = card

        layout.addStretch()
        self.retranslate()

    def retranslate(self) -> None:
        """Update all translatable strings."""
        self._btn_generate.setText(t("voice.generate_previews"))
        self._btn_refresh.setText(t("voice.refresh_previews"))
        self._btn_select_all.setText(
            "\u2611 All" if get_language() == "en" else "\u2611 \u0412\u0441\u0435"
        )
        self._btn_select_none.setText(
            "\u2610 None" if get_language() == "en" else "\u2610 \u041d\u0438\u0447\u0435\u0433\u043e"
        )
        self._dir_label.setText(t("voice.output_dir"))
        self._btn_browse.setText(t("voice.choose_dir"))
        self._phrase_label.setText(t("voice.preview_phrase"))
        self._phrase_input.setPlaceholderText(t("voice.default_phrase"))

        lang = get_language()
        titles = {
            "narrator": ("Narrators",
                         "\u0414\u0438\u043a\u0442\u043e\u0440\u044b"),
            "male": ("Male voices",
                     "\u041c\u0443\u0436\u0441\u043a\u0438\u0435 "
                     "\u0433\u043e\u043b\u043e\u0441\u0430"),
            "female": ("Female voices",
                       "\u0416\u0435\u043d\u0441\u043a\u0438\u0435 "
                       "\u0433\u043e\u043b\u043e\u0441\u0430"),
        }
        for cat_id, cat_label in self._cat_labels:
            en, ru = titles.get(cat_id, (cat_id, cat_id))
            cat_label.setText(ru if lang == "ru" else en)

        for card in self._cards:
            card.retranslate()

    def _select_all(self) -> None:
        for card in self._cards:
            card._checkbox.setChecked(True)

    def _select_none(self) -> None:
        for card in self._cards:
            card._checkbox.setChecked(False)

    def _browse_dir(self) -> None:
        chosen = QFileDialog.getExistingDirectory(
            self, t("voice.output_dir"), str(self._preview_dir),
        )
        if chosen:
            self._preview_dir = Path(chosen)
            self._dir_input.setText(str(self._preview_dir))
            self._refresh_all()

    def _refresh_all(self) -> None:
        """Refresh preview dir, status badges, and play buttons."""
        d = Path(self._dir_input.text().strip()) or self._preview_dir
        self._preview_dir = d
        ready = 0
        for card in self._cards:
            card.set_preview_dir(d)
            card.refresh_status()
            if card._btn_play.isEnabled():
                ready += 1

        self._status_label.setStyleSheet(_STYLE_STATUS_NORMAL)
        if ready == 0:
            self._status_label.setText(t("voice.no_previews"))
        else:
            self._status_label.setText(
                t("voice.previews_ready", count=ready,
                  total=len(self._cards))
            )

    def _generate_previews(self) -> None:
        """Generate selected preview WAVs via WSL TTS."""
        selected = [
            c.preset.id for c in self._cards if c.is_selected
        ]
        if not selected:
            self._status_label.setStyleSheet(_STYLE_STATUS_ERR)
            lang = get_language()
            self._status_label.setText(
                "\u041d\u0438\u0447\u0435\u0433\u043e \u043d\u0435 \u0432\u044b\u0431\u0440\u0430\u043d\u043e! "
                "\u041e\u0442\u043c\u0435\u0442\u044c\u0442\u0435 \u0433\u043e\u043b\u043e\u0441\u0430 "
                "\u0433\u0430\u043b\u043e\u0447\u043a\u0430\u043c\u0438."
                if lang == "ru"
                else "Nothing selected! Check the voices to generate."
            )
            return

        out_dir = Path(self._dir_input.text().strip())
        if not out_dir:
            out_dir = self._preview_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        self._preview_dir = out_dir

        # Quick WSL check.
        try:
            check = subprocess.run(
                ["wsl", "--status"],
                capture_output=True, text=True, timeout=10,
            )
            if check.returncode != 0:
                self._on_generate_error(
                    "WSL not available. Install WSL first."
                )
                return
        except FileNotFoundError:
            self._on_generate_error("WSL not found on this system.")
            return
        except Exception as exc:
            self._on_generate_error(f"WSL check failed: {exc}")
            return

        if not _SCRIPT_PATH.exists():
            self._on_generate_error(f"Script not found: {_SCRIPT_PATH}")
            return

        phrase = self._phrase_input.toPlainText().strip()
        if not phrase:
            phrase = t("voice.default_phrase")

        self._btn_generate.setEnabled(False)
        self._btn_generate.setText("Generating\u2026")
        self._progress_bar.setVisible(True)
        # Indeterminate mode during model loading.
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setFormat("")
        self._status_label.setStyleSheet(_STYLE_STATUS_ACTIVE)
        self._status_label.setText(t("voice.gen_loading"))

        self._worker = GeneratePreviewsWorker(
            out_dir, phrase, selected,
        )
        self._worker.progress_line.connect(self._on_progress_line)
        self._worker.progress_pct.connect(self._on_progress_pct)
        self._worker.voice_done.connect(self._on_voice_done)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.attn_info.connect(self._on_attn_info)
        self._worker.error.connect(self._on_generate_error)
        self._worker.start()

    def _on_progress_line(self, msg: str) -> None:
        self._status_label.setText(msg)

    def _on_progress_pct(self, done: int, total: int, eta: str) -> None:
        self._progress_bar.setRange(0, total)
        self._progress_bar.setValue(done)
        pct = int(done / total * 100) if total else 0
        self._progress_bar.setFormat(
            f"{pct}%  ({done}/{total})  ETA: {eta}"
        )

    def _on_voice_done(self, voice_id: str) -> None:
        """Refresh a single card when its WAV is ready."""
        card = self._card_by_id.get(voice_id)
        if card:
            card.refresh_status()

    def _on_attn_info(self, impl: str, note: str) -> None:
        """Show flash-attn status."""
        if impl == "sdpa":
            self._status_label.setText(
                f"Model loading... (attn: {impl} \u2014 "
                f"install flash-attn for 1.5\u20132\u00d7 speedup)"
            )

    def _on_finished(
        self, generated: int, total: int, elapsed: str,
    ) -> None:
        self._btn_generate.setEnabled(True)
        self._btn_generate.setText(t("voice.generate_previews"))
        self._progress_bar.setValue(self._progress_bar.maximum())
        self._status_label.setStyleSheet(_STYLE_STATUS_OK)
        self._status_label.setText(
            t("voice.gen_done", total=total, elapsed=elapsed)
        )
        self._refresh_all()

    def _on_generate_error(self, msg: str) -> None:
        self._btn_generate.setEnabled(True)
        self._btn_generate.setText(t("voice.generate_previews"))
        self._progress_bar.setVisible(False)
        self._status_label.setStyleSheet(_STYLE_STATUS_ERR)
        self._status_label.setText(f"Error: {msg[:300]}")
