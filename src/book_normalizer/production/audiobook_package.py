"""Final audiobook package builder."""

from __future__ import annotations

import json
import re
import subprocess
import wave
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from book_normalizer.chunking.manifest_v2 import chunk_is_excluded
from book_normalizer.runtime_paths import configured_ffmpeg_bin
from book_normalizer.tts.manifest_assembly import load_manifest_v2

PACKAGE_REPORT_VERSION = 1
DEFAULT_PACKAGE_DIR_NAME = "audiobook_package"
DEFAULT_PACKAGE_REPORT_NAME = "audiobook_package_report.json"
DEFAULT_PACKAGE_QA_NAME = "package_qa_report.json"
DEFAULT_CHECKSUM_MANIFEST_NAME = "checksums.sha256"
DEFAULT_LOUDNESS_TARGET = -18.0
MIN_COVER_PIXELS = 300
MAX_COVER_ASPECT_DRIFT = 0.05


@dataclass(frozen=True)
class PackageChapter:
    """One packaged chapter source."""

    chapter_number: int
    title: str
    source_path: Path
    duration_ms: int
    mp3_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_number": self.chapter_number,
            "title": self.title,
            "source_path": str(self.source_path),
            "duration_ms": self.duration_ms,
            "mp3_path": str(self.mp3_path) if self.mp3_path else "",
        }


@dataclass
class AudiobookPackageResult:
    """Package outputs and command log."""

    output_dir: Path
    report_path: Path
    title: str
    author: str = ""
    bitrate: str = "192k"
    loudness_target: float = DEFAULT_LOUDNESS_TARGET
    dry_run: bool = False
    chapters: list[PackageChapter] = field(default_factory=list)
    m4b_path: Path | None = None
    concat_path: Path | None = None
    ffmetadata_path: Path | None = None
    checksum_manifest_path: Path | None = None
    package_qa_path: Path | None = None
    cover_report: dict[str, Any] = field(default_factory=dict)
    package_qa: dict[str, Any] = field(default_factory=dict)
    commands: list[list[str]] = field(default_factory=list)
    blockers: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PACKAGE_REPORT_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "output_dir": str(self.output_dir),
            "title": self.title,
            "author": self.author,
            "bitrate": self.bitrate,
            "loudness_target": self.loudness_target,
            "dry_run": self.dry_run,
            "m4b_path": str(self.m4b_path) if self.m4b_path else "",
            "concat_path": str(self.concat_path) if self.concat_path else "",
            "ffmetadata_path": str(self.ffmetadata_path) if self.ffmetadata_path else "",
            "checksum_manifest_path": str(self.checksum_manifest_path) if self.checksum_manifest_path else "",
            "package_qa_path": str(self.package_qa_path) if self.package_qa_path else "",
            "naming_policy": _naming_policy(),
            "cover": self.cover_report,
            "package_qa": self.package_qa,
            "chapters": [chapter.to_dict() for chapter in self.chapters],
            "commands": self.commands,
            "blockers": self.blockers,
        }


