# Changelog

All notable changes should be documented in this file.

## Unreleased

### Added
- GitHub Pages docs site workflow (`.github/workflows/pages.yml`) with MkDocs build/deploy.
- New docs landing page (`docs/index.md`) and downloads page (`docs/downloads.md`) with latest-release links.
- Regression tests for docs-site workflow wiring and docs navigation.
- Workspace-scoped Jupyter runtime engine (`jupyter-client` + `ipykernel`) with one persistent kernel per workspace.
- Runtime kernel control endpoints:
  - `GET /api/v1/workspaces/{workspace_id}/kernel/status`
  - `POST /api/v1/workspaces/{workspace_id}/kernel/reset`
- Targeted regression coverage for Jupyter message parsing, runner environment bootstrap, kernel lifecycle, dataset lock conflicts, and idempotent ingest behavior.

### Changed
- Release workflow now gates tag releases on an already-successful `ci.yml` run for the same commit SHA.
- Wheel publishing flow now creates a draft release if missing before uploading wheel artifacts.
- Backend package metadata improved for PyPI (real description + package README for long description).
- Tauri desktop metadata and assets refreshed:
  - Bundle identifier updated to `com.inquira.desktop`
  - Platform icons regenerated from `backend/app/logo/inquira_logo.svg`
  - Cross-runner frontend prebuild command hardened for desktop builds
- Documentation install guidance now uses `pip install inquira-ce` and release download links (removed curl/PowerShell script-install instructions).
- Execution provider defaults now use `local_jupyter` and runner bootstrap installs kernel/runtime packages in runner venv (safe-py-runner removed from runtime path).
- Workspace notebook marker format standardized to `# cell: <title>` with backward parsing support for legacy numbered markers.
- Workspace kernel DuckDB connection now opens in read-only mode to reduce lock contention with dataset ingestion flows.
- Dataset ingestion now skips re-ingest when source file size and mtime are unchanged, and returns `409` with actionable guidance on lock conflicts.

### Notes
- Release execution remains tag-driven (`v*`) and currently creates draft prereleases for manual publish.

Next: [Back To Overview](./overview.md)
