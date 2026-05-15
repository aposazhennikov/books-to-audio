"""Tests for peyo-backed ё restoration."""

from __future__ import annotations

from book_normalizer.normalization.yoficator import collect_yo_suggestions, yoficate_text


def test_peyo_safe_restores_unambiguous_words() -> None:
    result = yoficate_text("Ежик и елка стояли у березы.")

    assert "Ёжик" in result
    assert "ёлка" in result
    assert "берёзы" in result


def test_safe_mode_does_not_global_replace_all_vse() -> None:
    assert yoficate_text("Все люди пришли.") == "Все люди пришли."


def test_contextual_vse_rule_handles_impersonal_context() -> None:
    assert yoficate_text("Все было тихо.") == "Всё было тихо."


def test_collects_not_safe_yo_suggestions_for_review() -> None:
    suggestions = collect_yo_suggestions("На этом все.")

    assert any(s.before == "все" and s.after == "всё" for s in suggestions)

