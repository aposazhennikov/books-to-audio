# AGENTS.md

Guidance for coding agents and maintainers working in this repository.

Repository rules are split into focused markdown files under `rules/` so they are easier to edit and extend.

These rules are mandatory project instructions, not optional references. At the start of work, read the relevant files under `rules/` before editing. If a task changes files, read [Before editing](rules/before-editing.md), [Git workflow](rules/git-workflow.md), and [Validation](rules/validation.md) as the default minimum. If you cannot read a referenced rule file, say so before proceeding.

After completing any requested file change, commit the coherent completed change by default unless the user explicitly says not to commit. Keep the commit scoped to the files for that completed change, and never include unrelated user changes.

If working in a Codex-created git worktree, finish by merging the completed work back into the main repository branch and pushing that unified branch, unless the user explicitly says not to merge or push. Do this only after verification passes and conflicts are resolved.

Project-specific skills live under `project-skills/`. Use them as optional workflow guidance when the task matches a skill description.

## Rule Compliance

At the start of every task, report which `rules/*.md` files and `project-skills/*/SKILL.md` files you read, and briefly state when you will use each one. If no project skill applies, say that explicitly.

While working, provide short progress updates that explain what you are doing, why you are doing it, and what remains. For longer tasks, include a rough time estimate or remaining-step estimate when practical.

Before finishing, report the verification performed, the commit hash if a commit was created, and any rules or skills that could not be applied.

## Rules

- [Repository hygiene](rules/repository-hygiene.md)
- [Before editing](rules/before-editing.md)
- [Git workflow](rules/git-workflow.md)
- [Tooling preferences](rules/tooling-preferences.md)
- [State and status](rules/state-and-status.md)
- [UI truthfulness](rules/ui-truthfulness.md)
- [UI localization](rules/ui-localization.md)
- [Production readiness](rules/production-readiness.md)
- [Portable artifacts](rules/portable-artifacts.md)
- [Automation boundaries](rules/automation-boundaries.md)
- [Testing scope](rules/testing-scope.md)
- [UI verification](rules/ui-verification.md)
- [Data privacy](rules/data-privacy.md)
- [Dependency changes](rules/dependency-changes.md)
- [CLI compatibility](rules/cli-compatibility.md)
- [Error handling](rules/error-handling.md)
- [Code organization](rules/code-organization.md)
- [Fresh verification](rules/fresh-verification.md)
- [Validation](rules/validation.md)

## Project Skills

Before using a project skill, read its `SKILL.md` fully and follow only the parts relevant to the current task. Prefer these local, reviewed skills over fetching external skill instructions at runtime.

- [Systematic debugging](project-skills/systematic-debugging/SKILL.md): use for bugs, test failures, unexpected behavior, and regressions before proposing fixes.
- [Test-first development](project-skills/test-first-development/SKILL.md): use for behavior changes, bug fixes, and regressions where a focused test can prove the change.
- [Verification before completion](project-skills/verification-before-completion/SKILL.md): use before claiming work is done, fixed, passing, committed, or ready.
- [Code review reception](project-skills/code-review-reception/SKILL.md): use when handling review feedback or external suggestions.
- [Planning work](project-skills/planning-work/SKILL.md): use before multi-step code changes or architectural edits.
- [Frontend UI quality](project-skills/frontend-ui-quality/SKILL.md): use for GUI, layout, copy, localization, and visual verification changes.
- [Skill authoring](project-skills/skill-authoring/SKILL.md): use when creating or modifying project skills.

The skill source audit and rejected sources are documented in [project-skills/SOURCES.md](project-skills/SOURCES.md).
