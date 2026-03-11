# Book Normalizer

Semi-automatic Russian book source normalizer for TTS pipelines.

## Features

- **Multi-format support**: TXT, PDF, EPUB, FB2, DOCX
- **Automatic output folders**: Creates `{bookname}_{format}/` directories
- **Smart chapter detection**: 
  - Finds chapter headings using regex patterns ("Глава", "Часть", etc.)
  - Fallback to Table of Contents parsing if few/no chapters found
  - Handles embedded TOC entries within multi-line paragraphs
- **PDF cleanup**: Removes repeated headers/footers (e.g., "Book Title | Page 123")
- **Empty chapter filtering**: Removes chapters with <10 chars (TOC artifacts)
- **Stress annotation**: Marks word stress for Russian TTS
- **Interactive review**: Fix punctuation and spelling issues manually

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

```bash
# Process single book
python -m book_normalizer.cli process books/mybook.pdf --out output -v

# Batch process all books
python -m book_normalizer.cli batch books --out output -v

# Show book info without processing
python -m book_normalizer.cli info books/mybook.txt

# With interactive review
python -m book_normalizer.cli process books/mybook.pdf --out output -v --interactive
```

### Output Structure

```
output/
├── mybook_pdf/
│   ├── 000_full_book.txt           # Full normalized book
│   ├── 001_chapter_01.txt          # Chapter 1
│   ├── 002_chapter_02.txt          # Chapter 2
│   ├── qwen_full.txt               # TTS-ready (stress marks stripped)
│   ├── qwen_chapter_01.txt         # TTS-ready chapters
│   ├── book_structure.json         # Machine-readable structure
│   └── audit_log.json              # Processing log
```

## What Gets Fixed

### PDF Issues
- ✅ **Repeated headers/footers**: "Book Title | 123" removed automatically
- ✅ **Page numbers**: Standalone numbers removed
- ✅ **Hyphenation**: "пси-\nхология" → "психология"

### All Formats
- ✅ **Chapter detection**: Regex patterns + TOC parsing fallback
- ✅ **TOC parsing**: Extracts chapter structure from "Оглавление"/"Содержание" sections
- ✅ **Empty chapters**: TOC entries without content filtered (< 10 chars)
- ✅ **Quotes**: Straight quotes → curly quotes
- ✅ **Dashes**: Hyphens → em-dashes where appropriate
- ✅ **Spacing**: Fixed around punctuation
- ✅ **Encoding**: UTF-8 normalization, mojibake fixes

## Testing

```bash
pytest                    # Run all 218 tests
pytest tests/test_chapter_detection.py -v  # Specific test file
```

## Recent Updates

**2026-03-11**:
- Added **Table of Contents parsing** for chapter detection:
  - Finds "Оглавление"/"Содержание" sections automatically
  - Extracts chapter titles from TOC entries (e.g., "1. Title ... 5")
  - Matches TOC titles against book text (handles embedded headings)
  - **Smart paragraph splitting**: When heading is found within a multi-line paragraph, splits it at the heading line to preserve context (no mid-sentence cuts)
  - Falls back to TOC when pattern matching finds ≤2 chapters
- Added "Часть" pattern for chapter detection (e.g., "Часть I", "Часть III")
- Automatic removal of repeated PDF headers/footers (pattern matching with numbers)
- Empty chapter filtering now works across all formats (not just FB2)
- Output folders now auto-create as `{bookname}_{format}/`
- All 218 E2E tests passing ✅
