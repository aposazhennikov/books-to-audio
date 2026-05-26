"""Chapter mastering helpers for QA-passed v2 audiobook manifests."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from book_normalizer.chunking.manifest_v2 import chunk_is_excluded
from book_normalizer.runtime_paths import configured_ffmpeg_bin
from book_normalizer.tts.manifest_assembly import assemble_from_manifest, load_manifest_v2
from book_normalizer.tts.quality_gate import chunk_quality_status

MASTERING_FILTER = (
    "highpass=f=80,"
    "acompressor=threshold=-18dB:ratio=2:attack=20:release=250,"
    "loudnorm=I=-18:TP=-1.5:LRA=11,"
    "alimiter=limit=0.85"
)


@dataclass
class MasteredFile:
    """One mastered output file."""

    chapter_number: int
    source_path: Path
    output_path: Path
    format: str
    command: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_number": self.chapter_number,
            "source_path": str(self.source_path),
            "output_path": str(self.output_path),
            "format": self.format,
            "command": self.command,
        }


@dataclass
class MasteringResult:
    """Mastering outputs and report path."""

    output_dir: Path
    report_path: Path
    files: list[MasteredFile] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "output_dir": str(self.output_dir),
            "report_path": str(self.report_path),
            "filter": MASTERING_FILTER,
            "files": [item.to_dict() for item in self.files],
        }


def master_manifest(
    manifest_path: Path,
    *,
    output_dir: Path | None = None,
    output_format: str = "both",
    chapter_filter: int | None = None,
    ffmpeg_bin: Path | str | None = None,
) -> MasteringResult:
    """Assemble and master QA-passed chapters to WAV/MP3 outputs."""
    manifest = load_manifest_v2(manifest_path)
    blocking = _quality_blockers(manifest, chapter_filter=chapter_filter)
    if blocking:
        preview = "; ".join(blocking[:8])
        extra = f" (+{len(blocking) - 8} more)" if len(blocking) > 8 else ""
        raise ValueError(f"Mastering blocked by non-passed chunk QA: {preview}{extra}")

    target_dir = output_dir or manifest_path.parent
    assembled = assemble_from_manifest(
        manifest,
        target_dir,
        chapter_filter=chapter_filter,
        strict_missing=True,
    )
    mastered_dir = target_dir / "mastered"
    mastered_dir.mkdir(parents=True, exist_ok=True)
    formats = _formats(output_format)
    ffmpeg = str(ffmpeg_bin or configured_ffmpeg_bin() or "ffmpeg")
    result = MasteringResult(
        output_dir=mastered_dir,
        report_path=mastered_dir / "mastering_report.json",
    )

    for chapter in assembled:
        if not chapter.output_path:
            continue
        for fmt in formats:
            out_path = mastered_dir / f"chapter_{chapter.chapter_number:03d}_mastered.{fmt}"
            command = _ffmpeg_command(ffmpeg, chapter.output_path, out_path, fmt)
            subprocess.run(command, check=True, capture_output=True, text=True)
            result.files.append(
                MasteredFile(
                    chapter_number=chapter.chapter_number,
                    source_path=chapter.output_path,
                    output_path=out_path,
                    format=fmt,
                    command=command,
                )
            )

    result.report_path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _quality_blockers(manifest: dict[str, Any], *, chapter_filter: int | None) -> list[str]:
    blockers: list[str] = []
    for chapter in manifest.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter_index = int(chapter.get("chapter_index", 0))
        if chapter_filter is not None and chapter_index != chapter_filter - 1:
            continue
        for chunk in chapter.get("chunks", []):
            if not isinstance(chunk, dict) or chunk_is_excluded(chunk):
                continue
            status = chunk_quality_status(chunk)
            if status != "passed" or bool(chunk.get("failed")):
                blockers.append(
                    f"ch{chapter_index + 1:03d}/chunk{int(chunk.get('chunk_index', 0)) + 1:03d}={status}"
                )
    return blockers


def _formats(output_format: str) -> list[str]:
    normalized = str(output_format or "both").strip().lower()
    if normalized == "both":
        return ["wav", "mp3"]
    if normalized in {"wav", "mp3"}:
        return [normalized]
    raise ValueError("Master format must be one of: both, wav, mp3.")


def _ffmpeg_command(ffmpeg: str, source: Path, output: Path, fmt: str) -> list[str]:
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(source),
        "-af",
        MASTERING_FILTER,
    ]
    if fmt == "mp3":
        command += ["-codec:a", "libmp3lame", "-b:a", "192k"]
    else:
        command += ["-codec:a", "pcm_s16le"]
    command.append(str(output))
    return command
