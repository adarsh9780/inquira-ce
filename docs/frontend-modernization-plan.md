# Frontend Modernization Plan

Date: 2026-07-23

Status: Implemented (2026-07-24)

## Outcome

Modernize the existing Vue frontend without replacing Vue or rewriting the product as a different application architecture.

The work will:

- adopt selected shadcn-vue components, backed by Reka UI, for reusable interaction primitives;
- split the current application store into domain stores;
- break large Vue components into focused components and composables;
- lazy-load expensive and infrequently used features;
- reduce the main and visualization bundles;
- make the generated OpenAPI client the default API contract;
- move state and API boundaries to TypeScript incrementally.

This is an incremental migration. Every phase must leave the application releasable. A temporary compatibility layer is allowed while consumers move, but every compatibility layer must have an explicit removal phase.

## Current Baseline

The baseline was measured with `npm run build` from `inquira-ce/frontend`.

| Area | Current state |
| --- | --- |
| Framework | Vue 3.5, Pinia 3, Vite 8, Tailwind CSS 4 |
| Frontend source | Approximately 35,279 lines |
| Vue components | 70 |
| Main Pinia store | `appStore.js`, 4,336 lines |
| Main application chunk | Approximately 461.60 KB gzip |
| Plotly chunk | Approximately 1,379.91 KB gzip |
| Main CSS | Approximately 32.71 KB gzip |
| Headless UI chunk | Approximately 7.80 KB gzip |
| Source contract tests | 263 |
| Runtime component/unit tests | 8 |
| End-to-end specifications | 4 |

The emitted Plotly chunk is not necessarily part of every initial screen load. The first measurement task must distinguish emitted chunk size, initial application payload, and payload loaded when a user first opens each feature.

## Principles and Guardrails

1. Do not perform a big-bang rewrite.
2. Preserve the frontend interaction contract in `docs/frontend-interaction-contract.md`.
3. Keep Inquira's existing visual identity, density, theme tokens, and Heroicons unless a specific replacement has a measured benefit.
4. Adopt shadcn-vue selectively. Do not install or generate every available component.
5. Use Reka UI behavior for focus management, keyboard navigation, ARIA semantics, portals, and controlled component state.
6. Do not introduce PrimeVue alongside shadcn-vue.
7. Do not replace product-specific components such as chat streaming, CodeMirror, xterm, Plotly, TanStack Table, the workspace shell, or artifact renderers with generic UI components.
8. Add a focused regression test for every migrated interaction.
9. Avoid cross-store circular dependencies. Cross-domain workflows belong in orchestration composables or services.
10. Preserve public component and store contracts temporarily when that allows a small, independently shippable change.
11. Record bundle measurements before and after every phase that changes dependencies or loading boundaries.
12. Any deviation from the order or scope below requires approval before implementation.

## Target Architecture

### UI foundation

The application will own a small component layer under `src/components/ui`. Selected shadcn-vue components will provide the starting source and Reka UI will provide interaction behavior. Inquira tokens will remain the styling source of truth.

Product components import the owned Inquira UI layer, not Reka UI directly. This gives the application one place for:

- variants and sizes;
- focus rings and disabled states;
- theme-token mapping;
- motion and reduced-motion behavior;
- portal and z-index policy;
- accessibility defaults;
- future upstream component changes.

### State boundaries

The final stores are:

| Store | Owns |
| --- | --- |
| `workspaceStore.ts` | Workspaces, active workspace, datasets, schema/context, workspace readiness, deletion and ingestion jobs |
| `conversationStore.ts` | Conversations, active conversation, messages, stream traces, interventions, turns, branches, usage |
| `executionStore.ts` | Generated and edited code, runtime readiness, foreground/background operations, conversation runs, terminal sessions and output |
| `artifactStore.ts` | Dataframes, figures, scalars, result selection, artifact promotion/removal, table paging and viewport state |
| `preferencesStore.ts` | Providers, models, credentials metadata, theme/font preferences, preference loading and persistence |
| `uiStore.ts` | Active panes, sidebar, dialogs, command palette, keyboard shortcuts, resizer values, editor focus and transient UI state |

