# Book Normalizer

Semi-automatic Russian book source normalizer for TTS pipelines.

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

```bash
normalize-book process input.txt --out ./output
normalize-book process input.pdf --out ./output --verbose
normalize-book batch ./books --out ./normalized
normalize-book info input.txt
```

## Testing

```bash
pytest
```
