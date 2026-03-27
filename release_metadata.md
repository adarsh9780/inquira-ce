# Release v0.5.25 — 2026-03-27

**29 commits · 44 files changed**

## Sidebar Redesign

The sidebar has been completely overhauled with a folder-tree layout built around a workspace-first mental model. Workspaces now expand into datasets and conversations directly, replacing the old dropdown. Section headers are compact and explorer-style, count badges and step labels are gone, and hover/selection states now share the chat bubble color token (`--color-chat-user-bubble`) for visual consistency. Conversation renaming is also now supported inline.

## Visual Polish

Separator lines, redundant borders, and descriptive helper text have been stripped throughout the UI. The chat input area sits closer to messages, secondary buttons adopt the bubble tint globally, and the overall sidebar density is tighter and cleaner.

## Kernel & Runtime Stability

- Stale "kernel required" banners in the figure pane now clear on recovery
- Bootstrap gating restored to prevent 409 startup conflicts
- Kernel state unified across StatusBar, TableTab, and FigureTab — no more stale readiness caches
- Noisy transient error logging during startup races reduced

## Windows / Desktop Fixes

- `uv` binary selection now skips non-executable bundled fallbacks (fixes OS error 193)
- `beforeBuildCommand` is deterministic for Windows Tauri builds
- Versioning enforced as stable-only to avoid MSI prerelease failures
- Dead code warnings from Unix-only shutdown constants no longer appear in Windows builds

## Testing

16 new or updated tests covering sidebar behavior, kernel state, UI theming, and build determinism.