# Project Skills Source Audit

This folder contains a small curated set of project skills adapted for Codex and this repository. Do not import external skill repositories wholesale. External skills can contain tool assumptions, outdated commands, product-specific policies, or prompt-injection-like instructions that are not appropriate for this project.

## Included and Adapted

- Obra Superpowers `systematic-debugging`: adapted into `systematic-debugging` for root-cause-first debugging.
  Source: https://github.com/obra/superpowers/tree/main/skills/systematic-debugging
- Obra Superpowers `test-driven-development`: adapted into `test-first-development` for focused red-green behavior changes.
  Source: https://github.com/obra/superpowers/tree/main/skills/test-driven-development
- Obra Superpowers `verification-before-completion`: adapted into `verification-before-completion` for evidence-first completion claims.
  Source: https://github.com/obra/superpowers/tree/main/skills/verification-before-completion
- Obra Superpowers `receiving-code-review`: adapted into `code-review-reception` for technical review handling.
  Source: https://github.com/obra/superpowers/tree/main/skills/receiving-code-review
- Obra Superpowers `writing-plans`: adapted into `planning-work` for multi-step implementation planning.
  Source: https://github.com/obra/superpowers/tree/main/skills/writing-plans
- Anthropic `frontend-design`: adapted into `frontend-ui-quality` for UI quality, copy, screenshots, and localization checks.
  Source: https://github.com/anthropics/skills/tree/main/skills/frontend-design
- Anthropic `skill-creator`: adapted into `skill-authoring` for creating maintainable Codex-facing skills.
  Source: https://github.com/anthropics/skills/tree/main/skills/skill-creator
- Sentry skills README guidance: used only for vendoring and attribution practices, not as runtime instructions.
  Source: https://github.com/getsentry/skills

## Reviewed but Not Included

- `openai/skills`: not vendored because the repository itself marks the catalog as deprecated and points to newer Codex plugin guidance.
- `vercel-labs/agent-skills`: mostly React, Next.js, Vercel, and web-specific guidance; not directly useful for this Python desktop/audio pipeline.
- `supabase/agent-skills`: Supabase-specific; not relevant unless this project adds Supabase.
- `google-labs-code/skills`: not included because no project-specific need was identified.
- `getsentry/sentry-skills`: valuable ideas, but many skills are Sentry-specific or assume Sentry workflows/tools.
- `firecrawl/firecrawl-skills`: web scraping/research oriented; unnecessary and potentially risky for private book content.
- `BehiSecc/awesome-claude-skills`, `ComposioHQ/awesome-claude-skills`, and `yusufkaraaslan/skill-seekers`: indexes/lists rather than reviewed project-ready skills.
- Marketing, blog, content, Typefully, Courier, YouTube, Telegram, Obsidian, and Pinme repositories: outside this project's core workflow and not worth adding by default.
- `aaron-he-zhu/seo-geo-claude-skills`: SEO/GEO and marketing workflow skills; not relevant to the private audiobook normalization pipeline and may encourage unnecessary web/market research.
- `zarazhangrui/frontend-slides`: useful for HTML presentation generation, but not part of this project's recurring code, GUI, or audio workflow. It also includes deployment-oriented paths that are unnecessary here.
- `garrytan/gstack`: broad multi-agent setup with many external tools, coordination flows, and environment assumptions. Too large and risky to vendor into this repository by default.
- `AlariCode/expense-tracker-market`: unrelated expense-tracker/PurpleSchool plugin material.
- `obra/superpowers`: already reviewed; only small, relevant engineering-process skills were adapted.

## Import Policy

- Add only skills that improve recurring work in this repository.
- Prefer short, local, reviewed adaptations over raw external instructions.
- Remove or rewrite instructions that mention Claude-specific tools, external accounts, broad web scraping, unsafe automation, or hidden state.
- Keep each `SKILL.md` under 500 lines and split references if it grows.
- Keep attribution in this file when a skill is adapted from external material.
