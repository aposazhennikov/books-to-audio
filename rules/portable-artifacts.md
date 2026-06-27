# Portable Artifacts

- Artifacts must remain portable across machines and project directories.
- Manifests, audio paths, reports, cache references, support bundles, and output directories must not depend on a developer's absolute path or current working directory.
- Prefer paths relative to the project, manifest, or configured output root.
- When reading older artifacts with absolute paths, preserve compatibility while writing new portable references.
- Tests for manifests and reports should cover relocation when the behavior depends on paths.
