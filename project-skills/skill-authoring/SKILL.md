---
name: skill-authoring
description: Use when creating, modifying, reviewing, or importing project skills. Keeps skills small, Codex-focused, safe, attributed, and relevant to this repository.
---

# Skill Authoring

Adapted for Codex from Anthropic `skill-creator` and Sentry skill vendoring guidance.

## Skill Folder Shape

Each project skill should live at:

```text
project-skills/<skill-name>/SKILL.md
```

Use lowercase kebab-case names. Keep each `SKILL.md` under 500 lines.

## Required Frontmatter

```yaml
---
name: skill-name
description: Use when <clear trigger context>. Explain what the skill helps Codex do and when to read it.
---
```

## Writing Guidance

- Write for Codex, not Claude-specific tooling.
- Keep instructions imperative, concrete, and scoped to this repository.
- Prefer "why this matters" over rigid all-caps rules.
- Put trigger context in the description; put workflow details in the body.
- Avoid broad permissions, hidden state, credential handling, and external-service assumptions.
- Reference Context7 or Playwright MCP only as preferred tools when available, with fallback instructions.

## Importing External Skills

Before importing:

- Read the source skill or README enough to understand its scope.
- Reject skills that are unrelated, service-specific, unsafe, prompt-injection prone, or too broad to audit.
- Adapt useful ideas instead of copying raw instructions wholesale.
- Replace Claude-specific commands, paths, and assumptions with Codex-friendly wording.
- Add attribution and rejection notes to `project-skills/SOURCES.md`.

## Review Checklist

- The skill has a clear trigger.
- It does not duplicate an existing rule or skill.
- It does not require unavailable tools.
- It preserves repository privacy and portability rules.
- It fits in one focused file or points to a small reference.
