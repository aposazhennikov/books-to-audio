from __future__ import annotations

import pytest

from book_normalizer.gui.i18n_catalog import (
    TranslationDuplicateError,
    enrich_translation_catalog,
    merge_translation_catalogs,
)


def test_merge_translation_catalogs_rejects_accidental_duplicate_locale() -> None:
    with pytest.raises(TranslationDuplicateError) as exc_info:
        merge_translation_catalogs(
            (
                ("base", {"app.title": {"en": "Books to Audio"}}),
                ("feature", {"app.title": {"en": "Book Audio"}}),
            )
        )

    duplicate = exc_info.value.duplicates[0]
    assert duplicate.key == "app.title"
    assert duplicate.locale == "en"
    assert duplicate.original_source == "base"
    assert duplicate.new_source == "feature"
    assert "app.title:en from base overwritten by feature" in str(exc_info.value)


def test_merge_translation_catalogs_reports_explicit_overrides() -> None:
    catalog, report = merge_translation_catalogs(
        (
            ("base", {"app.title": {"en": "Books to Audio", "ru": "Base"}}),
            ("polished", {"app.title": {"en": "Book Normalizer"}}),
        ),
        allow_overrides={("app.title", "en")},
    )

    assert catalog["app.title"] == {"en": "Book Normalizer", "ru": "Base"}
    assert len(report.overrides) == 1
    override = report.overrides[0]
    assert override.key == "app.title"
    assert override.locale == "en"
    assert override.original_text == "Books to Audio"
    assert override.new_text == "Book Normalizer"
    assert override.original_source == "base"
    assert override.new_source == "polished"


def test_enrich_translation_catalog_allows_new_locale_without_override() -> None:
    catalog = {"app.title": {"en": "Books to Audio"}}
    report = enrich_translation_catalog(
        catalog,
        {"app.title": {"uz": "Kitoblarni audioga"}},
        source="i18n_extra.uz",
    )

    assert catalog["app.title"]["uz"] == "Kitoblarni audioga"
    assert report.overrides == ()


def test_enrich_translation_catalog_rejects_same_text_duplicate_without_allowlist() -> None:
    catalog = {"app.title": {"en": "Books to Audio"}}

    with pytest.raises(TranslationDuplicateError) as exc_info:
        enrich_translation_catalog(
            catalog,
            {"app.title": {"en": "Books to Audio"}},
            source="duplicate",
        )

    duplicate = exc_info.value.duplicates[0]
    assert duplicate.original_text == duplicate.new_text == "Books to Audio"
    assert duplicate.original_source == "<existing catalog>"


def test_runtime_i18n_overrides_are_reported_with_provenance() -> None:
    from book_normalizer.gui.i18n import TRANSLATION_RUNTIME_REPORTS

    overrides = [
        override
        for report in TRANSLATION_RUNTIME_REPORTS
        for override in report.overrides
    ]

    assert overrides
    assert all(override.key and override.locale for override in overrides)
    assert all(override.original_source for override in overrides)
    assert all(override.new_source.startswith("i18n") for override in overrides)
