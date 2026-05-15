"""TTS synthesizer — generates audio from voice-annotated chunks."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from book_normalizer.dialogue.models import VoiceAnnotatedChunk
from book_normalizer.tts.voice_config import VoiceMethod
from book_normalizer.tts.voice_manager import VoiceManager

logger = logging.getLogger(__name__)

DEFAULT_SAMPLE_RATE = 24000


class SynthesisProgress:
    """Tracks which chunks have been synthesized for resume support."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._completed: set[str] = set()
        self._load()

    def is_done(self, chapter_index: int, chunk_index: int) -> bool:
        """Check if a chunk was already synthesized."""
        return self._key(chapter_index, chunk_index) in self._completed

    def mark_done(self, chapter_index: int, chunk_index: int) -> None:
        """Mark a chunk as synthesized and persist."""
        self._completed.add(self._key(chapter_index, chunk_index))
        self._save()

    @property
    def completed_count(self) -> int:
        """Number of completed chunks."""
        return len(self._completed)

    @staticmethod
    def _key(chapter_index: int, chunk_index: int) -> str:
        return f"{chapter_index}:{chunk_index}"

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._completed = set(data.get("completed", []))
            except (json.JSONDecodeError, OSError):
                self._completed = set()

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps({"completed": sorted(self._completed)}, indent=2),
            encoding="utf-8",
        )


class TTSSynthesizer:
    """Synthesizes audio from voice-annotated chunks using Qwen3-TTS.

    Features:
    - Clone, Design, and CustomVoice synthesis modes.
    - Batch inference for chunks of the same voice.
    - Checkpoint/resume via SynthesisProgress.
    - Progress reporting via rich.
    """

    def __init__(
        self,
        voice_manager: VoiceManager,
        output_dir: Path,
        resume: bool = False,
    ) -> None:
        self._vm = voice_manager
        self._output_dir = output_dir
        self._chunks_dir = output_dir / "audio_chunks"
        self._progress = SynthesisProgress(output_dir / "synthesis_progress.json")
        self._resume = resume
        self._manifest: list[dict[str, Any]] = []

    def synthesize_book(
        self,
        chapters: dict[int, list[VoiceAnnotatedChunk]],
    ) -> Path:
        """Synthesize all chapters and return the output directory."""
        self._chunks_dir.mkdir(parents=True, exist_ok=True)

        total = sum(len(ch) for ch in chapters.values())
        skipped = 0
        synthesized = 0
        start_time = time.monotonic()

        try:
            from rich.progress import Progress
            use_rich = True
        except ImportError:
            use_rich = False

        if use_rich:
            with Progress() as progress:
                task = progress.add_task("Synthesizing...", total=total)
                for ch_idx in sorted(chapters.keys()):
                    ch_chunks = chapters[ch_idx]
                    for chunk in ch_chunks:
                        if self._resume and self._progress.is_done(ch_idx, chunk.index):
                            skipped += 1
                            progress.advance(task)
                            continue
                        self._synthesize_chunk(chunk)
                        self._progress.mark_done(ch_idx, chunk.index)
                        synthesized += 1
                        progress.advance(task)
        else:
            for ch_idx in sorted(chapters.keys()):
                ch_chunks = chapters[ch_idx]
                for chunk in ch_chunks:
                    if self._resume and self._progress.is_done(ch_idx, chunk.index):
                        skipped += 1
                        continue
                    self._synthesize_chunk(chunk)
                    self._progress.mark_done(ch_idx, chunk.index)
                    synthesized += 1

        elapsed = time.monotonic() - start_time
        self._write_manifest()

        logger.info(
            "Synthesis complete: %d synthesized, %d skipped, %.1fs elapsed",
            synthesized, skipped, elapsed,
        )
        return self._output_dir

    def synthesize_chapters(
        self,
        chapters: dict[int, list[VoiceAnnotatedChunk]],
        chapter_range: tuple[int, int] | None = None,
    ) -> Path:
        """Synthesize a subset of chapters."""
        if chapter_range:
            lo, hi = chapter_range
            filtered = {
                k: v for k, v in chapters.items() if lo <= k + 1 <= hi
            }
        else:
            filtered = chapters
        return self.synthesize_book(filtered)

    def _synthesize_chunk(self, chunk: VoiceAnnotatedChunk) -> None:
        """Generate audio for a single chunk and save to disk."""
        ch_dir = self._chunks_dir / f"chapter_{chunk.chapter_index + 1:03d}"
        ch_dir.mkdir(parents=True, exist_ok=True)

        filename = (
            f"chunk_{chunk.index + 1:03d}_{chunk.voice_id}.wav"
        )
        out_path = ch_dir / filename

        profile = self._vm.get_profile(chunk.voice_id)
        wavs, sr = self._generate_audio(chunk.text, profile, chunk.voice_id)

        import soundfile as sf
        sf.write(str(out_path), wavs[0], sr)

        self._manifest.append({
            "chapter_index": chunk.chapter_index,
            "chunk_index": chunk.index,
            "voice_id": chunk.voice_id,
            "role": chunk.role.value,
            "text_len": len(chunk.text),
            "file": str(out_path.relative_to(self._output_dir)),
        })

    def _generate_audio(
        self, text: str, profile: Any, voice_id: str
    ) -> tuple[list[Any], int]:
        """Dispatch to the correct Qwen3-TTS generation method."""
        if profile.method == VoiceMethod.CLONE:
            return self._generate_clone(text, profile, voice_id)
        if profile.method == VoiceMethod.DESIGN:
            return self._generate_clone(text, profile, voice_id)
        if profile.method == VoiceMethod.CUSTOM:
            return self._generate_custom_voice(text, profile)
        raise ValueError(f"Unknown voice method: {profile.method}")

    def _generate_clone(
        self, text: str, profile: Any, voice_id: str
    ) -> tuple[list[Any], int]:
        """Generate audio using voice cloning."""
        model = self._vm.get_model()
        prompt = self._vm.get_clone_prompt(voice_id)
        wavs, sr = model.generate_voice_clone(
            text=text,
            language=profile.language,
            voice_clone_prompt=prompt,
        )
        return wavs, sr

    def _generate_custom_voice(
        self, text: str, profile: Any
    ) -> tuple[list[Any], int]:
        """Generate audio using a built-in CustomVoice speaker."""
        model = self._vm.get_custom_voice_model()
        wavs, sr = model.generate_custom_voice(
            text=text,
            language=profile.language,
            speaker=profile.speaker,
        )
        return wavs, sr

    def _write_manifest(self) -> None:
        """Write synthesis manifest JSON."""
        manifest_path = self._output_dir / "synthesis_manifest.json"
        manifest_path.write_text(
            json.dumps(self._manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
