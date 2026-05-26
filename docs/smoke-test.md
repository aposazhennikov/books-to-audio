# Smoke Test Checklist

Fast local check:

```powershell
pytest tests\test_end_to_end_smoke.py tests\test_comfyui_client.py tests\test_manifest_assembly.py
ruff check .
```

Manual pipeline check:

```powershell
normalize-book doctor
normalize-book pipeline books\sample.txt --out output --synthesize --assemble `
  --workflow comfyui_workflows\qwen3_tts_template.json
normalize-book audio-qa output\sample_txt\chunks_manifest_v2.json
```

Live TTS backend check:

```powershell
python scripts\live_tts_smoke.py `
  --comfyui-url http://127.0.0.1:8188 `
  --workflow comfyui_workflows\qwen3_tts_template.json `
  --out-dir output\live_tts_smoke
```

Exit codes:

- `0`: smoke synthesized, QA passed, and one chapter WAV was assembled.
- `1`: ComfyUI responded, but synthesis/QA/assembly needs review.
- `2`: ComfyUI is not reachable; start ComfyUI and rerun.

Manifest-only real-book check:

```powershell
python scripts\live_tts_smoke.py `
  --book-path books\monosov\monosov1.txt `
  --out-dir output\live_tts_real_book_manifest_only `
  --max-smoke-chunks 3 `
  --manifest-only
```

This writes `chunks_manifest_v2.json` and `live_tts_smoke_report.json` without
contacting ComfyUI. Use it to catch front matter, library URLs, or publisher
boilerplate before spending GPU time on synthesis.

Expected artifacts:

- `001_chapter_01.txt`
- `chunks_manifest_v2.json`
- `audio_chunks/chapter_001/chunk_*.wav`
- `chapter_001.wav`
- `output/live_tts_smoke/live_tts_smoke_report.json`

Post-run artifact audit:

```powershell
python scripts\audit_tts_smoke.py output\live_tts_smoke `
  --write-report output\live_tts_smoke\audit_report.json
```

The audit checks the live smoke report, manifest chunk count, front-matter
terms, WAV format, duration, and non-silent audio. It does not load ComfyUI,
Ollama, or any model.

Final automated readiness report:

```powershell
python scripts\final_readiness_check.py `
  --write-report output\final_readiness_report.json
```

This aggregates the automated gates and keeps the remaining human listening
step explicit instead of marking the project complete without ears on the
post-filter audio sample.

Manual listening checklist:

```powershell
python scripts\create_listening_checklist.py `
  --smoke-dir output\live_tts_real_book_smoke_after_filter `
  --out output\manual_listening_checklist.md
```

Use the generated checklist while listening to the post-filter WAV. It records
the exact sample, expected manifest text, objective audio checks, and the final
PASS/REVIEW/FAIL decision.
