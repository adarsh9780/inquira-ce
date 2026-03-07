# Changelog

All notable changes should be documented in this file.

## Unreleased

### Added
- Multi-provider chat model factory (Ollama, OpenAI, Anthropic) configurable via `inquira.toml`.
- Native real-time Output pane capturing execution logs (stdout/stderr) via SSE.
- Backend-driven Exploratory Data Analysis (EDA) slash commands with autocomplete.
- Hybrid schema retrieval using editable schema aliases in the schema generator.
- Arrow-key recall for chat input, and global VS Code-style keyboard shortcuts.
- Config-driven agent v2 scaffold with intervention-ready SSE flows.

### Changed
- Split persistence model into auth and appdata databases using principal-based ownership.
- Dataframe and figure outputs are now auto-captured from arbitrary variable names.
- Schema editor UI modernized with an in-tab dataset switcher.

### Fixed
- Synced backend state to accurately reflect API key requirements (fixes Ollama API key bug).
- Restored sorting and search features in AG Grid artifact tables.
- Fixed scrolling snapback in chat and improved contextual scroll-to-bottom behavior.
- Stabilized DuckDB runtime with read-only connections for safe schema introspection.
- Regenerated analysis code defensively to recover from runtime tool failures.

## [v0.5.7a6]

### Added
- Real-time token streaming in chat with smoother live response rendering.
- Upgraded built-in terminal experience with persistent sessions and better output visibility.
- Unified collapsible sidebar and dual resizable workspace panes for faster navigation and analysis flow.
- Improved agent response structure for clearer plans and explain-code output.

### Changed
- Runtime and artifact stability improved with stronger DuckDB lock handling and safer kernel/resource teardown.
- Artifact rendering became more reliable with better recovery from missing/deleted outputs and duplicate-row prevention.
- Chat UX now separates trace progress from final answers and improves code-block presentation/copy behavior.
- Desktop icon assets were normalized so the Inquira Dock icon no longer appears visually oversized.

### Notes
- This section intentionally lists only major, user-facing updates.

Next: [Back To Overview](./overview.md)
