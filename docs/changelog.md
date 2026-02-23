# Changelog

All notable changes should be documented in this file.

## Unreleased

### Added
- Root Makefile release orchestration (`set-version`, `metadata`, `push`, `release`, `git-tag`) for a safer and repeatable release flow.
- Strict version monotonic guard: `make set-version` now rejects same/lower versions.
- Release metadata generation flow through `make metadata`.
- Regression tests for Makefile wiring, release metadata generation, and README/docs expectations.

### Changed
- Root `README.md` is now a production-style landing page with quick start plus docs map.
- Main documentation moved into topic-based files under `docs/`.

### Notes
- Release execution remains optional and should be run only when preparing tags.

Next: [Back To Overview](./overview.md)
