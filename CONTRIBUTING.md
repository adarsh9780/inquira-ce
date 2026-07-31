# Contributing to Inquira

Inquira is currently developed in a private repository. Changes should be small,
reviewable, and covered by the closest practical automated test.

## Toolchains

The supported development versions are:

- Go 1.26.5
- Node.js 24.18.0
- Python 3.12.13
- UV 0.11.28 for the application runtime

Run `make doctor` to inspect the local environment and `make bootstrap` to
install locked dependencies.

## Development workflow

Create a focused branch, implement the change, and run:

```sh
make fmt
make test
make audit
make frontend-build
```

Use `make test-full` when changing runtime provisioning, worker startup,
ingestion, catalog publication, or cross-language RPC.

Pull requests must explain the user impact, validation, security implications,
and rollback strategy. Never include API keys, customer data, runtime
credentials, generated application data, or private diagnostic logs.

## Pull-request policy

Each PR must contain one independently understandable, testable, and revertible
change. Keep its regression tests in the same PR, but move unrelated cleanup
and refactoring into separate work.

The required `PR Policy` check warns above 200 human-authored changed lines and
blocks merge above 400 lines or 15 human-authored files. Generated output,
dependency lockfiles, vendored code, and binary assets are reported separately.
Tests and documentation remain reviewable code and count toward the limits.

If a change cannot be split safely, explain why under `## Size override` and ask
a maintainer to apply the `size-override` label. Overrides are for genuinely
indivisible generated migrations or mechanical refactors, not unrelated bugs.

Keep the PR as a draft until its validation checklist is complete. Repository
rules should require `Go`, `Frontend`, `Python worker`, `Secret history`, and
`PR Policy`, plus resolution of review conversations, before merge.

## Dependency and runtime changes

Dependency updates must include their lockfile changes. Updating the bundled UV
version also requires adding Astral's published SHA-256 values for every
supported OS and architecture to `cmd/prepareuv`.

Python runtime changes must remain compatible with both the managed and
external-Python provisioning policies.
