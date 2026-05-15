#!/usr/bin/env python3
"""WSL TTS runner — synthesizes audio from voice-annotated chunks using Qwen3-TTS.

Usage:
    source ~/venvs/qwen3tts/bin/activate
    python scripts/tts_runner.py --chunks-json output/chunks_manifest.json --out output/master_magii_1_pdf

Voice cloning:
    python scripts/tts_runner.py --chunks-json ... --out ... \
        --clone-config clone_voices.json

    clone_voices.json example:
    {
      "narrator_calm": {"ref_audio": "/path/to/ref.wav", "ref_text": "Transcript."},
      "male_young":    {"ref_audio": "/path/to/ref2.wav", "ref_text": "Transcript 2."}
    }

    Voices listed in clone-config use the Base model (voice cloning).
    All other voices fall back to CustomVoice presets as before.

This script runs inside WSL with CUDA access. It reads a JSON manifest
produced by the book normalizer pipeline and generates WAV files for
each chunk using the appropriate voice.
"""

from __future__ import annotations

# Suppress harmless warnings before any library imports.
# OnnxRuntime: DRM device discovery fails in WSL2 (CUDA works via separate path).
# Transformers: flash_attn dtype advisory is a false positive when using Qwen3TTSModel.
import os

os.environ.setdefault("ORT_LOGGING_LEVEL", "3")          # OnnxRuntime: errors only.
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")  # HuggingFace: no tips.

import argparse
import json
import random
import signal
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import soundfile as sf

from book_normalizer.tts.model_paths import (
    default_comfyui_models_dir,
    describe_model_resolution,
)


class ChunkTimeoutError(Exception):
    """Raised when a single chunk synthesis exceeds the timeout."""


def _timeout_handler(signum, frame):
    raise ChunkTimeoutError("Chunk synthesis timed out.")

# Legacy instruct prompts (backward compat for old manifests).
INSTRUCT_MAP = {
    "narrator": "Спокойный, чёткий голос рассказчика. Читай размеренно, не торопись.",
    "male": "Уверенный мужской голос. Говори с эмоцией. Естественные интонации.",
    "female": "Мягкий женский голос. Говори с эмоцией. Естественные интонации.",
}

# Legacy speaker mapping (backward compat for old manifests).
LEGACY_SPEAKER_MAP = {
    "narrator": "Aiden",
    "male": "Ryan",
    "female": "Serena",
}

# Extended voice presets: voice_id -> (speaker, instruct).
VOICE_PRESETS = {
    "narrator_calm": ("Aiden", "Спокойный, чёткий голос рассказчика. Читай размеренно, не торопись."),
    "narrator_energetic": ("Ryan", "Энергичный, уверенный голос рассказчика. Читай бодро."),
    "narrator_wise": ("Uncle_Fu", "Мудрый голос рассказчика. Читай неторопливо, с глубиной."),
    "male_young": ("Ryan", "Молодой мужской голос. Говори с эмоцией. Естественные интонации."),
    "male_confident": ("Aiden", "Уверенный мужской голос. Говори чётко и решительно."),
    "male_deep": ("Uncle_Fu", "Глубокий мужской голос. Говори с достоинством и весомостью."),
    "male_lively": ("Dylan", "Живой, весёлый мужской голос. Говори бодро, с юмором."),
    "male_regional": ("Eric", "Яркий мужской голос с характером. Говори экспрессивно."),
    "female_warm": ("Serena", "Мягкий, тёплый женский голос. Говори нежно, с теплотой."),
    "female_bright": ("Vivian", "Яркий, звонкий женский голос. Говори выразительно."),
    "female_playful": ("Ono_Anna", "Игривый женский голос. Говори легко, с улыбкой."),
    "female_gentle": ("Sohee", "Нежный, мелодичный женский голос. Говори спокойно и ласково."),
}

# Default Base model for voice cloning.
BASE_MODEL_NAME = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"


def resolve_voice(voice_id: str, speaker_map: dict) -> tuple[str, str]:
    """Resolve voice_id to (speaker, instruct), supporting both legacy and new presets."""
    if voice_id in VOICE_PRESETS:
        return VOICE_PRESETS[voice_id]
    speaker = speaker_map.get(voice_id, LEGACY_SPEAKER_MAP.get(voice_id, "Aiden"))
    instruct = INSTRUCT_MAP.get(voice_id, "")
    return speaker, instruct


def _detect_attn_impl(use_sage: bool = False) -> str:
    """Pick the best attention implementation available.

    Priority: flash_attention_2 > sdpa.
    When use_sage=True, we always return 'sdpa' because SageAttention
    replaces the SDPA kernel via monkey-patch.
    """
    if use_sage:
        return "sdpa"
    try:
        import flash_attn  # noqa: F401
        return "flash_attention_2"
    except ImportError:
        return "sdpa"


_sage_enabled = False


class SageAttentionUnavailableError(RuntimeError):
    """Raised when SageAttention was explicitly requested but cannot run."""

