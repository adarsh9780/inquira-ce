# CI And Release Automation

This page summarizes what runs automatically and what each workflow is responsible for.

## CI workflow

- File: `.github/workflows/ci.yml`
- Trigger: pushes to `master`
- Purpose: validate code quality and correctness before release work

It runs:
- Backend checks (lint, type check, migrations, tests)
- Frontend checks (tests, build)

## Release workflow

- File: `.github/workflows/release.yml`
- Trigger: pushed tags matching `v*`
- Purpose: build and publish release artifacts

It does:
- Enforce release preconditions (tag on `master` and successful CI for same commit)
- Build/publish backend wheel (GitHub Release + PyPI)
- Build desktop artifacts (macOS/Windows)
- Keep wheel and desktop publishing independent so one does not block the other

## Practical release behavior

- Releases are created as draft prereleases in the current setup.
- You can review release notes/assets and publish manually.
- Windows desktop is currently non-blocking in release workflow.

Detailed steps: [Release Process](./release_process.md)

Next: [Architecture](./architecture.md)
