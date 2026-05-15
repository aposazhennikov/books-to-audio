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

Expected artifacts:

- `001_chapter_01.txt`
- `chunks_manifest_v2.json`
- `audio_chunks/chapter_001/chunk_*.wav`
- `chapter_001.wav`
