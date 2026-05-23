"""Roles page — LLM character inventory for audiobook casting."""

from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from book_normalizer.chunking.role_inventory import build_role_inventory
from book_normalizer.gui.i18n import t
from book_normalizer.gui.widgets.progress_widget import ProgressWidget
from book_normalizer.gui.workers.tts_worker import ExportSegmentsWorker
from book_normalizer.languages import normalize_book_language
from book_normalizer.llm.model_router import PRIMARY_QWEN3_MODEL
from book_normalizer.runtime_paths import configured_ollama_endpoint


class RolesPage(QWidget):
    """Extract character roles and emotion variants before chunk editing."""

    segments_ready = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._book = None
        self._output_dir: Path | None = None
        self._segments_path: Path | None = None
        self._roles_path: Path | None = None
        self._worker: ExportSegmentsWorker | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        controls = QHBoxLayout()
        controls.setSpacing(8)

        self._llm_endpoint = QLineEdit(configured_ollama_endpoint())
        self._llm_endpoint.setMaximumWidth(260)
        controls.addWidget(self._llm_endpoint)

        self._llm_model = QLineEdit(PRIMARY_QWEN3_MODEL)
        controls.addWidget(self._llm_model, stretch=1)

        self._btn_extract = QPushButton()
        self._btn_extract.setObjectName("primaryBtn")
        self._btn_extract.setMinimumWidth(320)
        self._btn_extract.setEnabled(False)
        self._btn_extract.clicked.connect(self._run_role_extraction)
        controls.addWidget(self._btn_extract)
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
        self._table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._table, stretch=1)

        self.retranslate()

    def retranslate(self) -> None:
        """Update translatable strings."""
        self._llm_endpoint.setPlaceholderText(t("roles.llm_endpoint"))
        self._llm_model.setPlaceholderText(t("roles.llm_model"))
        self._btn_extract.setText(t("roles.extract"))
        self._table.setHorizontalHeaderLabels(
            [
                t("roles.col_role"),
                t("roles.col_description"),
                t("roles.col_speech"),
                t("roles.col_emotions"),
                t("roles.col_segments"),
            ]
        )
        if self._table.rowCount() == 0:
            self._summary.setText(t("roles.empty"))

    def set_book(self, book: object, output_dir: Path) -> None:
        """Receive the normalized book and output folder."""
        self._book = book
        self._output_dir = output_dir
        metadata = getattr(book, "metadata", None)
        extra = getattr(metadata, "extra", {}) if metadata is not None else {}
        candidates = extra.get("llm_model_candidates") if isinstance(extra, dict) else None
        if isinstance(candidates, list) and candidates:
            self._llm_model.setText(str(candidates[0]))
        self._btn_extract.setEnabled(True)
        self._summary.setText(t("roles.ready"))

    def _run_role_extraction(self) -> None:
        if not self._book or not self._output_dir:
            return

        self._btn_extract.setEnabled(False)
        self._progress.set_status(t("roles.extracting"))
        self._worker = ExportSegmentsWorker(
            book=self._book,
            output_dir=self._output_dir,
            speaker_mode="llm",
            llm_endpoint=self._llm_endpoint.text().strip() or configured_ollama_endpoint(),
            llm_model=self._llm_model.text().strip() or PRIMARY_QWEN3_MODEL,
            stress_mode="double_vowel",
        )
        self._worker.progress.connect(self._progress.set_status)
        self._worker.finished.connect(self._on_segments_ready)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_segments_ready(self, manifest_path: str) -> None:
        self._btn_extract.setEnabled(True)
        self.load_segments_manifest(Path(manifest_path))
        if self._segments_path and self._roles_path:
            self.segments_ready.emit(str(self._segments_path), str(self._roles_path))

    def load_segments_manifest(self, manifest_path: Path) -> dict[str, object]:
        """Load a segment manifest, build role inventory, and update UI."""
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
        self._progress.set_status(
            t("roles.done", n=len(inventory["roles"]))
        )
        return inventory

    def _populate_table(self, inventory: dict[str, object]) -> None:
        roles = list(inventory.get("roles", []))
        self._table.setRowCount(len(roles))
        for row, raw_role in enumerate(roles):
            role = raw_role if isinstance(raw_role, dict) else {}
            emotions = role.get("emotions", [])
            emotion_text = ", ".join(
                f"{item.get('emotion')}: {item.get('count')}"
                for item in emotions
                if isinstance(item, dict)
            )
            values = [
                str(role.get("display_name") or ""),
                str(role.get("description") or ""),
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
