"""Base GUI translation catalog assembled from focused modules."""

from __future__ import annotations

from book_normalizer.gui.i18n_catalogs.app_auto import APP_AUTO_TRANSLATIONS
from book_normalizer.gui.i18n_catalogs.assembly import ASSEMBLY_TRANSLATIONS
from book_normalizer.gui.i18n_catalogs.misc import MISC_TRANSLATIONS
from book_normalizer.gui.i18n_catalogs.normalize import NORMALIZE_TRANSLATIONS
from book_normalizer.gui.i18n_catalogs.roles import ROLES_TRANSLATIONS
from book_normalizer.gui.i18n_catalogs.synthesis import SYNTHESIS_TRANSLATIONS
from book_normalizer.gui.i18n_catalogs.synthesis_runtime import SYNTHESIS_RUNTIME_TRANSLATIONS
from book_normalizer.gui.i18n_catalogs.voice import VOICE_TRANSLATIONS

TRANSLATIONS: dict[str, dict[str, str]] = {}
TRANSLATIONS.update(APP_AUTO_TRANSLATIONS)
TRANSLATIONS.update(NORMALIZE_TRANSLATIONS)
TRANSLATIONS.update(ROLES_TRANSLATIONS)
TRANSLATIONS.update(VOICE_TRANSLATIONS)
TRANSLATIONS.update(SYNTHESIS_TRANSLATIONS)
TRANSLATIONS.update(SYNTHESIS_RUNTIME_TRANSLATIONS)
TRANSLATIONS.update(ASSEMBLY_TRANSLATIONS)
TRANSLATIONS.update(MISC_TRANSLATIONS)