# Ordered preference list for SageAttention kernels.
#   v2-only functions (available from GitHub install) first,
#   then v1 sageattn (available from pip install sageattention==1.0.6).
#
# PyPI ships v1.0.6 which has ONLY sageattn() — INT8 QK + FP16 PV natively.
# GitHub v2+ adds separate kernels with FP8 PV / configurable accumulators.
#
# smooth_k=False is critical for autoregressive TTS: smooth_k subtracts
# the K-mean at each step, which drifts as the KV-cache grows and causes
# accumulated quantization error → NaN in logits → CUDA device assert.
_SAGE_CANDIDATES = [
    # (function_name, extra_kwargs, label).
    # v2: FP16 PV + FP32 accumulator — most numerically stable.
    (
        "sageattn_qk_int8_pv_fp16_cuda",
        {"pv_accum_dtype": "fp32", "smooth_k": False},
        "v2 qk_int8_pv_fp16_cuda (pv_accum=fp32, no_smooth)",
    ),
    # v2: FP16 PV via pure Triton — no compiled CUDA modules needed.
    (
        "sageattn_qk_int8_pv_fp16_triton",
        {"smooth_k": False},
        "v2 qk_int8_pv_fp16_triton (no_smooth)",
    ),
    # v1 (PyPI 1.0.6): INT8 QK + FP16 PV + Triton kernels.
    (
        "sageattn",
        {"smooth_k": False},
        "v1 sageattn (qk_int8_pv_fp16, no_smooth)",
    ),
]


def _resolve_sage_fn():
    """Find the best available SageAttention kernel function.

    Probes sageattention.core first (v2 has all functions there),
    then the package root. Uses getattr so missing symbols never raise.
    Returns (callable, extra_kwargs_dict, label) or (None, {}, "").
    """
    import importlib

    modules_to_check = []
    for mod_name in ("sageattention.core", "sageattention"):
        try:
            modules_to_check.append(importlib.import_module(mod_name))
        except Exception:
            pass

    if not modules_to_check:
        return None, {}, ""

    for func_name, extra_kw, label in _SAGE_CANDIDATES:
        for mod in modules_to_check:
            fn = getattr(mod, func_name, None)
            if fn is not None:
                print(f"[sage] Found {func_name} in {mod.__name__}.")
                sys.stdout.flush()
                return fn, extra_kw, label

    avail = []
    for mod in modules_to_check:
        avail.extend(
            n for n in dir(mod)
            if n.startswith("sage") and callable(getattr(mod, n, None))
        )
    print(f"[sage] No candidate matched. Available: {avail}")
    sys.stdout.flush()
    return None, {}, ""


def _apply_sage_attention(required: bool = False) -> bool:
    """Replace F.scaled_dot_product_attention with a SageAttention wrapper.

    Searches for the most numerically-stable kernel available:
      1) sageattn_qk_int8_pv_fp16_cuda  — v2 FP16 PV, FP32 accumulator.
      2) sageattn_qk_int8_pv_fp16_triton — v2 FP16 PV, pure Triton.
      3) sageattn                        — v1 INT8 QK + FP16 PV (PyPI 1.0.6).

    Falls back to the original SDPA when attn_mask or dropout is present.

    Returns True if SageAttention was installed successfully.
    Raises SageAttentionUnavailableError when ``required`` is True and no
    compatible kernel can be installed.
    """
    global _sage_enabled  # noqa: PLW0603
    if _sage_enabled:
        return True

    try:
        import importlib.util

        import torch  # noqa: F401
        import torch.nn.functional as F  # noqa: N812

        sage_installed = importlib.util.find_spec("sageattention") is not None
        chosen_fn, extra_kw, variant = _resolve_sage_fn()

        if chosen_fn is None:
            if sage_installed:
                message = (
                    "sageattention is installed, but no compatible SageAttention "
                    "kernel was found."
                )
            else:
                message = "sageattention is not installed in the active Python environment."
            prefix = "ERROR" if required else "WARNING"
            print(f"[sage] {prefix}: {message}")
            sys.stdout.flush()
            if required:
                raise SageAttentionUnavailableError(message)
            return False

        _original_sdpa = F.scaled_dot_product_attention
        _sage_runtime_warned = False

        def _sage_wrapper(
            query, key, value,
            attn_mask=None, dropout_p=0.0, is_causal=False, scale=None,
            **kwargs,
        ):
            nonlocal _sage_runtime_warned
            if attn_mask is not None or dropout_p > 0.0 or kwargs.get("enable_gqa"):
                return _original_sdpa(
                    query, key, value,
                    attn_mask=attn_mask, dropout_p=dropout_p,
                    is_causal=is_causal, scale=scale, **kwargs,
                )
            try:
                sage_kwargs = {
                    "tensor_layout": "HND",
                    "is_causal": is_causal,
                    **extra_kw,
                }
                if scale is not None:
                    sage_kwargs["sm_scale"] = scale
                return chosen_fn(query, key, value, **sage_kwargs)
            except Exception as exc:
                if not _sage_runtime_warned:
                    print(
                        "[sage] WARNING: SageAttention kernel call failed "
                        f"({type(exc).__name__}: {exc}); falling back to SDPA "
                        "for this call shape."
                    )
                    sys.stdout.flush()
                    _sage_runtime_warned = True
                return _original_sdpa(
                    query, key, value,
                    attn_mask=attn_mask, dropout_p=dropout_p,
                    is_causal=is_causal, scale=scale, **kwargs,
                )

        F.scaled_dot_product_attention = _sage_wrapper
        _sage_enabled = True
        print(f"[sage] SageAttention installed: {variant}.")
        sys.stdout.flush()
        return True
    except ImportError as exc:
        message = (
            "SageAttention was requested but torch/sageattention cannot be "
            f"imported ({type(exc).__name__}: {exc}). Install the WSL TTS "
            "extras, e.g. pip install git+https://github.com/thu-ml/SageAttention.git"
        )
        print(f"[sage] ERROR: {message}" if required else "[sage] sageattention not installed, using default SDPA.")
        sys.stdout.flush()
        if required:
            raise SageAttentionUnavailableError(message) from exc
        return False