def build_audiobook_package(
    manifest_path: Path,
    *,
    output_dir: Path | None = None,
    chapter_audio_dir: Path | None = None,
    title: str = "",
    author: str = "",
    cover_path: Path | None = None,
    bitrate: str = "192k",
    loudness_target: float = DEFAULT_LOUDNESS_TARGET,
    make_m4b: bool = True,
    make_mp3: bool = True,
    require_passed_qa: bool = True,
    dry_run: bool = False,
    ffmpeg_bin: Path | str | None = None,
) -> AudiobookPackageResult:
    """Create final audiobook package metadata, chapter MP3s, and optional M4B."""
    manifest = load_manifest_v2(manifest_path)
    blockers = package_quality_blockers(manifest)
    if require_passed_qa and blockers:
        preview = "; ".join(_blocker_label(item) for item in blockers[:8])
        extra = f" (+{len(blockers) - 8} more)" if len(blockers) > 8 else ""
        raise ValueError(f"Package blocked by QA status: {preview}{extra}")

    package_dir = output_dir or manifest_path.parent / DEFAULT_PACKAGE_DIR_NAME
    package_dir.mkdir(parents=True, exist_ok=True)
    book_title = title or str(manifest.get("book_title") or manifest_path.parent.name or "Audiobook")
    cover_report = validate_cover(cover_path) if cover_path else {"status": "not_provided"}
    chapters = _collect_chapters(
        manifest,
        chapter_audio_dir=chapter_audio_dir or _default_chapter_audio_dir(manifest_path),
        package_dir=package_dir,
    )
    if not chapters:
        raise ValueError("No chapter audio files found for packaging.")

    ffmpeg = str(ffmpeg_bin or configured_ffmpeg_bin() or "ffmpeg")
    result = AudiobookPackageResult(
        output_dir=package_dir,
        report_path=package_dir / DEFAULT_PACKAGE_REPORT_NAME,
        title=book_title,
        author=author,
        bitrate=bitrate,
        loudness_target=loudness_target,
        dry_run=dry_run,
        chapters=chapters,
        blockers=blockers,
        cover_report=cover_report,
    )
    result.checksum_manifest_path = package_dir / DEFAULT_CHECKSUM_MANIFEST_NAME

    if make_mp3:
        _prepare_mp3_exports(result, ffmpeg=ffmpeg, cover_path=cover_path)
    if make_m4b:
        _prepare_m4b(result, ffmpeg=ffmpeg, cover_path=cover_path)

    result.package_qa_path = package_dir / DEFAULT_PACKAGE_QA_NAME
    result.package_qa = run_package_qa(result, require_media=not dry_run)
    result.package_qa_path.write_text(
        json.dumps(result.package_qa, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    result.report_path.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_checksum_manifest(result.checksum_manifest_path, package_dir)
    return result


def validate_cover(cover_path: Path) -> dict[str, Any]:
    """Validate audiobook cover format and production-friendly dimensions."""
    image = cover_path.read_bytes()
    fmt, width, height = _image_info(image)
    issues: list[str] = []
    if fmt not in {"jpeg", "png"}:
        issues.append("cover_must_be_jpeg_or_png")
    if width < MIN_COVER_PIXELS or height < MIN_COVER_PIXELS:
        issues.append(f"cover_min_dimension_{MIN_COVER_PIXELS}px")
    aspect_drift = abs(width - height) / max(width, height, 1)
    if aspect_drift > MAX_COVER_ASPECT_DRIFT:
        issues.append("cover_should_be_square")
    report = {
        "status": "passed" if not issues else "failed",
        "path": str(cover_path),
        "format": fmt,
        "width": width,
        "height": height,
        "issues": issues,
    }
    if issues:
        raise ValueError("Invalid cover image: " + ", ".join(issues))
    return report


def package_quality_blockers(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Return chunks that should block final package generation."""
    blockers: list[dict[str, Any]] = []
    for chapter in manifest.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter_index = int(chapter.get("chapter_index") or 0)
        for chunk in chapter.get("chunks", []):
            if not isinstance(chunk, dict) or chunk_is_excluded(chunk):
                continue
            status = str(chunk.get("qa_status") or "").strip().lower()
            perceptual = chunk.get("perceptual_qa") if isinstance(chunk.get("perceptual_qa"), dict) else {}
            perceptual_status = str(perceptual.get("status") or "").strip().lower()
            if not status and perceptual_status:
                status = perceptual_status
            if not status:
                status = "unchecked"
            if status != "passed" or bool(chunk.get("failed")):
                blockers.append(
                    {
                        "chapter_index": chapter_index,
                        "chunk_index": int(chunk.get("chunk_index") or 0),
                        "status": status,
                        "speaker": str(chunk.get("canonical_speaker") or chunk.get("speaker") or ""),
                        "issues": list(perceptual.get("issues") or []),
                    }
                )
    return blockers


def run_package_qa(result: AudiobookPackageResult, *, require_media: bool = True) -> dict[str, Any]:
    """Return package-level QA checks for final operator sign-off."""
    issues: list[dict[str, Any]] = []
    if not result.chapters:
        issues.append({"severity": "error", "kind": "no_chapters", "message": "No chapters were packaged."})
    for chapter in result.chapters:
        if chapter.duration_ms <= 1:
            issues.append(
                {
                    "severity": "warning",
                    "kind": "unknown_duration",
                    "message": f"Chapter {chapter.chapter_number:03d} has unknown or tiny duration.",
                }
            )
        if not chapter.source_path.exists():
            issues.append(
                {
                    "severity": "error",
                    "kind": "missing_source_audio",
                    "message": str(chapter.source_path),
                }
            )
        if require_media and chapter.mp3_path and not chapter.mp3_path.exists():
            issues.append({"severity": "error", "kind": "missing_mp3", "message": str(chapter.mp3_path)})
    if require_media and result.m4b_path and not result.m4b_path.exists():
        issues.append({"severity": "error", "kind": "missing_m4b", "message": str(result.m4b_path)})
    if result.cover_report.get("status") == "failed":
        issues.append(
            {"severity": "error", "kind": "invalid_cover", "message": ",".join(result.cover_report["issues"])}
        )
    if result.blockers:
        issues.append(
            {
                "severity": "error",
                "kind": "manifest_qa_blockers",
                "message": f"{len(result.blockers)} chunks are not production-passed.",
            }
        )
    status = "failed" if any(item["severity"] == "error" for item in issues) else "passed"
    return {
        "schema_version": 1,
        "status": status,
        "summary": {
            "chapters": len(result.chapters),
            "issues": len(issues),
            "loudness_target_lufs": result.loudness_target,
            "cover_status": result.cover_report.get("status", "not_provided"),
        },
        "issues": issues,
    }


def write_checksum_manifest(path: Path, package_dir: Path) -> None:
    """Write a sha256 checksum manifest for package artifacts."""
    import hashlib

    rows: list[str] = []
    for item in sorted(package_dir.rglob("*")):
        if not item.is_file() or item == path:
            continue
        digest = hashlib.sha256(item.read_bytes()).hexdigest()
        rel = item.relative_to(package_dir).as_posix()
        rows.append(f"{digest}  {rel}")
    path.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")


def _collect_chapters(
    manifest: dict[str, Any],
    *,
    chapter_audio_dir: Path,
    package_dir: Path,
) -> list[PackageChapter]:
    chapters: list[PackageChapter] = []
    for chapter in manifest.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter_index = int(chapter.get("chapter_index") or 0)
        chapter_number = chapter_index + 1
        title = str(chapter.get("chapter_title") or f"Chapter {chapter_number}")
        source = _find_chapter_audio(chapter_audio_dir, chapter_number)
        if source is None:
            continue
        mp3_path = package_dir / f"{chapter_number:02d} - {_safe_filename(title)}.mp3"
        chapters.append(
            PackageChapter(
                chapter_number=chapter_number,
                title=title,
                source_path=source,
                duration_ms=_duration_ms(source),
                mp3_path=mp3_path,
            )
        )
    return chapters


def _prepare_mp3_exports(
    result: AudiobookPackageResult,
    *,
    ffmpeg: str,
    cover_path: Path | None,
) -> None:
    updated: list[PackageChapter] = []
    for chapter in result.chapters:
        if chapter.mp3_path is None:
            updated.append(chapter)
            continue
        command = [
            ffmpeg,
            "-y",
            "-i",
            str(chapter.source_path),
        ]
        if cover_path:
            command += ["-i", str(cover_path), "-map", "0:a", "-map", "1:v?", "-disposition:v:0", "attached_pic"]
        command += [
            "-metadata",
            f"title={chapter.title}",
            "-metadata",
            f"album={result.title}",
        ]
        if result.author:
            command += ["-metadata", f"artist={result.author}"]
        command += [
            "-af",
            _loudnorm_filter(result.loudness_target),
            "-codec:a",
            "libmp3lame",
            "-b:a",
            result.bitrate,
            str(chapter.mp3_path),
        ]
        result.commands.append(command)
        if not result.dry_run:
            subprocess.run(command, check=True, capture_output=True, text=True)
        updated.append(chapter)
    result.chapters = updated


def _prepare_m4b(
    result: AudiobookPackageResult,
    *,
    ffmpeg: str,
    cover_path: Path | None,
) -> None:
    safe_title = _safe_filename(result.title)
    concat_path = result.output_dir / "chapters.concat.txt"
    ffmetadata_path = result.output_dir / "chapters.ffmetadata"
    m4b_path = result.output_dir / f"{safe_title}.m4b"
    _write_concat_file(concat_path, [chapter.source_path for chapter in result.chapters])
    _write_ffmetadata(ffmetadata_path, result)
    command = [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_path),
        "-i",
        str(ffmetadata_path),
    ]
    if cover_path:
        command += ["-i", str(cover_path)]
    command += [
        "-map",
        "0:a",
        "-map_metadata",
        "1",
        "-map_chapters",
        "1",
        "-metadata",
        f"title={result.title}",
    ]
    if result.author:
        command += ["-metadata", f"artist={result.author}"]
    if cover_path:
        command += ["-map", "2:v?", "-disposition:v:0", "attached_pic"]
    command += ["-af", _loudnorm_filter(result.loudness_target), "-c:a", "aac", "-b:a", result.bitrate, str(m4b_path)]
    result.concat_path = concat_path
    result.ffmetadata_path = ffmetadata_path
    result.m4b_path = m4b_path
    result.commands.append(command)
    if not result.dry_run:
        subprocess.run(command, check=True, capture_output=True, text=True)


def _write_concat_file(path: Path, chapter_paths: list[Path]) -> None:
    lines = [f"file '{_ffconcat_path(chapter)}'" for chapter in chapter_paths]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_ffmetadata(path: Path, result: AudiobookPackageResult) -> None:
    lines = [
        ";FFMETADATA1",
        f"title={_ffmetadata_escape(result.title)}",
        "genre=Audiobook",
    ]
    if result.author:
        lines.append(f"artist={_ffmetadata_escape(result.author)}")
    start = 0
    for chapter in result.chapters:
        end = start + max(1, int(chapter.duration_ms))
        lines += [
            "[CHAPTER]",
            "TIMEBASE=1/1000",
            f"START={start}",
            f"END={end}",
            f"title={_ffmetadata_escape(chapter.title)}",
        ]
        start = end
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _default_chapter_audio_dir(manifest_path: Path) -> Path:
    mastered = manifest_path.parent / "mastered"
    return mastered if mastered.exists() else manifest_path.parent


def _find_chapter_audio(chapter_audio_dir: Path, chapter_number: int) -> Path | None:
    patterns = [
        f"chapter_{chapter_number:03d}_mastered.mp3",
        f"chapter_{chapter_number:03d}_mastered.wav",
        f"chapter_{chapter_number:03d}.mp3",
        f"chapter_{chapter_number:03d}.wav",
    ]
    for pattern in patterns:
        candidate = chapter_audio_dir / pattern
        if candidate.exists():
            return candidate
    matches = sorted(chapter_audio_dir.glob(f"*{chapter_number:03d}*.wav"))
    if matches:
        return matches[0]
    matches = sorted(chapter_audio_dir.glob(f"*{chapter_number:03d}*.mp3"))
    return matches[0] if matches else None


def _duration_ms(path: Path) -> int:
    if path.suffix.lower() != ".wav":
        return 1
    with wave.open(str(path), "rb") as wav:
        frames = wav.getnframes()
        rate = wav.getframerate()
    return int(frames * 1000 / rate) if rate else 1


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]+', "", value).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:120] or "Audiobook"


def _naming_policy() -> dict[str, Any]:
    return {
        "chapter_mp3": "NN - Chapter Title.mp3",
        "m4b": "Book Title.m4b",
        "max_stem_chars": 120,
        "forbidden_characters": '<>:"/\\\\|?*',
        "whitespace": "collapsed",
    }


def _loudnorm_filter(target: float) -> str:
    return f"loudnorm=I={target:g}:TP=-1.5:LRA=11"


def _image_info(data: bytes) -> tuple[str, int, int]:
    if data.startswith(b"\xff\xd8"):
        return _jpeg_info(data)
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return "png", int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    return "unknown", 0, 0


def _jpeg_info(data: bytes) -> tuple[str, int, int]:
    index = 2
    while index + 9 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        index += 2
        if marker in {0xD8, 0xD9}:
            continue
        if index + 2 > len(data):
            break
        segment_length = int.from_bytes(data[index : index + 2], "big")
        if segment_length < 2 or index + segment_length > len(data):
            break
        if marker in {0xC0, 0xC1, 0xC2, 0xC3} and segment_length >= 7:
            height = int.from_bytes(data[index + 3 : index + 5], "big")
            width = int.from_bytes(data[index + 5 : index + 7], "big")
            return "jpeg", width, height
        index += segment_length
    return "jpeg", 0, 0


def _ffconcat_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace("'", "'\\''")


def _ffmetadata_escape(value: str) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace("#", "\\#")
        .replace("=", "\\=")
        .replace("\n", " ")
    )


def _blocker_label(item: dict[str, Any]) -> str:
    return (
        f"ch{int(item.get('chapter_index') or 0) + 1:03d}/"
        f"chunk{int(item.get('chunk_index') or 0) + 1:03d}={item.get('status')}"
    )
