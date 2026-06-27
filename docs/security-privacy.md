# Security And Privacy

Books to Audio is local-first. Treat book files, generated audio, manifests, logs, memory, and runtime paths as private operator data.

## Private Local Folders

These folders are intentionally local-only and must not be committed:

- `books/`: source books, covers, and private references.
- `output/`: generated chunks, audio, manifests, QA reports, and final packages.
- `data/`: runtime paths, local memory, tessdata, review state, and machine-specific settings.

The repository `.gitignore` excludes these folders. Keep large model files and caches outside git as well, including `ComfyUI/`, `ollama-models/`, `hf-cache/`, and `books-to-audio-models/`.

## Secret Scan And Pre-Commit

Run the built-in secret scan before pushing:

```bash
python scripts/secret_scan.py
```

To install the local pre-commit hook:

```bash
pip install pre-commit
pre-commit install
```

The hook uses `.pre-commit-config.yaml` and calls `python scripts/secret_scan.py`. It ignores private local folders and binary/audio assets, then scans source, tests, docs, scripts, and workflow files for common token and private-key patterns.

If a finding is a documented fake value, add `# pragma: allowlist secret` on that line.

## Redacted Support Bundle

When asking for help, send a redacted support bundle instead of the raw run folder:

```bash
normalize-book support-bundle output/mybook_pdf
```

The bundle:

- includes JSON reports, manifests, and text logs useful for debugging.
- replaces book text fields with `<REDACTED_BOOK_TEXT>`.
- replaces local paths under private folders with `<PRIVATE_PATH>`.
- does not include source books, generated audio, model files, `.env`, or caches.

Before sharing, open the zip and spot-check `support_manifest.json` plus one report. If a private book quote or machine path remains, do not send it; file a bug and attach a minimal synthetic reproduction instead.
