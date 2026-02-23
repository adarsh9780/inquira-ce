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
cargo tauri dev --manifest-path src-tauri/Cargo.toml
```

This command runs the desktop shell and wires frontend/backend development pieces together.

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
- If you touch release tooling, verify docs and workflow tests in `backend/tests/`.

Next: [Commit And Release Flow](./commit-and-release.md)