def _try_cuda_recover():
    """Attempt to recover CUDA state after a device-side error.

    Clears the CUDA cache and resets error state. This does NOT guarantee
    recovery — a device-side assert often corrupts the context permanently.
    """
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()
    except Exception:
        pass


def load_model(
    model_name: str,
    device: str = "cuda:0",
    use_sage: bool = False,
    models_dir: str | None = None,
):
    """Load a Qwen3-TTS model with the best available attention."""
    import torch
    from qwen_tts import Qwen3TTSModel

    if use_sage:
        _apply_sage_attention(required=True)

    want_dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    attn = _detect_attn_impl(use_sage=use_sage)
    resolved_model, is_local = describe_model_resolution(model_name, models_dir=models_dir)
    if is_local:
        print(f"Using local model folder: {resolved_model}")
    else:
        print(f"Local model not found under {models_dir or default_comfyui_models_dir()}; using {model_name}")
    print(f"Loading {resolved_model} on {device} ({want_dtype}, attn={attn})...")
    model = Qwen3TTSModel.from_pretrained(
        resolved_model,
        device_map=device,
        dtype=want_dtype,
        attn_implementation=attn,
    )

    import importlib
    fa_ok = importlib.util.find_spec("flash_attn") is not None
    sage_ok = importlib.util.find_spec("sageattention") is not None
    print(
        f"[OK] bfloat16={want_dtype}, flash_attn={fa_ok}, "
        f"sage_attn={sage_ok}, attn_impl={attn}"
    )

    print("Model loaded.")
    sys.stdout.flush()
    return model


def load_clone_config(config_path: str | None) -> dict[str, dict]:
    """Load voice clone configuration from a JSON file.

    Returns a dict mapping voice_id -> {"ref_audio": str, "ref_text": str}.
    """
    if not config_path:
        return {}
    path = Path(config_path)
    if not path.exists():
        print(f"WARNING: clone config {config_path} not found, skipping voice cloning.")
        sys.stdout.flush()
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"Loaded clone config with {len(data)} voice(s): {list(data.keys())}")
    sys.stdout.flush()
    return data


GENERATION_KWARG_NAMES = (
    "max_new_tokens",
    "top_p",
    "top_k",
    "temperature",
    "repetition_penalty",
)


def _build_generation_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    """Collect generation controls shared by CustomVoice and VoiceClone calls."""
    return {
        "max_new_tokens": args.max_new_tokens,
        "top_p": args.top_p,
        "top_k": args.top_k,
        "temperature": args.temperature,
        "repetition_penalty": args.repetition_penalty,
    }


def _set_seed(seed: int) -> None:
    """Set common RNG seeds when the user wants repeatable output."""
    if seed < 0:
        return
    random.seed(seed)
    try:
        import numpy as np

        np.random.seed(seed % (2**32 - 1))
    except Exception:
        pass
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except Exception:
        pass
    print(f"Seed: {seed}")
    sys.stdout.flush()


def _call_with_generation_kwargs(method: Any, kwargs: dict[str, Any]) -> Any:
    """Call Qwen generation while tolerating older package versions."""
    try:
        return method(**kwargs)
    except TypeError as exc:
        if not any(name in kwargs for name in GENERATION_KWARG_NAMES):
            raise
        fallback_kwargs = {
            key: value
            for key, value in kwargs.items()
            if key not in GENERATION_KWARG_NAMES
        }
        print(
            "  WARNING: installed qwen_tts rejected generation controls; "
            f"retrying with defaults ({exc})."
        )
        sys.stdout.flush()
        return method(**fallback_kwargs)


def _clone_prompt_for_voice(
    voice_id: str,
    clone_prompts: dict[str, Any] | None,
) -> Any | None:
    """Return a per-voice clone prompt or the global sample voice prompt."""
    if not clone_prompts:
        return None
    return clone_prompts.get(voice_id) or clone_prompts.get("__all__")


def _audio_extension(output_format: str) -> str:
    fmt = output_format.lower().strip()
    return "flac" if fmt == "flac" else "wav"


def build_clone_prompts(
    base_model: Any,
    clone_config: dict[str, dict],
) -> dict[str, Any]:
    """Build reusable voice_clone_prompt for each cloned voice."""
    prompts: dict[str, Any] = {}
    total = len(clone_config)
    for idx, (voice_id, cfg) in enumerate(clone_config.items(), start=1):
        ref_audio = cfg.get("ref_audio", "")
        ref_text = cfg.get("ref_text", "")
        if not ref_audio or not ref_text:
            print(
                f"  WARNING: clone voice '{voice_id}' missing ref_audio or ref_text, skipping."
            )
            continue
        if not Path(ref_audio).exists():
            print(f"  WARNING: ref_audio '{ref_audio}' not found for '{voice_id}', skipping.")
            continue
        print(f"  Building clone prompt for '{voice_id}' from {ref_audio}...")
        print(f"VOICE_PROMPT event=start done={idx - 1} total={total} voice={voice_id}")
        sys.stdout.flush()
        started = time.time()
        prompt = base_model.create_voice_clone_prompt(
            ref_audio=ref_audio,
            ref_text=ref_text,
        )
        prompts[voice_id] = prompt
        elapsed = time.time() - started
        print(f"  Clone prompt ready for '{voice_id}' in {elapsed:.1f}s.")
        print(
            f"VOICE_PROMPT event=done done={idx} total={total} "
            f"voice={voice_id} sec={elapsed:.1f}"
        )
        sys.stdout.flush()
    return prompts


