# Inquira Go

This repository is the Go/Wails desktop foundation for Inquira. The first
milestone keeps the existing Vue UI and establishes a versioned Python runtime
boundary without moving ingestion or agent code yet.

## Runtime modes

The embedded UV runtime supports three provisioning policies:

1. `managed`: UV installs the approved Python version.
2. `external-python`: Inquira uses an organization-provided Python executable
   and disables Python downloads.
3. `internal-mirror`: UV installs Python and packages from organization-owned
   mirrors and can use the operating system certificate store.

Secrets for authenticated indexes are intentionally not part of the persisted
runtime configuration.

## Build

Requirements for the first scaffold build are Go, Node.js, npm, and the Wails
v2 CLI. The build command downloads the pinned, target-specific UV release and
embeds it into the native executable.

```sh
make build
```

Verify the compiled executable's embedded runtime without launching the UI:

```sh
./build/bin/inquira-go.app/Contents/MacOS/inquira-go runtime-info
```

On Windows, run `build\\bin\\inquira-go.exe runtime-info`.

## Layout

```text
cmd/prepareuv/                 Build-time UV bundler
frontend/                      Existing Inquira Vue UI
internal/runtimeprovision/     Runtime policy and provisioning service
python/data_worker/            Minimal Python worker boundary
build/                         Wails platform packaging assets
```
