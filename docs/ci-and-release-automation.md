# CI And Release Automation

- CI workflow: `.github/workflows/ci.yml`
  - Runs on push to `master`.
- Release workflow: `.github/workflows/release.yml`
  - Runs on pushed tags matching `v*`.
  - Guard step fails if the tag commit is not on `master`.
  - Builds desktop artifacts (macOS/Windows) and backend wheel, then attaches to release.

Detailed steps: [Release Process](./release_process.md)

Next: [Architecture](./architecture.md)