def maybe_compile_model(model: Any, enable: bool, use_sage: bool = False) -> Any:
    """Optionally apply torch.compile for ~20-40% inference speedup.

    Note: the first chunk will take longer due to JIT compilation,
    but subsequent chunks benefit from the optimized code.

    When SageAttention is active, ``reduce-overhead`` mode (CUDA Graphs) is
    downgraded to ``default`` because the monkey-patched SDPA wrapper
    contains Python-level conditionals that break CUDA Graph capture.
    """
    if not enable:
        return model
    import torch
    if not hasattr(torch, "compile"):
        print("[compile] torch.compile not available (requires PyTorch >= 2.0), skipping.")
        return model

    if use_sage:
        print(
            "[compile] Skipping torch.compile — SageAttention provides its "
            "own acceleration and is incompatible with torch.compile tracing."
        )
        sys.stdout.flush()
        return model

    mode = "reduce-overhead"
    print(f"[compile] Applying torch.compile(mode='{mode}')…")
    sys.stdout.flush()
    try:
        import torch.nn as nn
        compiled_any = False
        for name, val in vars(model).items():
            if isinstance(val, nn.Module):
                try:
                    compiled = torch.compile(val, mode=mode, dynamic=True)
                    setattr(model, name, compiled)
                    print(f"[compile] Compiled model.{name}")
                    compiled_any = True
                except Exception as exc:
                    print(f"[compile] Could not compile model.{name}: {exc}")
        if not compiled_any:
            print("[compile] No sub-modules found to compile, skipping.")
    except Exception as exc:
        print(f"[compile] torch.compile failed: {exc} — running without.")
    sys.stdout.flush()
    return model


def synthesize_chunk(
    model: Any,
    text: str,
    voice_id: str,
    speaker_map: dict[str, str],
    clone_prompts: dict[str, Any] | None = None,
    clone_model: Any | None = None,
    instruct_map: dict[str, str] | None = None,
    language: str = "Russian",
    generation_kwargs: dict[str, Any] | None = None,
) -> tuple[Any, int]:
    """Generate audio for a single chunk.

    Uses voice cloning if the voice_id has a clone prompt,
    otherwise falls back to CustomVoice.
    """
    generation_kwargs = generation_kwargs or {}
    clone_prompt = _clone_prompt_for_voice(voice_id, clone_prompts)
    if clone_prompt is not None and clone_model is not None:
        wavs, sr = _call_with_generation_kwargs(
            clone_model.generate_voice_clone,
            {
                "text": text,
                "language": language,
                "voice_clone_prompt": clone_prompt,
                **generation_kwargs,
            },
        )
        return wavs, sr

    speaker, instruct = resolve_voice(voice_id, speaker_map)
    wavs, sr = _call_with_generation_kwargs(
        model.generate_custom_voice,
        {
            "text": text,
            "language": language,
            "speaker": speaker,
            "instruct": instruct,
            **generation_kwargs,
        },
    )
    return wavs, sr


def synthesize_batch(
    model: Any,
    texts: list[str],
    voice_ids: list[str],
    speaker_map: dict[str, str],
    clone_prompts: dict[str, Any] | None = None,
    clone_model: Any | None = None,
    instruct_map: dict[str, str] | None = None,
    language: str = "Russian",
    generation_kwargs: dict[str, Any] | None = None,
) -> list[tuple[Any, int]]:
    """Generate audio for multiple chunks in a single batch call.

    Falls back to one-by-one synthesis when the batch mixes
    cloned and custom voices.
    """
    generation_kwargs = generation_kwargs or {}
    has_clone = clone_prompts and clone_model is not None
    all_clone = bool(has_clone) and all(
        _clone_prompt_for_voice(vid, clone_prompts) is not None
        for vid in voice_ids
    )
    all_custom = not has_clone or all(
        _clone_prompt_for_voice(vid, clone_prompts) is None
        for vid in voice_ids
    )

    if all_custom:
        resolved = [resolve_voice(vid, speaker_map) for vid in voice_ids]
        speakers = [r[0] for r in resolved]
        instructs = [r[1] for r in resolved]
        langs = [language] * len(texts)
        wavs, sr = _call_with_generation_kwargs(
            model.generate_custom_voice,
            {
                "text": texts,
                "language": langs,
                "speaker": speakers,
                "instruct": instructs,
                **generation_kwargs,
            },
        )
        return [(w, sr) for w in wavs]

    if all_clone:
        results = []
        for txt, vid in zip(texts, voice_ids):
            wavs, sr = _call_with_generation_kwargs(
                clone_model.generate_voice_clone,
                {
                    "text": txt,
                    "language": language,
                    "voice_clone_prompt": _clone_prompt_for_voice(vid, clone_prompts),
                    **generation_kwargs,
                },
            )
            results.append((wavs[0], sr))
        return results

    # Mixed batch: synthesize one by one.
    results = []
    for txt, vid in zip(texts, voice_ids):
        wavs, sr = synthesize_chunk(
            model, txt, vid, speaker_map,
            clone_prompts=clone_prompts,
            clone_model=clone_model,
            language=language,
            generation_kwargs=generation_kwargs,
        )
        results.append((wavs[0], sr))
    return results