`authStore` remains separate.

Cross-domain persistence and startup hydration move to coordinators such as `useAppBootstrap`, `useSessionSnapshot`, and `useWorkspaceActivation`. A domain store must not reach into another domain store merely to update UI state.

### API boundaries

The target request flow is:

```text
Vue component or store
        |
        v
domain API module
        |
        +--> generated OpenAPI client for ordinary HTTP requests
        |
        +--> typed streaming transport for SSE/fetch streams
        |
        +--> typed Tauri transport for native commands and events
```

Components will not import the generated client, Axios, or raw endpoint strings directly.

## Phase 0: Measurement and Safety Net

### Work

- Add a reproducible bundle report command that records:
  - emitted raw and gzip chunk sizes;
  - initial application entry dependencies;
  - chunks loaded on first opening Settings, Code, Terminal, Table, Figure, and Other;
  - duplicate packages and unexpectedly shared chunks.
- Store the baseline report in a machine-readable format suitable for CI comparison.
- Add a CI budget check with warning thresholds first; turn stable thresholds into failures after the loading changes land.
- Add runtime tests for the current behavior of:
  - dialog focus, Escape, outside click, and focus restoration;
  - dropdown keyboard selection and search;
  - command palette keyboard navigation;
  - toast announcements;
  - pane resizing by pointer and keyboard.
- Add or extend Playwright coverage for the always-available workflows in the interaction contract.
- Capture light and dark screenshots at the supported wide and compact widths.
- Add an accessibility test dependency in development only and scan the settings dialog, command palette, primary dropdowns, and destructive confirmation flow.

### Exit criteria

- Baseline artifacts are repeatable locally and in CI.
- Critical interaction behavior is protected before component replacement starts.
- Bundle and accessibility regressions can be detected automatically.

## Phase 1: shadcn-vue and Reka UI Foundation

### Setup

- Initialize shadcn-vue for the existing Vite and Tailwind CSS 4 project.
- Use the Reka base.
- Add TypeScript configuration before generating TypeScript components.
- Map shadcn semantic variables to existing Inquira variables instead of introducing a second theme.
- Retain Heroicons initially; do not add an application-wide icon migration.
- Configure one portal/z-index policy compatible with the existing `layer-*` tokens.
- Verify every primitive under all existing themes and with reduced motion enabled.

### Initial owned primitives

Adopt only:

- Button
- Dialog
- Alert Dialog
- Dropdown Menu
- Context Menu
- Tooltip
- Popover
- Select
- Combobox
- Command
- Tabs
- Switch
- Checkbox
- Field and Label
- Toast/Sonner
- Resizable, only after it proves compatible with the current keyboard and pointer behavior

### Replacement order

#### 1. Low-risk visual primitives

- Buttons and icon buttons
- Tooltips
- Inline form fields
- Switches and checkboxes
- Toast presentation

Keep the existing component APIs where they are already widely consumed. Replace their internals first.

#### 2. Dialogs

Migrate the simplest dialogs before the settings shell:

- `ConfirmationModal.vue` -> Alert Dialog
- `WorkspaceRenameModal.vue` -> Dialog
- `ConversationTreeRulesModal.vue` -> Dialog
- `KeyboardShortcutsModal.vue` -> Dialog
- `TermsModal.vue` -> Dialog
- `SettingsModal.vue` -> Dialog after the smaller dialogs are stable

Each dialog regression test must cover:

- initial focus;
- focus trap;
- Escape behavior;
- outside-click policy;
- return focus;
- destructive action labelling;
- light, dark, wide, and compact presentation.

#### 3. Menus and dropdowns

