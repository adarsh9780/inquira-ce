# Inquira CE

<p align="center">
  <img src="./backend/app/logo/inquira_logo.svg" alt="Inquira CE Logo" width="180" />
</p>

<p align="center">
  <a href="https://github.com/adarsh9780/inquira-ce/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/adarsh9780/inquira-ce/ci.yml?branch=master&label=CI" alt="CI Status"></a>
  <a href="https://github.com/adarsh9780/inquira-ce/releases"><img src="https://img.shields.io/github/v/tag/adarsh9780/inquira-ce?label=release" alt="Latest Release Tag"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-SUL-blue.svg" alt="License SUL"></a>
  <img src="https://img.shields.io/badge/python-3.12%2B-blue.svg" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/stage-alpha-orange.svg" alt="Alpha">
</p>

Local-first desktop data analysis with AI-assisted Python generation and execution.

Tags: `desktop`, `local-first`, `fastapi`, `vue`, `tauri`, `duckdb`, `langgraph`, `gemini`.

Hosted docs site (GitHub Pages): [https://adarsh9780.github.io/inquira-ce/](https://adarsh9780.github.io/inquira-ce/)

## Why Inquira

- Keep data local while using AI-assisted analysis workflows.
- Turn natural language requests into reproducible Python/data operations.
- Package the app as a desktop experience with backend + frontend + Tauri shell.

## What's New (Since v0.5.7a10)

- Kept the chat composer available in both chat and code views, so follow-up questions no longer require tab switching.
- Moved slash commands, dataset ingestion, schema reads, and artifact access onto the active workspace kernel to avoid competing DuckDB connections.
- Improved recovery from workspace lock conflicts and kernel restarts during dataset uploads and table browsing.
- Smoothed table browsing with cached dataframe pages, lighter pagination updates, and better compact-toolbar behavior on tablet widths.
- Fixed several right-pane UX issues, including centered figure errors, cleaner export controls, and schema editor table selection from live workspace data.

## Upcoming Changes

*   **Supabase Auth**: Migrate to Supabase for robust authentication and align the auth page styling with the main UI.
*   **Proxy Infrastructure**: Launch `inquira-infra` as a private gateway using a LiteLLM proxy for secure key management and token analytics.
*   **Workspace Layout**: Allow independent toggling of the left and right panels, while retaining their dual-view capability.
*   **Secure Execution**: Sandbox code execution at the OS or Tauri app level.
*   **State Persistence**: Store generated workflows persistently by mapping one workspace to one Python script.
*   **Multi-Table Querying**: Drop the single-dataset constraint so agents can seamlessly query across multiple data sources in a single workspace.
*   **Performance Optimization**: Stream large images as base64 instead of interactive payloads when size crosses a threshold.
*   **Artifact Caching**: Smooth out table navigation (e.g., jumping between df1 and df2) by caching offsets and limits across artifact switches.
*   **Data Sources**: Add native support for loading DuckDB database files.
*   **Grid Options**: Restore active functionality for AG Grid sorting and filtering.

## Quick Start

### End Users

Desktop binaries (`.dmg`, `.exe`) are available on:
[https://github.com/adarsh9780/inquira-ce/releases/latest](https://github.com/adarsh9780/inquira-ce/releases/latest)

### Contributors (Run From Source)

```bash
git clone https://github.com/adarsh9780/inquira-ce.git
cd inquira-ce
cd src-tauri
cargo tauri dev
```

Before running `make git-commit`, create a local root `commit_message.txt` file and write your commit message in it.
Keep this file updated for each commit so team commit flow remains consistent.

## Common Commands

Atomic commit flow:
```bash
printf "feat(scope): your message\n\nDetails..." > commit_message.txt
make check-version
make ruff-test
make mypy-test
make test
make git-add
make git-commit
make git-push
```

Developer-friendly rich output (wrapped + spaced) for local runs:
```bash
make check-version-pretty
make ruff-test-pretty
make mypy-test-pretty
make test-pretty
```

Optional release flow:
```bash
make set-version X.Y.ZaN
make ruff-test
make mypy-test
make test
make git-add
make git-commit
make git-push
make git-tag
```

`make set-version` now refreshes `.github/release/metadata.json` from `release_metadata.md` when that source file exists.
Run `make metadata` separately only if you edit `release_metadata.md` again after bumping the version.

## Documentation Map

Core docs:

1. [Overview](./docs/overview.md)
2. [Install](./docs/install.md)
3. [Development](./docs/development.md)
4. [Commit And Release Flow](./docs/commit-and-release.md)
5. [CI And Release Automation](./docs/ci-and-release-automation.md)
6. [Architecture](./docs/architecture.md)
7. [Roadmap](./docs/roadmap.md)
8. [Contributing](./docs/contributing.md)
9. [Changelog](./docs/changelog.md)

Additional references:

- [Release Process (Detailed)](./docs/release_process.md)
- [Workflow Diagram](./docs/workflow_diagram.md)
- [Data Pipeline Diagram](./docs/data_pipeline_diagram.md)
- [Future Plans (Raw)](./docs/plans_for_future.md)

## License

Sustainable Use License 1.0 (see `LICENSE`). Free for personal, academic, and internal business use. Commercial exploitation or managed service distribution is prohibited without a commercial license.
