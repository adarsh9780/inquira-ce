# Frontend UI Audit

Date: 2026-06-23

This audit focuses on design-token consistency, reusable component opportunities, and stale code found while refining the sidebar conversation list.

## Priority Findings

1. **Floating action menus should be shared**
   - `UnifiedSidebar.vue`, `WorkspaceSwitcher.vue`, `TurnTreeNodeActions.vue`, and `FigureTab.vue` each hand-roll small fixed or dropdown action menus.
   - Extract a generic tokenized action menu with divider support, destructive actions, keyboard escape handling, and viewport clamping.

2. **Dropdown internals are duplicated**
   - `HeaderDropdown.vue`, `MultiSelectDropdown.vue`, and `ModelSelector.vue` repeat option-row styling, search input styling, empty states, and floating-menu positioning.
   - Keep public APIs separate, but move shared option row/search/menu surface styles into a reusable internal primitive or shared CSS classes.

3. **Large components need progressive extraction**
   - Largest hotspots: `WorkspaceTab.vue`, `ChatInput.vue`, `ChatHistory.vue`, `UnifiedSidebar.vue`, `TableTab.vue`.
   - Extract by workflow, not file size alone: sidebar rows/actions, workspace dataset sections, chat composer attachments, and tool/output renderers are the clearest first cuts.

## Design Token Gaps

- `text-white` appears in action/status surfaces such as `WorkspaceSwitcher.vue`, `SchemaEditorTab.vue`, and `StatusBar.vue`; prefer `text-[var(--color-on-accent)]` for accent-backed UI.
- `bg-black/25` appears in modal overlays in `KeyboardShortcutsModal.vue` and `TurnTreeNodeActions.vue`; prefer the shared `modal-overlay` token class unless the overlay intentionally needs a different strength.
- `AppearanceTab.vue` uses `color-mix(... white/black ...)` inside theme previews. This is acceptable for preview mockups, but should be wrapped in named preview helpers if these previews grow.
- Many components use inline token styles for routine surfaces. Tokens are used, but repeated inline style blocks make consistency harder to maintain; shared CSS utility classes would reduce drift.

## Stale Code Candidates

- `UnifiedSidebar.vue` had a hidden `v-if="false"` Legal & Terms duplicate and unreachable multi-conversation delete state; these should stay removed.
- `WorkspaceSwitcher.vue` assigns `isRenamingWorkspace.value = true` twice in `renameWorkspace`.
- Several tests still guard old removed sidebar concepts by string checks. Keep the useful regression intent, but refresh brittle strings when related files are touched.
- Legacy comments in `executionService.js`, `OutputTab.vue`, and v1 preference/model fallback paths may still describe compatibility behavior; review before removing.

## Recommended Next Pass

Start with a generic action-menu primitive, then migrate sidebar conversation actions, workspace context actions, turn-tree actions, and figure export actions one at a time. This gives the largest consistency gain with limited behavior risk.
