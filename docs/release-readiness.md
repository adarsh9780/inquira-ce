# Release readiness

This repository is private. Its automated binary distribution is an unsigned
preview channel and is not yet a signed general-availability release.

## Required before a signed general-availability release

- Choose and review the source-code license.
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

No open-source license is granted by the current repository contents. Keep the
source repository private until the ownership and license decision is complete.

## Current repository controls

CI validates frontend, Go, Python, secret history, and dependency
vulnerabilities on Ubuntu without spending native runner minutes on every pull
request. Stable GitHub Releases run Go tests on macOS and Windows, build the
native installers, generate SHA-256 checksums, archive the assets on GitHub,
and atomically publish public downloads through Cloudflare R2. Dependabot
alerts and automated security fixes are enabled. The current GitHub account
tier does not permit branch protection or native secret-scanning push
protection on a private repository; enable those controls after upgrading the
account or when an approved public-release plan makes the repository public.
