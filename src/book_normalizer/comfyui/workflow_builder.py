"""ComfyUI workflow builder for Qwen3-TTS synthesis.

The template file ``comfyui_workflows/qwen3_tts_template.json`` is already
included in the project and works with the FB_Qwen3TTSCustomVoice node from
the ComfyUI-Qwen-TTS custom-node pack.

Placeholder reference
---------------------
``"{{TEXT}}"``             — Russian text to synthesise.
``"{{SPEAKER}}"``          — FB_Qwen3TTSCustomVoice speaker name
                             (Aiden / Ryan / Serena, resolved from voice_label).
``"{{INSTRUCT}}"``         — Russian-language style instruction derived from
                             voice_label + voice_tone.
``"{{OUTPUT_FILENAME}}"``  — Filename prefix passed to SaveAudio
                             (e.g. ``"chunk_001_narrator"``).

Voice-label → speaker mapping
------------------------------
The v2 manifest uses three voice labels.  Each maps to a preset speaker from
the FB_Qwen3TTSCustomVoice dropdown::

    narrator  →  "Aiden"   (calm, clear male narrator)
    men       →  "Ryan"    (young male character)
    women     →  "Serena"  (warm female character)

Override the mapping at runtime by subclassing or modifying VOICE_LABEL_TO_SPEAKER.

voice_tone → instruct mapping
------------------------------
``voice_tone`` is a free-form English string produced by the LLM chunker
(e.g. ``"calm"``, ``"angry and tense"``, ``"warm and gentle"``).  The first
word is matched against TONE_TO_RUSSIAN; unrecognised tones fall back to
``"Ровно и чётко."``.  The final instruct combines a role prefix with the
tone sentence::

    narrator + calm   → "Голос рассказчика. Спокойно и размеренно."
    men      + angry  → "Мужской персонаж. Жёстко и напряжённо."
    women    + sad    → "Женский персонаж. Грустно, немного замедленно."
"""

from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Voice-label → FB_Qwen3TTSCustomVoice speaker name ────────────────────────

VOICE_LABEL_TO_SPEAKER: dict[str, str] = {
    "narrator": "Aiden",
    "men": "Ryan",
    "women": "Serena",
}

# ── Role-prefix instruct sentences ────────────────────────────────────────────

_ROLE_PREFIX: dict[str, str] = {
    "narrator": "Голос рассказчика.",
    "men": "Мужской персонаж.",
    "women": "Женский персонаж.",
}

# ── First-word tone → Russian instruct sentence ───────────────────────────────

TONE_TO_RUSSIAN: dict[str, str] = {
    "calm": "Спокойно и размеренно.",
    "neutral": "Ровно и чётко.",
    "happy": "Радостно и бодро.",
    "excited": "Взволнованно и экспрессивно.",
    "sad": "Грустно, немного замедленно.",
    "angry": "Жёстко и напряжённо.",
    "tense": "Напряжённо, настороженно.",
    "whisper": "Тихо, почти шёпотом.",
    "warm": "Тепло и по-дружески.",
    "gentle": "Мягко и нежно.",
    "cold": "Холодно и отстранённо.",
    "fearful": "Со страхом в голосе.",
    "surprised": "Удивлённо.",
}

_DEFAULT_TONE_RU = "Ровно и чётко."

# ── Placeholder tokens ────────────────────────────────────────────────────────

# Single-chunk template (qwen3_tts_template.json).
_PLACEHOLDER_TEXT = "{{TEXT}}"
_PLACEHOLDER_SPEAKER = "{{SPEAKER}}"
_PLACEHOLDER_INSTRUCT = "{{INSTRUCT}}"
_PLACEHOLDER_OUTPUT = "{{OUTPUT_FILENAME}}"
# Legacy alias kept for backward-compatibility with hand-crafted templates.
_PLACEHOLDER_VOICE_ID = "{{VOICE_ID}}"

