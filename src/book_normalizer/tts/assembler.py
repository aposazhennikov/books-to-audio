"""Audio assembly — merge chunk WAVs into chapter and full-book audio files."""

from __future__ import annotations

import json
import logging
import struct
import wave
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_PAUSE_PHRASE_MS = 300
DEFAULT_PAUSE_SPEAKER_MS = 1500
DEFAULT_PAUSE_CHAPTER_MS = 3000


class AudioAssembler:
    """Merges per-chunk WAV files into chapter-level and book-level audio.

    Adds configurable silence pauses between phrases, speaker changes,
    and chapters. Optionally converts the result to MP3 via pydub.
    """

    def __init__(
        self,
        output_dir: Path,
        pause_phrase_ms: int = DEFAULT_PAUSE_PHRASE_MS,
        pause_speaker_ms: int = DEFAULT_PAUSE_SPEAKER_MS,
        pause_chapter_ms: int = DEFAULT_PAUSE_CHAPTER_MS,
    ) -> None:
        self._output_dir = output_dir
        self._chunks_dir = output_dir / "audio_chunks"
        self._chapters_dir = output_dir / "audio_chapters"
        self._pause_phrase_ms = pause_phrase_ms
        self._pause_speaker_ms = pause_speaker_ms
        self._pause_chapter_ms = pause_chapter_ms

    def assemble(self, export_mp3: bool = False) -> dict[str, Path]:
        """Assemble all chapters and the full book from chunk WAVs.

        Returns a dict of output file paths keyed by description.
        """
        self._chapters_dir.mkdir(parents=True, exist_ok=True)

        manifest = self._load_manifest()
        if not manifest:
            logger.warning("No synthesis manifest found, nothing to assemble.")
            return {}

        chapters = self._group_by_chapter(manifest)
        result: dict[str, Path] = {}
        chapter_paths: list[Path] = []

        for ch_idx in sorted(chapters.keys()):
            ch_path = self._assemble_chapter(ch_idx, chapters[ch_idx])
            if ch_path:
                result[f"chapter_{ch_idx + 1:03d}"] = ch_path
                chapter_paths.append(ch_path)

        if chapter_paths:
            book_path = self._assemble_book(chapter_paths)
            result["full_book"] = book_path

            if export_mp3:
                mp3_path = self._convert_to_mp3(book_path)
                if mp3_path:
                    result["full_book_mp3"] = mp3_path

        logger.info("Assembly complete: %d files produced.", len(result))
        return result

    def _assemble_chapter(
        self, chapter_index: int, entries: list[dict[str, Any]]
    ) -> Path | None:
        """Concatenate chunk WAVs for a single chapter."""
        chunk_files: list[Path] = []
        voice_ids: list[str] = []

        for entry in sorted(entries, key=lambda e: e["chunk_index"]):
            fpath = self._output_dir / entry["file"]
            if fpath.exists():
                chunk_files.append(fpath)
                voice_ids.append(entry.get("voice_id", ""))

        if not chunk_files:
            return None

        out_path = self._chapters_dir / f"chapter_{chapter_index + 1:03d}.wav"
        self._concatenate_wavs(
            chunk_files, out_path, voice_ids,
            self._pause_phrase_ms, self._pause_speaker_ms,
        )
        return out_path

    def _assemble_book(self, chapter_paths: list[Path]) -> Path:
        """Concatenate chapter WAVs into a full book."""
        out_path = self._output_dir / "full_book.wav"
        self._concatenate_wavs(
            chapter_paths, out_path,
            pause_between_ms=self._pause_chapter_ms,
        )
        return out_path

    def _concatenate_wavs(
        self,
        wav_files: list[Path],
        output_path: Path,
        voice_ids: list[str] | None = None,
        pause_between_ms: int = 0,
        pause_speaker_change_ms: int = 0,
    ) -> None:
        """Concatenate multiple WAV files with silence pauses.

        All input WAVs must share the same sample rate and channel count.
        """
        if not wav_files:
            return

        params = self._read_wav_params(wav_files[0])
        if params is None:
            return

        sample_rate = params["framerate"]
        n_channels = params["nchannels"]
        sampwidth = params["sampwidth"]

        with wave.open(str(output_path), "wb") as out_wav:
            out_wav.setnchannels(n_channels)
            out_wav.setsampwidth(sampwidth)
            out_wav.setframerate(sample_rate)

            prev_voice: str | None = None
            for i, fpath in enumerate(wav_files):
                if i > 0:
                    use_pause = pause_between_ms
                    if (
                        voice_ids
                        and pause_speaker_change_ms > 0
                        and i < len(voice_ids)
                        and prev_voice
                        and voice_ids[i] != prev_voice
                    ):
                        use_pause = max(use_pause, pause_speaker_change_ms)

                    if use_pause > 0:
                        silence = self._generate_silence(
                            use_pause, sample_rate, n_channels, sampwidth
                        )
                        out_wav.writeframes(silence)

                try:
                    with wave.open(str(fpath), "rb") as in_wav:
                        out_wav.writeframes(in_wav.readframes(in_wav.getnframes()))
                except wave.Error as exc:
                    logger.warning("Skipping %s: %s", fpath, exc)

                if voice_ids and i < len(voice_ids):
                    prev_voice = voice_ids[i]

    @staticmethod
    def _read_wav_params(path: Path) -> dict[str, int] | None:
        """Read WAV parameters from a file."""
        try:
            with wave.open(str(path), "rb") as w:
                return {
                    "nchannels": w.getnchannels(),
                    "sampwidth": w.getsampwidth(),
                    "framerate": w.getframerate(),
                }
        except wave.Error as exc:
            logger.error("Cannot read WAV params from %s: %s", path, exc)
            return None

    @staticmethod
    def _generate_silence(
        duration_ms: int, sample_rate: int, n_channels: int, sampwidth: int
    ) -> bytes:
        """Generate a silence segment as raw PCM bytes."""
        n_frames = int(sample_rate * duration_ms / 1000)
        if sampwidth == 2:
            return b"\x00\x00" * n_frames * n_channels
        if sampwidth == 4:
            return b"\x00\x00\x00\x00" * n_frames * n_channels
        return b"\x00" * sampwidth * n_frames * n_channels

    def _convert_to_mp3(self, wav_path: Path) -> Path | None:
        """Convert WAV to MP3 using pydub (requires ffmpeg)."""
        try:
            from pydub import AudioSegment
        except ImportError:
            logger.warning("pydub not installed, skipping MP3 conversion.")
            return None

        mp3_path = wav_path.with_suffix(".mp3")
        try:
            audio = AudioSegment.from_wav(str(wav_path))
            audio.export(str(mp3_path), format="mp3", bitrate="192k")
            logger.info("MP3 exported: %s", mp3_path)
            return mp3_path
        except Exception as exc:
            logger.warning("MP3 conversion failed: %s", exc)
            return None

    def _load_manifest(self) -> list[dict[str, Any]]:
        """Load the synthesis manifest."""
        manifest_path = self._output_dir / "synthesis_manifest.json"
        if not manifest_path.exists():
            return []
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    @staticmethod
    def _group_by_chapter(
        manifest: list[dict[str, Any]]
    ) -> dict[int, list[dict[str, Any]]]:
        """Group manifest entries by chapter_index."""
        groups: dict[int, list[dict[str, Any]]] = {}
        for entry in manifest:
            ch = entry["chapter_index"]
            groups.setdefault(ch, []).append(entry)
        return groups
