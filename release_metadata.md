Release v0.5.7a9

### Workspace and kernel reliability

- Routed slash commands through the active workspace kernel instead of opening a second DuckDB connection from the API process.
- Moved dataset ingestion, schema reads, schema regeneration sampling, and artifact access onto kernel-owned DuckDB connections.
- Returned clearer kernel-required errors when a workspace operation needs a running kernel, so users are told to start or restart it and wait for `Kernel Ready`.
- Recovered dataset uploads from workspace DuckDB lock conflicts by resetting the kernel once and retrying the import flow.

### Chat and analysis workflow

- Kept the shared chat composer active in both chat and code views so users can ask follow-up questions without leaving generated code.
- Kept the code view visible during AI generation by replacing the blocking overlay with a non-blocking read-only state.
- Recovered the table pane after kernel restarts by polling for readiness, clearing stale timeout errors, and reopening the selected artifact when possible.
- Centered chart artifact errors in the empty state instead of showing them in the toolbar.

### Table, chart, and schema UX

- Cached dataframe artifact pages across artifact switches so revisiting a table does not immediately refetch the same page.
- Smoothed table pagination by reducing unnecessary reactive updates and removing row animation churn.
- Compacted the table, chart, and output toolbars for tablet widths with icon-first actions and flexing selectors.
- Prompted desktop users for a CSV save location instead of always exporting to `Downloads`.
- Removed the overlapping chevron from the figure export control.
- Sourced schema editor dataset options from live workspace tables so runtime-created tables still appear in schema selection flows.

### Release and distribution

- Enforced desktop-only release distribution and removed wheel and PyPI publishing from the release workflow and related docs.
