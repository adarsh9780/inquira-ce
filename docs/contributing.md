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
npm test
npm run build
```

## Updating Version

Do not bump version for every commit.

Bump only when preparing a release/tag:

```bash
make set-version 0.5.0a7
```

This enforces that the new version is greater than current `VERSION`.
Use PEP 440 input (`0.5.0a7`). Tag style (`v0.5.0a7`) is normalized automatically.

## Updating Release Metadata

1. Create or edit `release_metadata.md` in repo root (this file is intentionally untracked).
2. Generate tracked metadata JSON used by the release workflow:

```bash
make metadata
```

This writes `.github/release/metadata.json`.

## Release Steps

1. `make set-version X.Y.Z[a|b|rc]N`
2. `make metadata`
3. `make test`
4. `make git-add`
5. `make git-commit`
6. `make git-push`
7. `make git-tag`

## CI/Release Behavior

- CI (`.github/workflows/ci.yml`) runs on pushes to `master`.
- Release (`.github/workflows/release.yml`) runs on tag pushes `v*`.
- Release workflow enforces that tag commit must be on `master`.
- Release workflow also enforces successful CI for the same commit SHA.

## Commit Hygiene

- Keep commit messages clear and scoped.
- Create a local root `commit_message.txt` before running `make git-commit`, and keep it updated for each commit.
- `commit_message.txt` is intentionally untracked; contributors should maintain their own local file content.

Next: [Changelog](./changelog.md)
