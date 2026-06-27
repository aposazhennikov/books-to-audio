# Production Readiness

- Do not treat "the process reached the end" as proof that the audiobook is production-ready.
- Gate final packaging on explicit readiness checks: synthesis completed, expected files exist, QA passed, and relevant ASR, artifact, or perceptual checks have clear outcomes.
- Warnings, skipped checks, missing audio, and review-required states must remain visible until accepted or resolved.
- An automated pipeline must not silently convert warnings or review-required states into ready-for-packaging success.
- Packaging decisions should use structured readiness state, not log text or UI labels.
