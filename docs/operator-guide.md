# Operator Guide

This guide is for running the app, not changing the code.

## First Successful Audiobook In 30 Minutes

Goal: produce a short, reviewed chapter package from a known-good book sample.

1. Put the source book in `books/`. Do not commit this folder.
2. Run a local health check:

```bash
normalize-book doctor --skip-network
normalize-book doctor
```

3. Create the v2 manifest:

```bash
normalize-book pipeline books/mybook.pdf --out output --llm-normalize
```

4. Start ComfyUI, then synthesize and assemble:

```bash
normalize-book pipeline books/mybook.pdf \
  --out output \
  --llm-normalize \
  --synthesize \
  --workflow comfyui_workflows/qwen3_tts_template.json \
  --quality-loop \
  --assemble
```

5. Run production QA and package metadata as a dry run:

```bash
normalize-book production-preflight output/mybook_pdf/chunks_manifest_v2.json \
  --package \
  --chapter-audio-dir output/mybook_pdf/mastered
```

6. If QA is green, build the final package:

```bash
normalize-book package-audiobook output/mybook_pdf/chunks_manifest_v2.json \
  --chapter-audio-dir output/mybook_pdf/mastered \
  --cover books/cover.jpg \
  --format both
```

Expected final files are in `output/mybook_pdf/audiobook_package/`: chapter MP3 files, an M4B, `chapters.ffmetadata`, `package_qa_report.json`, `audiobook_package_report.json`, and `checksums.sha256`.

## Full Production Run Checklist

Before synthesis:

- `normalize-book doctor` passes.
- Book source is in `books/`, not repo root.
- Models and caches are outside git-tracked source folders.
- `chunks_manifest_v2.json` exists.
- Chapter detection looks correct.
- Voice roles and casting plan are reviewed.

During synthesis:

- Run one short chapter first.
- Watch ComfyUI for out-of-memory errors.
- Keep the run folder under `output/`.
- Use `--quality-loop` for automatic retry of failed chunks.

Before packaging:

- `normalize-book audio-qa <manifest> --artifact --asr` has no blocking errors.
- `normalize-book production-qa <manifest> --write-manifest` passes.
- `normalize-book master <manifest>` has produced mastered chapters.
- Cover is JPEG/PNG, square, and at least 300x300 pixels.

Final package:

- `normalize-book package-audiobook ... --format both` completes.
- `package_qa_report.json` status is `passed`.
- `chapters.ffmetadata` contains all chapter titles.
- `checksums.sha256` exists and includes the final reports and media files.
- Listen to the first minute, one middle chapter transition, and the ending.

## What To Do When VRAM Is Low

Use these in order:

1. Close other GPU apps and restart ComfyUI.
2. Process one chapter at a time with `--chapter`.
3. Reduce concurrent ComfyUI queue work to one item.
4. Use smaller LLM/TTS models when available.
5. Disable optional ASR during synthesis and run ASR QA later.
6. Move model caches to a fast external model directory, not the repo.
7. If failures repeat at the same chunk, review that chunk text for extreme length or unusual markup.

After an out-of-memory failure, restart the worker before resuming. A process can remain fragmented even after the failed job exits.

## How To Review Failed Chunks

1. Open the run manifest:

```bash
output/mybook_pdf/chunks_manifest_v2.json
```

2. Find chunks where `qa_status`, `artifact_qa.status`, or `asr_qa.status` is not `passed`.
3. Export a review list:

```bash
python scripts/prepare_listening_review.py \
  --manifest output/mybook_pdf/chunks_manifest_v2.json \
  --out output/mybook_pdf/listening_review
```

4. Listen to the failed chunk audio in `audio_chunks/`.
5. Fix the cause:

- bad pronunciation: adjust text normalization, stress hints, or voice settings.
- clipped/noisy audio: resynthesize the chunk.
- wrong speaker: update role/casting metadata.
- text mismatch: check OCR and normalized chapter text.

6. Rerun QA, then master and package again.
