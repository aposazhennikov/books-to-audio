# Books to Audio

Full-pipeline Russian audiobook generator: from book files (PDF/TXT/EPUB/FB2/DOCX) to multi-voice audio.

## Requirements

| Component | Requirement |
|-----------|-------------|
| **OS** | Windows 10/11 (GUI runs on Windows) |
| **WSL 2** | Required for TTS synthesis (Qwen3-TTS runs in Linux) |
| **Python** | 3.10 or newer |
| **GPU** | NVIDIA with CUDA (6+ GB VRAM recommended for 1.7B model) |
| **RAM** | 8+ GB (16 GB recommended for large books) |

### Libraries

| Group | Packages |
|-------|----------|
| **Core** | pydantic, click, PyMuPDF, python-docx, ebooklib, lxml, rich, num2words |
| **OCR** (optional) | pytesseract, Pillow — requires [Tesseract](https://github.com/tesseract-ocr/tesseract) on PATH (Windows: install from [UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)) |
| **GUI** | PyQt6 |
| **TTS** (in WSL) | qwen-tts, torch, soundfile, numpy |

## Features

- **Multi-format support**: TXT, PDF (with OCR), EPUB, FB2, DOCX
- **Smart chapter detection**: Regex patterns + TOC parsing
- **Text normalization**: encoding fixes, OCR artifact cleanup, abbreviation expansion, number-to-words
- **Yofication**: automatic restoration of the letter ё in Russian texts
- **Stress annotation**: word stress marks for better TTS pronunciation
- **Dialogue detection**: identifies direct speech (em-dashes, guillemets) and narrator remarks
- **Speaker attribution**: 3 modes — heuristic, LLM (OpenAI/Ollama), manual
- **Multi-voice TTS**: narrator, male dialogue, female dialogue via Qwen3-TTS
- **Audio assembly**: merge chunks into chapters/full book with configurable pauses
- **GUI application**: PyQt6 desktop app with all features
- **CLI interface**: full-featured command-line tools

## Documentation

Focused docs live in `docs/`:

- `docs/architecture.md` — pipeline shape and main modules
- `docs/manifest-v2.md` — v2 manifest contract
- `docs/comfyui-setup.md` — ComfyUI workflow and model setup
- `docs/troubleshooting.md` — common failure modes
- `docs/smoke-test.md` — quick regression checklist

## Quick Start (from scratch)

### 1. Prerequisites

| Step | Action |
|------|--------|
| **WSL 2** | `wsl --install` (restart if needed). Default Ubuntu is fine. |
| **Python 3.10+** | Install on Windows from [python.org](https://www.python.org/downloads/) or `winget install Python.Python.3.12` |
| **NVIDIA GPU** | Drivers with CUDA support. 6+ GB VRAM for 1.7B model. |
| **Ollama** | [ollama.com/download](https://ollama.com/download) — for LLM-based chunking |
| **ComfyUI** | Running locally with Qwen3-TTS custom nodes installed |

### 2. Install on Windows

**Option A — via requirements.txt (simplest):**

```powershell
cd C:\path\to\books-to-audio

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
pip install -e "."
```

**Option B — via pip extras (full control):**

```powershell
pip install -e ".[ocr,gui,llm]"     # GUI + OCR + LLM (recommended)
pip install -e ".[ocr,gui,llm,dev]" # + dev tools (pytest, ruff)
```

### 3. Ollama setup (for LLM-based chunking)

LLM chunking uses a local Ollama model to split text into TTS chunks with
voice assignment (narrator/male/female) and mood detection.

**Install Ollama:** [ollama.com/download](https://ollama.com/download)

**Pull a model** (run in PowerShell after Ollama is installed):

```powershell
# Recommended: best balance of speed and quality for Russian text
ollama pull gemma3:4b

# Better quality, slower (~10-15s/window instead of 2-5s):
ollama pull gemma3:12b
```

Ollama starts automatically as a background service. Default endpoint:
`http://localhost:11434`

### 4. WSL setup for TTS via WSL runner (one-time, legacy path)

The WSL path (`tts_runner.py`) is kept for backward compatibility.
For new workflows, use the **ComfyUI path** (see Step 5).

In **WSL terminal**:

```bash
sudo apt update && sudo apt install python3.10 python3.10-venv

python3.10 -m venv ~/venvs/qwen3tts
source ~/venvs/qwen3tts/bin/activate

pip install qwen-tts torch soundfile numpy

# Optional: flash-attention for 1.5-2x speedup
pip install flash-attn --no-build-isolation

# Optional: SageAttention for faster SDPA kernels
pip install git+https://github.com/thu-ml/SageAttention.git
```

### 5. ComfyUI setup for TTS (recommended path)

ComfyUI with Qwen3-TTS nodes provides streaming synthesis and better
integration with the new v2 manifest pipeline.

**Shared model folder:** the app now looks for Qwen3-TTS model folders in
`D:\ComfyUI-external\models` before it lets HuggingFace download anything.
For the WSL runner this is passed as `/mnt/d/ComfyUI-external/models`.
The expected layout is:

```text
D:\ComfyUI-external\models\audio_encoders\
  Qwen3-TTS-12Hz-1.7B-Base\
  Qwen3-TTS-12Hz-1.7B-CustomVoice\
  Qwen3-TTS-Tokenizer-12Hz\
```

You can override the folder with the GUI **Models dir** field, the CLI
`--models-dir` option, or the `BOOKS_TO_AUDIO_MODELS_DIR` environment variable.

**One-time workflow template setup:**

1. Open ComfyUI (default: `http://localhost:8188`)
2. Build your Qwen3-TTS workflow in the UI
3. Click **Save** → **Save (API Format)** → download the JSON
4. Open the JSON and replace static input values with these placeholder strings:
   - `"{{TEXT}}"` — the text to synthesize
   - `"{{VOICE_ID}}"` — voice preset (e.g. `narrator_calm`, `male_young`)
   - `"{{INSTRUCT}}"` — style/mood instruct prompt
   - `"{{OUTPUT_FILENAME}}"` — output filename prefix
5. Save as `comfyui_workflows/qwen3_tts_template.json` in the project root

**Create the workflows directory:**

```powershell
mkdir comfyui_workflows
```

### 6. Run the GUI

From **Windows PowerShell** (not WSL):

```powershell
cd C:\path\to\books-to-audio
.venv\Scripts\activate
python -m book_normalizer.gui.app
```

> GUI runs on Windows. WSL is used internally only for the legacy TTS path.

## Full Pipeline: Step-by-Step

### Step 1. Normalize text

```bash
python -m book_normalizer.cli process books/mybook.pdf --out output -v --ocr-mode auto
```

Options:
- `--ocr-mode auto|off|force|compare` — OCR mode for PDF (see below)
- `--ocr-dpi 400` — DPI for OCR rendering (see below)
- `--ocr-psm 6` — Tesseract page segmentation mode (see below)
- `--interactive` — enable interactive review
- `--skip-stress` — skip stress annotation

Output: `output/mybook_pdf/001_chapter_01.txt`, `002_chapter_02.txt`, ...

#### OCR Mode (`--ocr-mode`)

Controls how text is extracted from PDF files:

| Mode | Description |
|------|-------------|
| `auto` (default) | Uses native PDF text extraction first. If the result is empty or unreadable (less than 30% Cyrillic characters), automatically falls back to OCR. Best for most cases. |
| `off` | Only native PDF text extraction, no OCR at all. Fast, but won't work for scanned PDFs. Use for digitally-created PDFs. |
| `force` | Always runs OCR, ignores native text completely. Use when native text is garbled or the PDF is a scan. |
| `compare` | Runs both native and OCR extraction, saves comparison report (`pdf_compare_report.json`). Useful for debugging. |

#### OCR DPI (`--ocr-dpi`)

DPI (dots per inch) controls the resolution of PDF page rendering before OCR:

| DPI | Quality | Speed | When to use |
|-----|---------|-------|-------------|
| 300 | Basic | Fast (~1s/page) | Quick preview, clean scans |
| 400 (default) | Good | Medium (~2s/page) | Recommended for most books |
| 600 | Best | Slow (~4s/page) | Poor quality scans, small fonts |

Higher DPI means more pixels for Tesseract to work with, resulting in better character recognition, especially for small text, ligatures, and diacritics. However, processing time and memory usage increase proportionally.

#### Tesseract PSM (`--ocr-psm`)

Page Segmentation Mode controls how Tesseract analyzes the page layout:

| PSM | Description | When to use |
|-----|-------------|-------------|
| 3 | Fully automatic page segmentation | Mixed content (images + text) |
| 4 | Single column of variable-size text | Alternative for difficult single-column scans |
| 6 (default) | Uniform block of text | **Recommended after automatic spread splitting/cropping** |
| 11 | Sparse text, find as much as possible | Pages with scattered text fragments |
| 13 | Raw line, treat as single text line | Processing individual lines |

### Step 2. Export voice-annotated chunks

**Option A — Heuristic (fast, rule-based):**

```bash
python scripts/export_chunks.py --book-dir output/mybook_pdf --speaker-mode heuristic --max-chunk-chars 600
```

Output: `output/mybook_pdf/chunks_manifest.json` (v1 format)

**Option B — LLM chunking (recommended, voice + mood detection):**

```bash
# Using gemma3:4b (fast, good quality):
python scripts/export_chunks.py --book-dir output/mybook_pdf --mode llm --llm-model gemma3:4b --max-chunk-chars 400

# Using gemma3:12b (slower, better quality for complex dialogues):
python scripts/export_chunks.py --book-dir output/mybook_pdf --mode llm --llm-model gemma3:12b
```

Output: `output/mybook_pdf/chunks_manifest_v2.json` (v2 format with voice + mood)

LLM chunking options:
- `--mode llm|heuristic` — chunking mode
- `--llm-model gemma3:4b` — Ollama model (default: gemma3:4b)
- `--llm-endpoint http://localhost:11434/v1` — Ollama endpoint
- `--max-chunk-chars N` — soft chunk size limit. Splitting prefers sentence/clause boundaries and does not cut inside a word.

### Step 3a. Synthesize audio via ComfyUI (recommended)

Requires: ComfyUI running + workflow template at `comfyui_workflows/qwen3_tts_template.json`

```bash
python scripts/synthesize_comfyui.py \
    --chunks-json output/mybook_pdf/chunks_manifest_v2.json \
    --out output/mybook_pdf/audio_chunks \
    --workflow comfyui_workflows/qwen3_tts_template.json

# Only one chapter:
python scripts/synthesize_comfyui.py \
    --chunks-json output/mybook_pdf/chunks_manifest_v2.json \
    --out output/mybook_pdf/audio_chunks \
    --workflow comfyui_workflows/qwen3_tts_template.json \
    --chapter 3
```

Options:
- `--comfyui-url http://localhost:8188` — ComfyUI server URL
- `--chapter N` — synthesize only chapter N (1-based)
- `--chunk-timeout 300` — max seconds per chunk

### Step 3b. Synthesize audio via WSL runner (legacy)

```bash
wsl -e bash scripts/run_tts.sh             # All chapters
wsl -e bash scripts/run_tts.sh 3           # Only chapter 3
```

Or directly:

```bash
# In WSL:
source ~/venvs/qwen3tts/bin/activate
python scripts/tts_runner.py \
    --chunks-json output/mybook_pdf/chunks_manifest.json \
    --out output/mybook_pdf \
    --model Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice \
    --batch-size 1 \
    --sage-attention \
    --resume
```

Options:
- `--model Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` — 1.7B for best quality, 0.6B for speed
- `--batch-size 2` — batch inference (needs more VRAM)
- `--sage-attention` — require SageAttention; exits with a clear error if the active WSL venv does not have a compatible kernel
- `--resume` — skip already generated chunks
- `--chapter 3` — only generate specific chapter

### Step 4. Assemble audio

**From v2 manifest (ComfyUI path):**

```bash
python scripts/assemble_chapter.py \
    --manifest output/mybook_pdf/chunks_manifest_v2.json \
    --out output/mybook_pdf \
    --all

# Single chapter:
python scripts/assemble_chapter.py \
    --manifest output/mybook_pdf/chunks_manifest_v2.json \
    --out output/mybook_pdf \
    --chapter 3
```

**From audio directory (WSL path, backward compatible):**

```bash
python scripts/assemble_chapter.py \
    --audio-dir output/mybook_pdf/audio_chunks \
    --out output/mybook_pdf \
    --all
```

Output: `output/mybook_pdf/chapter_001.wav`, `chapter_002.wav`, ...

## Speaker Attribution Modes

### Heuristic (default)

Automatic detection using Russian verb endings and pronoun patterns:
- "сказал" → male, "сказала" → female
- Alternation when no attribution is found

```bash
python scripts/export_chunks.py --book-dir output/mybook_pdf --speaker-mode heuristic
```

### LLM (AI-powered)

Sends dialogue to an OpenAI-compatible API for gender detection:

```bash
# With local Ollama (no API key needed):
python -m book_normalizer.cli synthesize books/mybook.pdf \
    --speaker-mode llm \
    --llm-endpoint http://localhost:11434/v1 \
    --llm-model qwen3:8b

# With OpenAI API:
python -m book_normalizer.cli synthesize books/mybook.pdf \
    --speaker-mode llm \
    --llm-endpoint https://api.openai.com/v1 \
    --llm-model gpt-4o \
    --llm-api-key sk-your-key-here
```

### Manual (interactive)

Prompts for each dialogue line in the terminal:

```bash
python -m book_normalizer.cli synthesize books/mybook.pdf --speaker-mode manual
```

Decisions are saved to `manual_speaker_session.json` and reused on next run.

## GUI Application

Launch the visual application (from **Windows PowerShell**, not WSL):

```bash
cd c:\Users\Rog\Desktop\OwnProjects\books-to-audio
python -m book_normalizer.gui.app
```

> **Important**: The GUI runs on Windows. WSL is used only internally for TTS synthesis.

### Tab 1 — Normalize

Load a book file, configure OCR settings, run the full normalization pipeline.

| Field | Description |
|-------|-------------|
| **OCR Mode** | How text is extracted from PDF (auto/off/force/compare — see OCR Mode table above) |
| **OCR DPI** | Resolution for PDF-to-image rendering before OCR (300-600, default 400 — see DPI table above) |
| **Tesseract PSM** | Page layout analysis mode (0-13, default 6 after automatic spread splitting/cropping — see PSM table above) |

**Progress**: Shows per-page OCR progress with ETA (e.g., "OCR: page 45/120 — ETA: 2m 30s"), then normalization stages, then chapter detection. After completion, shows a before/after text comparison panel.

### Tab 2 — Voices

Interactive table for assigning voices and intonation to every text chunk:
- **Voice** dropdown: Narrator / Male / Female per chunk
- **Intonation** dropdown: Neutral / Calm / Excited / Sad / Angry / Whisper
- **Auto-detect** button: runs heuristic speaker detection
- **All → Narrator** button: mass-assign narrator to all chunks
- Dialogue lines are highlighted in blue for easy identification

### Tab 3 — Synthesize

Start/stop TTS generation with real-time progress:
- **Model** selector (see model comparison below)
- **Models dir** points to the shared ComfyUI models directory, defaulting to `D:\ComfyUI-external\models`
- **Batch Size** (see batch size guide below)
- **Chapter** filter: synthesize all or a specific chapter
- **Custom Voice** can use a new sample once, reuse a saved local voice, or map saved voices by role
- **ComfyUI Saved Voice** saves a reusable custom voice through `voice_setup_template.json`
- Progress bar with ETA and chunk counter
- **Stop** button to cancel mid-synthesis

#### Local Saved Voice Library

The direct WSL runner can persist Qwen `voice_clone_prompt` objects in
`output/voices` so prompt extraction does not run on every book:

```bash
python scripts/tts_runner.py \
    --save-voice ilya_isaev \
    --save-ref-audio /path/to/sample.wav \
    --save-ref-text "Exact words spoken in the sample."
```

This creates `output/voices/ilya_isaev.voice.pt` plus
`ilya_isaev.voice.json`. During synthesis, clone configs can reuse it:

```json
{
  "__all__": {"saved_voice": "ilya_isaev"},
  "narrator": {"saved_voice": "ilya_isaev"},
  "male": {"saved_voice": "male_actor"},
  "female_warm": {"saved_voice": "female_actor"}
}
```

`__all__` means one saved voice for the whole book. Role keys such as
`narrator`, `male`, and `female` apply to all matching GUI presets
(`male_young`, `female_warm`, etc.). Any role or preset not listed falls back
to the built-in Qwen speaker selected in the Voices step, so mixed mode is
supported.

The saved ComfyUI voice flow uploads a reference audio clip, extracts the
voice prompt with `FB_Qwen3TTSVoiceClonePrompt`, then saves it with
`FB_Qwen3TTSSaveVoice`. The saved name appears in `FB_Qwen3TTSLoadSpeaker`
and can be used by `scripts/synthesize_dialogue.py`.

#### Model Comparison

| Model | Parameters | VRAM | Speed | Quality (WER) | When to use |
|-------|-----------|------|-------|---------------|-------------|
| **Qwen3-TTS-12Hz-1.7B-CustomVoice** | 1.7 billion | ~4 GB | ~80–120 s/chunk | **Best** (18% fewer errors) | Final production audio. Recommended default. |
| **Qwen3-TTS-12Hz-0.6B-CustomVoice** | 0.6 billion | ~2 GB | ~30–60 s/chunk | Good | Drafts, quick previews, weaker GPUs. |

Both models support the same 9 speakers (Aiden, Ryan, Uncle_Fu, Dylan, Eric, Serena, Vivian, Ono_Anna, Sohee) and CustomVoice instruct prompts. The 1.7B model produces more natural intonation, fewer mispronunciations, and better handling of complex Russian words.

#### Batch Size Guide

Batch size controls how many text chunks are synthesized simultaneously on the GPU:

| Batch Size | VRAM (1.7B model) | VRAM (0.6B model) | Speedup | Stability |
|------------|-------------------|-------------------|---------|-----------|
| **1** (default) | ~4 GB | ~2 GB | 1× | Most stable. Recommended for most users. |
| **2–4** | 6–10 GB | 3–5 GB | ~1.5–2.5× | Good. Safe on 8+ GB GPUs. |
| **5–8** | 12+ GB | 6+ GB | ~3–4× | Risk of OOM on smaller GPUs. Use on 16+ GB VRAM. |

**How it works**: With batch=1, the GPU processes one chunk at a time — generate audio, save, move to the next. With batch=4, four chunks are loaded into GPU memory simultaneously and synthesized in parallel, then saved together. This significantly reduces the per-chunk overhead, but requires proportionally more VRAM.

**Recommendation**: Start with batch=1. If your GPU has 8+ GB VRAM (e.g., RTX 3070/4060 or better), try batch=2 or batch=3. Only use batch=5+ on 16+ GB cards (RTX 3090/4090, A5000+). If you get CUDA out-of-memory errors, reduce batch size.

### Tab 4 — Assemble

Merge individual audio chunks into full chapter WAV files:
- **Pause (same voice)**: silence between chunks from the same speaker (default 300ms)
- **Pause (voice change)**: silence when speaker changes (default 600ms)

## TTS Quality Tips

1. **Use the 1.7B model** — 18% better WER than 0.6B for Russian. Worth the extra time for final audio.
2. **Keep chunks short** — `--max-chunk-chars 300`–`600` for stable intonation. Smaller values create more chunks; splitting prefers sentence/clause boundaries and does not cut inside a word.
3. **Start with batch=1** — increase only if your GPU has enough VRAM (see Batch Size Guide above).
4. **Install SageAttention or flash-attention** — `pip install git+https://github.com/thu-ml/SageAttention.git` for the SageAttention path, or `pip install flash-attn --no-build-isolation` for the existing flash-attn path.
5. **Use `--resume`** — always add `--resume` when running TTS from CLI. It skips already generated chunks, saving hours on interrupted runs.
6. **Russian instruct prompts** — built-in for 12 voice presets (narrators, male, female). Custom instruct text controls intonation style.
7. **Yofication** — automatic ё restoration improves pronunciation of words like "всё", "её", "ёлка".
8. **Stress marks** — try `--stress-mode keep_acute` if the model handles them well. May improve emphasis on key syllables.

### Synthesis seems stuck?

- **First chunk can take 2–5 min** — model warm-up, especially with batch size 2+.
- **Check the log** — GUI shows a live log; also see `output/<book>/synthesis_log.txt`. Look for `[INFO] Starting synthesis of batch...` — if you see it but no `Batch done...` for 5+ min, the GPU may be overloaded.
- **Try batch=1** — on 6 GB VRAM, batch 2 can cause swapping or OOM.
- **Task Manager** — if GPU is 80–90% and VRAM is full, it's working, just slow.

## CLI Commands Reference

| Command | Description |
|---------|-------------|
| `normalize-book process <file>` | Load, normalize, detect chapters, export |
| `normalize-book batch <dir>` | Process all books in a directory |
| `normalize-book info <file>` | Show book info without processing |
| `normalize-book synthesize <file>` | Full TTS pipeline |
| `normalize-book init-voices` | Generate voice config template |
| `normalize-book review-session <path>` | Show review session info |

## Output Structure

```
output/mybook_pdf/
├── 000_full_book.txt               # Full normalized text
├── 001_chapter_01.txt              # Normalized chapters
├── qwen_full.txt                   # TTS-optimized full text
├── qwen_chapter_01.txt             # TTS-optimized chapters
├── qwen_chunks/                    # Pre-split TTS chunks
├── chunks_manifest.json            # Voice-annotated chunk manifest (v1, heuristic)
├── chunks_manifest_v2.json         # LLM chunk manifest with voice + mood (v2)
├── book_structure.json             # Machine-readable structure
├── speaker_cache/                  # LLM chunking cache (per chapter window)
│   ├── llm_chunks_ch000_win000.json
│   └── ...
├── audio_chunks/
│   ├── chapter_001/
│   │   ├── chunk_001_narrator.wav
│   │   ├── chunk_002_male.wav
│   │   └── chunk_003_female.wav
│   └── chapter_002/
├── chapter_001.wav                 # Assembled chapter audio
├── chapter_002.wav
├── synthesis_progress.json         # Resume checkpoint (WSL path)
├── synthesis_manifest.json         # Audio generation log (WSL path)
├── voice_config_template.json      # Voice configuration
└── audit_log.json                  # Processing audit trail
```

## New LLM Pipeline: Full Workflow

The recommended end-to-end flow for a Russian book with ComfyUI:

```
Step 1: normalize text
    python -m book_normalizer.cli process books/mybook.pdf --out output

Step 2: LLM chunking (Ollama + gemma3)
    python scripts/export_chunks.py --book-dir output/mybook_pdf --mode llm --llm-model gemma3:4b --max-chunk-chars 400

Step 3: synthesize via ComfyUI
    python scripts/synthesize_comfyui.py \
        --chunks-json output/mybook_pdf/chunks_manifest_v2.json \
        --out output/mybook_pdf/audio_chunks \
        --workflow comfyui_workflows/qwen3_tts_template.json

Optional WSL direct runner using the shared ComfyUI model folder:
    python scripts/tts_runner.py \
        --chunks-json output/mybook_pdf/chunks_manifest.json \
        --out output/mybook_pdf \
        --model Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice \
        --models-dir /mnt/d/ComfyUI-external/models \
        --resume

Step 4: assemble chapters
    python scripts/assemble_chapter.py \
        --manifest output/mybook_pdf/chunks_manifest_v2.json \
        --out output/mybook_pdf \
        --all
```

| Step | Tool | Input | Output |
|------|------|-------|--------|
| Normalize | `cli process` | Book file | `chapter_NNN.txt` |
| LLM Chunk | `export_chunks.py --mode llm` | Chapter TXTs | `chunks_manifest_v2.json` |
| Synthesize | `synthesize_comfyui.py` | Manifest v2 + workflow | `audio_chunks/chapter_NNN/*.wav` |
| Assemble | `assemble_chapter.py --manifest` | Manifest v2 | `chapter_NNN.wav` |

## Normalization Pipeline

19 stages applied in order:

1. Encoding artifact removal (BOM, control chars)
2. Mojibake fixes (UTF-8 as CP1252)
3. Mixed script fix (Latin→Cyrillic lookalikes)
4. OCR artifact cleanup (stray punctuation, garbage symbols)
5. Whitespace normalization
6. Hyphenation repair (word-\nbreak → wordbreak)
7. Broken line repair
8. Page number removal
9. Footnote removal
10. Repeated header removal
11. Empty line collapse
12. Paragraph indent strip
13. Quote normalization (→ «»)
14. Dash normalization (→ —)
15. Ellipsis normalization
16. Spacing around punctuation
17. Abbreviation expansion (т.д.→так далее)
18. Number expansion (17→семнадцать)
19. Yofication (е→ё)
20. TTS punctuation adaptation

## Testing

```bash
pytest                    # Run all tests
pytest tests/ -v          # Verbose
```

## Recent Updates

**2026-04-01**:
- Added **LLM-based chunking** via Ollama (`export_chunks.py --mode llm`): splits text into TTS chunks with voice (narrator/male/female) and mood (neutral/happy/sad/angry/tense/whisper) annotation in one LLM pass
- Added **ComfyUI integration** (`synthesize_comfyui.py`): synthesize via ComfyUI REST API with resume support and manifest updates
- Added **v2 manifest format** (`chunks_manifest_v2.json`) with voice, mood, synthesized status, and audio_file paths
- Updated **`assemble_chapter.py`**: now supports `--manifest` mode for v2 manifests in addition to `--audio-dir` file-scan mode
- Added **`requirements.txt`** for simplified installation (`pip install -r requirements.txt`)
- Added **Ollama + ComfyUI setup** instructions to README
- Recommended model for LLM chunking: `gemma3:4b` (fast) or `gemma3:12b` (quality)

**2026-03-17**:
- Added **yofication** (ё restoration) to normalization pipeline
- **OCR improvements**: configurable DPI (default 400), PSM mode, image preprocessing (binarization + noise removal), expanded artifact cleanup
- **TTS quality**: default model upgraded to 1.7B, Russian-language instruct prompts, reduced chunk size to 600 chars
- **TTS speed**: auto-detect flash-attention, batch inference support, ETA display
- **GUI application**: PyQt6 desktop app with 4-tab workflow (Normalize → Voices → Synthesize → Assemble)
- **LLM attribution**: added `--llm-api-key` CLI option for cloud APIs
- **CLI**: added `--ocr-dpi`, `--ocr-psm` options

**2026-03-11**:
- Added Table of Contents parsing for chapter detection
- Enhanced chapter patterns (numeric headings, common headings)
- FB2 improvements (subtitles, citations)
- Fixed EPUB chapter order (spine-based)
