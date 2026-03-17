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
- `--ocr-mode auto|off|force|compare` — OCR mode for PDF
- `--ocr-dpi 400` — DPI for OCR rendering (higher = better quality, slower)
- `--ocr-psm 6` — Tesseract page segmentation mode
- `--interactive` — enable interactive review
- `--skip-stress` — skip stress annotation

Output: `output/mybook_pdf/001_chapter_01.txt`, `002_chapter_02.txt`, ...

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

Launch the visual application:

```bash
python -m book_normalizer.gui.app
```

Features:
- **Tab 1 — Normalize**: Load book, configure OCR, run normalization with before/after preview
- **Tab 2 — Voices**: Interactive table to assign voices (narrator/male/female) and intonation per chunk
- **Tab 3 — Synthesize**: Start/stop TTS generation with progress bar and ETA
- **Tab 4 — Assemble**: Merge chunks into chapter WAV files with configurable pauses

## TTS Quality Tips

1. **Use the 1.7B model** — 18% better WER than 0.6B for Russian
2. **Keep chunks short** — `--max-chunk-chars 600` for stable intonation
3. **Install flash-attention** — `pip install flash-attn --no-build-isolation` for 1.5-2x speedup
4. **Russian instruct prompts** — built-in for narrator/male/female voices
5. **Yofication** — automatic ё restoration improves pronunciation
6. **Stress marks** — try `--stress-mode keep_acute` if the model handles them well

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
