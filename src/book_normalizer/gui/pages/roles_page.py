"""Roles page — LLM character inventory for audiobook casting."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QGridLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from book_normalizer.chunking.role_inventory import build_role_inventory
from book_normalizer.gui.dialog_styles import apply_readable_message_box_style
from book_normalizer.gui.i18n import t
from book_normalizer.gui.role_cache import (
    CachedRoleExtraction,
    RoleCacheSettings,
    cached_role_entry_from_output_dir,
    find_any_cached_roles,
    find_cached_roles,
    restore_role_cache,
    save_role_cache,
)
from book_normalizer.gui.widgets.progress_widget import ProgressWidget
from book_normalizer.gui.workers.tts_worker import ExportSegmentsWorker
from book_normalizer.languages import normalize_book_language
from book_normalizer.llm.model_router import PRIMARY_QWEN3_MODEL
from book_normalizer.runtime_paths import configured_ollama_endpoint

logger = logging.getLogger(__name__)


_ROLE_NAME_KEYS = {
    "Narrator": "voice.role_narrator",
    "Male character": "voice.role_male",
    "Female character": "voice.role_female",
    "Annotation": "voice.role_annotation",
    "Epigraph": "voice.role_epigraph",
    "Preface": "voice.role_preface",
    "Epilogue": "voice.role_epilogue",
    "Chapter title": "voice.role_chapter_title",
}

_ROLE_DESCRIPTION_KEYS = {
    "Direct-speech role detected in the book.": "roles.desc_direct_speech",
    "Direct-speech character inferred from local dialogue context.": "roles.desc_direct_speech_inferred",
    "Narrator and authorial prose.": "roles.desc_narrator",
}


def _localized_role_name(name: str) -> str:
    key = _ROLE_NAME_KEYS.get(name)
    return t(key) if key else name


def _localized_role_description(description: str, display_name: str) -> str:
    key = _ROLE_DESCRIPTION_KEYS.get(description)
    if key:
        return t(key)
    if description == f"System narration block for {display_name.lower()}.":
        return t("roles.desc_system", name=_localized_role_name(display_name))
    return description


def _localized_emotion_label(emotion: str) -> str:
    key = f"inton.{emotion.strip().lower().replace(' ', '_')}"
    label = t(key)
    return label if label != key else emotion


class RolesPage(QWidget):
    """Extract character roles and emotion variants before chunk editing."""

    segments_ready = pyqtSignal(str, str)
    role_extraction_failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._book = None
        self._output_dir: Path | None = None
        self._segments_path: Path | None = None
        self._roles_path: Path | None = None
        self._worker: ExportSegmentsWorker | None = None
        self._compact_mode = False
        self._current_inventory: dict[str, object] | None = None
        self._cache_restored_roles: int | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        controls = QGridLayout()
        controls.setHorizontalSpacing(10)
        controls.setVerticalSpacing(4)
        controls.setColumnStretch(0, 0)
        controls.setColumnStretch(1, 1)
        controls.setColumnStretch(2, 0)
        self._controls = controls

        self._llm_endpoint_label = QLabel()
        self._llm_endpoint = QLineEdit(configured_ollama_endpoint())
        self._llm_endpoint.setMinimumWidth(318)
        self._llm_endpoint.setMaximumWidth(340)
        self._llm_endpoint.setCursorPosition(0)
        controls.addWidget(self._llm_endpoint_label, 0, 0)
        controls.addWidget(self._llm_endpoint, 1, 0)

        self._llm_model_label = QLabel()
        self._llm_model = QLineEdit(PRIMARY_QWEN3_MODEL)
        self._llm_model.setCursorPosition(0)
        controls.addWidget(self._llm_model_label, 0, 1)
        controls.addWidget(self._llm_model, 1, 1)

        self._btn_extract = QPushButton()
        self._btn_extract.setObjectName("primaryBtn")
        self._btn_extract.setMinimumWidth(260)
        self._btn_extract.setMaximumWidth(340)
        self._btn_extract.setEnabled(False)
        self._btn_extract.clicked.connect(self._run_role_extraction)
        self._special_sections_check = QCheckBox()
        self._special_sections_check.setChecked(False)
        self._apply_control_layout()
        layout.addLayout(controls)

        self._progress = ProgressWidget()
        layout.addWidget(self._progress)

        self._summary = QLabel("")
        self._summary.setWordWrap(True)
        self._summary.setStyleSheet(
            "color: rgba(51,65,85,0.70); font-size: 12px; font-weight: 600;"
        )
        layout.addWidget(self._summary)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        header = self._table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(48)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table, stretch=1)

        self.retranslate()

    def resizeEvent(self, event) -> None:  # noqa: N802
        """Use compact table labels before headers start clipping."""
        super().resizeEvent(event)
        compact = self.width() < 860
        if compact != self._compact_mode:
            self._compact_mode = compact
            self._apply_control_layout()
            self._apply_table_headers()

    def retranslate(self) -> None:
        """Update translatable strings."""
        self._llm_endpoint_label.setText(t("roles.llm_endpoint"))
        self._llm_endpoint.setPlaceholderText(t("roles.llm_endpoint"))
        self._llm_model_label.setText(t("roles.llm_model"))
        self._llm_model.setPlaceholderText(t("roles.llm_model"))
        self._btn_extract.setText(t("roles.extract"))
        self._special_sections_check.setText(t("roles.special_sections"))
        self._special_sections_check.setToolTip(t("roles.special_sections_tip"))
        self._apply_table_headers()
        if self._current_inventory is not None:
            self._populate_table(self._current_inventory)
        elif self._table.rowCount() == 0:
            self._summary.setText(t("roles.empty"))
        if self._cache_restored_roles is not None:
            self._progress.set_status(
                t("roles.cache_restored", n=self._cache_restored_roles),
            )

    def _apply_control_layout(self) -> None:
        """Keep role extraction controls readable in compact windows."""
        widgets = (
            self._llm_endpoint_label,
            self._llm_endpoint,
            self._llm_model_label,
            self._llm_model,
            self._btn_extract,
            self._special_sections_check,
        )
        for widget in widgets:
            self._controls.removeWidget(widget)

        if self._compact_mode:
            self._controls.setVerticalSpacing(8)
            self._controls.setColumnStretch(0, 0)
            self._controls.setColumnStretch(1, 1)
            self._controls.setColumnStretch(2, 1)
            self._llm_endpoint.setMinimumWidth(318)
            self._llm_endpoint.setMaximumWidth(340)
            self._btn_extract.setMinimumWidth(0)
            self._btn_extract.setMaximumWidth(16777215)
            self._controls.addWidget(self._llm_endpoint_label, 0, 0)
            self._controls.addWidget(self._llm_model_label, 0, 1, 1, 2)
            self._controls.addWidget(self._llm_endpoint, 1, 0)
            self._controls.addWidget(self._llm_model, 1, 1, 1, 2)
            self._controls.addWidget(self._special_sections_check, 2, 0, 1, 3)
            self._controls.addWidget(self._btn_extract, 3, 0, 1, 3)
            return

        self._controls.setVerticalSpacing(4)
        self._controls.setColumnStretch(0, 0)
        self._controls.setColumnStretch(1, 1)
        self._controls.setColumnStretch(2, 0)
        self._llm_endpoint.setMinimumWidth(318)
        self._llm_endpoint.setMaximumWidth(340)
        self._btn_extract.setMinimumWidth(260)
        self._btn_extract.setMaximumWidth(340)
        self._controls.addWidget(self._llm_endpoint_label, 0, 0)
        self._controls.addWidget(self._llm_endpoint, 1, 0)
        self._controls.addWidget(self._llm_model_label, 0, 1)
        self._controls.addWidget(self._llm_model, 1, 1)
        self._controls.addWidget(self._special_sections_check, 0, 2)
        self._controls.addWidget(self._btn_extract, 1, 2)

    def _apply_table_headers(self) -> None:
        """Apply full or compact role table headers with full-text tooltips."""
        suffix = "_short" if self._compact_mode else ""
        keys = [
            "roles.col_role",
            f"roles.col_description{suffix}",
            f"roles.col_speech{suffix}",
            f"roles.col_emotions{suffix}",
            f"roles.col_segments{suffix}",
        ]
        full_keys = [
            "roles.col_role",
            "roles.col_description",
            "roles.col_speech",
            "roles.col_emotions",
            "roles.col_segments",
        ]
        self._table.setHorizontalHeaderLabels(
            [t(key) for key in keys]
        )
        for column, full_key in enumerate(full_keys):
            item = self._table.horizontalHeaderItem(column)
            if item is not None:
                item.setToolTip(t(full_key))

    def set_book(self, book: object, output_dir: Path) -> None:
        """Receive the normalized book and output folder."""
        self._book = book
        self._output_dir = output_dir
        self._cache_restored_roles = None
        metadata = getattr(book, "metadata", None)
        extra = getattr(metadata, "extra", {}) if metadata is not None else {}
        candidates = extra.get("llm_model_candidates") if isinstance(extra, dict) else None
        if isinstance(candidates, list) and candidates:
            self._llm_model.setText(str(candidates[0]))
        self._btn_extract.setEnabled(True)
        self._summary.setText(t("roles.ready"))

    def run_role_extraction(self, *, cache_choice: str | None = None) -> None:
        """Start role extraction, optionally choosing a cache action without prompting."""
        self._run_role_extraction(cache_choice=cache_choice)

    def _run_role_extraction(self, cache_choice: str | None = None) -> None:
        if not self._book or not self._output_dir:
            return

        cache_choice = cache_choice if cache_choice in {"restore", "fresh", "cancel"} else None
        self._cache_restored_roles = None
        settings = self._role_cache_settings()
        cached = self._find_cached_roles(settings)
        if cached is None and cache_choice == "restore":
            cached = self._find_any_cached_roles()
        if cached is not None:
            choice = cache_choice or self._ask_cached_roles()
            if choice == "restore":
                self._restore_cached_roles(cached)
                return
            if choice == "cancel":
                return

        self._btn_extract.setEnabled(False)
        self._progress.reset()
        self._progress.set_busy(t("roles.extracting"))
        self._worker = ExportSegmentsWorker(
            book=self._book,
            output_dir=self._output_dir,
            speaker_mode="llm",
            llm_endpoint=self._llm_endpoint.text().strip() or configured_ollama_endpoint(),
            llm_model=self._llm_model.text().strip() or PRIMARY_QWEN3_MODEL,
            stress_mode="double_vowel",
            detect_special_sections=self._special_sections_check.isChecked(),
        )
        self._worker.progress.connect(self._progress.set_busy)
        progress_pct = getattr(self._worker, "progress_pct", None)
        if progress_pct is not None:
            progress_pct.connect(self._progress.set_progress)
        self._worker.finished.connect(self._on_segments_ready)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_segments_ready(self, manifest_path: str) -> None:
        self._progress.set_busy(t("roles.extracting"))
        self._summary.setText(t("roles.extracting"))
        QApplication.processEvents()
        try:
            self.load_segments_manifest(Path(manifest_path))
            self._save_current_role_cache()
        except (OSError, ValueError, TypeError) as exc:
            self._on_error(str(exc))
            return
        finally:
            self._btn_extract.setEnabled(True)
        if self._segments_path and self._roles_path:
            self.segments_ready.emit(str(self._segments_path), str(self._roles_path))

    def _role_cache_settings(self) -> RoleCacheSettings:
        """Return settings that define reusable completed role extraction."""
        return RoleCacheSettings(
            book_language=self._book_language(),
            speaker_mode="llm",
            llm_endpoint=self._llm_endpoint.text().strip() or configured_ollama_endpoint(),
            llm_model=self._llm_model.text().strip() or PRIMARY_QWEN3_MODEL,
            stress_mode="double_vowel",
            detect_special_sections=self._special_sections_check.isChecked(),
        )

    def _find_cached_roles(
        self,
        settings: RoleCacheSettings,
    ) -> CachedRoleExtraction | None:
        """Find a completed role cache entry, ignoring unreadable cache state."""
        try:
            cached = find_cached_roles(self._book, settings)
        except (OSError, ValueError, TypeError) as exc:
            logger.debug("Could not inspect role cache: %s", exc)
            cached = None
        if cached is not None:
            return cached
        try:
            if self._output_dir is not None:
                return cached_role_entry_from_output_dir(self._output_dir)
        except (OSError, ValueError, TypeError) as exc:
            logger.debug("Could not inspect output role manifests: %s", exc)
            return None
        return None

    def _find_any_cached_roles(self) -> CachedRoleExtraction | None:
        """Find any completed role cache for the current book."""
        try:
            return find_any_cached_roles(self._book)
        except (OSError, ValueError, TypeError) as exc:
            logger.debug("Could not inspect role cache: %s", exc)
            return None

    def _ask_cached_roles(self) -> str:
        """Ask whether to restore cached completed roles or extract again."""
        box = QMessageBox(self)
        apply_readable_message_box_style(box)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle(t("roles.cache_dialog_title"))
        box.setText(t("roles.cache_dialog_text"))
        box.setInformativeText(t("roles.cache_dialog_informative"))
        restore_button = box.addButton(
            t("roles.cache_restore_button"),
            QMessageBox.ButtonRole.AcceptRole,
        )
        fresh_button = box.addButton(
            t("roles.cache_run_fresh_button"),
            QMessageBox.ButtonRole.ActionRole,
        )
        cancel_button = box.addButton(
            t("roles.cache_cancel_button"),
            QMessageBox.ButtonRole.RejectRole,
        )
        box.setDefaultButton(restore_button)
        box.setEscapeButton(cancel_button)
        box.exec()
        clicked = box.clickedButton()
        if clicked is restore_button:
            return "restore"
        if clicked is fresh_button:
            return "fresh"
        return "cancel"

    def _restore_cached_roles(self, cached: CachedRoleExtraction) -> None:
        """Restore completed role extraction manifests and continue the workflow."""
        if self._output_dir is None:
            return
        self._progress.reset()
        try:
            if cached.path.resolve() == self._output_dir.resolve():
                segments_path, roles_path = cached.segments_path, cached.roles_path
            else:
                segments_path, roles_path = restore_role_cache(cached, self._output_dir)
            inventory = self._load_role_inventory(segments_path, roles_path)
        except (OSError, ValueError, TypeError) as exc:
            self._progress.set_status(t("roles.cache_restore_failed", msg=str(exc)))
            self._btn_extract.setEnabled(True)
            self.role_extraction_failed.emit(str(exc))
            return

        role_count = len(list(inventory.get("roles", [])))
        self._cache_restored_roles = role_count
        self._btn_extract.setEnabled(True)
        if cached.path.resolve() == self._output_dir.resolve():
            self._save_current_role_cache()
        self._progress.set_status(t("roles.cache_restored", n=role_count))
        if self._segments_path and self._roles_path:
            self.segments_ready.emit(str(self._segments_path), str(self._roles_path))

    def _save_current_role_cache(self) -> None:
        """Save completed role extraction manifests for the current book/settings."""
        if not self._book or not self._segments_path or not self._roles_path:
            return
        review_report_path = None
        if self._output_dir is not None:
            review_report_path = self._output_dir / "llm_voice_review_report.json"
        try:
            save_role_cache(
                self._book,
                self._role_cache_settings(),
                self._segments_path,
                self._roles_path,
                review_report_path=review_report_path,
            )
        except (OSError, ValueError, TypeError) as exc:
            logger.debug("Could not save role cache: %s", exc)

    def load_segments_manifest(self, manifest_path: Path) -> dict[str, object]:
        """Load a segment manifest, build role inventory, and update UI."""
        self._cache_restored_roles = None
        self._segments_path = manifest_path
        segments = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(segments, list):
            raise ValueError("segments manifest must be a JSON array")
        language = self._book_language()
        inventory = build_role_inventory(segments, language=language)

        output_dir = self._output_dir or manifest_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        self._roles_path = output_dir / "roles_manifest.json"
        self._roles_path.write_text(
            json.dumps(inventory, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._populate_table(inventory)
        review_report = output_dir / "llm_voice_review_report.json"
        if review_report.exists():
            self._progress.set_status(
                t("roles.done_with_review", n=len(inventory["roles"]), path=str(review_report))
            )
        else:
            self._progress.set_status(
                t("roles.done", n=len(inventory["roles"]))
            )
        return inventory

    def _load_role_inventory(
        self,
        segments_path: Path,
        roles_path: Path,
    ) -> dict[str, object]:
        """Load restored segment and role manifests without rebuilding roles."""
        segments = json.loads(segments_path.read_text(encoding="utf-8"))
        if not isinstance(segments, list):
            raise ValueError("segments manifest must be a JSON array")
        inventory = json.loads(roles_path.read_text(encoding="utf-8"))
        if not isinstance(inventory, dict):
            raise ValueError("roles manifest must be a JSON object")
        self._segments_path = segments_path
        self._roles_path = roles_path
        self._populate_table(inventory)
        return inventory

    def _populate_table(self, inventory: dict[str, object]) -> None:
        self._current_inventory = inventory
        roles = list(inventory.get("roles", []))
        self._table.setRowCount(len(roles))
        for row, raw_role in enumerate(roles):
            role = raw_role if isinstance(raw_role, dict) else {}
            emotions = role.get("emotions", [])
            emotion_text = ", ".join(
                f"{_localized_emotion_label(str(item.get('emotion') or ''))}: {item.get('count')}"
                for item in emotions
                if isinstance(item, dict)
            )
            display_name = str(role.get("display_name") or "")
            description = str(role.get("description") or "")
            values = [
                _localized_role_name(display_name),
                _localized_role_description(description, display_name),
                str(role.get("direct_speech_count") or 0),
                emotion_text,
                str(role.get("segment_count") or 0),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in {2, 4}:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignCenter
                        | Qt.AlignmentFlag.AlignVCenter
                    )
                self._table.setItem(row, column, item)
        self._table.resizeColumnsToContents()
        self._summary.setText(
            t(
                "roles.summary",
                roles=len(roles),
                speech=inventory.get("total_direct_speech", 0),
                segments=inventory.get("total_segments", 0),
            )
        )

    def _book_language(self) -> str:
        metadata = getattr(self._book, "metadata", None)
        return normalize_book_language(getattr(metadata, "language", "ru"))

    def _on_error(self, msg: str) -> None:
        self._btn_extract.setEnabled(True)
        self._progress.set_status(t("roles.error", msg=msg))
        self.role_extraction_failed.emit(msg)
