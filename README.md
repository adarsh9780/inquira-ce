# Inquira Go

This repository is the Go/Wails desktop foundation for Inquira. The first
milestone keeps the existing Vue UI and establishes a versioned Python runtime
boundary without moving ingestion or agent code yet.

## First migrated product slice

Model connection is handled natively by Go when the UI runs inside Wails:

- model preferences and cached provider catalogs are stored in a migrated
  SQLite database under the user's Inquira data directory;
- OpenAI and OpenRouter API keys are verified before being stored in the OS
  keychain, and are never written to SQLite;
- Ollama remains keyless and stores only its local base URL;
- provider requests inherit standard `HTTP_PROXY`, `HTTPS_PROXY`, and
  `NO_PROXY` settings and use the operating-system certificate store;
- model refresh failures retain the verified credential and fall back to the
  cached catalog.

The Vue model-settings flow uses direct Wails bindings in the desktop build and
retains its existing HTTP fallback for browser/Tauri development. Other product
areas still use the Python API until their own vertical slices are migrated.

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
internal/appdirs/              Central application path resolution
internal/modelconfig/          SQLite, keychain, provider, and model services
internal/netclient/            Proxy and certificate-aware HTTP client
internal/runtimeprovision/     Runtime policy and provisioning service
python/data_worker/            Minimal Python worker boundary
build/                         Wails platform packaging assets
```
