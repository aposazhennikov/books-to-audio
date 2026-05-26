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
- Live TTS smoke runner is available for final backend sign-off.
  - Command: `python scripts/live_tts_smoke.py --comfyui-url http://127.0.0.1:8188 --workflow comfyui_workflows/qwen3_tts_template.json`
  - Output: `output/live_tts_smoke/live_tts_smoke_report.json`
  - Current machine state on 2026-05-26: ComfyUI was not reachable at
    `127.0.0.1:8188`, so live synthesis could not be executed in this run.
- Local image-only OCR smoke passed for `ru`, `en`, `zh`, `kk`, `uz`.
  - Report: `output/quality_reports/ocr_multilingual_smoke_20260526T025818Z.json`
  - Runtime: local WSL Tesseract with `data/tessdata`.

## Current External Gap

- Native Windows Tesseract is still not installed.
  - `winget list -e --id UB-Mannheim.TesseractOCR` found no installed package.
  - One noninteractive install attempt reached the package installer but Windows
    returned `0x800704c7` (`operation canceled by the user`), which usually
    means the UAC/installer confirmation was dismissed or unavailable to the
    background WSL session.
  - The GUI now handles this correctly: stale WSL runtime paths are ignored on
    Windows, standard `C:\Program Files\Tesseract-OCR\tesseract.exe` is probed
    even when `PATH` is stale, and the OCR install prompt points to the native
    install script.
- WSL Ollama is installed and has the required local LLM models.
  - `ollama list` includes `hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M` and
    `hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M`.
  - `python -m book_normalizer.cli doctor --json-output` reports the native
    Ollama API as reachable when the WSL Ollama server is running.
- ComfyUI/Qwen3-TTS model folders are present under
  `/mnt/d/ComfyUI-external/models`.
  - The app now falls back to this installed model root when the installer
    runtime config points at an empty stale directory.

## Remaining Before Final Sign-Off

- Confirm native Windows Tesseract after an interactive install/UAC approval.
- Run one full end-to-end audiobook chapter path against a live TTS backend
  (ComfyUI/Qwen CustomVoice), then listen to the previewed chapter.
- Keep `ollama ps` empty after benchmark runs so only one model is resident at a
  time on an 8 GB VRAM / 16 GB RAM machine.
