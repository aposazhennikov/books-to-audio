# Code Organization

- Avoid creating or growing source code files beyond 500 lines.
- When a file approaches 500 lines, split cohesive logic into smaller modules, helpers, or components.
- Keep splits aligned with existing project structure and ownership boundaries.
- Do not split files mechanically if it would make the code harder to follow; prefer cohesive, maintainable boundaries.
- Large modules are logic risk, not just style risk.
- When changing workflow logic in a large module, look for a small clean service, helper, or adapter that can carry the behavior safely.
- Keep UI orchestration, business decisions, worker startup, and status handling separated when practical.
