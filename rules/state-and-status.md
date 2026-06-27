# State and Status

- Do not trust visible success unless there is structured state behind it.
- Treat "file exists", "button enabled", "message looks good", or "log text says done" as insufficient proof by itself.
- Prefer machine-readable statuses such as `passed`, `warning`, `failed`, `review_required`, `missing_audio`, and `skipped`.
- If business logic depends on parsing UI labels, human log text, or translated messages, treat that as a design problem to fix.
- Tests should assert structured state or artifacts instead of only asserting display text.
