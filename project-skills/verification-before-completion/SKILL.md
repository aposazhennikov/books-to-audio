---
name: verification-before-completion
description: Use before claiming work is complete, fixed, passing, ready, committed, or production-ready. Requires fresh evidence instead of visible-success assumptions.
---

# Verification Before Completion

Adapted for Codex from Obra Superpowers `verification-before-completion`.

## Rule

Do not claim success without fresh verification evidence from this turn.

## Checklist

Before saying work is done:

- Identify what command, screenshot, structured state, or file diff proves the claim.
- Run or inspect that evidence freshly.
- Read the full output, exit code, and any warnings.
- Check that the evidence proves the actual claim, not a weaker nearby claim.
- If verification was not possible, state exactly why and what risk remains.

## Audiobook Readiness

For production/audio pipeline work, "the command finished" is not enough. Check structured readiness when relevant:

- Synthesis completed.
- Expected audio files exist.
- QA checks passed or produced explicit warnings.
- Review-required states are visible and accepted by the user.
- Packaging did not silently ignore warnings, skipped checks, or missing audio.

## Reporting

Use direct evidence:

- Good: "Ran `python -m pytest tests/test_pdf_loader.py`; 12 passed."
- Good: "Did not run GUI verification because no display/browser MCP is available in this session."
- Bad: "Should work now."
- Bad: "Looks fine from the code."
