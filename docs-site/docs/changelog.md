# Changelog

All notable changes should be documented in this file.

## Unreleased

### Added
- Implemented guest sessions and removed the mandatory login wall for immediate access.
- Revamped the documentation site home page and landing pages with a premium Zinc aesthetic and 'Local-First' narrative.
- Integrated an offline-first local search engine for the documentation site.
- Added a comprehensive Editions overview page and expanded the site footer with legal links.
- Shared the left-pane chat composer across both chat and code views so follow-up prompts stay available while reviewing generated code.
- Added structured custom tool execution in `agent_v2`, where the planner emits a canonical tool contract (`tool`, `args`, `explanation`) instead of relying on raw `bind_tools()` output.
- Added short operational tool explanations in streamed tool activity so users can see what the agent just established and what it is doing next without exposing chain-of-thought.

### Changed
- Deferred session verification until the desktop backend startup is ready, making Tauri startup authoritative.
- Modernized and pivoted the public roadmap from proxy infrastructure to pure OAuth BYOK, focusing on local-first capabilities.
- Removed arbitrary workspace limits and "Free Edition" nomenclature to clarify Community Edition positioning.
- Streamlined documentation site navigation by removing redundant pages, consolidating sidebar categories, and promoting downloads.
- Routed agent Python execution through the active backend workspace kernel instead of the agent runtime process, so generated code runs in the same dependency environment used by workspace analysis and artifact rendering.
- Routed slash commands, dataset ingestion, schema introspection, and artifact reads through the active workspace kernel instead of opening competing API-side DuckDB connections.
- Updated the schema editor to build its dataset selector from live workspace tables, including runtime-created tables without `source_path` metadata.
- Tightened right-pane toolbars for tablet-width layouts with more compact filter, export, and delete controls.
- Strengthened code-generation guidance so figure variable names must be meaningful and business-specific, reducing chart overwrites in persistent kernel sessions.

### Fixed
- Resolved `uv` path resolution issues outside of standard terminal environments during startup.
- Fixed guest fallbacks and restored App shell startup build.
- Fixed documentation site styling issues including oversized icons, missing imports, form styling, and duplicate formatting.
- Restored authentication guards and aligned stale UI assertions in the test suite.
- Recovered dataset uploads from workspace DuckDB lock conflicts by surfacing the real backend error, resetting the kernel once, and retrying the import path.
- Restored table and chart panes after kernel interruptions by reloading artifacts and clearing stale missing-kernel errors when the workspace becomes healthy again.
- Smoothed dataframe navigation by caching artifact pages across artifact switches and reducing reactive churn during pagination.
- Kept generated code visible during AI responses by replacing the blocking overlay with a non-blocking read-only state.
- Moved figure artifact errors into the centered empty state so the failure is shown where users expect chart output.
- Removed stale or crowded right-pane controls, including the overlapping figure export chevron and oversized table toolbar actions.
- Eliminated the agent/runtime dependency mismatch that caused generated chart code to fail on imports available in the workspace kernel but missing from the agent process.

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


