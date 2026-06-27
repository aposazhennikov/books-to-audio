from __future__ import annotations

from pathlib import Path

from book_normalizer.tts.compatible_audio import ffmpeg_compatible_mp3_command


def test_ffmpeg_compatible_mp3_command_matches_receiver_profile() -> None:
    command = ffmpeg_compatible_mp3_command(
        "ffmpeg-test",
        Path("input.wav"),
        Path("track_001.MP3"),
    )

    assert command == [
        "ffmpeg-test",
        "-nostdin",
        "-y",
        "-hide_banner",
        "-i",
        "input.wav",
        "-vn",
        "-map_metadata",
        "-1",
        "-c:a",
        "libmp3lame",
        "-b:a",
        "80k",
        "-ar",
        "24000",
        "-ac",
        "1",
        "-id3v2_version",
        "3",
        "track_001.MP3",
    ]
