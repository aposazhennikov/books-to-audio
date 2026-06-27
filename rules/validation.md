# Validation

For code changes, run the narrowest useful checks first:

```bash
python -m ruff check .
python -m pytest
```

For runtime or installation changes, also run:

```bash
normalize-book doctor --skip-network
```
