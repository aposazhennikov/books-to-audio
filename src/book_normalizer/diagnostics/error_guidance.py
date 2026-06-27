"""User-facing remediation hints for common local runtime failures."""

from __future__ import annotations


def error_action(message: str) -> str:
    """Return a concrete next action for a GUI/CLI error string."""
    text = (message or "").lower()
    if "comfyui" in text and ("not reachable" in text or "connection" in text):
        return "Запусти `normalize-book doctor`, затем перезапусти ComfyUI и повтори failed-only retry."
    if "workflow" in text:
        return "Выбери корректный ComfyUI workflow JSON или запусти `normalize-book doctor`."
    if "model" in text and ("missing" in text or "not found" in text):
        return "Скачай модель через `normalize-book install-tts-models` или выбери другой models dir."
    if "cuda" in text or "vram" in text or "out of memory" in text:
        return "Освободи VRAM, уменьши batch size или выбери CPU/другой CUDA профиль."
    if "manifest" in text:
        return "Проверь chunks_manifest_v2.json и при необходимости перегенерируй сегменты."
    return "Запусти `normalize-book doctor --skip-network`; если проверка зеленая, повтори этап с resume/failed-only."


def format_error_with_action(message: str) -> str:
    """Append a short remediation action to a low-level error."""
    action = error_action(message)
    return f"{message}\nДействие: {action}"
