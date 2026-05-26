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

## Remaining Before Final Sign-Off

- Confirm native Windows Tesseract after an interactive install/UAC approval.
- Run one full end-to-end audiobook chapter path:
  normalized book -> role inventory -> editable chunks -> voice assignment ->
  synthesis -> chapter assembly -> preview/audio QA.
- Keep `ollama ps` empty after benchmark runs so only one model is resident at a
  time on an 8 GB VRAM / 16 GB RAM machine.
