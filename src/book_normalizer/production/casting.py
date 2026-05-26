"""Automatic voice casting for character bibles."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from book_normalizer.chunking.manifest_v2 import ensure_v2_manifest
from book_normalizer.tts.voice_library import (
    SavedVoice,
    list_saved_voices,
    sanitize_voice_id,
)

CASTING_PLAN_VERSION = 1
DEFAULT_CASTING_PLAN_NAME = "casting_plan.json"
DEFAULT_VOICE_OVERRIDES_NAME = "voice_overrides.json"

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PRESET_PATH = _REPO_ROOT / "voice_previews" / "presets.json"

_FALLBACK_PRESETS: list[dict[str, str]] = [
    {"id": "narrator_calm", "speaker": "Aiden", "category": "narrator", "instruct": "Calm narrator."},
    {"id": "narrator_energetic", "speaker": "Ryan", "category": "narrator", "instruct": "Energetic narrator."},
    {"id": "narrator_wise", "speaker": "Uncle_Fu", "category": "narrator", "instruct": "Wise narrator."},
    {"id": "male_young", "speaker": "Ryan", "category": "male", "instruct": "Young male voice."},
    {"id": "male_confident", "speaker": "Aiden", "category": "male", "instruct": "Confident male voice."},
    {"id": "male_deep", "speaker": "Uncle_Fu", "category": "male", "instruct": "Deep male voice."},
    {"id": "male_lively", "speaker": "Dylan", "category": "male", "instruct": "Lively male voice."},
    {"id": "male_regional", "speaker": "Eric", "category": "male", "instruct": "Expressive male voice."},
    {"id": "female_warm", "speaker": "Serena", "category": "female", "instruct": "Warm female voice."},
    {"id": "female_bright", "speaker": "Vivian", "category": "female", "instruct": "Bright female voice."},
    {"id": "female_playful", "speaker": "Ono_Anna", "category": "female", "instruct": "Playful female voice."},
    {"id": "female_gentle", "speaker": "Sohee", "category": "female", "instruct": "Gentle female voice."},
]

_ASSERTIVE_EMOTIONS = {
    "angry",
    "anger",
    "tense",
    "confident",
    "stern",
    "irritated",
    "furious",
    "commanding",
}
_SOFT_EMOTIONS = {
    "sad",
    "fearful",
    "afraid",
    "tired",
    "calm",
    "gentle",
    "whisper",
    "quiet",
    "melancholy",
}
_BRIGHT_EMOTIONS = {
    "joyful",
    "happy",
    "excited",
    "playful",
    "cheerful",
    "laughing",
    "curious",
}


def load_voice_presets(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load available built-in voice presets keyed by preset id."""
    source = path or DEFAULT_PRESET_PATH
    presets: list[dict[str, Any]] = []
    if source.exists():
        raw = json.loads(source.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            presets = [dict(item) for item in raw if isinstance(item, dict)]
    if not presets:
        presets = [dict(item) for item in _FALLBACK_PRESETS]

    result: dict[str, dict[str, Any]] = {}
    for preset in presets:
        preset_id = str(preset.get("id") or "").strip()
        speaker = str(preset.get("speaker") or "").strip()
        if not preset_id or not speaker:
            continue
        result[preset_id] = {
            "id": preset_id,
            "speaker": speaker,
            "category": str(preset.get("category") or _category_from_preset_id(preset_id)),
            "instruct": str(preset.get("instruct") or ""),
        }
    return result


def build_casting_plan(
    character_bible: dict[str, Any],
    *,
    voice_library_dir: Path | None = None,
    preset_path: Path | None = None,
    prefer_saved: bool = True,
    design_important: bool = True,
    min_design_lines: int = 3,
) -> dict[str, Any]:
    """Choose a stable voice strategy for every character in a bible."""
    presets = load_voice_presets(preset_path)
    saved_voices = list_saved_voices(voice_library_dir) if voice_library_dir and prefer_saved else []
    saved_index = _saved_voice_index(saved_voices)

    characters: list[dict[str, Any]] = []
    for character in character_bible.get("characters", []):
        if not isinstance(character, dict):
            continue
        cast = _cast_character(
            character,
            presets=presets,
            saved_index=saved_index,
            design_important=design_important,
            min_design_lines=max(1, int(min_design_lines)),
        )
        characters.append(cast)

    summary = Counter(str(item.get("voice_strategy") or "") for item in characters)
    return {
        "version": CASTING_PLAN_VERSION,
        "book_title": str(character_bible.get("book_title") or ""),
        "language": str(character_bible.get("language") or "ru"),
        "strategy": "saved+design+builtin",
        "source_character_bible_version": character_bible.get("version"),
        "total_characters": len(characters),
        "characters": characters,
        "summary": {
            "saved": int(summary.get("saved", 0)),
            "designed": int(summary.get("designed", 0)),
            "builtin": int(summary.get("builtin", 0)),
            "requires_voice_generation": sum(
                1 for item in characters if bool(item.get("requires_voice_generation"))
            ),
        },
    }


def casting_voice_overrides(plan: dict[str, Any]) -> dict[str, Any]:
    """Return a speaker override config consumable by ComfyUI synthesis."""
    overrides: dict[str, Any] = {}
    for character in plan.get("characters", []):
        if not isinstance(character, dict):
            continue
        value = _override_value(character)
        for key in character.get("mapping_keys", []):
            key_text = str(key or "").strip()
            if key_text and key_text not in overrides:
                overrides[key_text] = value
    return overrides


def apply_casting_plan_to_manifest(
    manifest: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    """Attach selected cast voices to v2 manifest chunks."""
    record = ensure_v2_manifest(manifest).to_record()
    by_id, by_name = _character_lookup(plan)
    narrator = by_name.get(_key("Narrator"))

    for chapter in record.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        for chunk in chapter.get("chunks", []):
            if not isinstance(chunk, dict):
                continue
            cast = by_id.get(str(chunk.get("character_id") or ""))
            if cast is None:
                cast = by_name.get(_key(chunk.get("canonical_speaker")))
            if cast is None:
                cast = by_name.get(_key(chunk.get("speaker")))
            if cast is None and str(chunk.get("voice_label") or "") == "narrator":
                cast = narrator
            if cast is None:
                continue

            chunk["character_id"] = str(cast.get("character_id") or chunk.get("character_id") or "")
            chunk["canonical_speaker"] = str(cast.get("display_name") or chunk.get("canonical_speaker") or "")
            chunk["cast_voice_id"] = str(cast.get("selected_voice_id") or "")
            chunk["voice_strategy"] = str(cast.get("voice_strategy") or "")
            manifest_voice_id = str(
                cast.get("manifest_voice_id")
                or cast.get("fallback_voice_id")
                or cast.get("selected_voice_id")
                or ""
            )
            if manifest_voice_id:
                chunk["voice_id"] = manifest_voice_id
    return record


def write_casting_plan(path: Path, plan: dict[str, Any]) -> Path:
    """Write casting_plan.json."""
    return _write_json(path, plan)


def write_voice_overrides(path: Path, overrides: dict[str, Any]) -> Path:
    """Write voice_overrides.json."""
    return _write_json(path, overrides)


def _cast_character(
    character: dict[str, Any],
    *,
    presets: dict[str, dict[str, Any]],
    saved_index: dict[str, SavedVoice],
    design_important: bool,
    min_design_lines: int,
) -> dict[str, Any]:
    display_name = str(character.get("display_name") or "Character").strip() or "Character"
    role = _canonical_role(character)
    dominant_emotion = _dominant_emotion(character)
    aliases = _aliases(character, display_name)
    saved = _matching_saved_voice(aliases, saved_index)
    builtin = _select_builtin_preset(role, dominant_emotion, presets)
    design_prompt = _voice_design_prompt(character, role, dominant_emotion)
    important = role != "narrator" and int(character.get("direct_speech_count") or 0) >= min_design_lines

    candidates: list[dict[str, Any]] = []
    if saved is not None:
        candidates.append(
            {
                "voice_id": saved.voice_id,
                "display_name": saved.name,
                "strategy": "saved",
                "score": 1.0,
                "reason": "Saved voice matched character name or alias.",
                "speech_rate": saved.speech_rate,
                "prompt_path": str(saved.prompt_path),
            }
        )

    fallback_id = str(builtin.get("id") or "narrator_calm")
    fallback_speaker = str(builtin.get("speaker") or "Aiden")
    candidates.append(
        {
            "voice_id": fallback_id,
            "speaker": fallback_speaker,
            "strategy": "builtin",
            "score": _builtin_score(role, dominant_emotion),
            "reason": _builtin_reason(role, dominant_emotion),
        }
    )

    if saved is not None:
        selected_strategy = "saved"
        selected_voice_id = saved.voice_id
        selected_speaker = saved.voice_id
        manifest_voice_id = saved.voice_id
        speech_rate = saved.speech_rate
        requires_generation = False
    elif design_important and important:
        selected_strategy = "designed"
        selected_voice_id = f"design:{character.get('character_id') or sanitize_voice_id(display_name)}"
        selected_speaker = fallback_speaker
        manifest_voice_id = fallback_id
        speech_rate = 1.0
        requires_generation = True
        candidates.insert(
            0,
            {
                "voice_id": selected_voice_id,
                "speaker": fallback_speaker,
                "strategy": "designed",
                "score": 0.92,
                "reason": "Character has enough lines for voice design, using built-in voice as fallback.",
                "fallback_voice_id": fallback_id,
                "voice_design_prompt": design_prompt,
            },
        )
    else:
        selected_strategy = "builtin"
        selected_voice_id = fallback_id
        selected_speaker = fallback_speaker
        manifest_voice_id = fallback_id
        speech_rate = 1.0
        requires_generation = False

    return {
        "character_id": str(character.get("character_id") or ""),
        "display_name": display_name,
        "role": role,
        "aliases": aliases,
        "direct_speech_count": int(character.get("direct_speech_count") or 0),
        "selected_voice_id": selected_voice_id,
        "selected_speaker": selected_speaker,
        "voice_strategy": selected_strategy,
        "manifest_voice_id": manifest_voice_id,
        "fallback_voice_id": fallback_id,
        "fallback_speaker": fallback_speaker,
        "speech_rate": speech_rate,
        "dominant_emotion": dominant_emotion,
        "voice_design_prompt": design_prompt,
        "requires_voice_generation": requires_generation,
        "mapping_keys": _mapping_keys(role, aliases),
        "candidates": candidates,
    }


def _saved_voice_index(saved_voices: list[SavedVoice]) -> dict[str, SavedVoice]:
    index: dict[str, SavedVoice] = {}
    for voice in saved_voices:
        for value in (voice.voice_id, voice.name, sanitize_voice_id(voice.name)):
            key = _key(value)
            if key:
                index.setdefault(key, voice)
    return index


def _matching_saved_voice(aliases: list[str], saved_index: dict[str, SavedVoice]) -> SavedVoice | None:
    for alias in aliases:
        for value in (alias, sanitize_voice_id(alias)):
            voice = saved_index.get(_key(value))
            if voice is not None:
                return voice
    return None


def _select_builtin_preset(
    role: str,
    emotion: str,
    presets: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    def preset(preset_id: str, fallback_id: str = "narrator_calm") -> dict[str, Any]:
        return presets.get(preset_id) or presets.get(fallback_id) or dict(_FALLBACK_PRESETS[0])

    emotion_key = _key(emotion)
    if role == "narrator":
        if emotion_key in _BRIGHT_EMOTIONS or "excited" in emotion_key:
            return preset("narrator_energetic")
        if "wise" in emotion_key:
            return preset("narrator_wise")
        return preset("narrator_calm")

    if role == "male":
        if emotion_key in _ASSERTIVE_EMOTIONS or any(word in emotion_key for word in _ASSERTIVE_EMOTIONS):
            return preset("male_confident")
        if emotion_key in _SOFT_EMOTIONS or any(word in emotion_key for word in _SOFT_EMOTIONS):
            return preset("male_deep")
        if emotion_key in _BRIGHT_EMOTIONS or any(word in emotion_key for word in _BRIGHT_EMOTIONS):
            return preset("male_lively")
        return preset("male_young")

    if role == "female":
        if emotion_key in _ASSERTIVE_EMOTIONS or any(word in emotion_key for word in _ASSERTIVE_EMOTIONS):
            return preset("female_bright")
        if emotion_key in _SOFT_EMOTIONS or any(word in emotion_key for word in _SOFT_EMOTIONS):
            return preset("female_gentle")
        if emotion_key in _BRIGHT_EMOTIONS or any(word in emotion_key for word in _BRIGHT_EMOTIONS):
            return preset("female_playful")
        return preset("female_warm")

    return preset("narrator_calm")


def _override_value(character: dict[str, Any]) -> dict[str, Any]:
    strategy = str(character.get("voice_strategy") or "")
    if strategy == "saved":
        value: dict[str, Any] = {
            "saved_voice": str(character.get("selected_voice_id") or ""),
            "strategy": "saved",
        }
    else:
        value = {
            "speaker": str(character.get("selected_speaker") or character.get("fallback_speaker") or ""),
            "voice_id": str(character.get("selected_voice_id") or ""),
            "strategy": strategy or "builtin",
        }
    speech_rate = float(character.get("speech_rate") or 1.0)
    if speech_rate != 1.0:
        value["speech_rate"] = speech_rate
    if strategy == "designed":
        value["requires_voice_generation"] = True
        value["fallback_voice_id"] = str(character.get("fallback_voice_id") or "")
        value["voice_design_prompt"] = str(character.get("voice_design_prompt") or "")
    return value


def _character_lookup(plan: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_id: dict[str, dict[str, Any]] = {}
    by_name: dict[str, dict[str, Any]] = {}
    for character in plan.get("characters", []):
        if not isinstance(character, dict):
            continue
        character_id = str(character.get("character_id") or "")
        if character_id:
            by_id[character_id] = character
        for alias in character.get("aliases", []):
            alias_key = _key(alias)
            if alias_key:
                by_name[alias_key] = character
        display_key = _key(character.get("display_name"))
        if display_key:
            by_name[display_key] = character
    return by_id, by_name


def _aliases(character: dict[str, Any], display_name: str) -> list[str]:
    values = [display_name]
    values.extend(str(item) for item in character.get("aliases", []) if item)
    character_id = str(character.get("character_id") or "")
    if character_id:
        values.append(character_id)
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = re.sub(r"\s+", " ", str(value or "")).strip()
        key = _key(cleaned)
        if cleaned and key not in seen:
            result.append(cleaned)
            seen.add(key)
    return result


def _mapping_keys(role: str, aliases: list[str]) -> list[str]:
    keys: list[str] = []
    for alias in aliases:
        key = _key(alias)
        if key and key != "narrator":
            keys.append(f"speaker:{alias}")
    if role == "narrator":
        keys.append("narrator")
        keys.append("speaker:Narrator")
    return _unique(keys)


def _voice_design_prompt(character: dict[str, Any], role: str, emotion: str) -> str:
    description = str(character.get("description") or "").strip() or "No explicit description in the text."
    lines = [
        "Design a reusable audiobook voice for this character.",
        f"Character: {character.get('display_name') or 'Character'}.",
        f"Role: {role}.",
        f"Description: {description}",
    ]
    if emotion:
        lines.append(f"Dominant emotion: {emotion}.")
    samples = [str(item).strip() for item in character.get("sample_lines", []) if str(item).strip()]
    if samples:
        joined = " | ".join(samples[:3])
        lines.append(f"Sample dialogue: {joined}")
    lines.append("Keep the voice consistent across chapters; avoid caricature and synthetic overacting.")
    return " ".join(lines)


def _dominant_emotion(character: dict[str, Any]) -> str:
    counts: Counter[str] = Counter()
    for item in character.get("emotions", []):
        if not isinstance(item, dict):
            continue
        emotion = str(item.get("emotion") or "").strip().lower()
        if emotion:
            counts[emotion] += int(item.get("count") or 0)
    if counts:
        return counts.most_common(1)[0][0]
    return ""


def _canonical_role(character: dict[str, Any]) -> str:
    role = str(character.get("role") or "").strip().lower()
    if role in {"narrator", "male", "female", "unknown"}:
        return role
    if str(character.get("display_name") or "").strip().casefold() == "narrator":
        return "narrator"
    return "unknown"


def _builtin_score(role: str, emotion: str) -> float:
    if role in {"male", "female"} and emotion:
        return 0.78
    if role == "narrator":
        return 0.86
    return 0.55


def _builtin_reason(role: str, emotion: str) -> str:
    if role in {"male", "female"} and emotion:
        return f"Best built-in {role} preset for dominant emotion '{emotion}'."
    if role == "narrator":
        return "Stable built-in narrator preset."
    return "Fallback built-in preset for unresolved role."


def _category_from_preset_id(preset_id: str) -> str:
    prefix = preset_id.split("_", 1)[0]
    return prefix if prefix in {"narrator", "male", "female"} else "unknown"


def _key(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = _key(value)
        if value and key not in seen:
            result.append(value)
            seen.add(key)
    return result


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