def _format_eta(seconds: float) -> str:
    """Format seconds into human-readable HH:MM:SS."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}h{m:02d}m{s:02d}s"
    if m > 0:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def merge_chapter_audio(
    out_dir: Path,
    manifest: list[dict[str, Any]],
    output_format: str,
    pause_ms: int = 250,
) -> dict[str, Path]:
    """Merge synthesized chunks into one audio file per chapter."""
    try:
        import numpy as np
    except Exception as exc:
        print(f"WARNING: numpy unavailable, skipping chapter merge: {exc}")
        sys.stdout.flush()
        return {}

    ext = _audio_extension(output_format)
    chapters_dir = out_dir / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    grouped: dict[int, list[dict[str, Any]]] = {}
    for item in manifest:
        if not item.get("file"):
            continue
        grouped.setdefault(int(item.get("chapter_index", 0)), []).append(item)

    merged: dict[str, Path] = {}
    chapter_manifest: list[dict[str, Any]] = []
    for ch_idx in sorted(grouped):
        items = sorted(grouped[ch_idx], key=lambda c: int(c.get("chunk_index", 0)))
        arrays = []
        sample_rate = None
        channels = 1
        for item in items:
            audio_path = out_dir / item["file"]
            if not audio_path.exists():
                print(f"  WARNING: missing chunk for merge: {audio_path}")
                continue
            data, sr = sf.read(str(audio_path), always_2d=True)
            if sample_rate is None:
                sample_rate = sr
                channels = data.shape[1]
            elif sr != sample_rate:
                print(
                    f"  WARNING: skipping {audio_path}; sample rate {sr} "
                    f"!= chapter rate {sample_rate}."
                )
                continue
            if data.shape[1] != channels:
                if data.shape[1] == 1 and channels > 1:
                    data = np.repeat(data, channels, axis=1)
                elif data.shape[1] > channels == 1:
                    data = data.mean(axis=1, keepdims=True)
                else:
                    data = data[:, :channels]
            arrays.append(data)
            pause_frames = int((sample_rate or sr) * (pause_ms / 1000))
            if pause_frames > 0:
                arrays.append(np.zeros((pause_frames, channels), dtype=data.dtype))

        if not arrays or sample_rate is None:
            continue
        if len(arrays) > 1:
            arrays = arrays[:-1]
        joined = np.concatenate(arrays, axis=0)
        if joined.shape[1] == 1:
            joined = joined[:, 0]
        chapter_path = chapters_dir / f"chapter_{ch_idx + 1:03d}.{ext}"
        sf.write(str(chapter_path), joined, sample_rate, format=ext.upper())
        key = f"chapter_{ch_idx + 1:03d}"
        merged[key] = chapter_path
        chapter_manifest.append(
            {
                "chapter_index": ch_idx,
                "file": str(chapter_path.relative_to(out_dir)),
                "chunks": len(items),
            }
        )
        print(f"  [OK] Merged {key}: {chapter_path}")
        sys.stdout.flush()

    if chapter_manifest:
        (out_dir / "chapters_manifest.json").write_text(
            json.dumps(chapter_manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return merged


def main() -> None:
    parser = argparse.ArgumentParser(description="TTS runner for Qwen3-TTS in WSL")
    parser.add_argument(
        "--chunks-json", required=True,
        help="Path to chunks_manifest.json with voice-annotated chunks.",
    )
    parser.add_argument(
        "--out", required=True,
        help="Output directory for audio files.",
    )
    parser.add_argument(
        "--model", default="Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        help="Qwen3-TTS model name (default: 1.7B for better quality).",
    )
    parser.add_argument(
        "--models-dir",
        default=str(default_comfyui_models_dir()),
        help=(
            "Shared ComfyUI models directory. The runner first looks for "
            "Qwen model folders here (default: %(default)s)."
        ),
    )
    parser.add_argument(
        "--device", default="cuda:0",
        help="Device for inference.",
    )
    parser.add_argument(
        "--narrator-speaker", default="Aiden",
        help="CustomVoice speaker for narrator.",
    )
    parser.add_argument(
        "--male-speaker", default="Ryan",
        help="CustomVoice speaker for male dialogue.",
    )
    parser.add_argument(
        "--female-speaker", default="Serena",
        help="CustomVoice speaker for female dialogue.",
    )
    parser.add_argument(
        "--chapter", type=int, default=None,
        help="Only synthesize a specific chapter (1-based).",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Skip chunks that already have WAV files.",
    )
    parser.add_argument(
        "--batch-size", type=int, default=1,
        help="Number of chunks to synthesize in a single batch (1=sequential).",
    )
    parser.add_argument(
        "--max-chunk-chars", type=int, default=600,
        help="Max chars per chunk (shorter = better intonation stability).",
    )
    parser.add_argument(
        "--log-file", type=str, default=None,
        help="Write all output to this file (for debugging).",
    )
    parser.add_argument(
        "--chunk-timeout", type=int, default=300,
        help="Max seconds per chunk before skipping (default: 300 = 5 min).",
    )
    parser.add_argument(
        "--compile", action="store_true",
        help="Apply torch.compile for ~20-40%% speedup (first chunk will be slower).",
    )
    parser.add_argument(
        "--clone-config", type=str, default=None,
        help="Path to JSON with voice clone configs (ref_audio + ref_text per voice_id).",
    )
    parser.add_argument(
        "--clone-model", type=str, default=BASE_MODEL_NAME,
        help=f"Base model for voice cloning (default: {BASE_MODEL_NAME}).",
    )
    parser.add_argument(
        "--sage-attention", action="store_true",
        help=(
            "Require SageAttention (monkey-patches SDPA for ~2-3x speedup; "
            "exits if no compatible kernel is installed)."
        ),
    )
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--top-p", type=float, default=0.8)
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--repetition-penalty", type=float, default=1.05)
    parser.add_argument("--max-new-tokens", type=int, default=2048)
    parser.add_argument(
        "--seed", type=int, default=-1,
        help="Random seed for repeatable generation (-1 = random).",
    )
    parser.add_argument(
        "--output-format",
        choices=("wav", "flac"),
        default="wav",
        help="Audio format for chunks and merged chapters.",
    )
    parser.add_argument(
        "--merge-chapters",
        action="store_true",
        help="Also write merged chapter audio files under out/chapters.",
    )
    args = parser.parse_args()

    _log_file = None
    _orig_stdout = sys.stdout
    if args.log_file:
        _log_file = open(args.log_file, "w", encoding="utf-8")

        class Tee:
            def write(self, s):
                _orig_stdout.write(s)
                _orig_stdout.flush()
                _log_file.write(s)
                _log_file.flush()

            def flush(self):
                _orig_stdout.flush()
                _log_file.flush()

        sys.stdout = Tee()

    try:
        _main_impl(args)
    finally:
        if _log_file:
            sys.stdout = _orig_stdout
            _log_file.close()


def _main_impl(args: argparse.Namespace) -> None:
    manifest_path = Path(args.chunks_json)
    if not manifest_path.exists():
        print(f"ERROR: {manifest_path} not found.")
        sys.exit(1)

    chunks = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(f"Loaded {len(chunks)} chunks from manifest.")

    if args.chapter is not None:
        ch_idx = args.chapter - 1
        chunks = [c for c in chunks if c["chapter_index"] == ch_idx]
        print(f"Filtered to chapter {args.chapter}: {len(chunks)} chunks.")

    out_dir = Path(args.out)

    speaker_map = {
        "narrator": args.narrator_speaker,
        "male": args.male_speaker,
        "female": args.female_speaker,
    }
    print(f"Speakers: {speaker_map}")
    print(f"Batch size: {args.batch_size}")
    print(f"Output format: {args.output_format}")
    print(
        "Generation controls: "
        f"temperature={args.temperature}, top_p={args.top_p}, top_k={args.top_k}, "
        f"repetition_penalty={args.repetition_penalty}, "
        f"max_new_tokens={args.max_new_tokens}"
    )
    if args.sage_attention:
        print("SageAttention: enabled")
    print(f"Model directory: {args.models_dir}")
    _set_seed(args.seed)
    generation_kwargs = _build_generation_kwargs(args)

    # Load voice clone config if provided.
    clone_config = load_clone_config(args.clone_config)
    clone_model = None
    clone_prompts: dict[str, Any] = {}

    if clone_config:
        print(f"Loading Base model for voice cloning: {args.clone_model}")
        clone_model = load_model(
            args.clone_model,
            args.device,
            use_sage=args.sage_attention,
            models_dir=args.models_dir,
        )
        clone_model = maybe_compile_model(
            clone_model, enable=args.compile, use_sage=args.sage_attention,
        )
        print("Building clone prompts...")
        sys.stdout.flush()
        clone_prompts = build_clone_prompts(clone_model, clone_config)
        print(f"Clone prompts ready: {list(clone_prompts.keys())}")
        sys.stdout.flush()

    # Determine which voice_ids actually need the CustomVoice model.
    voice_ids_in_manifest = {c.get("voice_id", "narrator") for c in chunks}
    needs_custom = any(
        _clone_prompt_for_voice(vid, clone_prompts) is None
        for vid in voice_ids_in_manifest
    )

    if needs_custom:
        model = load_model(
            args.model,
            args.device,
            use_sage=args.sage_attention,
            models_dir=args.models_dir,
        )
        model = maybe_compile_model(
            model, enable=args.compile, use_sage=args.sage_attention,
        )
    else:
        # All voices are cloned; no need for CustomVoice model.
        print("All voices use cloning, skipping CustomVoice model load.")
        model = clone_model

    total = len(chunks)
    total_chars = sum(len(c.get("text", "")) for c in chunks)
    done = 0
    skipped = 0
    errors = 0
    consecutive_errors = 0
    max_consecutive_errors = 3
    processed_chars = 0
    start = time.time()
    chunk_times: list[tuple[float, int]] = []

    progress_path = out_dir / "synthesis_progress.json"
    completed_keys: set[str] = set()
    if args.resume and progress_path.exists():
        try:
            pdata = json.loads(progress_path.read_text(encoding="utf-8"))
            completed_keys = set(pdata.get("completed", []))
        except (json.JSONDecodeError, OSError):
            pass

    manifest_out: list[dict[str, Any]] = []
    audio_ext = _audio_extension(args.output_format)

    i = 0
    while i < len(chunks):
        batch_chunks = []
        batch_paths = []
        batch_keys = []

        # Collect a batch of unprocessed chunks.
        while len(batch_chunks) < args.batch_size and i < len(chunks):
            chunk = chunks[i]
            ch_idx = chunk["chapter_index"]
            ck_idx = chunk["chunk_index"]
            voice_id = chunk["voice_id"]
            key = f"{ch_idx}:{ck_idx}"

            ch_dir = out_dir / "audio_chunks" / f"chapter_{ch_idx + 1:03d}"
            ch_dir.mkdir(parents=True, exist_ok=True)
            wav_path = ch_dir / f"chunk_{ck_idx + 1:03d}_{voice_id}.{audio_ext}"

            if args.resume and (key in completed_keys or wav_path.exists()):
                skipped += 1
                processed_chars += len(chunk.get("text", ""))
                manifest_out.append({**chunk, "file": str(wav_path.relative_to(out_dir))})
                i += 1
                continue

            batch_chunks.append(chunk)
            batch_paths.append(wav_path)
            batch_keys.append(key)
            i += 1

        if not batch_chunks:
            continue

        t0 = time.time()
        batch_nums = [c["chunk_index"] + 1 for c in batch_chunks]
        timeout = args.chunk_timeout
        print(
            f"  [INFO] Starting synthesis of batch: chunks {batch_nums} "
            f"(timeout {timeout}s)..."
        )
        sys.stdout.flush()

        if len(batch_chunks) == 1:
            chunk = batch_chunks[0]
            try:
                signal.signal(signal.SIGALRM, _timeout_handler)
                signal.alarm(timeout)
                try:
                    wavs, sr = synthesize_chunk(
                        model, chunk["text"], chunk["voice_id"], speaker_map,
                        clone_prompts=clone_prompts,
                        clone_model=clone_model,
                        generation_kwargs=generation_kwargs,
                    )
                    wav_data = wavs[0]
                    if hasattr(wav_data, "cpu"):
                        wav_data = wav_data.cpu().numpy()
                    wav_file = str(batch_paths[0])
                    sf.write(wav_file, wav_data, sr, format=audio_ext.upper())
                    fsize = batch_paths[0].stat().st_size
                    print(f"  [OK] Wrote {wav_file} ({fsize} bytes, sr={sr})")
                    sys.stdout.flush()
                    done += 1
                    consecutive_errors = 0
                    completed_keys.add(batch_keys[0])
                    manifest_out.append({
                        **chunk, "file": str(batch_paths[0].relative_to(out_dir)),
                    })
                finally:
                    signal.alarm(0)
            except ChunkTimeoutError:
                elapsed = time.time() - t0
                text_preview = chunk["text"][:60].replace("\n", " ")
                print(
                    f"  TIMEOUT ch{chunk['chapter_index']+1} "
                    f"chunk{chunk['chunk_index']+1} "
                    f"after {elapsed:.0f}s — skipping. "
                    f"Text: «{text_preview}…»"
                )
                sys.stdout.flush()
                skipped += 1
                processed_chars += len(chunk.get("text", ""))
                manifest_out.append({
                    **chunk, "file": "", "error": f"timeout after {elapsed:.0f}s",
                })
            except Exception as exc:
                err_str = str(exc)
                is_cuda = "CUDA" in err_str or "cuda" in err_str
                print(f"  ERROR {batch_keys[0]}: {exc}")
                sys.stdout.flush()
                skipped += 1
                errors += 1
                processed_chars += len(chunk.get("text", ""))
                manifest_out.append({**chunk, "file": "", "error": err_str})
                if is_cuda:
                    consecutive_errors += 1
                    _try_cuda_recover()
                    if consecutive_errors >= max_consecutive_errors:
                        print(
                            f"\n  FATAL: {consecutive_errors} consecutive CUDA errors. "
                            "GPU context is likely corrupted. Aborting synthesis.\n"
                            "  Hint: try disabling SageAttention — it may be "
                            "incompatible with this model/GPU."
                        )
                        sys.stdout.flush()
                        break
                else:
                    consecutive_errors = 0
        else:
            batch_timeout = timeout * len(batch_chunks)
            try:
                signal.signal(signal.SIGALRM, _timeout_handler)
                signal.alarm(batch_timeout)
                try:
                    texts = [c["text"] for c in batch_chunks]
                    vids = [c["voice_id"] for c in batch_chunks]
                    results = synthesize_batch(
                        model, texts, vids, speaker_map,
                        clone_prompts=clone_prompts,
                        clone_model=clone_model,
                        generation_kwargs=generation_kwargs,
                    )
                    for j, (wav_data_j, sr) in enumerate(results):
                        if hasattr(wav_data_j, "cpu"):
                            wav_data_j = wav_data_j.cpu().numpy()
                        sf.write(
                            str(batch_paths[j]), wav_data_j, sr,
                            format=audio_ext.upper(),
                        )
                        done += 1
                        consecutive_errors = 0
                        completed_keys.add(batch_keys[j])
                        manifest_out.append({
                            **batch_chunks[j],
                            "file": str(batch_paths[j].relative_to(out_dir)),
                        })
                finally:
                    signal.alarm(0)
            except ChunkTimeoutError:
                elapsed = time.time() - t0
                print(
                    f"  TIMEOUT batch chunks {batch_nums} "
                    f"after {elapsed:.0f}s — falling back one-by-one..."
                )
                sys.stdout.flush()
                # Fallback: try one-by-one with individual timeout.
                for j, chunk in enumerate(batch_chunks):
                    try:
                        signal.signal(signal.SIGALRM, _timeout_handler)
                        signal.alarm(timeout)
                        try:
                            wavs, sr = synthesize_chunk(
                                model, chunk["text"], chunk["voice_id"], speaker_map,
                                clone_prompts=clone_prompts,
                                clone_model=clone_model,
                                generation_kwargs=generation_kwargs,
                            )
                            wav_fb = wavs[0]
                            if hasattr(wav_fb, "cpu"):
                                wav_fb = wav_fb.cpu().numpy()
                            sf.write(
                                str(batch_paths[j]), wav_fb, sr,
                                format=audio_ext.upper(),
                            )
                            done += 1
                            completed_keys.add(batch_keys[j])
                            manifest_out.append({
                                **chunk,
                                "file": str(batch_paths[j].relative_to(out_dir)),
                            })
                        finally:
                            signal.alarm(0)
                    except ChunkTimeoutError:
                        elapsed2 = time.time() - t0
                        print(
                            f"  TIMEOUT {batch_keys[j]} after {elapsed2:.0f}s — skipping."
                        )
                        sys.stdout.flush()
                        skipped += 1
                        processed_chars += len(chunk.get("text", ""))
                        manifest_out.append({
                            **chunk, "file": "",
                            "error": f"timeout after {elapsed2:.0f}s",
                        })
                    except Exception as exc2:
                        err_str2 = str(exc2)
                        is_cuda2 = "CUDA" in err_str2 or "cuda" in err_str2
                        print(f"  ERROR {batch_keys[j]}: {exc2}")
                        sys.stdout.flush()
                        skipped += 1
                        errors += 1
                        processed_chars += len(chunk.get("text", ""))
                        manifest_out.append({
                            **chunk, "file": "", "error": err_str2,
                        })
                        if is_cuda2:
                            consecutive_errors += 1
                            _try_cuda_recover()
                            if consecutive_errors >= max_consecutive_errors:
                                break
                        else:
                            consecutive_errors = 0
                if consecutive_errors >= max_consecutive_errors:
                    print(
                        f"\n  FATAL: {consecutive_errors} consecutive CUDA errors. "
                        "GPU context is likely corrupted. Aborting synthesis.\n"
                        "  Hint: try disabling SageAttention — it may be "
                        "incompatible with this model/GPU."
                    )
                    sys.stdout.flush()
                    break
            except Exception as exc:
                err_str = str(exc)
                is_cuda = "CUDA" in err_str or "cuda" in err_str
                print(f"  ERROR batch: {exc}")
                sys.stdout.flush()
                for chunk in batch_chunks:
                    skipped += 1
                    errors += 1
                    processed_chars += len(chunk.get("text", ""))
                manifest_out.append({
                    **batch_chunks[-1], "file": "", "error": err_str,
                })
                if is_cuda:
                    consecutive_errors += len(batch_chunks)
                    _try_cuda_recover()
                    if consecutive_errors >= max_consecutive_errors:
                        print(
                            f"\n  FATAL: {consecutive_errors} consecutive CUDA "
                            "errors. Aborting synthesis.\n"
                            "  Hint: try disabling SageAttention — it may be "
                            "incompatible with this model/GPU."
                        )
                        sys.stdout.flush()
                        break
                else:
                    consecutive_errors = 0

        elapsed_chunk = time.time() - t0
        print(f"  [INFO] Batch done in {elapsed_chunk:.1f}s")
        sys.stdout.flush()

        batch_chars = sum(len(c.get("text", "")) for c in batch_chunks)
        processed_chars += batch_chars
        per_chunk_sec = elapsed_chunk / len(batch_chunks)
        for c in batch_chunks:
            chunk_times.append((per_chunk_sec, len(c.get("text", ""))))

        # Char-weighted ETA: sec per char from recent chunks.
        recent = chunk_times[-20:]
        sum_time = sum(t for t, _ in recent)
        sum_chars = sum(c for _, c in recent)
        remaining_chunks = total - done - skipped
        remaining_chars = total_chars - processed_chars
        if sum_chars > 0 and remaining_chars > 0:
            sec_per_char = sum_time / sum_chars
            eta = sec_per_char * remaining_chars
        elif recent and remaining_chunks > 0:
            eta = (sum_time / len(recent)) * remaining_chunks
        else:
            eta = 0

        c = batch_chunks[-1]
        chunk_chars = len(c.get("text", ""))
        print(
            f"  [{done + skipped}/{total}] "
            f"ch{c['chapter_index']+1} chunk{c['chunk_index']+1} "
            f"[{c['voice_id']}] {chunk_chars}ch "
            f"({elapsed_chunk:.1f}s, ETA: {_format_eta(eta)})"
        )
        sys.stdout.flush()
        # Machine-parseable line for GUI.
        print(
            f"  PROGRESS "
            f"done={done + skipped} total={total} remaining={remaining_chunks} "
            f"chunk_chars={chunk_chars} chunk_sec={elapsed_chunk:.1f} "
            f"total_chars={total_chars} processed_chars={processed_chars} "
            f"remaining_chars={remaining_chars} eta_sec={int(eta)} ch={c['chapter_index']+1}"
        )
        sys.stdout.flush()

        # Save progress periodically.
        if (done + skipped) % 5 == 0:
            progress_path.write_text(
                json.dumps({"completed": sorted(completed_keys)}, indent=2),
                encoding="utf-8",
            )

    # Final save.
    progress_path.write_text(
        json.dumps({"completed": sorted(completed_keys)}, indent=2),
        encoding="utf-8",
    )

    synth_manifest = out_dir / "synthesis_manifest.json"
    synth_manifest.write_text(
        json.dumps(manifest_out, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if args.merge_chapters:
        merged = merge_chapter_audio(out_dir, manifest_out, args.output_format)
        if merged:
            print(f"Chapters: {out_dir / 'chapters'}")

    elapsed = time.time() - start
    err_part = f", {errors} errors" if errors else ""
    print(
        f"\nDone: {done} synthesized, {skipped} skipped{err_part}, "
        f"{_format_eta(elapsed)} total."
    )
    print(f"Manifest: {synth_manifest}")


if __name__ == "__main__":
    main()
