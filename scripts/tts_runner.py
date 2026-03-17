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


def load_model(model_name: str, device: str = "cuda:0"):
    """Load a Qwen3-TTS model."""
    import torch
    from qwen_tts import Qwen3TTSModel

    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    print(f"Loading {model_name} on {device} ({dtype})...")
    model = Qwen3TTSModel.from_pretrained(
        model_name,
        device_map=device,
        dtype=dtype,
        attn_implementation="sdpa",
    )
    print("Model loaded.")
    return model


def synthesize_chunk(
    model: Any,
    text: str,
    voice_id: str,
    speaker_map: dict[str, str],
    language: str = "Russian",
) -> tuple[Any, int]:
    """Generate audio for a single chunk using CustomVoice."""
    speaker = speaker_map.get(voice_id, "Serena")

    instruct_map = {
        "narrator": "Calm, clear, warm narration voice. Read steadily with good pacing.",
        "male": "Confident male voice. Speak with emotion appropriate to dialogue.",
        "female": "Warm female voice. Speak with emotion appropriate to dialogue.",
    }
    instruct = instruct_map.get(voice_id, "")

    wavs, sr = model.generate_custom_voice(
        text=text,
        language=language,
        speaker=speaker,
        instruct=instruct,
    )
    return wavs, sr


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
        "--model", default="Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
        help="Qwen3-TTS model name.",
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

    model = load_model(args.model, args.device)

    total = len(chunks)
    done = 0
    skipped = 0
    start = time.time()

    progress_path = out_dir / "synthesis_progress.json"
    completed_keys: set[str] = set()
    if args.resume and progress_path.exists():
        try:
            pdata = json.loads(progress_path.read_text(encoding="utf-8"))
            completed_keys = set(pdata.get("completed", []))
        except (json.JSONDecodeError, OSError):
            pass

    manifest_out: list[dict[str, Any]] = []

    for i, chunk in enumerate(chunks):
        ch_idx = chunk["chapter_index"]
        ck_idx = chunk["chunk_index"]
        voice_id = chunk["voice_id"]
        text = chunk["text"]
        key = f"{ch_idx}:{ck_idx}"

        ch_dir = out_dir / "audio_chunks" / f"chapter_{ch_idx + 1:03d}"
        ch_dir.mkdir(parents=True, exist_ok=True)
        wav_path = ch_dir / f"chunk_{ck_idx + 1:03d}_{voice_id}.wav"

        if args.resume and (key in completed_keys or wav_path.exists()):
            skipped += 1
            manifest_out.append({
                **chunk,
                "file": str(wav_path.relative_to(out_dir)),
            })
            continue

        try:
            wavs, sr = synthesize_chunk(model, text, voice_id, speaker_map)
            sf.write(str(wav_path), wavs[0], sr)
            done += 1
            completed_keys.add(key)

            manifest_out.append({
                **chunk,
                "file": str(wav_path.relative_to(out_dir)),
            })

            elapsed = time.time() - start
            rate = done / elapsed if elapsed > 0 else 0
            remaining = (total - done - skipped) / rate if rate > 0 else 0
            print(
                f"  [{done + skipped}/{total}] ch{ch_idx+1} chunk{ck_idx+1} "
                f"[{voice_id}] {len(text)}ch -> {wav_path.name} "
                f"({rate:.1f} chunks/s, ~{remaining:.0f}s left)"
            )
        except Exception as exc:
            print(f"  ERROR ch{ch_idx+1} chunk{ck_idx+1}: {exc}")
            manifest_out.append({
                **chunk,
                "file": "",
                "error": str(exc),
            })

        # Save progress every 5 chunks.
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
    print(f"\nDone: {done} synthesized, {skipped} skipped, {elapsed:.1f}s total.")
    print(f"Manifest: {synth_manifest}")


if __name__ == "__main__":
    main()
