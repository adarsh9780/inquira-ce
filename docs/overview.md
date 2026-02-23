# Overview

Inquira CE is a local-first desktop app for AI-assisted data analysis.

In plain terms: you ask a question about data in natural language, and Inquira helps generate and run analysis workflows while keeping your data and runtime under your control.

Version source of truth: root `VERSION` file.

## Who this is for

- Users who want a local AI-assisted analytics workflow.
- Teams that want transparent release artifacts (`.whl`, `.dmg`, `.exe`) and auditable CI/release automation.
- Contributors who prefer explicit tooling and reproducible workflows.

## Repository Layout

- `src-tauri/`: Desktop shell (Tauri/Rust) and app packaging.
- `backend/`: FastAPI backend, agent/runtime services, and tests.
- `frontend/`: Vue frontend used by the desktop app.
- `scripts/`: maintenance scripts used by Makefile and release workflow.
- `docs/`: project documentation, diagrams, and release/process guides.

## Distribution channels

- Python package: `pip install inquira-ce`
- Desktop binaries: GitHub Releases (`.dmg`, `.exe`)
- Documentation site: GitHub Pages

Next: [Install](./install.md)
