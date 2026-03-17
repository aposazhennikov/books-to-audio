# Books to Audio

Full-pipeline Russian audiobook generator: from book files (PDF/TXT/EPUB/FB2/DOCX) to multi-voice audio.

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

## Quick Start

### Installation

```bash
# Core (normalization only)
pip install -e "."

# With OCR support
pip install -e ".[ocr]"

# With GUI
pip install -e ".[gui]"

# Everything
pip install -e ".[ocr,gui,llm,dev]"
```

### WSL Setup for TTS (one-time)

Qwen3-TTS runs on GPU via WSL. Setup:

```bash
# In WSL:
python3.10 -m venv ~/venvs/qwen3tts
source ~/venvs/qwen3tts/bin/activate
pip install qwen-tts torch soundfile numpy

# Optional: install flash-attention for 1.5-2x speedup
pip install flash-attn --no-build-isolation
```

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
| 4 | Single column of variable-size text | Single-column books |
| 6 (default) | Uniform block of text | **Best for books** — consistent text layout |
| 11 | Sparse text, find as much as possible | Pages with scattered text fragments |
| 13 | Raw line, treat as single text line | Processing individual lines |

### Step 2. Export voice-annotated chunks

```bash
python scripts/export_chunks.py --book-dir output/mybook_pdf --speaker-mode heuristic --max-chunk-chars 600
```

Options:
- `--speaker-mode heuristic|llm|manual` — voice attribution mode
- `--max-chunk-chars 600` — shorter chunks = more stable intonation
- `--stress-mode strip|keep_acute` — keep stress marks for TTS

Output: `output/mybook_pdf/chunks_manifest.json`

### Step 3. Synthesize audio (runs in WSL)

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
    --resume
```

Options:
- `--model Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` — 1.7B for best quality, 0.6B for speed
- `--batch-size 2` — batch inference (needs more VRAM)
- `--resume` — skip already generated chunks
- `--chapter 3` — only generate specific chapter

### Step 4. Assemble audio

```bash
# In WSL:
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
| **Tesseract PSM** | Page layout analysis mode (0-13, default 6 for books — see PSM table above) |

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
- **Batch Size** (see batch size guide below)
- **Chapter** filter: synthesize all or a specific chapter
- Progress bar with ETA and chunk counter
- **Stop** button to cancel mid-synthesis

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
2. **Keep chunks short** — `--max-chunk-chars 600` for stable intonation. Longer chunks may drift in tone.
3. **Start with batch=1** — increase only if your GPU has enough VRAM (see Batch Size Guide above).
4. **Install flash-attention** — `pip install flash-attn --no-build-isolation` for 1.5-2x speedup. Highly recommended for production runs.
5. **Use `--resume`** — always add `--resume` when running TTS from CLI. It skips already generated chunks, saving hours on interrupted runs.
6. **Russian instruct prompts** — built-in for 12 voice presets (narrators, male, female). Custom instruct text controls intonation style.
7. **Yofication** — automatic ё restoration improves pronunciation of words like "всё", "её", "ёлка".
8. **Stress marks** — try `--stress-mode keep_acute` if the model handles them well. May improve emphasis on key syllables.

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
├── chunks_manifest.json            # Voice-annotated chunk manifest
├── book_structure.json             # Machine-readable structure
├── audio_chunks/
│   ├── chapter_001/
│   │   ├── chunk_001_narrator.wav
│   │   ├── chunk_002_male.wav
│   │   └── chunk_003_female.wav
│   └── chapter_002/
├── chapter_001.wav                 # Assembled chapter audio
├── chapter_002.wav
├── synthesis_progress.json         # Resume checkpoint
├── synthesis_manifest.json         # Audio generation log
├── voice_config_template.json      # Voice configuration
└── audit_log.json                  # Processing audit trail
```

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
