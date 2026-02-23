# CI And Release Automation

- CI workflow: `.github/workflows/ci.yml`
  - Runs on push to `master`.
- Release workflow: `.github/workflows/release.yml`
  - Runs on pushed tags matching `v*`.
  - Guard step fails if the tag commit is not on `master`.
  - Builds/publishes backend wheel (GitHub Release + PyPI) and builds desktop artifacts (macOS/Windows).
  - Wheel and desktop publishing are independent so one failing does not block the other.

Detailed steps: [Release Process](./release_process.md)

Next: [Architecture](./architecture.md)
