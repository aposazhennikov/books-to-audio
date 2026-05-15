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
        self._manifest: list[dict[str, Any]] = (
            self._load_manifest() if resume else []
        )

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
                        if self._should_skip_chunk(chunk):
                            self._record_existing_chunk(chunk)
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
                    if self._should_skip_chunk(chunk):
                        self._record_existing_chunk(chunk)
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
        out_path = self._chunk_output_path(chunk)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        profile = self._vm.get_profile(chunk.voice_id)
        wavs, sr = self._generate_audio(chunk.text, profile, chunk.voice_id)

        import soundfile as sf
        sf.write(str(out_path), wavs[0], sr)

        self._upsert_manifest_entry(self._manifest_entry(chunk, out_path))

    def _should_skip_chunk(self, chunk: VoiceAnnotatedChunk) -> bool:
        """Return True only when progress and the WAV file both exist."""
        if not self._resume:
            return False
        if not self._progress.is_done(chunk.chapter_index, chunk.index):
            return False
        out_path = self._chunk_output_path(chunk)
        if out_path.exists():
            return True
        logger.warning(
            "Progress marked chapter %d chunk %d done, but %s is missing; regenerating.",
            chunk.chapter_index,
            chunk.index,
            out_path,
        )
        return False

    def _record_existing_chunk(self, chunk: VoiceAnnotatedChunk) -> None:
        """Keep skipped resume chunks in the synthesis manifest."""
        out_path = self._chunk_output_path(chunk)
        self._upsert_manifest_entry(self._manifest_entry(chunk, out_path))

    def _chunk_output_path(self, chunk: VoiceAnnotatedChunk) -> Path:
        """Return the expected WAV path for a chunk."""
        ch_dir = self._chunks_dir / f"chapter_{chunk.chapter_index + 1:03d}"
        filename = f"chunk_{chunk.index + 1:03d}_{chunk.voice_id}.wav"
        return ch_dir / filename

    def _manifest_entry(
        self,
        chunk: VoiceAnnotatedChunk,
        out_path: Path,
    ) -> dict[str, Any]:
        """Build a synthesis manifest entry for a chunk."""
        return {
            "chapter_index": chunk.chapter_index,
            "chunk_index": chunk.index,
            "voice_id": chunk.voice_id,
            "role": chunk.role.value,
            "text_len": len(chunk.text),
            "file": out_path.relative_to(self._output_dir).as_posix(),
        }

    def _upsert_manifest_entry(self, entry: dict[str, Any]) -> None:
        """Insert or replace a manifest entry by chapter/chunk index."""
        key = (entry["chapter_index"], entry["chunk_index"])
        for i, existing in enumerate(self._manifest):
            existing_key = (
                existing.get("chapter_index"),
                existing.get("chunk_index"),
            )
            if existing_key == key:
                self._manifest[i] = entry
                return
        self._manifest.append(entry)

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
        ordered = sorted(
            self._manifest,
            key=lambda e: (e.get("chapter_index", 0), e.get("chunk_index", 0)),
        )
        manifest_path.write_text(
            json.dumps(ordered, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_manifest(self) -> list[dict[str, Any]]:
        """Load an existing synthesis manifest for resume."""
        manifest_path = self._output_dir / "synthesis_manifest.json"
        if not manifest_path.exists():
            return []
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]
