#!/usr/bin/env python3
"""A/B test: does Qwen3-TTS respond to Unicode acute accents (U+0301)?

Generates pairs of WAVs for ambiguous Russian words:
  - without stress marks (plain text)
  - with stress marks (acute accent)

Listen to both and compare pronunciation.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from book_normalizer.tts.model_paths import default_comfyui_models_dir, describe_model_resolution

TEST_PAIRS = [
    {
        "id": "zamok",
        "plain": "Старый замок стоял на холме уже триста лет.",
        "stressed": "Старый за\u0301мок стоял на холме\u0301 уже три\u0301ста лет.",
        "note": "за\u0301мок (castle) vs замо\u0301к (lock)",
    },
    {
        "id": "muka",
        "plain": "Она просеяла муку через сито.",
        "stressed": "Она\u0301 просе\u0301яла муку\u0301 через си\u0301то.",
        "note": "му\u0301ка (torment) vs мука\u0301 (flour)",
    },
    {
        "id": "pisat",
        "plain": "Он начал писать письмо другу.",
        "stressed": "Он на\u0301чал писа\u0301ть письмо\u0301 дру\u0301гу.",
        "note": "пи\u0301сать vs писа\u0301ть — stress changes meaning",
    },
    {
        "id": "doroga",
        "plain": "Эта дорога была очень дорога для него.",
        "stressed": "Э\u0301та доро\u0301га была\u0301 о\u0301чень дорога\u0301 для него\u0301.",
        "note": "доро\u0301га (road) vs дорога\u0301 (expensive/dear)",
    },
    {
        "id": "mixed",
        "plain": "Большой замок на двери не открывался, "
                 "а старый замок на горе разрушался.",
        "stressed": "Большо\u0301й замо\u0301к на двери\u0301 не открыва\u0301лся, "
                    "а ста\u0301рый за\u0301мок на горе\u0301 разруша\u0301лся.",
        "note": "Same word 'замок' with different stress in one sentence",
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="A/B test stress marks in Qwen3-TTS.",
    )
    parser.add_argument(
        "--out", default="voice_previews/stress_test",
        help="Output directory.",
    )
    parser.add_argument(
        "--model",
        default="Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        help="Model name.",
    )
    parser.add_argument(
        "--speaker", default="Aiden",
        help="Speaker voice.",
    )
    parser.add_argument(
        "--models-dir",
        default=str(default_comfyui_models_dir()),
        help="Shared ComfyUI models directory.",
    )
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()

    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        import flash_attn  # noqa: F401
        attn = "flash_attention_2"
    except ImportError:
        attn = "sdpa"

    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    model_name, is_local = describe_model_resolution(args.model, models_dir=args.models_dir)
    if is_local:
        print(f"Using local model folder: {model_name}")
    print(f"Loading {model_name} ({attn})...")
    sys.stdout.flush()

    model = Qwen3TTSModel.from_pretrained(
        model_name,
        device_map=args.device,
        dtype=dtype,
        attn_implementation=attn,
    )
    print("Model ready.\n")

    instruct = (
        "Спокойный, чёткий голос рассказчика. "
        "Читай размеренно, с правильными паузами."
    )

    for pair in TEST_PAIRS:
        pid = pair["id"]
        print(f"=== {pid} ===")
        print(f"  Note: {pair['note']}")

        for variant, text in [("plain", pair["plain"]),
                              ("stressed", pair["stressed"])]:
            wav_path = out_dir / f"{pid}_{variant}.wav"
            if wav_path.exists():
                print(f"  [{variant}] already exists, skipping.")
                continue

            print(f"  [{variant}] {text[:80]}...")
            sys.stdout.flush()
            t0 = time.time()

            wavs, sr = model.generate_custom_voice(
                text=text,
                language="Russian",
                speaker=args.speaker,
                instruct=instruct,
            )
            sf.write(str(wav_path), wavs[0], sr)
            elapsed = time.time() - t0
            print(f"  [{variant}] saved ({elapsed:.1f}s)")
            sys.stdout.flush()

        print()

    print(f"Done! Files in: {out_dir}")
    print("Compare *_plain.wav vs *_stressed.wav for each pair.")


if __name__ == "__main__":
    main()
