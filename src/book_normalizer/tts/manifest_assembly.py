"""Assemble v2 manifest audio chunks into chapter WAV files."""

from __future__ import annotations

import json
import logging
import re
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from book_normalizer.chunking.manifest_v2 import chunk_is_excluded, ensure_v2_manifest
from book_normalizer.runtime_paths import configured_ffmpeg_bin
from book_normalizer.tts.compatible_audio import export_compatible_mp3

logger = logging.getLogger(__name__)


@dataclass
class ChapterAssemblyResult:
    """Result for one assembled chapter."""

    chapter_number: int
    output_path: Path | None
    chunks: int
    compatible_output_path: Path | None = None
    missing: int = 0
    skipped: bool = False
    messages: list[str] = field(default_factory=list)


def load_manifest_v2(manifest_path: Path) -> dict[str, Any]:
    """Load a v2 chunks manifest from disk."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = ensure_v2_manifest(data).to_record()
    manifest["_manifest_path"] = str(manifest_path)
    return manifest


def assemble_from_manifest(
    manifest: dict[str, Any],
    out_dir: Path,
    *,
    pause_same_voice_ms: int = 300,
    pause_voice_change_ms: int = 600,
    chapter_filter: int | None = None,
    strict_missing: bool = False,
    manifest_path: Path | None = None,
) -> list[ChapterAssemblyResult]:
    """Assemble synthesized chunks in manifest order."""
    manifest_path = manifest_path or _manifest_path_from_record(manifest)
    manifest = ensure_v2_manifest(manifest).to_record()
    out_dir.mkdir(parents=True, exist_ok=True)
    chapters = manifest.get("chapters", [])
    if not chapters:
        raise ValueError("No chapters found in manifest.")

    results: list[ChapterAssemblyResult] = []
    for chapter_entry in chapters:
        if not isinstance(chapter_entry, dict):
            continue
        chapter_index = int(chapter_entry.get("chapter_index", 0))
        chapter_number = chapter_index + 1
        if chapter_filter is not None and chapter_number != chapter_filter:
            continue

        chunks = [
            c for c in chapter_entry.get("chunks", [])
            if (
                isinstance(c, dict)
                and not chunk_is_excluded(c)
                and c.get("synthesized", False)
                and c.get("audio_file")
            )
        ]
        if not chunks:
            results.append(
                ChapterAssemblyResult(
                    chapter_number=chapter_number,
                    output_path=None,
                    chunks=0,
                    skipped=True,
                    messages=[f"Chapter {chapter_number:03d}: no synthesized chunks found, skipping."],
                )
            )
            continue

        wav_files: list[Path] = []
        voice_labels: list[str] = []
        pause_after_ms: list[int] = []
        messages: list[str] = []
        missing = 0
        for chunk in chunks:
            audio_path = _resolve_audio_path(str(chunk["audio_file"]), manifest_path)
            if not audio_path.exists():
                missing += 1
                message = f"Missing audio file {audio_path}"
                if strict_missing:
                    raise FileNotFoundError(message)
                messages.append(f"WARNING: {message}, skipping chunk.")
                continue
            wav_files.append(audio_path)
            voice_labels.append(str(chunk.get("voice", chunk.get("voice_label", "narrator"))))
            pause_after_ms.append(int(chunk.get("pause_after_ms") or 0))

        if not wav_files:
            results.append(
                ChapterAssemblyResult(
                    chapter_number=chapter_number,
                    output_path=None,
                    chunks=0,
                    missing=missing,
                    skipped=True,
                    messages=messages + [f"Chapter {chapter_number:03d}: no audio files available, skipping."],
                )
            )
            continue

        out_path = out_dir / f"chapter_{chapter_number:03d}.wav"
        assembled_chunks = assemble_wav_files(
            wav_files,
            out_path,
            pause_same_voice_ms=pause_same_voice_ms,
            pause_voice_change_ms=pause_voice_change_ms,
            voice_labels=voice_labels,
            pause_after_ms=pause_after_ms,
        )
        compatible_path = _export_compatible_chapter(out_path, messages)
        results.append(
            ChapterAssemblyResult(
                chapter_number=chapter_number,
                output_path=out_path,
                chunks=assembled_chunks,
                compatible_output_path=compatible_path,
                missing=missing,
                messages=messages,
            )
        )

    return results


def _export_compatible_chapter(out_path: Path, messages: list[str]) -> Path | None:
    """Best-effort compatible MP3 sidecar for an assembled chapter."""
    try:
        return export_compatible_mp3(
            out_path,
            ffmpeg=str(configured_ffmpeg_bin() or "ffmpeg"),
        )
    except Exception as exc:  # pragma: no cover - depends on local ffmpeg/runtime media
        logger.warning("Compatible chapter MP3 export failed for %s: %s", out_path, exc)
        messages.append(f"WARNING: compatible MP3 export failed for {out_path}: {exc}")
        return None


def _manifest_path_from_record(manifest: dict[str, Any]) -> Path | None:
    raw_path = str(manifest.get("_manifest_path") or "")
    return Path(raw_path) if raw_path else None


def _resolve_audio_path(audio_file: str, manifest_path: Path | None) -> Path:
    path = Path(audio_file)
    if not path.is_absolute() and manifest_path is not None:
        path = manifest_path.parent / path
    return path


def assemble_wav_files(
    wav_files: list[Path],
    out_path: Path,
    *,
    pause_same_voice_ms: int = 300,
    pause_voice_change_ms: int = 600,
    voice_labels: list[str] | None = None,
    pause_after_ms: list[int] | None = None,
) -> int:
    """Concatenate WAV files with silence between chunks."""
    if not wav_files:
        return 0

    first_params = _read_params(wav_files[0])
    if first_params is None:
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as out_wav:
        out_wav.setparams(first_params)
        prev_voice: str | None = None
        written = 0

        for idx, wav_path in enumerate(wav_files):
            voice = voice_labels[idx] if voice_labels and idx < len(voice_labels) else _voice_from_filename(wav_path)
            with wave.open(str(wav_path), "rb") as in_wav:
                params = in_wav.getparams()
                if params[:3] != first_params[:3]:
                    raise ValueError(
                        f"WAV params mismatch for {wav_path}: expected {first_params[:3]}, got {params[:3]}"
                    )
                if prev_voice is not None:
                    pause_ms = pause_voice_change_ms if voice != prev_voice else pause_same_voice_ms
                    if pause_after_ms and idx - 1 < len(pause_after_ms):
                        pause_ms = max(pause_ms, pause_after_ms[idx - 1])
                    out_wav.writeframes(_silence_bytes(pause_ms, first_params))
                out_wav.writeframes(in_wav.readframes(in_wav.getnframes()))
                written += 1
            prev_voice = voice

    return written


def _read_params(path: Path) -> wave._wave_params | None:  # type: ignore[name-defined]
    try:
        with wave.open(str(path), "rb") as wav:
            return wav.getparams()
    except wave.Error:
        return None


def _voice_from_filename(path: Path) -> str:
    match = re.search(r"chunk_\d+_(\w+)\.wav", path.name)
    return match.group(1) if match else "unknown"


def _silence_bytes(duration_ms: int, params: wave._wave_params) -> bytes:  # type: ignore[name-defined]
    frames = int(params.framerate * duration_ms / 1000)
    return b"\x00" * frames * params.nchannels * params.sampwidth
