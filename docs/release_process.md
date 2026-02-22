# Release Process

## 1. Ensure master is green

CI must pass on `master`.

## 2. Bump versions

Use centralized helper:

```bash
uv run python scripts/maintenance/bump_versions.py --version 0.5.0a1 --write-version-file
```

Commit version updates.

## 3. Create and push tag

```bash
git tag -a v0.5.0a1 -m "Inquira v0.5.0a1"
git push origin v0.5.0a1
```

## 4. GitHub Actions release workflow

Workflow file: `.github/workflows/release.yml`

What it does:

1. Verifies tag commit is on `master`.
2. Runs backend validation (ruff, mypy, migration check, pytest).
3. Runs frontend validation (test + build).
4. Builds backend wheel (`backend/dist/*.whl`).
5. Builds desktop artifacts via Tauri action (macOS + Windows matrix).
6. Creates/updates a draft GitHub release and uploads artifacts.

## 5. Publish release

Open GitHub Releases, review draft notes/artifacts, then publish.

## Notes

- Current artifacts are unsigned unless signing is configured.
- Optional signing/notarization hooks are already wired in workflow via secrets.
- Add production secrets before distributing signed builds:
  - `TAURI_SIGNING_PRIVATE_KEY`
  - `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`
  - `APPLE_CERTIFICATE`
  - `APPLE_CERTIFICATE_PASSWORD`
  - `APPLE_SIGNING_IDENTITY`
  - `APPLE_ID`
  - `APPLE_PASSWORD`
  - `APPLE_TEAM_ID`
  - `WINDOWS_CERTIFICATE`
  - `WINDOWS_CERTIFICATE_PASSWORD`
