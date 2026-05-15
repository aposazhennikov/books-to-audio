"""Voice manager — loads TTS models and prepares reusable voice prompts."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from book_normalizer.tts.model_paths import describe_model_resolution
from book_normalizer.tts.voice_config import VoiceConfig, VoiceMethod, VoiceProfile
from book_normalizer.tts.voice_library import (
    default_voice_library_dir,
    load_voice_prompt,
    resolve_saved_voice_path,
)

logger = logging.getLogger(__name__)

BASE_MODEL_NAME = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
DESIGN_MODEL_NAME = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
CUSTOM_VOICE_MODEL_NAME = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"


class VoiceManager:
    """Manages Qwen3-TTS model loading and voice prompt creation.

    Caches voice_clone_prompt objects so they are computed once per
    voice and reused across all chunks of that voice.
    """

    def __init__(
        self,
        config: VoiceConfig,
        device: str = "cuda:0",
        dtype: str = "bfloat16",
        use_flash_attn: bool = True,
        models_dir: str | None = None,
        voice_library_dir: str | None = None,
    ) -> None:
        self._config = config
        self._device = device
        self._dtype = dtype
        self._use_flash_attn = use_flash_attn
        self._models_dir = models_dir
        self._voice_library_dir = Path(voice_library_dir) if voice_library_dir else default_voice_library_dir()
        self._base_model: Any = None
        self._design_model: Any = None
        self._custom_model: Any = None
        self._clone_prompts: dict[str, Any] = {}

    @property
    def config(self) -> VoiceConfig:
        """Return the voice configuration."""
        return self._config

    def initialize(self) -> None:
        """Load required TTS models based on voice config methods."""
        methods = {
            self._config.narrator.method,
            self._config.male.method,
            self._config.female.method,
        }

        if (
            VoiceMethod.CLONE in methods
            or VoiceMethod.DESIGN in methods
            or VoiceMethod.SAVED in methods
        ):
            self._load_base_model()

        if VoiceMethod.DESIGN in methods:
            self._load_design_model()

        if VoiceMethod.CUSTOM in methods:
            self._load_custom_voice_model()

        self._prepare_clone_prompts()
        logger.info("VoiceManager initialized: %d voice prompts ready", len(self._clone_prompts))

    def get_clone_prompt(self, voice_id: str) -> Any:
        """Return the cached voice_clone_prompt for a given voice_id."""
        if voice_id not in self._clone_prompts:
            raise KeyError(
                f"No clone prompt for voice_id='{voice_id}'. "
                f"Available: {list(self._clone_prompts.keys())}"
            )
        return self._clone_prompts[voice_id]

    def get_model(self) -> Any:
        """Return the loaded base model for synthesis calls."""
        if self._base_model is None:
            raise RuntimeError("Base model not loaded. Call initialize() first.")
        return self._base_model

    def get_custom_voice_model(self) -> Any:
        """Return the loaded CustomVoice model."""
        if self._custom_model is None:
            raise RuntimeError("CustomVoice model not loaded.")
        return self._custom_model

    def get_profile(self, voice_id: str) -> VoiceProfile:
        """Return the voice profile for a given voice_id."""
        return self._config.get_profile(voice_id)

    def _load_base_model(self) -> None:
        """Load Qwen3-TTS Base model for voice cloning."""
        try:
            import torch
            from qwen_tts import Qwen3TTSModel

            dtype = getattr(torch, self._dtype, torch.bfloat16)
            kwargs: dict[str, Any] = {
                "device_map": self._device,
                "dtype": dtype,
            }
            if self._use_flash_attn:
                kwargs["attn_implementation"] = "flash_attention_2"

            model_name = self._resolve_model(BASE_MODEL_NAME)
            logger.info("Loading %s on %s...", model_name, self._device)
            self._base_model = Qwen3TTSModel.from_pretrained(
                model_name, **kwargs
            )
            logger.info("Base model loaded.")
        except ImportError as exc:
            raise ImportError(
                "qwen-tts and torch are required: pip install qwen-tts torch"
            ) from exc

    def _load_design_model(self) -> None:
        """Load Qwen3-TTS VoiceDesign model."""
        try:
            import torch
            from qwen_tts import Qwen3TTSModel

            dtype = getattr(torch, self._dtype, torch.bfloat16)
            kwargs: dict[str, Any] = {
                "device_map": self._device,
                "dtype": dtype,
            }
            if self._use_flash_attn:
                kwargs["attn_implementation"] = "flash_attention_2"

            model_name = self._resolve_model(DESIGN_MODEL_NAME)
            logger.info("Loading %s on %s...", model_name, self._device)
            self._design_model = Qwen3TTSModel.from_pretrained(
                model_name, **kwargs
            )
            logger.info("VoiceDesign model loaded.")
        except ImportError as exc:
            raise ImportError(
                "qwen-tts and torch are required: pip install qwen-tts torch"
            ) from exc

    def _load_custom_voice_model(self) -> None:
        """Load Qwen3-TTS CustomVoice model."""
        try:
            import torch
            from qwen_tts import Qwen3TTSModel

            dtype = getattr(torch, self._dtype, torch.bfloat16)
            kwargs: dict[str, Any] = {
                "device_map": self._device,
                "dtype": dtype,
            }
            if self._use_flash_attn:
                kwargs["attn_implementation"] = "flash_attention_2"

            model_name = self._resolve_model(CUSTOM_VOICE_MODEL_NAME)
            logger.info("Loading %s on %s...", model_name, self._device)
            self._custom_model = Qwen3TTSModel.from_pretrained(
                model_name, **kwargs
            )
            logger.info("CustomVoice model loaded.")
        except ImportError as exc:
            raise ImportError(
                "qwen-tts and torch are required: pip install qwen-tts torch"
            ) from exc

    def _prepare_clone_prompts(self) -> None:
        """Build reusable voice_clone_prompt for each clone-type voice."""
        for voice_id in ("narrator", "male", "female"):
            profile = self._config.get_profile(voice_id)
            if profile.method == VoiceMethod.CLONE:
                self._build_clone_prompt(voice_id, profile)
            elif profile.method == VoiceMethod.DESIGN:
                self._build_design_then_clone_prompt(voice_id, profile)
            elif profile.method == VoiceMethod.SAVED:
                self._load_saved_clone_prompt(voice_id, profile)

    def _build_clone_prompt(self, voice_id: str, profile: VoiceProfile) -> None:
        """Create a voice_clone_prompt from a reference audio file."""
        if not self._base_model:
            return
        if not profile.ref_audio or not profile.ref_text:
            logger.warning(
                "Skipping clone prompt for '%s': missing ref_audio or ref_text.", voice_id
            )
            return

        logger.info("Building clone prompt for '%s' from %s", voice_id, profile.ref_audio)
        prompt = self._base_model.create_voice_clone_prompt(
            ref_audio=profile.ref_audio,
            ref_text=profile.ref_text,
        )
        self._clone_prompts[voice_id] = prompt

    def _build_design_then_clone_prompt(
        self, voice_id: str, profile: VoiceProfile
    ) -> None:
        """Design a voice, then build a clone prompt from the result."""
        if not self._design_model or not self._base_model:
            return

        logger.info("Designing voice for '%s': %s", voice_id, profile.design_instruct[:80])
        ref_text = profile.ref_text or "This is a reference sentence for voice design."
        wavs, sr = self._design_model.generate_voice_design(
            text=ref_text,
            language=profile.language,
            instruct=profile.design_instruct,
        )

        prompt = self._base_model.create_voice_clone_prompt(
            ref_audio=(wavs[0], sr),
            ref_text=ref_text,
        )
        self._clone_prompts[voice_id] = prompt
        logger.info("Design+clone prompt ready for '%s'.", voice_id)

    def _load_saved_clone_prompt(self, voice_id: str, profile: VoiceProfile) -> None:
        """Load a persisted voice clone prompt from the local library."""
        source = profile.voice_prompt_path or profile.saved_voice
        if not source:
            logger.warning("Skipping saved voice for '%s': no source configured.", voice_id)
            return
        prompt_path = (
            Path(profile.voice_prompt_path)
            if profile.voice_prompt_path
            else resolve_saved_voice_path(profile.saved_voice, self._voice_library_dir)
        )
        logger.info("Loading saved voice prompt for '%s' from %s", voice_id, prompt_path)
        self._clone_prompts[voice_id] = load_voice_prompt(prompt_path, map_location=self._device)

    def _resolve_model(self, model_name: str) -> str:
        """Resolve a model id to the shared ComfyUI model folder when present."""
        resolved, is_local = describe_model_resolution(
            model_name,
            models_dir=self._models_dir,
        )
        if is_local:
            logger.info("Using local model folder: %s", resolved)
        return resolved