- Replace `FloatingActionMenu.vue` internals with Dropdown Menu.
- Migrate sidebar conversation actions, workspace actions, turn-tree actions, and figure actions to the shared menu.
- Replace duplicated option/menu behavior in:
  - `HeaderDropdown.vue`;
  - `MultiSelectDropdown.vue`;
  - `ModelSelector.vue`;
  - `SidebarWorkspaces.vue`.
- Use Select for small fixed collections and Combobox for searchable or server-backed model collections.
- Preserve the existing public props and events until all consumers migrate.

#### 4. Command palette and tabs

- Rebuild `CommandPaletteModal.vue` on Command and Dialog primitives.
- Replace hand-written tab semantics where shadcn Tabs fits without changing product navigation.
- Keep pane switching and application routing outside the Tabs primitive.

#### 5. Resizers

- Prototype the Resizable primitive against the existing two-axis layout.
- Adopt it only if it preserves:
  - keyboard resizing;
  - compact single-pane behavior;
  - persisted sizes;
  - terminal collapse animation;
  - pointer capture across the Tauri webview.
- Otherwise retain the current resizer and extract it into a tested composable.

### Exit criteria

- No hand-written application dialog lacks focus trapping or focus restoration.
- Menus and searchable selects have one interaction implementation.
- The current visual identity and density remain recognizable.
- Headless UI has no consumers and is removed, or remaining consumers and the reason for retaining it are documented.
- Bundle change from the UI foundation is measured. A small increase is acceptable; an unreviewed broad increase is not.

## Phase 2: TypeScript Foundations

This phase begins before generated shadcn components land and continues through all later phases.

### Work

- Add `tsconfig.json` configured for Vue, Vite, and incremental JavaScript coexistence.
- Add `vue-tsc --noEmit` as a separate script and CI check.
- Initially allow JavaScript without enabling repository-wide `checkJs`.
- Create shared types for:
  - identifiers;
  - workspace and dataset summaries;
  - conversations, turns, branches, and stream events;
  - runtime and operation states;
  - artifacts and table pages;
  - preferences and provider/model catalog responses;
  - API errors and streaming envelopes.
- Generate API types from OpenAPI rather than duplicating response interfaces by hand.
- Use discriminated unions for stream events, runtime states, operation states, and artifact kinds.
- Prevent new untyped endpoint wrappers and new `.js` stores.

### Migration order

1. API transport and generated-client adapter
2. Shared domain types
3. New UI primitives
4. Domain stores
5. Orchestration composables
6. Extracted components when they are otherwise being modified
7. Remaining services and utilities

### Exit criteria

- `vue-tsc --noEmit` passes.
- All new stores, API modules, and shadcn-based primitives are TypeScript.
- No parallel handwritten version of an OpenAPI-generated request or response type is added.

## Phase 3: Split `appStore.js`

### Preparation

- Add characterization tests for state snapshot creation, hydration, workspace switching, concurrent conversation streaming, artifact selection, terminal caps, and preference synchronization.
- Create a state ownership inventory and assign every exported field/action from `appStore.js` to one target store or coordinator.
- Identify cross-domain actions and design explicit coordinator APIs before moving code.

### Extraction sequence

The sequence is chosen to reduce dependency cycles.

#### 1. `uiStore.ts`

Move pane selection, dialog visibility, sidebar state, layout dimensions, editor focus, and transient loading presentation.

#### 2. `preferencesStore.ts`

Move provider/model settings, theme/font settings, preference normalization, and preference persistence.

Keep credential values out of local snapshots. Preserve the existing authentication boundary reset behavior.

#### 3. `artifactStore.ts`

Move tables, figures, scalars, result selection, paging, viewport data, artifact promotion, and artifact removal.

#### 4. `executionStore.ts`

Move code state, runtime status, operations, conversation run cancellation, terminal state, terminal entry caps, and execution errors.

#### 5. `workspaceStore.ts`

