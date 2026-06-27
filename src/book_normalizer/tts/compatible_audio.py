"""Radio-compatible MP3 export helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

COMPATIBLE_MP3_BITRATE = "80k"
COMPATIBLE_SAMPLE_RATE = 24000
COMPATIBLE_CHANNELS = 1
COMPATIBLE_ID3_VERSION = "3"


def compatible_mp3_path(source: Path) -> Path:
    """Return the compatible MP3 sidecar path for an audio source."""
    return source.with_suffix(".MP3")


def ffmpeg_compatible_mp3_command(
    ffmpeg: str,
    source: Path,
    output: Path,
    *,
    audio_filter: str = "",
    bitrate: str = COMPATIBLE_MP3_BITRATE,
) -> list[str]:
    """Build the ffmpeg command for the receiver-compatible MP3 profile."""
    command = [
        ffmpeg,
        "-nostdin",
        "-y",
        "-hide_banner",
        "-i",
        str(source),
        "-vn",
        "-map_metadata",
        "-1",
    ]
    if audio_filter:
        command += ["-af", audio_filter]
    command += [
        "-c:a",
        "libmp3lame",
        "-b:a",
        bitrate,
        "-ar",
        str(COMPATIBLE_SAMPLE_RATE),
        "-ac",
        str(COMPATIBLE_CHANNELS),
        "-id3v2_version",
        COMPATIBLE_ID3_VERSION,
        str(output),
    ]
    return command


def export_compatible_mp3(
    source: Path,
    output: Path | None = None,
    *,
    ffmpeg: str,
    audio_filter: str = "",
    bitrate: str = COMPATIBLE_MP3_BITRATE,
) -> Path:
    """Transcode an audio source to the receiver-compatible MP3 profile."""
    target = output or compatible_mp3_path(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ffmpeg_compatible_mp3_command(ffmpeg, source, target, audio_filter=audio_filter, bitrate=bitrate),
        check=True,
        capture_output=True,
        text=True,
    )
    return target
