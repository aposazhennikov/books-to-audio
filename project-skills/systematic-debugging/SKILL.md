---
name: systematic-debugging
description: Use for any bug, test failure, regression, build failure, or unexpected behavior before proposing fixes. Focuses Codex on root cause, evidence, and minimal tested changes.
---

# Systematic Debugging

Adapted for Codex from Obra Superpowers `systematic-debugging`.

## When To Use

Use this skill when:

- A test, lint, build, install, CLI, GUI, or pipeline step fails.
- Behavior is surprising or inconsistent.
- A previous fix did not work.
- The failure crosses boundaries such as GUI -> worker -> pipeline -> files.

## Process

1. Reproduce the issue or identify the exact command, input, screen, or state that shows it.
2. Read the full error, traceback, log, UI state, and exit code. Do not skim.
3. Check recent changes and nearby working examples in the codebase.
4. Trace the data or state flow back to the first wrong value or missing transition.
5. State one concrete hypothesis before changing code.
6. Make the smallest change that tests or fixes that hypothesis.
7. Add or update a regression test when practical.
8. Run the narrowest relevant verification, then broaden if shared behavior changed.

## Red Flags

- Guessing a fix before knowing where the bad state originates.
- Treating log text or UI labels as proof instead of structured state.
- Applying several fixes at once.
- Fixing symptoms while leaving the source untouched.
- Trying a fourth fix after three failed attempts without questioning the design.

## Expected Output

When reporting back, include:

- Root cause or best current hypothesis.
- Evidence used to identify it.
- Files changed.
- Verification command and result.
- Any remaining uncertainty.
