"""Load named LLM prompts from packaged text files."""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import files


@lru_cache(maxsize=128)
def load_prompt(relative_path: str) -> str:
    """Return a prompt template from ``book_normalizer/prompts``."""

    clean_path = relative_path.replace("\\", "/").strip("/")
    if not clean_path or ".." in clean_path.split("/"):
        raise ValueError(f"Unsafe prompt path: {relative_path!r}")
    prompt_path = files("book_normalizer.prompts").joinpath(clean_path)
    return prompt_path.read_text(encoding="utf-8").strip()


def load_language_prompt(stage: str, name: str, language: str, *, fallback_language: str = "ru") -> str:
    """Load ``stage/name_language.txt``, falling back to Russian."""

    code = (language or fallback_language).strip().lower()
    try:
        return load_prompt(f"{stage}/{name}_{code}.txt")
    except FileNotFoundError:
        return load_prompt(f"{stage}/{name}_{fallback_language}.txt")

