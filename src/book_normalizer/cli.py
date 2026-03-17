"""Command-line interface for the book normalizer."""

from __future__ import annotations

import json
import logging
import sys
from copy import deepcopy
from pathlib import Path

import click

from book_normalizer import __version__
from book_normalizer.chaptering.detector import ChapterDetector
from book_normalizer.config import AppConfig, OcrMode
from book_normalizer.exporters.json_exporter import JsonExporter
from book_normalizer.exporters.qwen_exporter import QwenExporter
from book_normalizer.exporters.txt_exporter import TxtExporter
from book_normalizer.loaders.factory import LoaderFactory
from book_normalizer.loaders.pdf_loader import PdfLoader, extract_pdf_with_ocr_mode
from book_normalizer.logging_config import setup_logging
from book_normalizer.memory.correction_store import CorrectionStore
from book_normalizer.memory.punctuation_store import PunctuationStore
from book_normalizer.memory.stress_store import StressStore
from book_normalizer.normalization.pipeline import NormalizationPipeline
from book_normalizer.review.reviewer import Reviewer
from book_normalizer.review.session import ReviewSession, SessionManager
from book_normalizer.review.tui import InteractiveReviewer
from book_normalizer.stress.annotator import StressAnnotator
from book_normalizer.stress.dictionary import StressDictionary
from book_normalizer.stress.resolver import StressResolver
from book_normalizer.verification import run_verification

logger = logging.getLogger(__name__)


