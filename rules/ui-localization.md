# UI Localization

- Apply every UI text or layout change consistently across all supported locales.
- When adding, renaming, or removing user-facing UI text, update every locale catalog in the same change.
- Check UI files, locale catalogs, tests, and documentation touched by the change for broken or mojibake characters.
- Treat garbled text, replacement characters, and mixed encodings as defects to fix before finishing the change.
- Treat broken localized strings, mismatched placeholders, and misleading translations as product bugs.
- Verify that localized button labels preserve the user's decision meaning in every supported locale.
