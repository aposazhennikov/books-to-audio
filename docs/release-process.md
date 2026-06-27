# Release Process

Books to Audio releases are cut from a git tag and must pass the automated
readiness checks plus the required human listen-through.

## Version Rules

Use semantic versions: `MAJOR.MINOR.PATCH`.

Before tagging, the same version must be present in:

- `src/book_normalizer/__init__.py` as `book_normalizer.__version__`
- `pyproject.toml` as `project.version`
- the release tag, with or without a leading `v`

Example tag:

```powershell
git tag v0.1.0
```

## Final Acceptance Gate

The release gate is intentionally stricter than normal CI. It runs
`scripts/final_readiness_check.py` and requires:

- all automated readiness checks to pass
- `output/manual_listening_verdict.json` to exist
- the manual verdict to be `pass`

Generate or refresh the human verdict only after listening to the required
post-filter smoke sample:

```powershell
python scripts\prepare_listening_review.py --open
python scripts\record_listening_verdict.py `
  --verdict pass `
  --notes "Accepted post-filter narrator smoke sample." `
  --refresh-readiness
```

## Build Release Artifacts

Run the release builder from the tagged commit:

```powershell
python scripts\release_build.py --tag v0.1.0
```

This command fails if versions do not match or if the human listen-through gate
has not passed. On success it writes:

- `dist/release/book_normalizer-<version>-py3-none-any.whl`
- `dist/release/book_normalizer-<version>.tar.gz`
- `output/final_readiness_report.json`

## Windows Desktop Bundle

Build the portable desktop package on Windows after the release gate passes:

```powershell
python -m pip install -e ".[desktop,desktop-build]"
python scripts\build_windows_desktop.py
```

The bundle is written to `dist/windows/BooksToAudio/` and zipped as
`dist/windows/BooksToAudio.zip`. It contains:

- `BooksToAudio.exe` for the GUI
- `NormalizeBook.exe` for CLI workflows
- `Books to Audio.bat`
- `Normalize Book CLI.bat`
- `Create Desktop Shortcut.ps1`
- local-only `models/`, `data/`, and `output/` folders

Keep models, private books, generated audio, and runtime state out of git.
