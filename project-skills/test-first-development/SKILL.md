---
name: test-first-development
description: Use for behavior changes, bug fixes, regressions, refactors with observable behavior, and workflow changes where a focused test can prove the expected outcome before implementation.
---

# Test-First Development

Adapted for Codex from Obra Superpowers `test-driven-development`.

## When To Use

Use this skill when changing behavior in source code, especially:

- Bug fixes.
- New user-facing or pipeline behavior.
- Manifest, readiness, artifact, or path handling.
- GUI state transitions that can be tested without a full manual session.
- Refactors where existing behavior must be preserved.

## Process

1. Identify the smallest behavior that should change or stay protected.
2. Write or update a focused test before implementation when practical.
3. Run the test and confirm it fails for the expected reason.
4. Implement the smallest code change that should make the test pass.
5. Run the focused test again and confirm it passes.
6. Run broader tests when shared behavior or shared modules changed.
7. Keep the test about real behavior, not only mocks or implementation details.

## Exceptions

It is acceptable to skip test-first flow for:

- Documentation-only changes.
- Small rule or skill text updates.
- Exploratory spikes that will be thrown away.
- Changes where this repository has no realistic test harness yet.

When skipping, say why and choose the narrowest useful verification instead.

## Good Test Targets

- Structured status values, not display strings only.
- Portable paths and manifest relocation.
- Warning, review-required, skipped, and failed states.
- Locale placeholders and user-facing text coverage.
- CLI/install behavior on the affected platform.
