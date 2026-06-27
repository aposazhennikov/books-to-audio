# Changelog

All notable changes to Books to Audio are tracked here.

The project follows semantic versioning. Release notes should summarize user
visible changes, compatibility notes, and known limitations for each tag.

## Unreleased

- Added a release builder that requires the final readiness gate, including the
  mandatory human listen-through verdict, before producing wheel and source
  artifacts.
- Added a Windows portable desktop bundle workflow with separate GUI and CLI
  executables plus local-only `models/`, `data/`, and `output/` folders.
