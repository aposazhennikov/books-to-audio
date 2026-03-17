"""Verification and quality-control utilities for normalized books."""

from __future__ import annotations

from pathlib import Path

from book_normalizer.models.book import Book
from book_normalizer.verification.report import (
    VerificationConfig,
    VerificationResult,
    generate_reports,
)


def run_verification(
    before: Book,
    after: Book,
    output_dir: Path,
    sample_size: int = 20,
) -> VerificationResult:
    """
    Run verification for a book before/after normalization and write reports.
    """
    config = VerificationConfig(sample_size=sample_size)
    return generate_reports(before=before, after=after, output_dir=output_dir, config=config)

