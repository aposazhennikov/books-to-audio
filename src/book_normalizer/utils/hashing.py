"""Hashing utilities for content fingerprinting."""

from __future__ import annotations

import hashlib


def text_hash(text: str) -> str:
    """Return a short SHA-256 hex digest of the given text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
