# AGENTS.md

Guidance for coding agents and maintainers working in this repository.

## Repository Hygiene

Only source code, tests, documentation, workflow templates, and small static assets should be committed.

Do not commit:

- `.venv/`, `.venv-windows/`, `.venv-wsl/`, `venv/`, `env/`
- `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.coverage`
- `books/`
- `output/`
- `data/`
- `ComfyUI/`
- `ollama-models/`
- `hf-cache/`
- `books-to-audio-models/`
- `.env`, `.env.*`
- temporary editor, OS, log, cache, and generated files

`books/`, `output/`, and `data/` are intentionally local-only folders. They can contain private books, generated audio, manifests, runtime paths, user memory, and other machine-specific state.

Large model files must stay outside git. Configure model locations through `install.py`, `.env`, or environment variables such as `BOOKS_TO_AUDIO_MODELS_DIR`, `COMFYUI_MODELS_DIR`, `BOOKS_TO_AUDIO_OLLAMA_MODELS_DIR`, `OLLAMA_MODELS`, and `HF_HOME`.

## Before Editing

- Check `git status --short` before changing files.
- Do not revert unrelated user changes.
- Keep changes focused on the requested task.
- Prefer existing project patterns over introducing new structure.

## Validation

For code changes, run the narrowest useful checks first:

```bash
python -m ruff check .
python -m pytest
```

For runtime or installation changes, also run:

```bash
normalize-book doctor --skip-network
```
