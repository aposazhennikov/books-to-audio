"""Voice profile configuration for multi-voice TTS synthesis."""

from __future__ import annotations

import json
import logging
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class VoiceMethod(str, Enum):
    """How a voice is produced."""

    CLONE = "clone"
    DESIGN = "design"
    CUSTOM = "custom"


class VoiceProfile(BaseModel):
    """Configuration for a single TTS voice."""

    name: str = ""
    method: VoiceMethod = VoiceMethod.CLONE
    ref_audio: str = ""
    ref_text: str = ""
    design_instruct: str = ""
    speaker: str = ""
    language: str = "Russian"

    def validate_for_method(self) -> list[str]:
        """Return a list of validation errors, empty if valid."""
        errors: list[str] = []
        if self.method == VoiceMethod.CLONE:
            if not self.ref_audio:
                errors.append(f"Voice '{self.name}': clone method requires ref_audio.")
            if not self.ref_text:
                errors.append(f"Voice '{self.name}': clone method requires ref_text.")
        elif self.method == VoiceMethod.DESIGN:
            if not self.design_instruct:
                errors.append(
                    f"Voice '{self.name}': design method requires design_instruct."
                )
        elif self.method == VoiceMethod.CUSTOM:
            if not self.speaker:
                errors.append(f"Voice '{self.name}': custom method requires speaker.")
        return errors


class VoiceConfig(BaseModel):
    """Top-level configuration mapping speaker roles to voice profiles."""

    narrator: VoiceProfile = Field(
        default_factory=lambda: VoiceProfile(name="narrator")
    )
    male: VoiceProfile = Field(
        default_factory=lambda: VoiceProfile(name="male")
    )
    female: VoiceProfile = Field(
        default_factory=lambda: VoiceProfile(name="female")
    )

    def validate_all(self) -> list[str]:
        """Validate all voice profiles and return errors."""
        errors: list[str] = []
        errors.extend(self.narrator.validate_for_method())
        errors.extend(self.male.validate_for_method())
        errors.extend(self.female.validate_for_method())
        return errors

    def get_profile(self, voice_id: str) -> VoiceProfile:
        """Look up a voice profile by its role id."""
        mapping = {
            "narrator": self.narrator,
            "male": self.male,
            "female": self.female,
        }
        if voice_id not in mapping:
            raise KeyError(f"Unknown voice_id: {voice_id}")
        return mapping[voice_id]

    @classmethod
    def from_json(cls, path: Path) -> VoiceConfig:
        """Load voice configuration from a JSON file."""
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(**data)

    def to_json(self, path: Path) -> None:
        """Save voice configuration to a JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            self.model_dump_json(indent=2, exclude_none=True),
            encoding="utf-8",
        )

    @classmethod
    def default_clone_config(cls) -> VoiceConfig:
        """Create a config template for voice cloning (all fields blank)."""
        return cls(
            narrator=VoiceProfile(
                name="narrator",
                method=VoiceMethod.CLONE,
            ),
            male=VoiceProfile(
                name="male",
                method=VoiceMethod.CLONE,
            ),
            female=VoiceProfile(
                name="female",
                method=VoiceMethod.CLONE,
            ),
        )

    @classmethod
    def default_custom_voice_config(cls) -> VoiceConfig:
        """Create a config using Qwen3-TTS built-in CustomVoice speakers."""
        return cls(
            narrator=VoiceProfile(
                name="narrator",
                method=VoiceMethod.CUSTOM,
                speaker="Aiden",
                language="Russian",
            ),
            male=VoiceProfile(
                name="male",
                method=VoiceMethod.CUSTOM,
                speaker="Ryan",
                language="Russian",
            ),
            female=VoiceProfile(
                name="female",
                method=VoiceMethod.CUSTOM,
                speaker="Serena",
                language="Russian",
            ),
        )
