# Contributing to Inquira CE

Thanks for contributing.

## Development Flow

1. Branch from `master`.
2. Make focused changes.
3. Run local checks (backend + frontend).
4. Open PR.
5. Merge only after CI is green.

## Local Checks

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

## Version Bumps

Do not bump version for every commit.

Bump only when preparing a release/tag:

```bash
uv run python scripts/maintenance/bump_versions.py --version 0.5.0a2 --write-version-file
```

## CI/Release Behavior

- CI (`.github/workflows/ci.yml`) runs on pushes to `master`.
- Release (`.github/workflows/release.yml`) runs on tag pushes `v*`.
- Release workflow enforces that tag commit must be on `master`.

## Commit Hygiene

- Keep commit messages clear and scoped.
- Keep `commit_message` root file updated as required by repo conventions.
