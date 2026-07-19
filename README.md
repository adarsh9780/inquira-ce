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
retains its existing HTTP fallback for browser/Tauri development.

On first Wails launch, Inquira now opens a focused model-connection flow before
the workspace shell. Completion is persisted in SQLite only after a key-backed
provider is configured or an Ollama endpoint successfully returns models. The
in-app Setup checklist uses the same native connection status and then guides
the user to workspace and local-data setup.

Workspace metadata is also native in the Wails build. Go now creates, lists,
activates, renames, and deletes workspaces in the same migrated SQLite database.
The first workspace becomes active automatically, names are case-insensitively
unique, and deleting the active workspace selects a remaining workspace. The
browser/Tauri build retains its Python HTTP fallback.

Local data now starts with refreshable connections rather than uploads. The
first adapters support CSV, Parquet, and modern Excel (`.xlsx`) files through a shared discover,
preview, materialize, refresh, and status contract. Go owns connection metadata
and atomic snapshot publication; the bundled Python worker uses DuckDB to write
canonical Parquet snapshots without an application row or memory cap. Preview
limits do not limit materialization. Excel discovery exposes every sheet and
its visibility, dimensions, and inferred schema. Users explicitly select one
or more sheets, and each selection becomes its own Parquet output. Cached
formula values are the default, with formula text available as an option.

A fresh installation asks the user to configure the data runtime before any
download. Managed Python, a company-provided Python executable, and internal
Python/package mirrors are supported. Proxy, bypass, index, and system
certificate settings are passed only to that setup run and are not saved by
Inquira.

Legacy `.xls` files are not accepted because the streaming reader supports the
modern Office Open XML format only. SQLite is the next planned adapter and will
reuse the same discovery, explicit table selection, and multi-output contract.
Conversations, analysis runtimes, and workspace-specific AI overrides remain
outside the current migration slice.

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
internal/connection/           Connection metadata, snapshots, refresh, and worker RPC
internal/modelconfig/          SQLite, keychain, provider, and model services
internal/netclient/            Proxy and certificate-aware HTTP client
internal/runtimeprovision/     Runtime policy and provisioning service
internal/workspace/            Native workspace metadata and activation service
python/data_worker/            Embedded DuckDB adapter worker and contract tests
build/                         Wails platform packaging assets
```