def _sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a directory name."""
    import re

    name = name.strip()
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = re.sub(r"\s+", "_", name)
    name = name[:100]
    return name if name else "untitled"


def _build_output_dir(input_path: Path, base_out: Path) -> Path:
    """Build output directory path: base_out/bookname_format/."""
    stem = input_path.stem
    fmt = input_path.suffix.lstrip(".")
    sanitized_name = _sanitize_filename(stem)
    folder_name = f"{sanitized_name}_{fmt}" if fmt else sanitized_name
    return base_out / folder_name


def _build_config(
    verbose: bool,
    interactive: bool,
    resume: bool,
    skip_stress: bool,
    skip_punctuation_review: bool,
    skip_spellcheck: bool,
    export_json: bool,
    chapters_only: bool,
    ocr_mode: OcrMode,
) -> AppConfig:
    """Build an AppConfig from CLI flags."""
    return AppConfig(
        verbose=verbose,
        interactive=interactive,
        resume=resume,
        skip_stress=skip_stress,
        skip_punctuation_review=skip_punctuation_review,
        skip_spellcheck=skip_spellcheck,
        export_json=export_json,
        chapters_only=chapters_only,
        ocr_mode=ocr_mode,
    )


@click.group()
@click.version_option(version=__version__, prog_name="normalize-book")
def main() -> None:
    """Semi-automatic Russian book normalizer for TTS pipelines."""


@main.command(name="process")
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option("--out", "-o", type=click.Path(path_type=Path), default=Path("output"), help="Output directory.")
@click.option("--interactive", "-i", is_flag=True, default=False, help="Enable interactive review mode.")
@click.option("--resume", is_flag=True, default=False, help="Resume previous review session.")
@click.option("--skip-stress", is_flag=True, default=False, help="Skip stress annotation.")
@click.option("--skip-punctuation-review", is_flag=True, default=False, help="Skip punctuation review.")
@click.option("--skip-spellcheck", is_flag=True, default=False, help="Skip spell checking.")
@click.option("--chapters-only", is_flag=True, default=False, help="Export only chapter files.")
@click.option("--export-json/--no-export-json", default=True, help="Export JSON structure.")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Verbose logging output.")
@click.option(
    "--ocr-mode",
    type=click.Choice([m.value for m in OcrMode]),
    default=OcrMode.OFF.value,
    show_default=True,
    help="OCR execution mode for PDF files.",
)
@click.option(
    "--verify-report",
    is_flag=True,
    default=False,
    help="Generate before/after verification reports for quality control.",
)
@click.option(
    "--sample-size",
    type=int,
    default=20,
    show_default=True,
    help="Number of random paragraph samples in verification report.",
)
def process_command(
    input_path: Path,
    out: Path,
    interactive: bool,
    resume: bool,
    skip_stress: bool,
    skip_punctuation_review: bool,
    skip_spellcheck: bool,
    chapters_only: bool,
    export_json: bool,
    verbose: bool,
    ocr_mode: str,
    verify_report: bool,
    sample_size: int,
) -> None:
    """Process a single book file: load, normalize, split chapters, export."""
    setup_logging(verbose=verbose)

    config = _build_config(
        verbose=verbose,
        interactive=interactive,
        resume=resume,
        skip_stress=skip_stress,
        skip_punctuation_review=skip_punctuation_review,
        skip_spellcheck=skip_spellcheck,
        export_json=export_json,
        chapters_only=chapters_only,
        ocr_mode=OcrMode(ocr_mode),
    )

    click.echo(f"Processing: {input_path}")

    try:
        factory = LoaderFactory.default()
        if input_path.suffix.lower() == ".pdf":
            compare = extract_pdf_with_ocr_mode(input_path, config.ocr_mode)
            chosen_variant, ocr_stats = select_pdf_text_for_mode(compare, config.ocr_mode)

            # Build Book from the chosen text variant.
            loader = PdfLoader()
            paragraphs = loader._split_paragraphs(chosen_variant.text)
            chapter = Chapter(
                title="Full Text",
                index=0,
                paragraphs=paragraphs,
                source_span_start=0,
                source_span_end=len(chosen_variant.text),
            )
            metadata = Metadata(
                source_path=str(input_path.resolve()),
                source_format="pdf",
            )
            from book_normalizer.models.book import Book as BookModel

            book = BookModel(metadata=metadata, chapters=[chapter])
            book.add_audit(
                "loading",
                "pdf_loader_ocr_mode",
                f"mode={config.ocr_mode.value}, selected={ocr_stats.get('selected')}, "
                f"native_len={ocr_stats.get('native_len')}, ocr_len={ocr_stats.get('ocr_len')}",
            )
            # In COMPARE mode, compare artifacts will be written after output_dir is known.
        else:
            book = factory.load(input_path)
    except (FileNotFoundError, ValueError, ImportError) as exc:
        click.echo(f"Error loading file: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Loaded: {len(book.chapters)} chapter(s), source={book.metadata.source_format}")

    verification_before = deepcopy(book) if verify_report else None

    output_dir = _build_output_dir(input_path, out).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # If PDF compare mode was used, write compare report artifacts now.
    if input_path.suffix.lower() == ".pdf" and config.ocr_mode == OcrMode.COMPARE:
        try:
            from book_normalizer.loaders.pdf_loader import (
                extract_pdf_with_ocr_mode as _extract_for_report,
                select_pdf_text_for_mode as _select_for_report,
                write_pdf_compare_report,
            )

            compare = _extract_for_report(input_path, config.ocr_mode)
            chosen_variant, ocr_stats = _select_for_report(compare, config.ocr_mode)
            write_pdf_compare_report(output_dir, compare, ocr_stats)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to write PDF compare report: %s", exc)

    pipeline = NormalizationPipeline()
    book = pipeline.normalize_book(book)
    click.echo("Normalization complete.")

    detector = ChapterDetector()
    book = detector.detect_and_split(book)
    click.echo(f"Chapter detection complete: {len(book.chapters)} chapter(s) found.")

    pipeline.normalize_book(book)

    correction_store = CorrectionStore(config.correction_memory_path)
    punctuation_store = PunctuationStore(config.punctuation_memory_path)
    session_mgr = SessionManager(config.review_sessions_dir)

    need_review = interactive or not (skip_punctuation_review and skip_spellcheck)

    if need_review:
        session = _run_review(
            book=book,
            config=config,
            correction_store=correction_store,
            punctuation_store=punctuation_store,
            session_mgr=session_mgr,
            interactive=interactive,
            resume=resume,
        )

        if session and session.resolved_count > 0:
            reviewer = Reviewer(correction_store=correction_store, punctuation_store=punctuation_store)
            reviewer.apply_decisions_to_book(book, session)
            click.echo(f"Applied {session.resolved_count} review correction(s).")

        if session:
            session_path = session_mgr.save(session)
            click.echo(f"Review session: {session_path}")

    if not skip_stress:
        stress_store = StressStore(config.stress_dict_path)
        stress_dict = StressDictionary(store=stress_store)
        annotator = StressAnnotator(stress_dict)
        ann_result = annotator.annotate_book(book)

        click.echo(
            f"Stress annotation: {ann_result.total_words} words, "
            f"{ann_result.known_words} known, "
            f"{ann_result.unknown_words} unknown."
        )

        if ann_result.unknown_words > 0 and interactive:
            resolver = StressResolver(dictionary=stress_dict)
            resolved = resolver.resolve(book, ann_result)
            click.echo(f"Stress review: {resolved} word(s) resolved.")

    if not chapters_only:
        txt_exporter = TxtExporter()
        txt_files = txt_exporter.export(book, output_dir)
        click.echo(f"TXT export: {len(txt_files)} file(s)")

    qwen_exporter = QwenExporter()
    qwen_files = qwen_exporter.export(book, output_dir)
    click.echo(f"Qwen-TTS export: {len(qwen_files)} file(s)")

    if export_json:
        json_exporter = JsonExporter()
        json_path = json_exporter.export(book, output_dir)
        click.echo(f"JSON structure: {json_path}")

    audit_path = output_dir / "audit_log.json"
    audit_path.write_text(
        json.dumps(book.audit_trail, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    click.echo(f"Audit log: {audit_path}")

    if verify_report and verification_before is not None:
        verification_result = run_verification(
            before=verification_before,
            after=book,
            output_dir=output_dir,
            sample_size=sample_size,
        )
        click.echo(
            "Verification reports generated: "
            f"{verification_result.artifacts['stats_before_after']}, "
            f"{verification_result.artifacts['suspicious_changes']}, "
            f"{verification_result.artifacts['random_sample_review']}"
        )

    click.echo("Done.")


def _run_review(
    book: object,
    config: AppConfig,
    correction_store: CorrectionStore,
    punctuation_store: PunctuationStore,
    session_mgr: SessionManager,
    interactive: bool,
    resume: bool,
) -> ReviewSession | None:
    """Run the review scan and optionally the interactive TUI."""
    from book_normalizer.models.book import Book

    if not isinstance(book, Book):
        return None

    if resume:
        existing = session_mgr.find_latest_for_book(book.id)
        if existing:
            click.echo(f"Resuming session from {existing}")
            session = session_mgr.load(existing)
        else:
            click.echo("No previous session found, starting fresh scan.")
            session = _scan_book(book, config, correction_store, punctuation_store)
    else:
        session = _scan_book(book, config, correction_store, punctuation_store)

    if session.pending_count == 0:
        click.echo("No issues require review.")
        return session

    click.echo(f"Found {session.pending_count} issue(s) requiring review.")

    if interactive:
        tui = InteractiveReviewer(
            correction_store=correction_store,
            punctuation_store=punctuation_store,
        )
        session = tui.run(session)
    else:
        click.echo("Run with --interactive to review issues, or they will be skipped.")

    return session


def _scan_book(
    book: object,
    config: AppConfig,
    correction_store: CorrectionStore,
    punctuation_store: PunctuationStore,
) -> ReviewSession:
    """Run detectors on the book and return a session."""
    from book_normalizer.models.book import Book

    reviewer = Reviewer(
        correction_store=correction_store,
        punctuation_store=punctuation_store,
        skip_punctuation=config.skip_punctuation_review,
        skip_spellcheck=config.skip_spellcheck,
    )
    return reviewer.scan(book)


@main.command(name="batch")
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--out", "-o", type=click.Path(path_type=Path), default=Path("output"), help="Output base directory.")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Verbose logging output.")
def batch_command(input_dir: Path, out: Path, verbose: bool) -> None:
    """Process all supported book files in a directory."""
    setup_logging(verbose=verbose)

    factory = LoaderFactory.default()
    supported_exts = set()
    for loader in factory._loaders:
        supported_exts.update(loader.supported_extensions)

    files = [f for f in sorted(input_dir.iterdir()) if f.suffix.lower() in supported_exts]

    if not files:
        click.echo(f"No supported files found in {input_dir}")
        sys.exit(0)

    click.echo(f"Found {len(files)} file(s) to process.")

    pipeline = NormalizationPipeline()
    chapter_detector = ChapterDetector()
    txt_exporter = TxtExporter()
    json_exporter = JsonExporter()
    qwen_exporter = QwenExporter()

    for file_path in files:
        click.echo(f"\n--- Processing: {file_path.name} ---")
        try:
            book = factory.load(file_path)
            book = pipeline.normalize_book(book)
            book = chapter_detector.detect_and_split(book)
            pipeline.normalize_book(book)

            book_out = _build_output_dir(file_path, out)
            book_out.mkdir(parents=True, exist_ok=True)
            txt_exporter.export(book, book_out)
            qwen_exporter.export(book, book_out)
            json_exporter.export(book, book_out)

            click.echo(f"  OK: {len(book.chapters)} chapter(s)")
        except Exception as exc:
            click.echo(f"  FAILED: {exc}", err=True)
            logger.exception("Failed to process %s", file_path)

    click.echo("\nBatch processing complete.")


@main.command(name="info")
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
def info_command(input_path: Path) -> None:
    """Show basic info about a book file without processing."""
    setup_logging(verbose=False)

    try:
        factory = LoaderFactory.default()
        book = factory.load(input_path)
    except (FileNotFoundError, ValueError, ImportError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    total_paras = sum(len(ch.paragraphs) for ch in book.chapters)
    total_chars = len(book.raw_text)

    click.echo(f"File:       {input_path}")
    click.echo(f"Format:     {book.metadata.source_format}")
    click.echo(f"Title:      {book.metadata.title}")
    click.echo(f"Author:     {book.metadata.author}")
    click.echo(f"Chapters:   {len(book.chapters)}")
    click.echo(f"Paragraphs: {total_paras}")
    click.echo(f"Characters: {total_chars:,}")


@main.command(name="review-session")
@click.argument("session_path", type=click.Path(exists=True, path_type=Path))
def review_session_command(session_path: Path) -> None:
    """Show info about a saved review session."""
    setup_logging(verbose=False)

    session_mgr = SessionManager(session_path.parent)
    try:
        session = session_mgr.load(session_path)
    except (FileNotFoundError, Exception) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Session ID:  {session.session_id}")
    click.echo(f"Book ID:     {session.book_id}")
    click.echo(f"Source:      {session.source_path}")
    click.echo(f"Created:     {session.created_at}")
    click.echo(f"Updated:     {session.updated_at}")
    click.echo(f"Total:       {session.total_issues}")
    click.echo(f"Resolved:    {session.resolved_count}")
    click.echo(f"Pending:     {session.pending_count}")
    click.echo(f"Progress:    {session.progress_pct:.1f}%")
    click.echo(f"Completed:   {session.completed}")


if __name__ == "__main__":
    main()
