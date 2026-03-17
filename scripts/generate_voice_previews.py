#!/usr/bin/env python3
"""Generate short preview WAV files for all voice presets.

Usage (in WSL with qwen3tts venv activated):
    python scripts/generate_voice_previews.py --out voice_previews/
    python scripts/generate_voice_previews.py --out voice_previews/ --ids narrator_calm,male_young

Creates one short WAV per voice preset so users can audition voices in the GUI.
Emits machine-readable progress lines for the GUI to parse.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PRESETS_JSON = [
    {"id": "narrator_calm", "speaker": "Aiden",
     "instruct": "Спокойный, чёткий голос рассказчика. "
                 "Читай размеренно, с правильными паузами."},
    {"id": "narrator_energetic", "speaker": "Ryan",
     "instruct": "Энергичный, уверенный голос рассказчика. "
                 "Читай бодро, с выразительной интонацией."},
    {"id": "narrator_wise", "speaker": "Uncle_Fu",
     "instruct": "Мудрый, опытный голос рассказчика. "
                 "Читай неторопливо, с глубиной."},
    {"id": "male_young", "speaker": "Ryan",
     "instruct": "Молодой мужской голос. "
                 "Говори с эмоцией, естественные интонации."},
    {"id": "male_confident", "speaker": "Aiden",
     "instruct": "Уверенный мужской голос. Говори чётко и решительно."},
    {"id": "male_deep", "speaker": "Uncle_Fu",
     "instruct": "Глубокий мужской голос. "
                 "Говори с достоинством и весомостью."},
    {"id": "male_lively", "speaker": "Dylan",
     "instruct": "Живой, весёлый мужской голос. Говори бодро, с юмором."},
    {"id": "male_regional", "speaker": "Eric",
     "instruct": "Яркий мужской голос с характером. "
                 "Говори экспрессивно."},
    {"id": "female_warm", "speaker": "Serena",
     "instruct": "Мягкий, тёплый женский голос. "
                 "Говори нежно, с теплотой."},
    {"id": "female_bright", "speaker": "Vivian",
     "instruct": "Яркий, звонкий женский голос. "
                 "Говори выразительно и энергично."},
    {"id": "female_playful", "speaker": "Ono_Anna",
     "instruct": "Игривый женский голос. "
                 "Говори легко, с улыбкой в голосе."},
    {"id": "female_gentle", "speaker": "Sohee",
     "instruct": "Нежный, мелодичный женский голос. "
                 "Говори спокойно и ласково."},
]

PRESET_BY_ID = {p["id"]: p for p in PRESETS_JSON}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate voice preview WAVs.",
    )
    parser.add_argument(
        "--out", required=True,
        help="Output directory for preview WAVs.",
    )
    parser.add_argument(
        "--model",
        default="Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        help="Qwen3-TTS model name.",
    )
    parser.add_argument(
        "--device", default="cuda:0",
        help="Device for inference.",
    )
    parser.add_argument(
        "--text", default=None,
        help="Preview text to synthesize.",
    )
    parser.add_argument(
        "--ids", default=None,
        help="Comma-separated voice IDs to generate (default: all).",
    )
    args = parser.parse_args()

    preview_text = args.text or (
        "Сергей сидел за столом и пил чай с малиновым вареньем. "
        "Состояние было весьма тоскливым."
    )

    if args.ids:
        selected_ids = [x.strip() for x in args.ids.split(",") if x.strip()]
        presets = [PRESET_BY_ID[i] for i in selected_ids if i in PRESET_BY_ID]
        if not presets:
            print(f"ERROR|No valid IDs in: {args.ids}")
            sys.stdout.flush()
            sys.exit(1)
    else:
        presets = PRESETS_JSON

    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        import flash_attn  # noqa: F401
        attn = "flash_attention_2"
        print("ATTN_INFO|flash_attention_2|installed")
    except ImportError:
        attn = "sdpa"
        print("ATTN_INFO|sdpa|flash-attn not installed")
    sys.stdout.flush()

    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    print(f"LOADING_MODEL|{args.model}|{args.device}|{attn}")
    sys.stdout.flush()

    model = Qwen3TTSModel.from_pretrained(
        args.model,
        device_map=args.device,
        dtype=dtype,
        attn_implementation=attn,
    )
    print("MODEL_READY")
    sys.stdout.flush()

    total = len(presets)
    t0 = time.time()
    generated = 0

    for i, preset in enumerate(presets):
        out_path = out_dir / f"{preset['id']}.wav"
        if out_path.exists():
            elapsed = time.time() - t0
            print(
                f"PROGRESS|{i + 1}|{total}|{elapsed:.1f}|"
                f"{preset['id']}|skipped"
            )
            sys.stdout.flush()
            generated += 1
            continue

        try:
            wavs, sr = model.generate_custom_voice(
                text=preview_text,
                language="Russian",
                speaker=preset["speaker"],
                instruct=preset["instruct"],
            )
            sf.write(str(out_path), wavs[0], sr)
            generated += 1
            elapsed = time.time() - t0
            print(
                f"PROGRESS|{i + 1}|{total}|{elapsed:.1f}|"
                f"{preset['id']}|done"
            )
            sys.stdout.flush()
        except Exception as exc:
            elapsed = time.time() - t0
            print(
                f"PROGRESS|{i + 1}|{total}|{elapsed:.1f}|"
                f"{preset['id']}|error:{exc}"
            )
            sys.stdout.flush()

    elapsed = time.time() - t0
    print(f"FINISHED|{generated}|{total}|{elapsed:.1f}")
    sys.stdout.flush()

    meta_path = out_dir / "presets.json"
    meta_path.write_text(
        json.dumps(PRESETS_JSON, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
