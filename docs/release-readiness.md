# Release readiness

This repository is private and is not yet ready for public source or binary
distribution.

## Required before a public release

- Choose and review the source-code license.
- Produce complete third-party notices for Go, frontend, Python, UV, and
  redistributed Python runtime artifacts.
- Enable GitHub private vulnerability reporting and required branch checks.
- Sign and notarize macOS artifacts.
- Sign Windows artifacts.
- Generate checksums, an SBOM, and verifiable provenance for every package.
- Define the supported upgrade, rollback, and data-migration policy.
- Complete privacy, terms, telemetry, and diagnostic-export review.
- Exercise installation and runtime recovery on every supported OS and
  architecture.

No open-source license is granted by the current repository contents. Keep the
repository private until the ownership and license decision is complete.
