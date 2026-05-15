# Architecture

Books to Audio is organized as a four-stage pipeline:

1. `book_normalizer.cli process` loads TXT/PDF/EPUB/FB2/DOCX, normalizes Russian text, detects chapters, and writes chapter TXT files.
2. Chunking creates `chunks_manifest_v2.json`, grouped by chapter with one record per TTS chunk.
3. ComfyUI synthesis reads the v2 manifest, writes chunk WAV files, and updates each chunk with `synthesized`, `failed`, `error`, and `audio_file`.
4. Manifest assembly reads `audio_file` values in manifest order and writes `chapter_NNN.wav`.

The recommended path is v2 manifest + ComfyUI. The legacy WSL `tts_runner.py` path remains available for v1 manifests.

Key modules:

- `book_normalizer.chunking.manifest`: v2 manifest construction and flattening.
- `book_normalizer.comfyui.synthesis`: ComfyUI synthesis loop with resume and failed-only retry.
- `book_normalizer.tts.manifest_assembly`: manifest-ordered chapter assembly.
- `book_normalizer.tts.audio_qa`: audio/manifest consistency checks.
- `book_normalizer.diagnostics.doctor`: local preflight checks.