Move workspaces, datasets, workspace activation, readiness, schema/context state, ingestion jobs, and deletion jobs.

Workspace activation becomes a coordinator because it touches preferences, runtime, conversations, and artifacts.

#### 6. `conversationStore.ts`

Move conversation lists, active conversation, message state, streaming trace mutations, interventions, token usage, turns, branches, and final-turn behavior.

Keep high-frequency streaming mutations isolated so they do not cause unrelated store consumers to update.

#### 7. Remove compatibility facade

During migration, `useAppStore()` may temporarily forward old properties and actions to the domain stores. New code must use domain stores directly. Remove the facade after the final consumer migrates.

### Store rules

- Stores own state and domain mutations.
- Network operations use domain API modules.
- Multi-store workflows use coordinators.
- Stores do not import Vue components.
- Stores do not directly manipulate the DOM.
- Persisted state has an explicit version and migration function.
- High-frequency streaming state is scoped by conversation ID.

### Exit criteria

- `appStore.js` is removed.
- No target store exceeds approximately 1,200 lines without a written justification.
- There are no circular store imports.
- Workspace switching, simultaneous conversation runs, startup hydration, and auth-boundary cleanup pass dedicated tests.

## Phase 4: Break Up Large Components

Extraction should follow responsibilities, not arbitrary line counts. UI rendering stays in components; workflow orchestration moves to composables or services.

### `App.vue`

Extract:

- `AppShell.vue`
- `StartupScreen.vue`
- `StartupFailureScreen.vue`
- `BlockingOperationOverlay.vue`
- `useAppBootstrap.ts`
- `useDesktopStartup.ts`
- `useGlobalShortcuts.ts`
- `useNativeDatasetDrop.ts`
- `useRealtimeSettings.ts`

`App.vue` should become composition and top-level routing only.

### `WorkspaceTab.vue`

Turn the current slot-only section wrappers into real workflow components:

- `WorkspaceListPanel.vue`
- `WorkspaceGeneralSection.vue`
- `WorkspaceDatasetSection.vue`
- `WorkspaceContextSection.vue`
- `WorkspaceAISection.vue`
- `WorkspaceRuntimeSection.vue`
- `WorkspaceDangerZone.vue`
- `useWorkspaceSettings.ts`
- `useWorkspaceDatasetOperations.ts`

Keep deletion and database-clear confirmations at the section boundary.

### `ChatInput.vue`

Extract:

- `ChatComposer.vue`
- `ChatReadinessNotice.vue`
- existing attachment, autocomplete, model, voice, and action components behind simpler contracts;
- `useChatSubmission.ts`;
- `useChatStream.ts`;
- `useChatCommandExecution.ts`;
- `useConversationRunControl.ts`.

The streaming orchestration must remain conversation-scoped and continue to support simultaneous runs.

### `ChatHistory.vue`

Extract:

- `ChatMessageList.vue`
- `ChatReasoningTrace.vue`
- `ChatToolActivityList.vue`
- `ChatTurnNavigation.vue`
- `ChatInterventionHost.vue`
- `MarkdownContent.vue`
- `useMessageRendering.ts`
- `useTurnActions.ts`

Initialize Markdown, sanitization, syntax highlighting, and KaTeX in one rendering module rather than independently across message components.

### Exit criteria

- The four root components primarily compose smaller components and composables.
- No extracted component reaches into unrelated domain state.
- Existing props/events remain stable where other components depend on them.
- Runtime tests exercise extracted logic rather than relying mainly on source-string assertions.

## Phase 5: Lazy Loading and Feature Boundaries

### Settings

- Load `SettingsModal.vue` only when it is first opened.
- Load settings tabs independently.
- Do not preload model catalogs, workspace maintenance UI, legal Markdown, or appearance previews before the relevant section opens.

### Code editor