# Dialogue template (qwen3_dialogue_template.json).
_PLACEHOLDER_SCRIPT = "{{SCRIPT}}"
_PLACEHOLDER_NARRATOR = "{{NARRATOR_SPEAKER}}"
_PLACEHOLDER_MEN = "{{MEN_SPEAKER}}"
_PLACEHOLDER_WOMEN = "{{WOMEN_SPEAKER}}"

# Voice-setup template (voice_setup_template.json).
_PLACEHOLDER_AUDIO_FILE = "{{AUDIO_FILENAME}}"
_PLACEHOLDER_VOICE_NAME = "{{VOICE_NAME}}"
_PLACEHOLDER_REF_TEXT = "{{REF_TEXT}}"

_ALL_PLACEHOLDERS = (
    _PLACEHOLDER_TEXT,
    _PLACEHOLDER_SPEAKER,
    _PLACEHOLDER_INSTRUCT,
    _PLACEHOLDER_OUTPUT,
)


class WorkflowBuilderError(Exception):
    """Raised when the template is missing or malformed."""


class WorkflowBuilder:
    """Load a ComfyUI API-format JSON template and substitute synthesis parameters.

    The builder performs a deep recursive scan of the workflow dict,
    replacing placeholder strings with actual values.  This approach is
    format-agnostic — it works regardless of which ComfyUI node types or
    IDs are used, as long as the placeholder strings are present in the
    correct input fields.
    """

    def __init__(self, template_path: str | Path) -> None:
        self._template_path = Path(template_path)
        self._template = self._load_template()
        self._warn_missing_placeholders()

    # ── Public API ──────────────────────────────────────────────────────────

    def build(
        self,
        text: str,
        voice_label: str,
        voice_tone: str,
        output_filename: str,
    ) -> dict[str, Any]:
        """Return a workflow dict with all placeholders substituted.

        Args:
            text: Russian text to synthesise.
            voice_label: Role label from the v2 manifest: ``narrator`` / ``men`` / ``women``.
            voice_tone: Free-form English tone string from the LLM chunker
                (e.g. ``"calm"``, ``"angry and tense"``).
            output_filename: Desired filename prefix (e.g. ``"chunk_001_narrator"``).

        Returns:
            A deep copy of the template with all placeholders replaced.
        """
        speaker = voice_label_to_speaker(voice_label)
        instruct = voice_tone_to_instruct(voice_label, voice_tone)
        replacements = {
            _PLACEHOLDER_TEXT: text,
            _PLACEHOLDER_SPEAKER: speaker,
            # Keep backward-compat: some old templates may still use {{VOICE_ID}}.
            _PLACEHOLDER_VOICE_ID: speaker,
            _PLACEHOLDER_INSTRUCT: instruct,
            _PLACEHOLDER_OUTPUT: output_filename,
        }
        return _deep_replace(copy.deepcopy(self._template), replacements)

    def build_dialogue(
        self,
        script: str,
        narrator_speaker: str,
        men_speaker: str,
        women_speaker: str,
        output_filename: str,
    ) -> dict[str, Any]:
        """Return a dialogue workflow with role-speaker bindings substituted.

        Intended for use with ``qwen3_dialogue_template.json`` +
        ``FB_Qwen3TTSDialogueInference``.  The ``script`` parameter must
        already be formatted as ``"narrator: ...\nmen: ...\nwomen: ...\n"``.

        Args:
            script: Full dialogue script for one chapter.
            narrator_speaker: Saved-voice name for the narrator role.
            men_speaker: Saved-voice name for the male character role.
            women_speaker: Saved-voice name for the female character role.
            output_filename: Filename prefix for SaveAudio.

        Returns:
            A deep copy of the template with all placeholders replaced.
        """
        replacements = {
            _PLACEHOLDER_SCRIPT: script,
            _PLACEHOLDER_NARRATOR: narrator_speaker,
            _PLACEHOLDER_MEN: men_speaker,
            _PLACEHOLDER_WOMEN: women_speaker,
            _PLACEHOLDER_OUTPUT: output_filename,
        }
        return _deep_replace(copy.deepcopy(self._template), replacements)

    def build_voice_setup(
        self,
        audio_filename: str,
        voice_name: str,
        ref_text: str,
    ) -> dict[str, Any]:
        """Return a voice-setup workflow to clone and save a speaker.

        Intended for use with ``voice_setup_template.json``.

        Args:
            audio_filename: Filename as returned by ``ComfyUIClient.upload_audio()``.
            voice_name: Desired speaker name (e.g. ``"narrator"``).
            ref_text: Transcript of the reference audio (improves clone quality).

        Returns:
            A deep copy of the template with all placeholders replaced.
        """
        replacements = {
            _PLACEHOLDER_AUDIO_FILE: audio_filename,
            _PLACEHOLDER_VOICE_NAME: voice_name,
            _PLACEHOLDER_REF_TEXT: ref_text,
        }
        return _deep_replace(copy.deepcopy(self._template), replacements)

    @staticmethod
    def voice_tone_to_instruct(voice_label: str, voice_tone: str) -> str:
        """Translate a voice_label + voice_tone pair to a Russian instruct string."""
        return voice_tone_to_instruct(voice_label, voice_tone)

    # ── Internal helpers ────────────────────────────────────────────────────

    def _load_template(self) -> dict[str, Any]:
        """Read and parse the JSON template file."""
        if not self._template_path.exists():
            raise WorkflowBuilderError(
                f"ComfyUI workflow template not found: {self._template_path}\n"
                "See the module docstring for instructions on how to create it."
            )
        try:
            data = json.loads(
                self._template_path.read_text(encoding="utf-8")
            )
        except json.JSONDecodeError as exc:
            raise WorkflowBuilderError(
                f"Invalid JSON in workflow template {self._template_path}: {exc}"
            ) from exc
        if not isinstance(data, dict):
            raise WorkflowBuilderError(
                f"Workflow template must be a JSON object (dict), got {type(data).__name__}"
            )
        return data

    def _warn_missing_placeholders(self) -> None:
        """Log a warning for each placeholder that is absent from the template."""
        template_str = json.dumps(self._template)
        missing = [p for p in _ALL_PLACEHOLDERS if p not in template_str]
        if missing:
            logger.warning(
                "Workflow template %s is missing placeholder(s): %s — "
                "synthesis parameters may not be applied correctly.",
                self._template_path.name,
                ", ".join(missing),
            )


