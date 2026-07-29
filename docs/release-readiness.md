# Release readiness

This repository is public and source-available under the Sustainable Use
License 1.0. Its automated binary distribution is an unsigned preview channel
and is not yet a signed general-availability release.

## Required before a signed general-availability release

- Produce complete third-party notices for Go, frontend, Python, UV, and
  redistributed Python runtime artifacts.
- Enable GitHub private vulnerability reporting and required branch checks.
- Sign and notarize macOS artifacts.
- Sign Windows artifacts.
- Generate an SBOM and verifiable provenance for every package. SHA-256
  checksums are already produced by the automatic release workflow.
- Define the supported upgrade, rollback, and data-migration policy.
- Complete privacy, terms, telemetry, and diagnostic-export review.
- Exercise installation and runtime recovery on every supported OS and
  architecture.

The Sustainable Use License permits personal, academic, non-commercial, and
internal business use subject to its terms. It is not an OSI-approved
open-source license and restricts commercial exploitation and managed-service
distribution.

## Current repository controls

CI validates frontend, Go, Python, secret history, and dependency
vulnerabilities on Ubuntu without spending native runner minutes on every pull
request. Stable GitHub Releases run Go tests on macOS and Windows, build the
native installers, generate SHA-256 checksums, archive the assets on GitHub,
and atomically publish public downloads through Cloudflare R2. Dependabot
alerts and automated security fixes are enabled. The current GitHub account
tier does not permit branch protection or native secret-scanning push
protection while the repository was private. Re-evaluate required branch
checks and security controls after the public repository migration.