- Convert `CodeTab.vue` to an async component.
- Import CodeMirror packages only when the Code pane is first selected.
- Preserve editor state when switching between Chat and Code.
- Provide a lightweight loading placeholder without layout shift.

### Terminal

- Load `TerminalTab.vue`, `TauriTerminalPane.vue`, xterm, and its CSS only when terminal access is opened.
- Do not initialize native terminal listeners until the terminal feature is active.
- Ensure closing the terminal disposes listeners and terminal instances correctly.

### Visualization

- Keep Figure and run-chart components async.
- Move Plotly initialization behind a single cached loader.
- Do not download Plotly until a chart must render.
- Avoid loading Plotly merely because figure metadata exists.
- Inventory the Plotly trace types and features actually used.
- Compare:
  - the current `plotly.js-dist-min`;
  - a supported smaller distribution;
  - a custom Plotly core build registering only required traces and components.
- Retain the full distribution if a smaller build breaks required exports, but keep it out of the initial feature path.

### Markdown and syntax rendering

- Share one lazy rendering module for Markdown, DOMPurify, Prism, KaTeX, and language grammars.
- Load uncommon syntax grammars only when needed where practical.

### Exit criteria

- Opening the normal workspace/chat experience does not evaluate CodeMirror, xterm, Plotly, settings tabs, or legal Markdown.
- Every async feature has loading, error, retry, and teardown behavior.
- Feature switching does not lose editor, terminal, or selection state.

## Phase 6: Consolidate API Layers

### Current problem

The frontend currently has:

- `generatedApi.ts`;
- handwritten `contracts/v1Api.js`;
- a large `apiService.js` facade;
- raw fetch handling for streaming;
- Tauri-specific base URL and native operations.

This duplicates endpoint knowledge and weakens generated type coverage.

### Target modules

- `api/httpClient.ts` — configured Axios instance, auth, base URL, error normalization
- `api/generated/` — Orval output, generated from the checked OpenAPI document
- `api/workspaces.ts`
- `api/conversations.ts`
- `api/execution.ts`
- `api/artifacts.ts`
- `api/preferences.ts`
- `api/streaming.ts` — typed fetch/SSE parser, cancellation, reconnect/fallback policy
- `api/native.ts` — typed Tauri commands and events

Domain modules should mostly expose generated operations with stable application-oriented names. Handwritten code is reserved for streaming, transport configuration, response normalization, and operations that cannot be expressed in OpenAPI.

### Sequence

1. Configure Orval to use the shared Axios instance instead of the global Axios singleton.
2. Add a generated-client freshness test.
3. Move one endpoint domain at a time from `v1Api.js` and `apiService.js`.
4. Migrate consumers to domain modules.
5. Remove raw endpoint strings outside approved transport modules.
6. Remove `contracts/v1Api.js`.
7. Remove `apiService.js` after the last consumer moves.

### Exit criteria

- Ordinary HTTP endpoint paths are generated from OpenAPI.
- Streaming and native operations have explicit typed transports.
- Components do not import Axios or construct API URLs.
- Generated-client drift fails CI.
- `apiService.js` and `contracts/v1Api.js` are removed.

## Phase 7: Bundle Reduction and Budgets

Lazy loading determines when code is loaded; dependency reduction determines how much is loaded. Treat them as separate measurements.

### Initial budgets

These are targets to validate during Phase 0, not permission to remove required behavior:

| Metric | Baseline | First target |
| --- | ---: | ---: |
| Main application chunk | 461.60 KB gzip | At or below 350 KB gzip |
| Plotly emitted chunk | 1,379.91 KB gzip | Reduce after trace inventory, or document why full Plotly is required |
| Plotly in initial chat path | To be measured | 0 KB |
| CodeMirror in initial chat path | To be measured | 0 KB |
| xterm in initial closed-terminal path | To be measured | 0 KB |
| Settings-only code in initial path | To be measured | 0 KB |

### Work

