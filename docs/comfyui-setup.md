# ComfyUI Setup

The recommended synthesis route is:

```powershell
normalize-book pipeline books\mybook.pdf --out output --synthesize --assemble `
  --workflow comfyui_workflows\qwen3_tts_template.json
```

Preflight:

```powershell
normalize-book doctor
```

Required:

- ComfyUI running at `http://localhost:8188`.
- Qwen3-TTS custom nodes installed.
- Workflow saved in API format.
- Template placeholders present:
  - `{{TEXT}}`
  - `{{SPEAKER}}`
  - `{{INSTRUCT}}`
  - `{{OUTPUT_FILENAME}}`

Default model directory:

```text
D:\ComfyUI-external\models\audio_encoders\
  Qwen3-TTS-12Hz-1.7B-Base\
  Qwen3-TTS-12Hz-1.7B-CustomVoice\
  Qwen3-TTS-Tokenizer-12Hz\
```
