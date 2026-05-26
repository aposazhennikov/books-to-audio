# Quality Status

Last updated: 2026-05-26.

This file records local verification evidence for the multilingual LLM/OCR
quality pass. Full generated reports stay under `output/quality_reports/` and
are intentionally not committed.

## Verified Locally

- Ollama models are present:
  - `hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M`
  - `hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M`
- Production 8B synthetic smoke passed for `ru`, `en`, `zh`, `kk`, `uz`.
  - Report: `output/quality_reports/quality_report_20260526T033844Z.*`
  - Result: 5/5 cases `ok`; normalization, smart voice segments, and chunks
    all preserved text.
- Lightweight 4B synthetic smoke passed for `ru`, `en`, `zh`, `kk`, `uz`.
  - Report: `output/quality_reports/quality_report_20260526T033607Z.*`
  - Result: 5/5 cases `ok`; model unloaded after the run.
- Fresh WSL lightweight 4B synthetic smoke passed for `ru`, `en`, `zh`, `kk`,
  `uz`.
  - Report: `output/quality_reports/quality_report_20260526T043343Z.*`
  - Result: 5/5 cases `ok`; normalization, smart voice segments, and chunks
    preserved text.
  - Post-run resource check: `ollama ps` was empty, so no model remained
    resident in memory after the benchmark.
- Production 8B real public-corpus smoke passed for `en`, `zh`, `kk`, `uz`.
  - Report: `output/quality_reports/quality_report_20260526T034345Z.*`
  - Sources:
    - `output/public_quality_corpus_current/english/pride_and_prejudice.txt`
    - `output/public_quality_corpus_current/chinese/gui_tian_lu.txt`
    - `output/public_quality_corpus_current/kazakh/abylai_khan.txt`
    - `output/public_quality_corpus_current/uzbek/xalq.txt`
  - Result: 4/4 cases `ok`; segment and chunk text preservation passed.
- Production 8B local Russian book smoke passed.
  - Report: `output/quality_reports/quality_report_20260526T034458Z.*`
  - Source: `books/monosov/monosov1.txt`
  - Result: `ok`; normalized text, segments, and chunks preserved text.
- Real-format extraction and chunking smoke passed without GPU.
  - Report: `output/quality_reports/quality_report_20260526T034602Z.*`
  - Sources: `books/monosov/monosov1.epub`, `.fb2`, `.pdf`, `.txt`
  - Result: 4/4 cases `offline_checked`; text preserved through chunks.
- Local audiobook E2E smoke passed without external TTS services.
  - Test: `tests/test_end_to_end_smoke.py::test_role_chunks_voice_assignment_audio_qa_and_assembly_skip_deleted_text`
  - Covered path: role inventory -> active chunks -> v2 manifest -> voice
    assignment -> synthesized WAV placeholders -> audio QA -> chapter assembly.
  - Deleted/excluded chunks with stale audio are skipped by synthesis, QA, and
    chapter assembly, so removed publisher boilerplate cannot leak into the
    final chapter WAV.
- Live TTS smoke passed against the local Windows ComfyUI/Qwen3-TTS backend.
  - Command: `python scripts/live_tts_smoke.py --comfyui-url http://127.0.0.1:8188 --workflow comfyui_workflows/qwen3_tts_template.json`
  - Output: `output/live_tts_smoke/live_tts_smoke_report.json`
  - Result: `ok`; 2/2 chunks synthesized, audio QA passed, and
    `output/live_tts_smoke/chapter_001.wav` was assembled.
  - Container fix verified: ComfyUI `SaveAudio` returns FLAC bytes, so the
    client converts FLAC downloads to real PCM WAV before QA/assembly. The live
    chunk files and assembled chapter now start with a RIFF/WAVE header.
  - Post-run resource check: ComfyUI reported about 7.3 GB free VRAM, and
    `ollama ps` was empty.
- Local image-only OCR smoke passed for `ru`, `en`, `zh`, `kk`, `uz`.
  - Report: `output/quality_reports/ocr_multilingual_smoke_20260526T025818Z.json`
  - Runtime: local WSL Tesseract with `data/tessdata`.

## Current External Gap

- Native Windows Tesseract is not installed system-wide, but the GUI now has a
  verified project-local fallback.
  - `winget list -e --id UB-Mannheim.TesseractOCR` found no installed package.
  - Noninteractive install attempts reached the UB-Mannheim package installer,
    but Windows returned `0x800704c7` (`operation canceled by the user`). This
    usually means the UAC/installer confirmation was dismissed or unavailable
    to the background WSL session.
  - Latest attempted command:
    `install.bat --yes --install-system-tools --download-tessdata --venv .venv-windows`.
  - The UB-Mannheim installer was downloaded from winget metadata, SHA256 was
    verified, and the payload was extracted without admin rights to
    `tools/Tesseract-OCR/`.
  - Windows doctor now reports Tesseract as `ok` through
    `tools/Tesseract-OCR/tesseract.exe`, with OCR languages:
    `eng`, `rus`, `chi_sim`, `kaz`, `uzb`.
  - The GUI handles this path correctly: stale WSL runtime paths are ignored on
    Windows, standard `C:\Program Files\Tesseract-OCR\tesseract.exe` is probed
    even when `PATH` is stale, and the project-local portable binary is used
    when the system installer is unavailable.
- WSL Ollama is installed and has the required local LLM models.
  - `ollama list` includes `hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M` and
    `hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M`.
  - `python -m book_normalizer.cli doctor --json-output` reports the native
    Ollama API as reachable when the WSL Ollama server is running.
- ComfyUI/Qwen3-TTS model folders are present under
  `/mnt/d/ComfyUI-external/models`.
  - The app now falls back to this installed model root when the installer
    runtime config points at an empty stale directory.
- ComfyUI portable was found at `/mnt/d/ComfyUI` and can be started from WSL
  with `python scripts/start_comfyui.py --wait-seconds 300`.

## Remaining Before Final Sign-Off

- Optional only: install native Windows Tesseract system-wide after an
  interactive UAC approval. The GUI no longer depends on this because the
  project-local fallback is verified.
- Listen to the generated live smoke chapter and/or one real-book short
  chapter for subjective voice-quality sign-off.
- Keep `ollama ps` empty after benchmark runs so only one model is resident at a
  time on an 8 GB VRAM / 16 GB RAM machine.
