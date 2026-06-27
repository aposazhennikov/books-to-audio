---
name: planning-work
description: Use before multi-step implementation, architecture changes, risky refactors, workflow changes, or changes touching multiple modules.
---

# Planning Work

Adapted for Codex from Obra Superpowers `writing-plans`.

## When To Use

Use this skill before work that:

- Touches multiple modules or layers.
- Changes workflow, pipeline, GUI state, install, CLI, or artifact formats.
- Requires migrations, compatibility decisions, or staged commits.
- Could benefit from tests before implementation.

## Plan Shape

Keep the plan short enough to use. Include:

- Goal: one sentence.
- Scope: what is included and excluded.
- Files or areas likely to change.
- Task slices that each produce a testable result.
- Verification for each slice.
- Commit boundaries for intermediate results.

## Design Constraints

- Prefer existing project patterns.
- Avoid files over 500 lines; when touching a large file, look for a focused helper/service extraction.
- Keep GUI orchestration separate from business workflow logic when practical.
- Preserve portable artifacts and private data boundaries.
- Update all locales for UI text changes.

## During Execution

Revise the plan when facts change. Do not keep following a stale plan after the codebase contradicts it.
