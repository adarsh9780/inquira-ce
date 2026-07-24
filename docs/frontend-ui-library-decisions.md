# Frontend UI Library Decisions

Inquira uses selected shadcn-vue source components backed by Reka UI. Existing
theme tokens, density, and Heroicons remain the visual source of truth.

## Migrated

- Confirmation uses the owned Alert Dialog primitive.
- Workspace rename, conversation tree rules, keyboard shortcuts, terms,
  settings, and command palette use the owned Dialog primitive.
- The command palette also uses the owned Command primitive.
- Owned Button, form, tooltip, popover, select, combobox, menu, tabs, switch,
  checkbox, toast, and resizable primitives are available for incremental use.

## Deliberately retained Headless UI consumers

Four dropdowns remain on Headless UI for now:

- `HeaderDropdown.vue` supports provider grouping, local and server-backed
  search, longest-label sizing, and viewport-aware positioning.
- `ModelSelector.vue` supports grouped model catalogs and a compact anchored
  search surface.
- `MultiSelectDropdown.vue` has a multi-value contract that does not map
  directly to the current owned Select.
- `SidebarWorkspaces.vue` combines a workspace picker with asynchronous
  conversation caches and sidebar-specific positioning.

They share one option/search/positioning implementation and have existing
keyboard tests. Replacing them without feature parity would reduce usability.
No new Headless UI consumers should be added; new fixed selects and menus use
the owned shadcn-vue layer.

## Bundle policy

The UI foundation is selective: do not generate the full component catalog and
do not add PrimeVue alongside shadcn-vue. Heavy product renderers such as
CodeMirror, xterm, Plotly, and TanStack Table stay purpose-built and lazy.

