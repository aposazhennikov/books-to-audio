# Manifest v2

`chunks_manifest_v2.json` is the main contract between chunking, synthesis, QA, and assembly.

Minimal shape:

```json
{
  "version": 2,
  "book_title": "mybook_pdf",
  "chunker": "llm",
  "chapters": [
    {
      "chapter_index": 0,
      "chapter_title": "Chapter 1",
      "chunks": [
        {
          "chapter_index": 0,
          "chunk_index": 0,
          "voice_label": "narrator",
          "narrator": "Текст чанка.",
          "voice": "narrator",
          "voice_id": "narrator_calm",
          "voice_tone": "calm",
          "text": "Текст чанка.",
          "synthesized": false,
          "failed": false,
          "error": "",
          "audio_file": null
        }
      ]
    }
  ]
}
```

Roles:

- `voice_label`: ComfyUI-facing role: `narrator`, `men`, `women`.
- `voice`: internal canonical role: `narrator`, `male`, `female`.
- `voice_id`: GUI preset id.
- `voice_tone`: tone/instruction key.

Resume behavior:

- Synthesized chunks have `synthesized: true` and a valid `audio_file`.
- Failed chunks have `failed: true` and `error`.
- `--failed-only` retries only chunks marked `failed: true`.
