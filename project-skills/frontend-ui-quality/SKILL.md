---
name: frontend-ui-quality
description: Use for GUI, layout, copy, localization, screenshots, visual QA, accessibility, and user-facing state changes.
---

# Frontend UI Quality

Adapted for Codex from Anthropic `frontend-design` and local project UI rules.

## Principles

- UI must be honest: visible controls should affect the current scenario.
- User-facing text must match what the action actually does.
- Localization is product behavior, not decoration.
- Visual success requires inspection, not just code that compiles.

## Before Editing UI

Check:

- Existing UI patterns and component structure.
- Supported locales and catalog shape.
- Whether the visible control is wired to current backend/workflow logic.
- Loading, disabled, empty, warning, error, and review-required states.

## Implementation Requirements

- Update every supported locale when changing user-facing UI text.
- Keep placeholders and formatting variables consistent across locales.
- Check touched UI and locale files for mojibake, replacement characters, or mixed encodings.
- Do not expose controls for future, legacy, or experimental behavior unless disabled or clearly labeled.
- Prefer structured state behind buttons, badges, progress, readiness, and warnings.

## Verification

When practical:

- Use Playwright MCP or the best available screenshot/manual path for main affected screens.
- Confirm text is not clipped or overlapping.
- Confirm buttons and controls do not overlap.
- Verify disabled, loading, error, warning, and success states affected by the change.
- State if visual verification could not be run.
