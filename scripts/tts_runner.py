#!/usr/bin/env python3
"""WSL TTS runner — synthesizes audio from voice-annotated chunks using Qwen3-TTS.

Usage:
    source ~/venvs/qwen3tts/bin/activate
    python scripts/tts_runner.py --chunks-json output/chunks_manifest.json --out output/master_magii_1_pdf

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
import signal
import sys
import time
from pathlib import Path
from typing import Any

import soundfile as sf


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


def resolve_voice(voice_id: str, speaker_map: dict) -> tuple[str, str]:
    """Resolve voice_id to (speaker, instruct), supporting both legacy and new presets."""
    if voice_id in VOICE_PRESETS:
        return VOICE_PRESETS[voice_id]
    speaker = speaker_map.get(voice_id, LEGACY_SPEAKER_MAP.get(voice_id, "Aiden"))
    instruct = INSTRUCT_MAP.get(voice_id, "")
    return speaker, instruct


def _detect_attn_impl() -> str:
    """Pick the best attention implementation available."""
    try:
        import flash_attn  # noqa: F401
        return "flash_attention_2"
    except ImportError:
        return "sdpa"


def load_model(model_name: str, device: str = "cuda:0"):
    """Load a Qwen3-TTS model with the best available attention."""
    import torch
    from qwen_tts import Qwen3TTSModel

    want_dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    attn = _detect_attn_impl()
    print(f"Loading {model_name} on {device} ({want_dtype}, attn={attn})...")
    model = Qwen3TTSModel.from_pretrained(
        model_name,
        device_map=device,
        dtype=want_dtype,
        attn_implementation=attn,
    )

    import importlib
    fa_ok = importlib.util.find_spec("flash_attn") is not None
    print(
        f"[OK] bfloat16={want_dtype}, flash_attn={fa_ok}, "
        f"attn_impl={attn}"
    )

    print("Model loaded.")
    sys.stdout.flush()
    return model


def maybe_compile_model(model: Any, enable: bool) -> Any:
    """Optionally apply torch.compile for ~20-40% inference speedup.

    Note: the first chunk will take longer due to JIT compilation,
    but subsequent chunks benefit from the optimized code.
    """
    if not enable:
        return model
    import torch
    if not hasattr(torch, "compile"):
        print("[compile] torch.compile not available (requires PyTorch >= 2.0), skipping.")
        return model
    print("[compile] Applying torch.compile(mode='reduce-overhead')…")
    sys.stdout.flush()
    try:
        import torch.nn as nn
        # Compile inner nn.Module sub-components that own actual parameters.
        compiled_any = False
        for name, val in vars(model).items():
            if isinstance(val, nn.Module):
                try:
                    compiled = torch.compile(val, mode="reduce-overhead", dynamic=True)
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
    instruct_map: dict[str, str] | None = None,
    language: str = "Russian",
) -> tuple[Any, int]:
    """Generate audio for a single chunk using CustomVoice."""
    speaker, instruct = resolve_voice(voice_id, speaker_map)

    wavs, sr = model.generate_custom_voice(
        text=text,
        language=language,
        speaker=speaker,
        instruct=instruct,
    )
    return wavs, sr


def synthesize_batch(
    model: Any,
    texts: list[str],
    voice_ids: list[str],
    speaker_map: dict[str, str],
    instruct_map: dict[str, str] | None = None,
    language: str = "Russian",
) -> list[tuple[Any, int]]:
    """Generate audio for multiple chunks in a single batch call."""
    resolved = [resolve_voice(vid, speaker_map) for vid in voice_ids]
    speakers = [r[0] for r in resolved]
    instructs = [r[1] for r in resolved]
    langs = [language] * len(texts)

    wavs, sr = model.generate_custom_voice(
        text=texts,
        language=langs,
        speaker=speakers,
        instruct=instructs,
    )
    return [(w, sr) for w in wavs]


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

    model = load_model(args.model, args.device)
    model = maybe_compile_model(model, enable=args.compile)

    total = len(chunks)
    total_chars = sum(len(c.get("text", "")) for c in chunks)
    done = 0
    skipped = 0
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
            wav_path = ch_dir / f"chunk_{ck_idx + 1:03d}_{voice_id}.wav"

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
                    )
                    sf.write(str(batch_paths[0]), wavs[0], sr)
                    done += 1
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
                print(f"  ERROR {batch_keys[0]}: {exc}")
                sys.stdout.flush()
                skipped += 1
                processed_chars += len(chunk.get("text", ""))
                manifest_out.append({**chunk, "file": "", "error": str(exc)})
        else:
            batch_timeout = timeout * len(batch_chunks)
            try:
                signal.signal(signal.SIGALRM, _timeout_handler)
                signal.alarm(batch_timeout)
                try:
                    texts = [c["text"] for c in batch_chunks]
                    vids = [c["voice_id"] for c in batch_chunks]
                    results = synthesize_batch(model, texts, vids, speaker_map)
                    for j, (wav_data, sr) in enumerate(results):
                        sf.write(str(batch_paths[j]), wav_data, sr)
                        done += 1
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
                            )
                            sf.write(str(batch_paths[j]), wavs[0], sr)
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
                        print(f"  ERROR {batch_keys[j]}: {exc2}")
                        sys.stdout.flush()
                        skipped += 1
                        processed_chars += len(chunk.get("text", ""))
                        manifest_out.append({
                            **chunk, "file": "", "error": str(exc2),
                        })
            except Exception as exc:
                print(f"  ERROR batch: {exc}")
                sys.stdout.flush()
                for chunk in batch_chunks:
                    skipped += 1
                    processed_chars += len(chunk.get("text", ""))
                manifest_out.append({
                    **batch_chunks[-1], "file": "", "error": str(exc),
                })

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

    elapsed = time.time() - start
    print(f"\nDone: {done} synthesized, {skipped} skipped, {_format_eta(elapsed)} total.")
    print(f"Manifest: {synth_manifest}")


if __name__ == "__main__":
    main()
