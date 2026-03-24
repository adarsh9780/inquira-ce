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
- Build desktop artifacts (macOS/Windows)

## Practical release behavior

- Release waits for CI to finish successfully for the same commit before build/publish steps begin.
- Releases are published immediately as prereleases (not drafts).
- Release title/body are synchronized from `.github/release/metadata.json` during the workflow run.
- Windows desktop is currently non-blocking in release workflow.

Detailed steps: [Release Process](./release_process.md)