# ── Module-level helpers ──────────────────────────────────────────────────────


def voice_label_to_speaker(voice_label: str) -> str:
    """Return the FB_Qwen3TTSCustomVoice speaker name for a voice label.

    Falls back to the narrator speaker for unknown labels.
    """
    return VOICE_LABEL_TO_SPEAKER.get(voice_label, VOICE_LABEL_TO_SPEAKER["narrator"])


def voice_tone_to_instruct(voice_label: str, voice_tone: str) -> str:
    """Build a Russian-language instruct string from voice_label + free-form voice_tone.

    The first word of ``voice_tone`` is used as the tone key; unrecognised
    first words fall back to the default neutral sentence.
    """
    role_prefix = _ROLE_PREFIX.get(voice_label, _ROLE_PREFIX["narrator"])
    # Use only the first word for lookup to tolerate compound tones like "angry and tense".
    first_word = voice_tone.strip().lower().split()[0] if voice_tone.strip() else ""
    tone_sentence = TONE_TO_RUSSIAN.get(first_word, _DEFAULT_TONE_RU)
    return f"{role_prefix} {tone_sentence}"


def _deep_replace(
    obj: Any, replacements: dict[str, str]
) -> Any:
    """Recursively replace placeholder strings in a nested dict/list structure."""
    if isinstance(obj, str):
        for placeholder, value in replacements.items():
            if obj == placeholder:
                return value
            if placeholder in obj:
                obj = obj.replace(placeholder, value)
        return obj

    if isinstance(obj, dict):
        return {k: _deep_replace(v, replacements) for k, v in obj.items()}

    if isinstance(obj, list):
        return [_deep_replace(item, replacements) for item in obj]

    return obj
