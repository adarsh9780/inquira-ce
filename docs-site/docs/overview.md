# Overview

Inquira CE is a local-first desktop app for AI-assisted data analysis.

In plain terms: you ask a question about data in natural language, and Inquira helps generate and run analysis workflows while keeping your data and runtime under your control.

## Current product highlights

- Real-time chat streaming with clearer final response presentation and tool-by-tool operational progress updates.
- Unified workspace interface with collapsible navigation and dual resizable panes.
- Built-in terminal support with persistent sessions for workspace-focused development.
- Workspace-kernel-backed execution, so generated Python runs in the same environment used for schema reads, artifacts, and chart dependencies.
- Stronger artifact and runtime reliability, including DuckDB lock recovery, stable table/figure restoration, and safer chart naming in persistent kernel sessions.

Version source of truth: root `VERSION` file.

## Who this is for

- Users who want a local AI-assisted analytics workflow.
- Teams that want transparent release artifacts (`.whl`, `.dmg`, `.exe`) and auditable CI/release automation.
- Contributors who prefer explicit tooling and reproducible workflows.

## Repository Layout

- `src-tauri/`: Desktop shell (Tauri/Rust) and app packaging.
- `backend/`: FastAPI backend, agent/runtime services, and tests.
- `frontend/`: Vue frontend used by the desktop app.
- `agents/`: LangGraph agent graphs, tool routing, tracing hooks, and tool execution contracts.
- `scripts/`: maintenance scripts used by Makefile and release workflow.
- `docs-site/`: Docusaurus website project for public docs, landing pages, and downloads.

## Distribution channels

- Desktop installers distributed via GitHub Releases
- Desktop binaries: GitHub Releases (`.dmg`, `.exe`)
- Documentation site: GitHub Pages

Next: [Install](./install.md)
