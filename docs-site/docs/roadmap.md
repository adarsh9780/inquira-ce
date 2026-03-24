# Roadmap


## Product Direction

The next phase focuses on:
- a more controllable workspace UI (panels, shortcuts, responsive layout),
- stronger runtime/data reliability (artifact loading, tables, DuckDB support),
- and scalable conversation execution (token-aware summarization/truncation and better live run visibility).

## Near-Term Priorities

### 1) Workspace layout and interaction quality

- Make left and right panels independently toggleable while enforcing that at least one panel remains visible.
- Keep the current behavior where both panels can be open together.
- Add smooth panel open/close animation.
- Add keyboard shortcuts aligned with common VS Code muscle memory:
  - `Ctrl+J`: toggle terminal
  - `Ctrl+L`: toggle left panel (chat/code)
  - `Ctrl+B`: toggle right panel
- Improve responsive behavior for narrow windows:
  - avoid fixed-width controls (for example, table/chart selector dropdown should size with available space)
  - keep workspace controls usable at reduced widths.
- Fix auth page background styling so it matches the rest of the product theme.

### 2) Data and schema UX improvements

- Add schema selector dropdown in schema editor so users can switch between all schemas in a workspace.
- Remove “single selected dataset” emphasis styling in dataset selector and move toward multi-dataset workspace querying by default.
- Support schema composition/combination so agent workflows are not constrained to one table at a time.

### 3) Execution visibility and runtime feedback

- Add websocket-driven run status for code UI so users can clearly see:
  - code running/idle state,
  - kernel active/connecting state,
  - real-time execution lifecycle signals.
- For large images, stream non-interactive base64 image output when payload size crosses a threshold, instead of always sending interactive image objects.

### 4) Conversation scaling and background memory management

- Add token-aware summarization + truncation node in the agent graph.
- Trigger summarization when turn/token thresholds are exceeded.
- Use `tiktoken` (or API token usage metadata) for token accounting.
- Run summarization/truncation asynchronously in background so UI remains non-blocking.

### 5) Data model and persistence cleanup

- Split conversation/turn storage from global account/billing tables.
- Persist generated code per workspace as a stable Python script (`1 workspace = 1 code file` lifecycle).

### 6) Artifact/table behavior hardening

- Fix AG Grid sorting/filtering behavior.
- Remove table inline fallback path when artifact is missing; show explicit “artifact not found on disk” state instead.
- Improve artifact-switch performance (`df1 -> df2 -> df1`) by introducing at least page-offset/limit cache first, with optional deeper backend page cache later.

### 7) File format/runtime compatibility

- Add first-class DuckDB file support where currently blocked.

## Current Behavior Notes (To Be Addressed)

- Runtime retries currently re-run the same generated code up to retry limit; there is no automatic “regenerate code and retry” loop after execution failure.
- Artifact table loading is artifact-backed first; in-memory dataframe payload is fallback only.
- Switching artifacts currently clears table state and re-requests pages; persistent response caching is not retained across artifact switches.
- Hidden/idle tab handling currently affects polling cadence only; chat history is not evicted due to hidden state.

## Future Plans (Raw Checklist)

- [ ] Responsive UI: remove fixed-width behavior in controls such as table/chart selector dropdown.
- [ ] Data model: split conversation/turn tables from global users/payment-status tables.
- [ ] Workspace code persistence: save generated code as one Python script per workspace.
- [ ] Image payload policy: stream base64 image output when payload size exceeds threshold, instead of sending interactive image payload.
- [ ] Agent memory scaling: add background summarize+truncate node based on token thresholds (use `tiktoken` or API token usage).
- [ ] Agent memory scaling: ensure summarization/truncation does not block UI.
- [ ] Artifact switching (`df1 -> df2 -> df1`): add at least offset/limit cache first; evaluate deeper backend page cache later.
- [ ] DuckDB support: enable direct DuckDB file support where currently unsupported.
- [ ] Runtime failure loop: evaluate optional “regenerate/fix code then retry” path, since current retries only rerun same code.
- [ ] Lifecycle behavior: hidden/idle tab currently does not evict chat history; define and implement explicit policy if needed.
