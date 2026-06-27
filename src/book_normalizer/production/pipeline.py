"""Production preflight orchestration for audiobook manifests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from book_normalizer.chunking.manifest_v2 import save_manifest
from book_normalizer.production.audiobook_package import (
    AudiobookPackageResult,
    build_audiobook_package,
)
from book_normalizer.production.casting import (
    DEFAULT_CASTING_PLAN_NAME,
    DEFAULT_VOICE_OVERRIDES_NAME,
    apply_casting_plan_to_manifest,
    build_casting_plan,
    casting_voice_overrides,
    write_casting_plan,
    write_voice_overrides,
)
from book_normalizer.production.character_bible import (
    DEFAULT_CHARACTER_BIBLE_NAME,
    apply_character_bible_to_manifest,
    build_character_bible,
    rows_from_manifest,
    write_character_bible,
)
from book_normalizer.production.director import (
    DEFAULT_DIRECTOR_SCORE_NAME,
    apply_director_score_to_manifest,
    build_director_score,
    write_director_score,
)
from book_normalizer.production.quality import (
    DEFAULT_PRODUCTION_QA_REPORT_NAME,
    ProductionQaConfig,
    annotate_manifest_with_production_qa,
    run_production_qa,
    write_production_qa_report,
)

DEFAULT_PRODUCTION_RUN_REPORT_NAME = "production_run_report.json"


@dataclass(frozen=True)
class ProductionPreflightResult:
    """Paths produced by one production preflight run."""

    output_dir: Path
    manifest_path: Path
    character_bible_path: Path
    casting_plan_path: Path
    voice_overrides_path: Path
    director_score_path: Path
    production_qa_report_path: Path
    run_report_path: Path
    package_report_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_dir": str(self.output_dir),
            "manifest_path": str(self.manifest_path),
            "character_bible_path": str(self.character_bible_path),
            "casting_plan_path": str(self.casting_plan_path),
            "voice_overrides_path": str(self.voice_overrides_path),
            "director_score_path": str(self.director_score_path),
            "production_qa_report_path": str(self.production_qa_report_path),
            "run_report_path": str(self.run_report_path),
            "package_report_path": str(self.package_report_path or ""),
        }


def run_production_preflight(
    manifest_path: Path,
    *,
    output_dir: Path | None = None,
    voice_library_dir: Path | None = None,
    preset_path: Path | None = None,
    min_design_lines: int = 3,
    package: bool = False,
    chapter_audio_dir: Path | None = None,
    title: str = "",
    author: str = "",
    cover_path: Path | None = None,
    bitrate: str = "192k",
    loudness_target: float = -18.0,
    dry_run_package: bool = True,
    allow_review_package: bool = False,
) -> ProductionPreflightResult:
    """Run character, casting, director, QA, and optional packaging stages."""
    out_dir = output_dir or manifest_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    book_title = title or str(raw.get("book_title") or manifest_path.parent.name)

    bible = build_character_bible(
        rows_from_manifest(raw),
        book_title=book_title,
        language=str(raw.get("language") or "ru"),
    )
    bible_path = out_dir / DEFAULT_CHARACTER_BIBLE_NAME
    write_character_bible(bible_path, bible)

    manifest = apply_character_bible_to_manifest(raw, bible)
    casting_plan = build_casting_plan(
        bible,
        voice_library_dir=voice_library_dir,
        preset_path=preset_path,
        min_design_lines=min_design_lines,
    )
    casting_path = out_dir / DEFAULT_CASTING_PLAN_NAME
    overrides_path = out_dir / DEFAULT_VOICE_OVERRIDES_NAME
    write_casting_plan(casting_path, casting_plan)
    write_voice_overrides(overrides_path, casting_voice_overrides(casting_plan))
    manifest = apply_casting_plan_to_manifest(manifest, casting_plan)

    director_score = build_director_score(manifest)
    director_path = out_dir / DEFAULT_DIRECTOR_SCORE_NAME
    write_director_score(director_path, director_score)
    manifest = apply_director_score_to_manifest(manifest, director_score)

    qa_report = run_production_qa(manifest, config=ProductionQaConfig())
    qa_path = out_dir / DEFAULT_PRODUCTION_QA_REPORT_NAME
    write_production_qa_report(qa_path, qa_report)
    annotate_manifest_with_production_qa(manifest, qa_report, report_path=qa_path)
    save_manifest(manifest_path, manifest)

    package_result: AudiobookPackageResult | None = None
    if package:
        package_result = build_audiobook_package(
            manifest_path,
            output_dir=out_dir / "audiobook_package",
            chapter_audio_dir=chapter_audio_dir,
            title=book_title,
            author=author,
            cover_path=cover_path,
            bitrate=bitrate,
            loudness_target=loudness_target,
            require_passed_qa=not allow_review_package,
            dry_run=dry_run_package,
        )

    result = ProductionPreflightResult(
        output_dir=out_dir,
        manifest_path=manifest_path,
        character_bible_path=bible_path,
        casting_plan_path=casting_path,
        voice_overrides_path=overrides_path,
        director_score_path=director_path,
        production_qa_report_path=qa_path,
        run_report_path=out_dir / DEFAULT_PRODUCTION_RUN_REPORT_NAME,
        package_report_path=package_result.report_path if package_result else None,
    )
    run_report = {
        "schema_version": 1,
        "paths": result.to_dict(),
        "character_bible": {
            "total_characters": bible["total_characters"],
            "unresolved_dialogue": bible["summary"]["unresolved_dialogue"],
        },
        "casting": casting_plan["summary"],
        "director": director_score["summary"],
        "production_qa": qa_report["summary"],
        "package": package_result.to_dict() if package_result else None,
    }
    result.run_report_path.write_text(
        json.dumps(run_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result
