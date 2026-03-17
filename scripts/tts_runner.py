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

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

# Russian-language instruct prompts for better intonation and pacing.
INSTRUCT_MAP = {
    "narrator": (
        "Спокойный, чёткий голос рассказчика. "
        "Читай размеренно, с правильными паузами и естественной интонацией. "
        "Не торопись."
    ),
    "male": (
        "Уверенный мужской голос. "
        "Говори с эмоцией, соответствующей контексту диалога. "
        "Естественные интонации."
    ),
    "female": (
        "Мягкий женский голос. "
        "Говори с эмоцией, соответствующей контексту диалога. "
        "Естественные интонации."
    ),
}


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

    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    attn = _detect_attn_impl()
    print(f"Loading {model_name} on {device} ({dtype}, attn={attn})...")
    model = Qwen3TTSModel.from_pretrained(
        model_name,
        device_map=device,
        dtype=dtype,
        attn_implementation=attn,
    )
    print("Model loaded.")
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
    speaker = speaker_map.get(voice_id, "Serena")
    imap = instruct_map or INSTRUCT_MAP
    instruct = imap.get(voice_id, "")

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
    imap = instruct_map or INSTRUCT_MAP
    speakers = [speaker_map.get(vid, "Serena") for vid in voice_ids]
    instructs = [imap.get(vid, "") for vid in voice_ids]
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
    args = parser.parse_args()

    import soundfile as sf

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

    total = len(chunks)
    done = 0
    skipped = 0
    start = time.time()
    chunk_times: list[float] = []

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

        if len(batch_chunks) == 1:
            chunk = batch_chunks[0]
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
            except Exception as exc:
                print(f"  ERROR {batch_keys[0]}: {exc}")
                manifest_out.append({**chunk, "file": "", "error": str(exc)})
        else:
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
            except Exception as exc:
                print(f"  ERROR batch: {exc}")
                # Fallback: try one-by-one.
                for j, chunk in enumerate(batch_chunks):
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
                    except Exception as exc2:
                        print(f"  ERROR {batch_keys[j]}: {exc2}")
                        manifest_out.append({
                            **chunk, "file": "", "error": str(exc2),
                        })

        elapsed_chunk = time.time() - t0
        chunk_times.append(elapsed_chunk / len(batch_chunks))

        # Rolling average for ETA.
        avg_time = sum(chunk_times[-20:]) / len(chunk_times[-20:])
        remaining_chunks = total - done - skipped
        eta = avg_time * remaining_chunks

        c = batch_chunks[-1]
        print(
            f"  [{done + skipped}/{total}] "
            f"ch{c['chapter_index']+1} chunk{c['chunk_index']+1} "
            f"[{c['voice_id']}] {len(c['text'])}ch "
            f"({elapsed_chunk:.1f}s, ETA: {_format_eta(eta)})"
        )

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
