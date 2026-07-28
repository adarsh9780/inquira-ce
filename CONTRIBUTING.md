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

## Dependency and runtime changes

Dependency updates must include their lockfile changes. Updating the bundled UV
version also requires adding Astral's published SHA-256 values for every
supported OS and architecture to `cmd/prepareuv`.

Python runtime changes must remain compatible with both the managed and
external-Python provisioning policies.
