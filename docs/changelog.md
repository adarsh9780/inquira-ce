# Changelog

All notable changes should be documented in this file.

## Unreleased

### Added
- GitHub Pages docs site workflow (`.github/workflows/pages.yml`) with MkDocs build/deploy.
- New docs landing page (`docs/index.md`) and downloads page (`docs/downloads.md`) with latest-release links.
- Regression tests for docs-site workflow wiring and docs navigation.

### Changed
- Release workflow now gates tag releases on an already-successful `ci.yml` run for the same commit SHA.
- Wheel publishing flow now creates a draft release if missing before uploading wheel artifacts.
- Backend package metadata improved for PyPI (real description + package README for long description).
- Tauri desktop metadata and assets refreshed:
  - Bundle identifier updated to `com.inquira.desktop`
  - Platform icons regenerated from `backend/app/logo/inquira_logo.svg`
  - Cross-runner frontend prebuild command hardened for desktop builds
- Documentation install guidance now uses `pip install inquira-ce` and release download links (removed curl/PowerShell script-install instructions).

### Notes
- Release execution remains tag-driven (`v*`) and currently creates draft prereleases for manual publish.

Next: [Back To Overview](./overview.md)