- Inspect why the application entry remains large after manual vendor chunks.
- Split feature entry points based on user workflows rather than package names alone.
- Replace broad package imports with narrow imports where supported.
- Deduplicate Markdown, Prism, KaTeX, and renderer initialization.
- Remove obsolete compatibility code and dependencies after migrations finish.
- Keep generated API output from forcing unused endpoint implementations into the entry chunk.
- Add size-diff output to pull requests.
- Fail CI only after budgets are proven stable across supported build environments.

### Exit criteria

- The main chunk meets the agreed budget or has an approved exception with evidence.
- Heavy feature code is absent from unrelated initial paths.
- No bundle reduction removes accessibility, offline desktop behavior, export fidelity, or supported visualization types.

## Test Strategy

Every implementation pull request must add or update the smallest meaningful regression test.

### Unit and runtime tests

- Store state transitions and persistence migrations
- Stream event reducers
- Artifact selection and paging
- API adapters and error normalization
- Dialog/menu/select keyboard behavior
- Composable lifecycle and cancellation
- Async component error and retry behavior

### Component tests

- Focus trap and focus restoration
- Searchable model selection
- Command palette navigation
- Settings section navigation
- Concurrent conversation progress
- Chat history rendering and intervention responses
- Workspace dataset operations
- Resizer keyboard behavior

### End-to-end tests

- Startup to usable workspace
- Create/select workspace and import data
- Start and stop chat execution
- Switch between simultaneous conversations
- Open Code without automatic execution
- Open/close terminal with consent
- Render table and figure artifacts
- Settings and destructive confirmations
- Compact-width primary workflows

### Required checks per phase

At minimum:

```bash
npm test
npm run build
npm run e2e:list
```

Run focused Playwright specifications for behavior changed in the phase. Run the full applicable end-to-end suite before removing a compatibility layer.

## Delivery Sequence

Implement as small, reviewable changes in this order:

1. Measurement and characterization tests
2. TypeScript configuration and API/domain types
3. shadcn-vue/Reka theme foundation
4. Low-risk primitives
5. Dialogs
6. Menus, selects, and command palette
7. UI and preferences stores
8. Artifact and execution stores
9. Workspace and conversation stores
10. Remove `appStore.js` compatibility facade
11. Break up `App.vue` and `WorkspaceTab.vue`
12. Break up `ChatInput.vue` and `ChatHistory.vue`
13. Lazy-load Settings, CodeMirror, xterm, visualization, and rendering code
14. Consolidate API layers
15. Reduce Plotly and remaining main-bundle contributors
16. Remove obsolete dependencies, compatibility code, and temporary tests

API types and extracted domain types may move earlier when required by a store migration. Otherwise, changing this sequence requires approval.

## Definition of Done

The modernization is complete when:

- selected shadcn-vue/Reka primitives provide shared accessible interactions;
- Headless UI is removed or intentionally retained with documented consumers;
- `appStore.js`, `apiService.js`, and `contracts/v1Api.js` are removed;
- the six domain stores own clearly separated state;
- the four large root components are decomposed by responsibility;
- Settings, CodeMirror, xterm, Plotly, and rich rendering code load only when needed;
- TypeScript covers state stores, API contracts, transports, and new UI primitives;
- generated OpenAPI code is current and is the source of ordinary HTTP endpoint types;
- agreed bundle budgets pass in CI;
- interaction, accessibility, light/dark, compact/wide, and critical workflow tests pass;
- no temporary compatibility facade remains.

## Explicit Non-Goals

- Replacing Vue or Pinia
- Introducing Alpine, Alpine AJAX, HTMX, or PrimeVue into the core application
- Replacing TanStack Table solely for visual consistency
- Replacing Plotly before required visualization coverage is inventoried
- Rewriting the entire interface to match stock shadcn styling
- Migrating all JavaScript to TypeScript in one change
- Changing backend behavior solely to support the component migration
