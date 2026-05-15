#!/usr/bin/env python3
"""Clone and save a custom speaker voice for dialogue synthesis.

Uploads a reference audio file to ComfyUI, extracts voice features via
FB_Qwen3TTSVoiceClonePrompt, and saves them via FB_Qwen3TTSSaveVoice.
After running this script the voice becomes available in the
FB_Qwen3TTSLoadSpeaker dropdown and can be used by synthesize_dialogue.py.

Run this once for each of the three roles (narrator, men, women).

Usage:
    # Narrator voice (30+ seconds of clean speech recommended)
    python scripts/save_voice.py \\
        --audio my_narrator.wav \\
        --name narrator \\
        --ref-text "Точный текст из аудиозаписи для лучшего качества клонирования."

    # Male character voice
    python scripts/save_voice.py \\
        --audio male_voice.wav \\
        --name men \\
        --ref-text "Реплики мужского персонажа из записи."

    # Female character voice
    python scripts/save_voice.py \\
        --audio female_voice.wav \\
        --name women \\
        --ref-text "Реплики женского персонажа из записи."

Tips for best results:
    - Record 30–120 seconds of clean, natural speech.
    - Avoid background noise, music, or multiple speakers.
    - The --ref-text should be an exact transcript of the audio.
    - Use WAV 16–44 kHz, mono or stereo — both work.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from book_normalizer.comfyui.client import ComfyUIClient, ComfyUIError
from book_normalizer.comfyui.workflow_builder import WorkflowBuilder, WorkflowBuilderError

# Default paths.
_DEFAULT_WORKFLOW = str(
    Path(__file__).resolve().parent.parent / "comfyui_workflows" / "voice_setup_template.json"
)
_DEFAULT_COMFYUI_URL = "http://localhost:8188"

# Timeout for voice-feature extraction (in seconds).
_EXTRACT_TIMEOUT = 300.0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clone and save a custom speaker voice for use in dialogue synthesis.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--audio", required=True,
        help="Path to reference audio file (WAV / FLAC / MP3, 30+ seconds recommended).",
    )
    parser.add_argument(
        "--name", required=True,
        help="Voice name to save as (e.g. narrator, men, women). "
             "This name appears in the FB_Qwen3TTSLoadSpeaker dropdown.",
    )
    parser.add_argument(
        "--ref-text", default="",
        help="Exact transcript of the reference audio. "
             "Strongly recommended for better clone quality.",
    )
    parser.add_argument(
        "--workflow", default=_DEFAULT_WORKFLOW,
        help=f"Path to voice_setup_template.json (default: {_DEFAULT_WORKFLOW}).",
    )
    parser.add_argument(
        "--comfyui-url", default=_DEFAULT_COMFYUI_URL,
        help=f"ComfyUI server URL (default: {_DEFAULT_COMFYUI_URL}).",
    )
    parser.add_argument(
        "--timeout", type=float, default=_EXTRACT_TIMEOUT,
        help=f"Max seconds to wait for feature extraction (default: {_EXTRACT_TIMEOUT}).",
    )
    args = parser.parse_args()

    audio_path = Path(args.audio)
    if not audio_path.exists():
        print(f"ERROR: Audio file not found: {audio_path}")
        sys.exit(1)

    # Connect to ComfyUI.
    client = ComfyUIClient(args.comfyui_url)
    if not client.is_reachable():
        print(f"ERROR: ComfyUI not reachable at {args.comfyui_url}")
        print("Make sure ComfyUI is running.")
        sys.exit(1)
    print(f"ComfyUI: connected to {args.comfyui_url}")

    # Load workflow builder.
    try:
        builder = WorkflowBuilder(args.workflow)
    except WorkflowBuilderError as exc:
        print(f"ERROR loading workflow template: {exc}")
        sys.exit(1)

    # Step 1: Upload the audio file to ComfyUI's input directory.
    size_kb = audio_path.stat().st_size // 1024
    print(f"\nUploading {audio_path.name} ({size_kb} KB) → ComfyUI input...")
    try:
        uploaded_name = client.upload_audio(audio_path)
    except ComfyUIError as exc:
        print(f"ERROR during upload: {exc}")
        sys.exit(1)
    print(f"  Uploaded as: {uploaded_name}")

    # Step 2: Build and queue the voice-extraction workflow.
    ref_text = args.ref_text.strip()
    if not ref_text:
        print("  WARNING: --ref-text not provided. Clone quality may be lower.")

    print(f"\nExtracting voice features for \"{args.name}\"...")
    workflow = builder.build_voice_setup(
        audio_filename=uploaded_name,
        voice_name=args.name,
        ref_text=ref_text,
    )

    t_start = time.monotonic()
    try:
        prompt_id = client.queue_prompt(workflow)
        print(f"  Queued: {prompt_id}")
        print("  Waiting for FB_Qwen3TTSVoiceClonePrompt + FB_Qwen3TTSSaveVoice...")
        client.wait_for_execution(prompt_id, timeout=args.timeout)
    except ComfyUIError as exc:
        print(f"ERROR during voice extraction: {exc}")
        sys.exit(1)

    elapsed = time.monotonic() - t_start
    print(f"  Done in {elapsed:.1f}s")

    # Step 3: Verify the speaker now appears in the dropdown.
    speakers = client.list_saved_speakers()
    if args.name in speakers or any(args.name in s for s in speakers):
        print(f"\nSpeaker \"{args.name}\" saved successfully.")
        print(f"Available speakers: {', '.join(speakers)}")
    else:
        print("\nSpeaker saved (may need ComfyUI restart to refresh the dropdown).")
        print(f"Current dropdown options: {speakers or ['(none)']}")

    print(
        f"\nNext step: run synthesize_dialogue.py with "
        f"--{'narrator' if args.name == 'narrator' else args.name}-speaker {args.name}"
    )


if __name__ == "__main__":
    main()
