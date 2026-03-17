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
from book_normalizer.loaders.pdf_loader import (
    PdfLoader,
    extract_pdf_with_ocr_mode,
    select_pdf_text_for_mode,
    write_pdf_compare_report,
)
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
    default=OcrMode.AUTO.value,
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
        is_pdf = input_path.suffix.lower() == ".pdf"
        if is_pdf:
            compare = extract_pdf_with_ocr_mode(input_path, config.ocr_mode)
            chosen_variant, ocr_stats = select_pdf_text_for_mode(compare, config.ocr_mode)

            from book_normalizer.models.book import Book as BookModel, Chapter, Metadata, Paragraph
            from book_normalizer.loaders.pdf_loader import PdfLoader

            # Split text into paragraphs (from_raw_text creates 1 paragraph
            # from the entire text, which breaks chapter detection).
            paragraphs = PdfLoader._split_paragraphs(chosen_variant.text)
            chapter = Chapter(title="Full Text", index=0, paragraphs=paragraphs)
            metadata = Metadata(source_path=str(input_path), source_format="pdf")
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
            compare = extract_pdf_with_ocr_mode(input_path, config.ocr_mode)
            chosen_variant, ocr_stats = select_pdf_text_for_mode(compare, config.ocr_mode)
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

    # Emit basic chapter sanity report for downstream TTS inspection.
    _write_chapter_sanity_report(book, output_dir)

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


def _write_chapter_sanity_report(book: object, output_dir: Path) -> None:
    """Write a simple chapter sanity report for TTS-oriented inspection."""
    from book_normalizer.models.book import Book

    if not isinstance(book, Book):
        return

    total_chapters = len(book.chapters)
    total_paragraphs = sum(len(ch.paragraphs) for ch in book.chapters)

    tiny_threshold = 3
    tiny_counts = [len(ch.paragraphs) for ch in book.chapters if len(ch.paragraphs) <= tiny_threshold]
    tiny_ratio = (len(tiny_counts) / total_chapters) if total_chapters else 0.0

    max_paras = max((len(ch.paragraphs) for ch in book.chapters), default=0)
    avg_paras = (total_paragraphs / total_chapters) if total_chapters else 0.0

    suspicious = False
    reasons: list[str] = []

    if total_chapters > 50:
        suspicious = True
        reasons.append("too_many_chapters")
    if tiny_ratio > 0.7 and total_chapters > 5:
        suspicious = True
        reasons.append("too_many_tiny_chapters")
    if avg_paras > 0 and max_paras > 5 * avg_paras and total_chapters > 3:
        suspicious = True
        reasons.append("very_uneven_distribution")

    lines: list[str] = []
    lines.append(f"total_chapters={total_chapters}")
    lines.append(f"total_paragraphs={total_paragraphs}")
    lines.append(f"avg_paragraphs_per_chapter={avg_paras:.2f}")
    lines.append(f"max_paragraphs_in_chapter={max_paras}")
    lines.append(f"tiny_chapters_ratio={tiny_ratio:.2f}")
    lines.append(f"suspicious={'yes' if suspicious else 'no'}")
    if reasons:
        lines.append("reasons=" + ",".join(reasons))

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "chapter_sanity_report.txt"
    report_path.write_text("\n".join(lines), encoding="utf-8")

    if suspicious:
        logger.warning("Chapter sanity check flagged book as suspicious: %s", ", ".join(reasons))


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


def _parse_chapter_range(value: str) -> tuple[int, int] | None:
    """Parse a chapter range string like '1-5' into (start, end) tuple."""
    if not value:
        return None
    parts = value.split("-")
    if len(parts) == 2:
        return int(parts[0]), int(parts[1])
    if len(parts) == 1:
        n = int(parts[0])
        return n, n
    raise click.BadParameter(f"Invalid chapter range: {value}")


