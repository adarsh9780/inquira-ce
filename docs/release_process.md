# Release Process

Use this checklist when you are preparing a tag-based release.

## 1. Ensure master is green

CI must pass on `master`.

## 2. Bump versions

Use the Makefile guard (recommended):

```bash
make set-version 0.5.0a7
```

This writes to `VERSION` and updates backend/frontend/tauri packaging files.
It also blocks same-or-lower version values.

## 3. Generate release metadata

Create local `release_metadata.md` in repo root (untracked) with:
- first non-empty line as title
- remaining content as release body

Then generate tracked metadata JSON:

```bash
make metadata
```

This writes `.github/release/metadata.json`, which release workflow uses for title/body.

## 4. Commit and push

```bash
make test
make git-add
make git-commit
make git-push
```

## 5. Create and push tag

```bash
make git-tag
```

## 6. GitHub Actions release workflow

Workflow file: `.github/workflows/release.yml`

What it does:

1. Verifies tag commit is on `master`.
2. Verifies `ci.yml` already succeeded for the same commit SHA.
3. Builds frontend assets for wheel packaging, syncs them into `backend/app/frontend/dist`, and builds backend wheel (`backend/dist/*.whl`).
4. Uploads wheel to GitHub Release and publishes wheel to PyPI (environment: `pypi`).
5. Builds desktop artifacts via Tauri action (macOS + Windows matrix; Windows uses NSIS bundle).
6. Desktop and wheel publishing are independent: one can fail while the other still publishes.

## 7. Publish release

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
