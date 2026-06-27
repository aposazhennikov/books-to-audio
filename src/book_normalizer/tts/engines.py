"""Registry of TTS engines and their downloadable model repositories."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TTSEngine:
    """A selectable TTS engine family."""

    engine_id: str
    display_name: str
    model_ids: tuple[str, ...]
    backend: str = "comfyui"
    recommended: bool = False
    default: bool = False
    runnable: bool = False
    notes: str = ""

    @property
    def primary_model_id(self) -> str:
        """Return the model id used when a UI needs one representative value."""
        return self.model_ids[0]


QWEN3_TTS_CUSTOM_VOICE_17B = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
QWEN3_TTS_CUSTOM_VOICE_06B = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
QWEN3_TTS_BASE_17B = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
QWEN3_TTS_BASE_06B = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
QWEN3_TTS_VOICE_DESIGN_17B = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
QWEN3_TTS_TOKENIZER = "Qwen/Qwen3-TTS-Tokenizer-12Hz"

FISH_SPEECH_15 = "fishaudio/fish-speech-1.5"
F5_TTS = "SWivid/F5-TTS"
XTTS_V2 = "coqui/XTTS-v2"
COSYVOICE_3 = "FunAudioLLM/Fun-CosyVoice3-0.5B-2512"

TTS_ENGINES: tuple[TTSEngine, ...] = (
    TTSEngine(
        engine_id="qwen3-customvoice-1.7b",
        display_name="Qwen3 CustomVoice 1.7B (recommended)",
        model_ids=(QWEN3_TTS_CUSTOM_VOICE_17B,),
        recommended=True,
        default=True,
        runnable=True,
        notes="Best integrated option for the current ComfyUI workflow.",
    ),
    TTSEngine(
        engine_id="qwen3-customvoice-0.6b",
        display_name="Qwen3 CustomVoice 0.6B",
        model_ids=(QWEN3_TTS_CUSTOM_VOICE_06B,),
        runnable=True,
        notes="Lighter Qwen3 option for previews and lower VRAM.",
    ),
    TTSEngine(
        engine_id="fish-speech-1.5",
        display_name="Fish Speech v1.5",
        model_ids=(FISH_SPEECH_15,),
        backend="local-command",
        runnable=True,
        notes="Runs through the local Fish Speech CLI adapter.",
    ),
    TTSEngine(
        engine_id="f5-tts",
        display_name="F5-TTS",
        model_ids=(F5_TTS,),
        backend="local-command",
        runnable=True,
        notes="Runs through the local F5-TTS CLI adapter.",
    ),
    TTSEngine(
        engine_id="xtts-v2",
        display_name="XTTS v2",
        model_ids=(XTTS_V2,),
        backend="local-command",
        runnable=True,
        notes="Runs through the local XTTS/Coqui CLI adapter.",
    ),
    TTSEngine(
        engine_id="cosyvoice-3",
        display_name="CosyVoice 3",
        model_ids=(COSYVOICE_3,),
        backend="local-command",
        runnable=True,
        notes="Runs through the local CosyVoice CLI adapter.",
    ),
)


DEFAULT_TTS_ENGINE_ID = "qwen3-customvoice-1.7b"
RECOMMENDED_TTS_ENGINE_ID = DEFAULT_TTS_ENGINE_ID
RUNNABLE_TTS_BACKENDS = {"comfyui", "local-command"}


def get_tts_engine(engine_id_or_model_id: str) -> TTSEngine | None:
    """Resolve an engine by id, display name, or any model id it owns."""
    needle = str(engine_id_or_model_id or "").strip()
    if not needle:
        return None
    for engine in TTS_ENGINES:
        if needle in {engine.engine_id, engine.display_name, *engine.model_ids}:
            return engine
    return None


def tts_engine_choices() -> list[tuple[str, str]]:
    """Return ``(display_name, engine_id)`` pairs for GUI selectors."""
    return [(engine.display_name, engine.engine_id) for engine in TTS_ENGINES]


def tts_model_ids_for_engine(engine_id_or_model_id: str) -> tuple[str, ...]:
    """Return model ids for a known engine, or the original value as a model id."""
    engine = get_tts_engine(engine_id_or_model_id)
    if engine:
        return engine.model_ids
    value = str(engine_id_or_model_id or "").strip()
    return (value,) if value else ()


def unsupported_tts_engine_message(engine_id_or_model_id: str) -> str | None:
    """Return an actionable message when an engine cannot synthesize yet."""
    engine = get_tts_engine(engine_id_or_model_id)
    if engine is None or engine.runnable:
        return None
    return (
        f"{engine.display_name} models can be downloaded, but synthesis is not wired yet. "
        f"Current runnable backend: Qwen3 CustomVoice via ComfyUI. "
        f"Missing backend: {engine.backend}."
    )
