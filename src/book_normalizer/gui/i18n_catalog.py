"""Base GUI translation catalog assembled from focused modules."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass

from book_normalizer.gui.i18n_catalogs.app_auto import APP_AUTO_TRANSLATIONS
from book_normalizer.gui.i18n_catalogs.assembly import ASSEMBLY_TRANSLATIONS
from book_normalizer.gui.i18n_catalogs.misc import MISC_TRANSLATIONS
from book_normalizer.gui.i18n_catalogs.normalize import NORMALIZE_TRANSLATIONS
from book_normalizer.gui.i18n_catalogs.roles import ROLES_TRANSLATIONS
from book_normalizer.gui.i18n_catalogs.synthesis import SYNTHESIS_TRANSLATIONS
from book_normalizer.gui.i18n_catalogs.synthesis_runtime import SYNTHESIS_RUNTIME_TRANSLATIONS
from book_normalizer.gui.i18n_catalogs.voice import VOICE_TRANSLATIONS

TranslationCatalog = Mapping[str, Mapping[str, str]]
MutableTranslationCatalog = MutableMapping[str, MutableMapping[str, str]]
TranslationSource = tuple[str, TranslationCatalog]
TranslationOverride = tuple[str, str]
TranslationProvenance = MutableMapping[TranslationOverride, str]


@dataclass(frozen=True)
class TranslationDuplicate:
    """Duplicate locale write with enough context to audit the source."""

    key: str
    locale: str
    original_source: str
    new_source: str
    original_text: str
    new_text: str


@dataclass(frozen=True)
class TranslationMergeReport:
    """Auditable summary of explicit translation overwrites."""

    overrides: tuple[TranslationDuplicate, ...] = ()


class TranslationDuplicateError(RuntimeError):
    """Raised when a translation key/locale is written twice unintentionally."""

    def __init__(self, duplicates: list[TranslationDuplicate]) -> None:
        self.duplicates = tuple(duplicates)
        details = "; ".join(
            f"{duplicate.key}:{duplicate.locale} "
            f"from {duplicate.original_source} overwritten by {duplicate.new_source}"
            for duplicate in duplicates
        )
        super().__init__(f"Duplicate translation entries: {details}")


def _copy_catalog_entry(entry: Mapping[str, str]) -> dict[str, str]:
    return {locale: text for locale, text in entry.items()}


def enrich_translation_catalog(
    catalog: MutableTranslationCatalog,
    updates: TranslationCatalog,
    *,
    source: str,
    allow_overrides: set[TranslationOverride] | frozenset[TranslationOverride] = frozenset(),
    provenance: TranslationProvenance | None = None,
) -> TranslationMergeReport:
    """Merge locale updates, rejecting unallowlisted duplicate key/locale writes."""
    provenance = provenance if provenance is not None else {}
    duplicates: list[TranslationDuplicate] = []
    overrides: list[TranslationDuplicate] = []

    for key, entry in updates.items():
        target_entry = catalog.setdefault(key, {})
        for locale, text in entry.items():
            source_key = (key, locale)
            if locale in target_entry:
                duplicate = TranslationDuplicate(
                    key=key,
                    locale=locale,
                    original_source=provenance.get(source_key, "<existing catalog>"),
                    new_source=source,
                    original_text=target_entry[locale],
                    new_text=text,
                )
                if source_key not in allow_overrides:
                    duplicates.append(duplicate)
                    continue
                overrides.append(duplicate)
            target_entry[locale] = text
            provenance[source_key] = source

    if duplicates:
        raise TranslationDuplicateError(duplicates)
    return TranslationMergeReport(overrides=tuple(overrides))


def merge_translation_catalogs(
    sources: list[TranslationSource] | tuple[TranslationSource, ...],
    *,
    allow_overrides: set[TranslationOverride] | frozenset[TranslationOverride] = frozenset(),
) -> tuple[dict[str, dict[str, str]], TranslationMergeReport]:
    """Build a catalog from named sources with duplicate writes made explicit."""
    catalog: dict[str, dict[str, str]] = {}
    provenance: dict[TranslationOverride, str] = {}
    overrides: list[TranslationDuplicate] = []

    for source, source_catalog in sources:
        report = enrich_translation_catalog(
            catalog,
            {key: _copy_catalog_entry(entry) for key, entry in source_catalog.items()},
            source=source,
            allow_overrides=allow_overrides,
            provenance=provenance,
        )
        overrides.extend(report.overrides)

    return catalog, TranslationMergeReport(overrides=tuple(overrides))


TRANSLATIONS, TRANSLATION_CATALOG_REPORT = merge_translation_catalogs(
    (
        ("app_auto", APP_AUTO_TRANSLATIONS),
        ("normalize", NORMALIZE_TRANSLATIONS),
        ("roles", ROLES_TRANSLATIONS),
        ("voice", VOICE_TRANSLATIONS),
        ("synthesis", SYNTHESIS_TRANSLATIONS),
        ("synthesis_runtime", SYNTHESIS_RUNTIME_TRANSLATIONS),
        ("assembly", ASSEMBLY_TRANSLATIONS),
        ("misc", MISC_TRANSLATIONS),
    )
)
