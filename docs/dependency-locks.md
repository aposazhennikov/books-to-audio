# Dependency Locks

Production installs should use lock files rather than the version ranges in
`pyproject.toml`.

- `requirements.lock`: core CPU-only normalization and manifest tooling.
- `requirements-cpu.lock`: core plus OCR/audio helpers for CPU hosts.
- `requirements-desktop.lock`: CPU profile plus PyQt GUI.
- `requirements-asr.lock`: ASR QA profile.
- `requirements-tts-cuda.lock`: TTS/CUDA profile for ComfyUI/Qwen synthesis.

Upgrade policy:

1. Update `pyproject.toml` ranges only when the supported compatibility window changes.
2. Update the relevant `requirements*.lock` file in the same change.
3. Validate with `python -m ruff check .`, `python -m pytest`, and for runtime changes `normalize-book doctor --skip-network`.
