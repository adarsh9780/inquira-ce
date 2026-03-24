# Development

This page describes the local development workflow used by the project.

## Prerequisites

- Python 3.12+
- `uv`
- Node.js 20+
- Rust stable toolchain

## Run Desktop App In Development

```bash
git clone https://github.com/adarsh9780/inquira-ce.git
cd inquira-ce
cd src-tauri
cargo tauri dev
```

This command runs the desktop shell and wires frontend, backend, workspace-kernel, and agent development pieces together.

## Current runtime model

- The desktop app starts the FastAPI backend and connects chat requests to `agent_v2`.
- `agent_v2` uses structured tool planning and custom tool execution instead of generic `ToolNode` execution.
- Generated Python is executed through the active backend workspace kernel, not inside the agent process.
- Long-lived kernel sessions mean generated figure variable names should stay meaningful and stable to avoid overwriting prior chart objects.

## Local CI Commands

Backend:
```bash
cd backend
uv sync --group dev
uv run --group dev ruff check app/v1 tests
uv run --group dev mypy --config-file mypy.ini app/v1
uv run alembic upgrade head
uv run pytest tests -q
```

Frontend:
```bash
cd frontend
npm ci
npm test
npm run build
```

Shortcut from repo root:
```bash
make test
```

## Practical guidance

- Run `make test` before committing.
- Keep backend and frontend changes in focused commits when possible.
- If you touch agent execution flow, verify both the LangGraph graph path and the backend workspace-kernel runtime path.
- If you touch release tooling, verify docs and workflow tests in `backend/tests/`.

## Repository Layout

- `src-tauri/`: Desktop shell (Tauri/Rust) and app packaging.
- `backend/`: FastAPI backend, agent/runtime services, and tests.
- `frontend/`: Vue frontend used by the desktop app.
- `agents/`: LangGraph agent graphs, tool routing, tracing hooks, and tool execution contracts.
- `scripts/`: maintenance scripts used by Makefile and release workflow.
- `docs-site/`: Docusaurus website project for public docs, landing pages, and downloads.

