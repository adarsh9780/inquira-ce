# Inquira CE

<p align="center">
  <img src="./backend/app/logo/inquira_logo.svg" alt="Inquira CE Logo" width="180" />
</p>

<p align="center">
  <a href="https://github.com/adarsh9780/inquira-ce/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/adarsh9780/inquira-ce/ci.yml?branch=master&label=CI" alt="CI Status"></a>
  <a href="https://github.com/adarsh9780/inquira-ce/releases"><img src="https://img.shields.io/github/v/release/adarsh9780/inquira-ce?display_name=tag" alt="Latest Release"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License MIT"></a>
  <img src="https://img.shields.io/badge/python-3.12%2B-blue.svg" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/stage-alpha-orange.svg" alt="Alpha">
</p>

Local-first desktop data analysis with AI-assisted Python generation and execution.

Tags: `desktop`, `local-first`, `fastapi`, `vue`, `tauri`, `duckdb`, `langgraph`, `gemini`.

## Why Inquira

- Keep data local while using AI-assisted analysis workflows.
- Turn natural language requests into reproducible Python/data operations.
- Package the app as a desktop experience with backend + frontend + Tauri shell.

## Quick Start

### End Users (Installer)

macOS/Linux:
```bash
curl -fsSL https://raw.githubusercontent.com/adarsh9780/inquira-ce/master/scripts/install-inquira.sh | bash
inquira
```

Windows (PowerShell):
```powershell
irm https://raw.githubusercontent.com/adarsh9780/inquira-ce/master/scripts/install-inquira.ps1 | iex
inquira
```

### Contributors (Run From Source)

```bash
git clone https://github.com/adarsh9780/inquira-ce.git
cd inquira-ce
cargo tauri dev --manifest-path src-tauri/Cargo.toml
```

## Common Commands

Atomic commit flow:
```bash
make check-version
make test
make git-add
make git-commit
make git-push
```

Optional release flow:
```bash
make set-version 0.5.0a7
make metadata
make test
make git-add
make git-commit
make git-push
make git-tag
```

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

MIT (see `LICENSE`).
