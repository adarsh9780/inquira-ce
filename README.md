# Inquira CE

Local-first desktop data analysis with AI-assisted Python generation and execution.

Current release line: `0.5.0a1` (alpha).

## What This Repo Contains

- `src-tauri/`: Desktop shell (Tauri/Rust) and app packaging.
- `backend/`: FastAPI backend, agent/runtime services, and tests.
- `frontend/`: Vue frontend used by the desktop app.
- `scripts/`: install and maintenance scripts.

## Install (End Users)

### Option A: Install CLI shim (recommended)

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

The installer uses release wheel URLs published under GitHub Releases.

## Build/Run From Source (Contributors)

Prerequisites:

- `uv`
- Node.js 20+
- Rust stable toolchain

Run desktop app in development:

```bash
git clone https://github.com/adarsh9780/inquira-ce.git
cd inquira-ce
cargo tauri dev --manifest-path src-tauri/Cargo.toml
```

## Local CI Commands (Same Intent As GitHub CI)

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
npm test -- --run
npm run build
```

## Versioning

Versioning is centralized:

- `VERSION` is the source of truth (PEP 440 style, e.g. `0.5.0a1`).
- Use:
```bash
uv run python scripts/maintenance/bump_versions.py --help
```

This updates backend, tauri, frontend, and installer wheel URLs consistently.

## CI and Release Automation

- CI workflow: `.github/workflows/ci.yml`
  - Runs on push to `master`.
- Release workflow: `.github/workflows/release.yml`
  - Runs on pushed tags matching `v*`.
  - Guard step fails if the tag commit is not on `master`.
  - Builds desktop artifacts (macOS/Windows) and backend wheel, then attaches to release.

## Notes For Alpha Releases

- `0.5.x` is alpha track. Expect iterative changes.
- Desktop artifacts from CI are unsigned by default.
- For production-grade distribution, add signing/notarization secrets and steps.

## Contributing

Please read `CONTRIBUTING.md` before opening a PR.

## License

MIT (see `LICENSE`).