@main.command(name="synthesize")
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option("--out", "-o", type=click.Path(path_type=Path), default=Path("output"), help="Output directory.")
@click.option(
    "--speaker-mode",
    type=click.Choice(["heuristic", "llm", "manual"]),
    default="heuristic",
    show_default=True,
    help="Speaker attribution strategy.",
)
@click.option(
    "--voice-config",
    "voice_config_path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to voice_config.json with voice profiles.",
)
@click.option("--gpu-device", default="cuda:0", show_default=True, help="GPU device for TTS inference.")
@click.option("--resume", is_flag=True, default=False, help="Resume from last checkpoint.")
@click.option("--chapter-range", default="", help="Chapter range to synthesize, e.g. '1-5'.")
@click.option(
    "--format",
    "audio_format",
    type=click.Choice(["wav", "mp3", "both"]),
    default="wav",
    show_default=True,
    help="Output audio format.",
)
@click.option("--max-chunk-chars", type=int, default=900, show_default=True, help="Max characters per TTS chunk.")
@click.option("--pause-phrase-ms", type=int, default=300, show_default=True, help="Pause between phrases (ms).")
@click.option("--pause-speaker-ms", type=int, default=1500, show_default=True, help="Pause on speaker change (ms).")
@click.option("--pause-chapter-ms", type=int, default=3000, show_default=True, help="Pause between chapters (ms).")
@click.option("--skip-assembly", is_flag=True, default=False, help="Only generate chunks, skip assembly.")
@click.option("--llm-endpoint", default="", help="API endpoint for LLM speaker attribution.")
@click.option("--llm-model", default="qwen3:8b", show_default=True, help="LLM model name for speaker attribution.")
@click.option("--skip-stress", is_flag=True, default=False, help="Skip stress annotation.")
@click.option(
    "--ocr-mode",
    type=click.Choice([m.value for m in OcrMode]),
    default=OcrMode.AUTO.value,
    show_default=True,
    help="OCR execution mode for PDF files.",
)
@click.option("--verbose", "-v", is_flag=True, default=False, help="Verbose logging output.")
def synthesize_command(
    input_path: Path,
    out: Path,
    speaker_mode: str,
    voice_config_path: Path | None,
    gpu_device: str,
    resume: bool,
    chapter_range: str,
    audio_format: str,
    max_chunk_chars: int,
    pause_phrase_ms: int,
    pause_speaker_ms: int,
    pause_chapter_ms: int,
    skip_assembly: bool,
    llm_endpoint: str,
    llm_model: str,
    skip_stress: bool,
    ocr_mode: str,
    verbose: bool,
) -> None:
    """Synthesize an audiobook from a book file using Qwen3-TTS."""
    setup_logging(verbose=verbose)

    click.echo(f"Loading: {input_path}")

    try:
        is_pdf = input_path.suffix.lower() == ".pdf"
        if is_pdf:
            ocr = OcrMode(ocr_mode)
            compare = extract_pdf_with_ocr_mode(input_path, ocr)
            chosen_variant, ocr_stats = select_pdf_text_for_mode(compare, ocr)

            from book_normalizer.models.book import Book as BookModel, Chapter, Metadata, Paragraph

            paragraphs = PdfLoader._split_paragraphs(chosen_variant.text)
            chapter = Chapter(title="Full Text", index=0, paragraphs=paragraphs)
            metadata = Metadata(source_path=str(input_path), source_format="pdf")
            book = BookModel(metadata=metadata, chapters=[chapter])
            book.add_audit(
                "loading", "pdf_loader_ocr_mode",
                f"mode={ocr.value}, selected={ocr_stats.get('selected')}",
            )
        else:
            factory = LoaderFactory.default()
            book = factory.load(input_path)
    except (FileNotFoundError, ValueError, ImportError) as exc:
        click.echo(f"Error loading file: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Loaded: {len(book.chapters)} chapter(s)")

    # --- Normalization & chapter detection ---
    pipeline = NormalizationPipeline()
    book = pipeline.normalize_book(book)

    detector = ChapterDetector()
    book = detector.detect_and_split(book)
    pipeline.normalize_book(book)
    click.echo(f"Chapters detected: {len(book.chapters)}")

    # --- Stress annotation ---
    if not skip_stress:
        from book_normalizer.memory.stress_store import StressStore
        from book_normalizer.stress.annotator import StressAnnotator
        from book_normalizer.stress.dictionary import StressDictionary

        config = AppConfig()
        stress_store = StressStore(config.stress_dict_path)
        stress_dict = StressDictionary(store=stress_store)
        annotator = StressAnnotator(stress_dict)
        ann_result = annotator.annotate_book(book)
        click.echo(
            f"Stress: {ann_result.total_words} words, "
            f"{ann_result.known_words} known, "
            f"{ann_result.unknown_words} unknown."
        )

    # --- Dialogue detection ---
    from book_normalizer.dialogue.detector import DialogueDetector

    dialogue_detector = DialogueDetector()
    annotated_chapters = dialogue_detector.detect_book(book)
    total_dialogue = sum(ch.dialogue_count for ch in annotated_chapters)
    click.echo(f"Dialogue detected: {total_dialogue} dialogue line(s)")

    # --- Speaker attribution ---
    from book_normalizer.dialogue.attribution import SpeakerMode, create_attributor

    attr_mode = SpeakerMode(speaker_mode)
    output_dir = _build_output_dir(input_path, out).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    cache_dir = output_dir / "speaker_cache"
    session_path = output_dir / "manual_speaker_session.json"

    attributor = create_attributor(
        attr_mode,
        llm_endpoint=llm_endpoint,
        llm_model=llm_model,
        cache_dir=cache_dir,
        session_path=session_path,
    )
    attr_result = attributor.attribute(annotated_chapters)
    click.echo(
        f"Attribution ({attr_result.strategy}): "
        f"male={attr_result.male_lines}, "
        f"female={attr_result.female_lines}, "
        f"narrator={attr_result.narrator_lines}"
    )

    # --- Voice-annotated chunking ---
    from book_normalizer.chunking.voice_splitter import chunk_annotated_book

    chunked = chunk_annotated_book(annotated_chapters, max_chunk_chars=max_chunk_chars)
    total_chunks = sum(len(v) for v in chunked.values())
    click.echo(f"Chunks: {total_chunks} voice-annotated chunks across {len(chunked)} chapter(s)")

    # --- Voice config ---
    from book_normalizer.tts.voice_config import VoiceConfig

    if voice_config_path:
        voice_cfg = VoiceConfig.from_json(voice_config_path)
    else:
        voice_cfg = VoiceConfig.default_clone_config()
        click.echo("No --voice-config provided. Using default clone config template.")
        template_path = output_dir / "voice_config_template.json"
        voice_cfg.to_json(template_path)
        click.echo(f"Template saved to: {template_path}")
        click.echo("Fill in ref_audio and ref_text for each voice, then re-run with --voice-config.")
        sys.exit(0)

    errors = voice_cfg.validate_all()
    if errors:
        for err in errors:
            click.echo(f"Voice config error: {err}", err=True)
        sys.exit(1)

    # --- TTS synthesis ---
    from book_normalizer.tts.voice_manager import VoiceManager

    click.echo(f"Initializing TTS on {gpu_device}...")
    vm = VoiceManager(voice_cfg, device=gpu_device)
    vm.initialize()

    from book_normalizer.tts.synthesizer import TTSSynthesizer

    synthesizer = TTSSynthesizer(vm, output_dir, resume=resume)

    ch_range = _parse_chapter_range(chapter_range) if chapter_range else None
    synthesizer.synthesize_chapters(chunked, chapter_range=ch_range)
    click.echo("TTS synthesis complete.")

    # --- Audio assembly ---
    if not skip_assembly:
        from book_normalizer.tts.assembler import AudioAssembler

        assembler = AudioAssembler(
            output_dir,
            pause_phrase_ms=pause_phrase_ms,
            pause_speaker_ms=pause_speaker_ms,
            pause_chapter_ms=pause_chapter_ms,
        )
        export_mp3 = audio_format in ("mp3", "both")
        result_files = assembler.assemble(export_mp3=export_mp3)
        for desc, path in result_files.items():
            click.echo(f"  {desc}: {path}")

    click.echo("Done.")


@main.command(name="init-voices")
@click.option("--out", "-o", type=click.Path(path_type=Path), default=Path("voices"), help="Output directory.")
@click.option(
    "--preset",
    type=click.Choice(["clone", "custom"]),
    default="clone",
    show_default=True,
    help="Preset type: 'clone' for reference audio, 'custom' for built-in speakers.",
)
def init_voices_command(out: Path, preset: str) -> None:
    """Generate a voice_config.json template."""
    from book_normalizer.tts.voice_config import VoiceConfig

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)

    if preset == "custom":
        cfg = VoiceConfig.default_custom_voice_config()
    else:
        cfg = VoiceConfig.default_clone_config()

    config_path = out / "voice_config.json"
    cfg.to_json(config_path)
    click.echo(f"Voice config template created: {config_path}")

    if preset == "clone":
        click.echo("Next steps:")
        click.echo("  1. Place 3-10 sec WAV reference files in the voices/ directory.")
        click.echo("  2. Edit voice_config.json: set ref_audio and ref_text for each voice.")
        click.echo("  3. Run: normalize-book synthesize <book> --voice-config voices/voice_config.json")


if __name__ == "__main__":
    main()
