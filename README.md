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

Hosted docs site (GitHub Pages): [https://docs.inquiraai.com/](https://docs.inquiraai.com/)

## Why Inquira

- Keep data local while using AI-assisted analysis workflows.
- Turn natural language requests into reproducible Python/data operations.
- Package the app as a desktop experience with backend + frontend + Tauri shell.

## Current Product Highlights

- Local-first desktop workflow for AI-assisted data analysis.
- Real-time chat streaming with clearer final responses and tool-by-tool progress updates.
- Unified workspace UI with collapsible navigation and dual resizable panes.
- Persistent built-in terminal for workspace-focused development and debugging.
- Workspace-kernel-backed execution so generated Python runs in the same environment used for schema reads, artifacts, and charts.
- Better runtime reliability, including DuckDB lock recovery, artifact restoration, and safer chart naming in long-lived sessions.
- Public documentation, pricing, and download site served from [docs.inquiraai.com](https://docs.inquiraai.com/).

## Current Focus

- Secure execution hardening at the OS or Tauri app level.
- Better workspace layout control, including independent panel toggles and narrow-window behavior.
- Multi-dataset and multi-table analysis flows inside a single workspace.
- Stronger artifact and table behavior, especially sorting, filtering, and cross-artifact navigation.
- Workspace-level persistence for generated code and analysis state.
- First-class DuckDB file support.

## Quick Start

### End Users

Start here:

- Website and docs: [https://docs.inquiraai.com/](https://docs.inquiraai.com/)
- Direct download page: [https://docs.inquiraai.com/download](https://docs.inquiraai.com/download)
- Latest GitHub release: [https://github.com/adarsh9780/inquira-ce/releases/latest](https://github.com/adarsh9780/inquira-ce/releases/latest)

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

1. [Overview](./docs-site/docs/overview.md)
2. [Install](./docs-site/docs/install.md)
3. [Development](./docs-site/docs/development.md)
4. [Commit And Release Flow](./docs-site/docs/commit-and-release.md)
5. [CI And Release Automation](./docs-site/docs/ci-and-release-automation.md)
6. [Architecture](./docs-site/docs/architecture.md)
7. [Roadmap](./docs-site/docs/roadmap.md)
8. [Contributing](./docs-site/docs/contributing.md)
9. [Changelog](./docs-site/docs/changelog.md)

Additional references:

- [Release Process (Detailed)](./docs-site/docs/release_process.md)
- [Workflow Diagram](./docs-site/docs/workflow_diagram.md)
- [Data Pipeline Diagram](./docs-site/docs/data_pipeline_diagram.md)
- [Future Plans (Raw)](./docs-site/docs/plans_for_future.md)

## License

Sustainable Use License 1.0 (see `LICENSE`). Free for personal, academic, and internal business use. Commercial exploitation or managed service distribution is prohibited without a commercial license.
