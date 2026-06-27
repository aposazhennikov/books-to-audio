"""Helper functions for the voice assignment table."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import QComboBox

from book_normalizer.gui.i18n import t, voice_category_label, voice_preset_label
from book_normalizer.gui.ui_scaler import apply_combo_content_width
from book_normalizer.gui.voice_presets import VOICE_PRESETS
from book_normalizer.tts.voice_library import default_voice_library_dir, list_saved_voices
from book_normalizer.tts.voice_mapping import segment_speaker

INTONATION_KEYS = [
    "neutral", "calm", "excited", "joyful", "sad", "angry", "whisper",
]
SAVED_VOICE_PREFIX = "saved:"

_DIALOGUE_BG = QColor(14, 165, 233, 28)
_voice_library_dir_provider = default_voice_library_dir

_CANONICAL_ROLE_KEYS = {
    "narrator": "voice.role_narrator",
    "male": "voice.role_male",
    "female": "voice.role_female",
    "unknown": "voice.role_unknown",
}

_SECTION_ROLE_KEYS = {
    "annotation": "voice.role_annotation",
    "epigraph": "voice.role_epigraph",
    "preface": "voice.role_preface",
    "epilogue": "voice.role_epilogue",
    "chapter_title": "voice.role_chapter_title",
}


def set_voice_library_dir_provider(provider) -> None:
    """Override the saved-voice library directory provider."""
    global _voice_library_dir_provider  # noqa: PLW0603
    _voice_library_dir_provider = provider


def _saved_voices():
    return list_saved_voices(_voice_library_dir_provider())


def _editor_style() -> str:
    return (
        "QPlainTextEdit {"
        "  background: rgba(255,255,255,0.90);"
        "  border: 1px solid rgba(91,115,142,0.18);"
        "  border-radius: 8px;"
        "  padding: 8px;"
        "  color: rgba(30,41,59,0.92);"
        "  font-size: 12px;"
        "}"
    )


def _role_from_voice_id(voice_id: str, fallback: str = "narrator") -> str:
    """Infer canonical role from a GUI voice preset id."""
    normalized = (voice_id or "").strip().lower()
    if normalized.startswith(SAVED_VOICE_PREFIX):
        return fallback if fallback in {"narrator", "male", "female", "unknown"} else "narrator"
    if normalized == "male" or normalized.startswith("male_"):
        return "male"
    if normalized == "female" or normalized.startswith("female_"):
        return "female"
    if normalized == "narrator" or normalized.startswith("narrator_"):
        return "narrator"
    return fallback if fallback in {"narrator", "male", "female", "unknown"} else "narrator"


def _segment_role_display(segment: dict[str, Any]) -> str:
    """Return the human-facing role label for one segment."""
    speaker = segment_speaker(segment)
    if speaker:
        return speaker
    section = str(segment.get("section_kind") or "").strip().lower()
    if section in _SECTION_ROLE_KEYS:
        return t(_SECTION_ROLE_KEYS[section])
    role = str(segment.get("role") or "narrator").strip().lower()
    return t(_CANONICAL_ROLE_KEYS.get(role, "voice.role_narrator"))


def _make_voice_combo(current: str = "narrator_calm") -> QComboBox:
    """Create a QComboBox with all voice presets, grouped by category."""
    combo = QComboBox()
    _populate_voice_combo(combo, current)
    return combo


def _populate_voice_combo(combo: QComboBox, current: str = "narrator_calm") -> None:
    """Refresh voice combo labels for the active UI language."""
    combo.blockSignals(True)
    combo.clear()
    categories = ["narrator", "male", "female"]

    for cat_id in categories:
        combo.addItem(f"--- {voice_category_label(cat_id)} ---", "")
        idx = combo.count() - 1
        model = combo.model()
        item = model.item(idx)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        item.setForeground(QBrush(QColor(2, 132, 199, 190)))

        presets = [p for p in VOICE_PRESETS if p.category == cat_id]
        for p in presets:
            combo.addItem(f"  {voice_preset_label(p)}", p.id)

    saved_voices = _saved_voices()
    if saved_voices:
        combo.addItem(f"--- {voice_category_label('custom')} ---", "")
        idx = combo.count() - 1
        model = combo.model()
        item = model.item(idx)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        item.setForeground(QBrush(QColor(15, 118, 110, 190)))
        for voice in saved_voices:
            combo.addItem(f"  {voice.name}", f"{SAVED_VOICE_PREFIX}{voice.voice_id}")

    for i in range(combo.count()):
        if combo.itemData(i) == current:
            combo.setCurrentIndex(i)
            break
    combo.blockSignals(False)
    apply_combo_content_width(combo)


def _voice_display(voice_id: str) -> str:
    """Return the visible label for a voice preset id."""
    if voice_id.startswith(SAVED_VOICE_PREFIX):
        saved_id = voice_id.removeprefix(SAVED_VOICE_PREFIX)
        for voice in _saved_voices():
            if voice.voice_id == saved_id:
                return voice.name
        return saved_id
    for preset in VOICE_PRESETS:
        if preset.id == voice_id:
            return voice_preset_label(preset)
    return voice_id


def _intonation_display(key: str) -> str:
    """Return the visible label for an intonation key."""
    label = t(f"inton.{key}")
    return label if label != f"inton.{key}" else key


def _make_intonation_combo(current: str = "neutral") -> QComboBox:
    """Create a QComboBox with translated intonation options."""
    combo = QComboBox()

    for key in INTONATION_KEYS:
        combo.addItem(t(f"inton.{key}"), key)

    for i in range(combo.count()):
        if combo.itemData(i) == current:
            combo.setCurrentIndex(i)
            break

    apply_combo_content_width(combo)
    return combo
