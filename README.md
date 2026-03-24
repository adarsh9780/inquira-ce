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

## Why Inquira Community Edition (CE)

- **Absolute Privacy**: Keep massive datasets entirely local on your machine.
- **Unlimited Workspaces**: 100% Free with zero cloud lock-in.
- **Reproducible Analysis**: Turn natural language requests into reproducible Python/data operations.
- **BYOK (Bring Your Own Key)**: Native support for OpenAI, Anthropic, OpenRouter, or local Ollama networks.

## Current Product Highlights

- **Embedded DuckDB Engine**: Drag and drop CSVs, Parquet, or Excel files for instant high-speed relational tables.
- **Unified Workspace UI**: Dual resizable panes combining data visualization, Chat, and code execution.
- **Persistent Local Sandboxes**: Workspaces physically retain their database state across app closures—no re-uploads required.
- **Real-time Agent Workflow**: Watch the LangGraph planner logically trace, test, and correct its own Python/SQL code locally.

## Quick Start

### End Users

Download and start right away:
- Website and docs: [https://docs.inquiraai.com/](https://docs.inquiraai.com/)
- Direct download: [https://docs.inquiraai.com/download](https://docs.inquiraai.com/download)
- Latest GitHub release: [https://github.com/adarsh9780/inquira-ce/releases/latest](https://github.com/adarsh9780/inquira-ce/releases/latest)

### Contributors (Run From Source)

```bash
git clone https://github.com/adarsh9780/inquira-ce.git
cd inquira-ce
cd src-tauri
cargo tauri dev
```

Before running `make git-commit`, create a local root `commit_message.txt` file and write your commit message in it. Check the Developer Documentation for full Makefile rules.

## Official Documentation Map

1. [Welcome & Editions](./docs-site/docs/index.md)
2. [Getting Data In](./docs-site/docs/getting_data_in.md)
3. [Workspace Management](./docs-site/docs/workspace_management.md)
4. [System Architecture](./docs-site/docs/architecture.md)
5. [Local Development Guide](./docs-site/docs/development.md)
6. [Future Roadmap](./docs-site/docs/roadmap.md)

## License

Sustainable Use License 1.0 (see `LICENSE`). Free for personal, academic, and internal business use. Commercial exploitation or managed service distribution is prohibited without a commercial license.
