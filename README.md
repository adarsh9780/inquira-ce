# Inquira Go

This repository is the Go/Wails desktop application for Inquira. It keeps the
existing Vue UI, uses Go for native application services, and runs ingestion,
Jupyter, and the LangGraph analysis agent through one bundled Python worker.

## First migrated product slice

Model connection is handled natively by Go when the UI runs inside Wails:

- model preferences and cached provider catalogs are stored in a migrated
  SQLite database under the user's Inquira data directory;
- OpenAI, OpenRouter, and Anthropic API keys are verified before being stored in the OS
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

Workspace AI configuration is native as well. Application credentials remain
in the OS keychain, while each workspace can persist provider, main, lite, and
coding model overrides, generation controls, and its explicit data-sample
privacy choice in SQLite. Both schema generation and agent analysis resolve
this effective workspace configuration before calling the Python worker.

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
modern Office Open XML format only. The SQLite connector is deferred. Before
chat or code execution starts, Go can now prepare an atomic workspace DuckDB
catalog whose read-only views point at the latest connection snapshots. This
gives analysis processes one stable database contract without copying the
imported data again.

Conversation persistence uses SQLite as the authoritative index and the local
filesystem as an immutable payload heap. Messages, generated code, branching,
execution state, and artifact pointers live only in SQLite. A conversation has
one local directory containing flat, UUID-named artifact and attachment files;
there are no per-question folders or duplicate Markdown, Python, or manifest
files. Payloads are staged and atomically published before their SQLite pointer
is committed. Startup reconciliation removes unreferenced files, completes
interrupted conversation deletion, marks missing payloads, and changes turns
left queued or running by an unclean shutdown into retryable failed turns
without touching the workspace DuckDB catalog.

Conversation history is loaded newest-first through stable SQLite cursor pages,
so opening a long conversation does not load every turn into the UI.
Provider-reported token and cost usage is aggregated from persisted turn
metadata without estimating missing fields, and the same usage is shown in
conversation trees.

Wails session restoration also uses the local SQLite database. Small structured
snapshots preserve pane layout, active workspace/conversation pointers, question
history, and in-progress editor state per local user. They do not contain
artifact payloads or duplicate conversation results from the filesystem heap.
Theme and font preferences use a separate SQLite snapshot so they can be loaded
before authentication; the first native load migrates any valid preference
values left in WebView local storage by an earlier build.

Python analysis runs through one lazily started worker process owned by Go.
That process maintains one Jupyter kernel per active workspace, opens the
workspace DuckDB catalog read-only, preserves notebook state between turns,
and isolates state across workspaces. Go routes concurrent JSON-RPC requests
and execution events by request ID. Dataframe and figure outputs are written to
short-lived staging paths and then copied into the conversation heap through
the same atomic artifact publication contract; Python never writes final heap
pointers or application metadata.

Native agent streams are also scoped by client request, workspace,
conversation, turn, and run. Cancelling a request cannot stop a newer analysis
in the same workspace. Tool progress and intervention responses use the same
local Go-to-worker RPC boundary rather than the legacy HTTP service.

The consent-gated local terminal also runs natively in the Wails application.
Go owns one interactive shell session per workspace, streams PTY data through
scoped Wails events, and cleans up sessions on reset, workspace deletion, or
application shutdown. Unix builds use the operating-system PTY and Windows uses
ConPTY, including terminal resizing on both platforms.

Desktop startup and recovery are native to Wails as well. The UI reads Go's
actual initialization state, can open a private rotating startup log, and can
restart the current executable with its original arguments. External links are
opened through a Go allowlist that accepts only credential-free HTTP and HTTPS
URLs and invokes the platform launcher without a shell.

CSV, Python, PNG, and HTML exports use the native Wails save dialog. Go validates
the filename and file filters, decodes the binary payload, and atomically
publishes a private file at the destination selected by the user. Canceling the
dialog does not fall through to a browser download.

The same worker hosts the ported LangGraph agent, including tool calling,
structured responses, retries, memory summarization, and the existing pandas,
DuckDB, and Plotly analysis tools.

## Runtime modes

The embedded UV runtime supports three provisioning policies:

1. `managed`: UV installs the approved Python version.
2. `external-python`: Inquira uses an organization-provided Python executable
   and disables Python downloads.
3. `internal-mirror`: UV installs Python and packages from organization-owned
   mirrors and can use the operating system certificate store.

External interpreters must be an executable Python 3.12 file. Runtime setup can
also use HTTP/HTTPS proxies, the operating system certificate store, or a custom
PEM CA bundle. Mirror, package-index, and proxy URLs are validated before setup;
credential-bearing values are redacted from plan previews and errors.

After successful setup, Inquira remembers only the non-secret source choice,
Python version or executable path, and certificate preference. Proxy, mirror,
index, and bypass values are cleared after every attempt and are never written
to the runtime configuration. A ready runtime can be reviewed and replaced from
Workspace → Connections → Data runtime setup.

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

## Runtime validation

Exercise the production Go-to-Python pipeline in a fresh isolated runtime:

```sh
make test-runtime-e2e
```

This provisions the embedded worker with the bundled UV binary, imports CSV,
builds the DuckDB catalog, executes Jupyter code, runs LangGraph against a
local OpenAI-compatible protocol server, persists artifacts, and reads them
after restarting the worker.

Live provider validation is opt-in so normal tests never consume credentials
or paid tokens. Set `INQUIRA_E2E_PROVIDER`, `INQUIRA_E2E_MODEL`, and
`INQUIRA_E2E_API_KEY`, then run:

```sh
make test-live-provider
```

`INQUIRA_E2E_BASE_URL`, `INQUIRA_E2E_LITE_MODEL`, and
`INQUIRA_E2E_CODING_MODEL` can be supplied when the provider requires them.

## Layout

```text
cmd/prepareuv/                 Build-time UV bundler
frontend/                      Existing Inquira Vue UI
internal/appdirs/              Central application path resolution
internal/connection/           Connection metadata, snapshots, refresh, and worker RPC
internal/conversation/         SQLite conversation index and filesystem artifact heap
internal/desktop/              Startup diagnostics, restart, and safe external links
internal/localstate/           SQLite-backed local UI and session snapshots
internal/modelconfig/          SQLite, keychain, provider, and model services
internal/netclient/            Proxy and certificate-aware HTTP client
internal/runtimeprovision/     Runtime policy and provisioning service
internal/terminal/             Workspace-scoped native PTY lifecycle
internal/worker/               Persistent Python process and concurrent JSON-RPC routing
internal/workspace/            Native workspace metadata and activation service
python/data_worker/            Embedded DuckDB adapter worker and contract tests
build/                         Wails platform packaging assets
```
