# Frontend TypeScript Migration Plan

Date: 2026-07-24

Status: Proposed

## Outcome

Move the production frontend to strict TypeScript without changing product
behavior or attempting a risky bulk conversion.

The migration is complete when:

- `frontend/src` contains no `.js` files;
- every Vue component script uses `lang="ts"`;
- `allowJs` is disabled for production source;
- API, SSE, WebSocket, and Tauri boundaries have explicit types;
- domain state and mutations live in the six typed stores;
- the application coordinator contains only cross-domain workflows;
- type checking, tests, production build, bundle budgets, and E2E discovery pass.

Every phase must leave the application releasable.

## Scope

### Included

- Production modules under `frontend/src`
- Vue component props, emits, refs, slots, and exposed methods
- Domain stores and cross-store coordinators
- Generated API adapters and handwritten transports
- SSE, WebSocket, and Tauri command/event contracts
- Composables, services, constants, and utilities
- Vite and Vitest TypeScript configuration needed to enforce the migration
- Regression tests required for migrated behavior

### Not required for production-source completion

- Converting every existing Node source-contract test from `.mjs` to TypeScript
- Changing backend behavior solely to make frontend types easier
- Replacing Vue, Pinia, Plotly, CodeMirror, xterm, or TanStack Table
- Rewriting working components while converting them
- Removing runtime validation because a compile-time type exists

Tooling and test files can be converted later where TypeScript provides a clear
maintenance benefit. They do not ship in the application.

## Current Baseline

Measured from `frontend/src` on 2026-07-24:

| Area | Current state |
| --- | ---: |
| JavaScript modules | 56 files, approximately 11,262 lines |
| TypeScript modules | 31 files |
| Vue components | 193 files |
| Vue components with TypeScript scripts | 129 |
| Vue components without TypeScript scripts | 64, approximately 20,151 total SFC lines |
| TypeScript mode | `strict: true`, `allowJs: true`, `checkJs: false` |

The current `vue-tsc` check does not check the remaining JavaScript.

### Largest remaining JavaScript boundaries

| File | Lines | Risk |
| --- | ---: | --- |
| `stores/appCoordinatorStore.js` | 4,298 | Cross-domain state and workflow coupling |
| `services/apiRuntime.js` | 1,318 | HTTP configuration, SSE, caching, and native integration |
| `composables/useLLMConfig.js` | 726 | Provider-specific configuration and credentials metadata |
| `utils/plotlyTheme.js` | 585 | Large third-party object shapes |
| `services/websocketService.js` | 401 | Untyped real-time event boundary |

### Largest Vue components without TypeScript

| File | Lines |
| --- | ---: |
| `WorkspaceTab.vue` | 1,789 |
| `ChatInput.vue` | 1,735 |
| `ChatHistory.vue` | 1,298 |
| `UnifiedSidebar.vue` | 1,081 |
| `App.vue` | 1,044 |
| `TableTab.vue` | 970 |
| `CodeTab.vue` | 939 |
| `DataTable.vue` | 852 |
| `StatusBar.vue` | 851 |
| `CommandPaletteModal.vue` | 771 |

## Principles

1. Do not rename files to `.ts` until the file passes strict checking.
2. Do not hide migration errors with broad `any`, `@ts-ignore`, or
   `@ts-nocheck`.
3. Use `unknown` at external boundaries and narrow it with runtime validation.
4. Prefer generated OpenAPI types for ordinary HTTP requests and responses.
5. Model event streams with discriminated unions.
6. Keep credential values out of persisted state and diagnostic payloads.
7. Split large files by responsibility before converting them.
8. Preserve existing component props and events unless a planned migration
   explicitly changes all consumers together.
9. Do not introduce circular store imports.
10. Add a focused regression test for every behavior moved or restructured.
11. Record bundle measurements for dependency or loading-boundary changes.
12. Any change to this sequence or scope requires approval.

## Type Architecture

### Shared types

Create focused type modules under `src/types`:

```text
src/types/
  identifiers.ts
  workspace.ts
  conversation.ts
  execution.ts
  artifacts.ts
  preferences.ts
  streaming.ts
  realtime.ts
  native.ts
  ui.ts
  errors.ts
```

Do not duplicate generated API interfaces. Shared domain types should be:

- aliases or derived types from generated contracts where possible;
- application view models when the UI shape intentionally differs;
- discriminated unions for events and state machines;
- branded or documented string aliases only where they prevent real mistakes.

### External boundaries

All data entering the frontend is untrusted at runtime:

```text
HTTP response / SSE event / WebSocket message / Tauri payload
                         |
                         v
              typed parser or normalizer
                         |
                         v
               domain store or service
                         |
                         v
                    Vue component
```

Compile-time types do not replace parsing and validation at transport
boundaries.

### Vue conventions

- Use typed `defineProps`, `defineEmits`, `defineModel`, and template refs.
- Use `ComponentPublicInstance` only when a concrete element type is not
  available.
- Type asynchronous component boundaries and exposed methods.
- Avoid casting entire store or API objects.
- Keep template-only presentation types local to the component.
- Move reusable workflow types to the owning domain module.

## Phase 0: Guardrails and Measurement

### Work

- Add a TypeScript migration inventory script that reports:
  - remaining `.js` files under `src`;
  - Vue files without `lang="ts"`;
  - counts and line totals by feature area;
  - newly introduced JavaScript compared with the checked baseline.
- Add a CI check that prevents the JavaScript count from increasing.
- Add `typecheck` to the required CE validation path if it is not already
  called there.
- Add ESLint or an equivalent focused rule set for TypeScript source:
  - no explicit `any` by default;
  - no unused type suppressions;
  - consistent type-only imports;
  - no floating promises in TypeScript workflow code.
- Create `src/types` and define naming/import rules.
- Record the current type, test, build, and bundle baselines.

### Exit criteria

- New production JavaScript cannot be added accidentally.
- Type coverage is measurable and cannot regress.
- The existing application still builds and passes tests.

## Phase 1: Leaf Types, Constants, and Utilities

Start with modules that have few dependencies and strong unit tests.

### Batch 1: identifiers and simple utilities

- `constants/fonts.js`
- `constants/themes.js`
- `utils/pathUtils.js`
- `utils/dateUtils.js`
- `utils/workspaceDisplay.js`
- `utils/modelCapabilities.js`
- `utils/usageFormat.js`
- `utils/apiError.js`
- `utils/keyboardShortcuts.js`

### Batch 2: data and execution view models

- `utils/chatBootstrap.js`
- `utils/datasetCatalogMerge.js`
- `utils/datasetImport.js`
- `utils/executionRouting.js`
- `utils/executionServiceMapper.js`
- `utils/executionViewModel.js`
- `utils/runtimeExecution.js`
- `utils/unifiedResults.js`
- `utils/toolOutputPreview.js`
- `components/analysis/table/tableQuery.js`

### Batch 3: rendering and layout helpers

- `utils/figurePayload.js`
- `utils/plotlyTheme.js`
- `utils/turnTreeGraphLayout.js`
- `utils/sseParser.js`
- `utils/exportFile.js`
- `components/ui/dropdownShared.js`
- `components/ui/modelDropdownUtils.js`

Add a local declaration or narrow adapter for third-party libraries whose
published types do not match the imported distribution. Do not type Plotly
objects as unrestricted `Record<string, any>`.

### Exit criteria

- All constants and standalone utilities are TypeScript.
- Public utility inputs and outputs are explicit.
- Existing unit tests cover normalization and fallback behavior.

## Phase 2: API and Transport Boundaries

Convert transports before their consumers so downstream code receives stable
types.

### Target modules

```text
src/api/
  httpClient.ts
  errors.ts
  cache.ts
  workspaces.ts
  conversations.ts
  execution.ts
  artifacts.ts
  preferences.ts
  streaming.ts
  realtime.ts
  native.ts
```

### Sequence

1. Move Axios configuration, base URL resolution, authentication headers, and
   error normalization from `apiRuntime.js` to `httpClient.ts`.
2. Configure the generated client to use the typed shared HTTP client.
3. Move artifact request caching and cancellation to `cache.ts`.
4. Move SSE parsing, cancellation, and final/error event handling to
   `streaming.ts`.
5. Define a discriminated union for every supported analysis stream event.
6. Convert `websocketService.js` to `realtime.ts` with typed subscription
   payloads and unsubscribe functions.
7. Convert Tauri calls and events:
   - `tauriTerminalService.js`;
   - external links;
   - file selection/export;
   - backend URL and startup events.
8. Move stable domain methods to the relevant API modules.
9. Remove `apiRuntime.js` after its final consumer migrates.

### Required tests

- HTTP error normalization
- API base resolution
- SSE partial buffers and terminal events
- Abort and cancellation behavior
- Artifact cache keys and in-flight deduplication
- WebSocket event narrowing and unsubscribe behavior
- Tauri command payload and response normalization

### Exit criteria

- No component imports Axios or constructs an API URL.
- Streaming, WebSocket, and native boundaries are typed and runtime-validated.
- `apiRuntime.js` is removed.
- Generated-client freshness and `vue-tsc` checks pass.

## Phase 3: Stores and Application Coordination

This phase finishes the state migration described in
`frontend-state-ownership.md`.

### Sequence

1. Convert `authStore.js` to TypeScript.
2. Move workspace-only actions from the coordinator into
   `workspaceStore.ts`.
3. Move conversation messages, stream reducers, turns, usage, and run state
   into `conversationStore.ts`.
4. Move artifact selection, paging, promotion, and removal into
   `artifactStore.ts`.
5. Move runtime, operation, code, and terminal mutations into
   `executionStore.ts`.
6. Move provider/model and appearance normalization into
   `preferencesStore.ts`.
7. Keep pane and dialog mutations in `uiStore.ts`.
8. Extract explicit coordinators:
   - `useAppBootstrap.ts`;
   - `useSessionSnapshot.ts`;
   - `useWorkspaceActivation.ts`;
   - `useConversationActivation.ts`;
   - `useAuthBoundaryReset.ts`.
9. Convert `appCoordinatorStore.js` to a small typed orchestration module.

### Store rules

- Stores own their domain state and mutations.
- Domain stores call typed domain APIs, not the coordinator.
- Coordinators may invoke multiple stores but do not own duplicate state.
- A high-frequency conversation update must not invalidate unrelated stores.
- Persisted snapshots have a typed version and migration function.
- The coordinator should be below approximately 800 lines; a larger result
  requires written justification.

### Required tests

- Snapshot creation, migration, hydration, and user-boundary cleanup
- Workspace activation and stale workspace recovery
- Simultaneous conversation streaming and cancellation
- Turn and branch selection
- Artifact selection and page restoration
- Terminal entry caps and output trimming
- Preference synchronization without credential leakage

### Exit criteria

- `appCoordinatorStore.js` and `authStore.js` are removed.
- All six domain stores are strict TypeScript.
- Cross-store workflows have explicit typed inputs and results.
- There are no circular store imports.

## Phase 4: Services and Composables

Convert consumers after transports and stores expose stable typed contracts.

### Services

- `cacheService.js`
- `commandRegistry.js` and command modules
- `executionService.js`
- `fontService.js`
- `localStateService.js`
- `previewService.js`
- `themeService.js`
- `uiPreferencesService.js`

### Composables

- `useChatAttachments.js`
- `useChatAutocomplete.js`
- `useChatScrollFollow.js`
- `useFloatingDropdown.js`
- `useLLMConfig.js`
- `useSidebarConversations.js`
- `useTableArtifacts.js`
- `useToast.js`
- `useVoiceInput.js`
- `useWorkspaceDatasets.js`

Split `useLLMConfig.js` by provider catalog, credential workflow, and preference
editing before converting it. Keep sensitive credential values out of shared
module state.

### Exit criteria

- All services and composables under `src` are TypeScript.
- Async operations expose typed success, failure, and cancellation states.
- DOM and browser resources have tested cleanup behavior.

## Phase 5: Leaf Vue Components

Convert small components before feature roots.

### Suggested order

1. Shared presentation components:
   - empty states;
   - notices;
   - toolbars;
   - disclosure and segmented controls;
   - toast presentation.
2. Sidebar leaf rows, footer, primary navigation, and action menus.
3. Chat message, attachment, suggestion, tool activity, intervention, and
   terminal-renderer components.
4. Analysis toolbar, empty state, table shell, and run output components.
5. Settings leaf sections and startup failure actions.

For each component:

- type props and emits first;
- type template refs and event handlers;
- replace implicit object shapes with a named domain or local view-model type;
- add or update a runtime component test;
- preserve the public component contract.

### Exit criteria

- Shared and leaf components use `lang="ts"`.
- Parent feature components no longer receive untyped event payloads.

## Phase 6: Feature Roots and Large Components

Do not convert the largest files in place. Split responsibilities first, then
type each extracted boundary.

### Workspace settings

Complete extraction from `WorkspaceTab.vue`:

- workspace selection and general settings;
- dataset operations and status;
- schema/context editing;
- runtime controls;
- AI configuration;
- destructive actions.

Convert the extracted components and composables before the root component.

### Chat

Complete extraction from `ChatInput.vue` and `ChatHistory.vue`:

- submission and command execution;
- stream lifecycle and event reduction;
- concurrent run control;
- Markdown/rendering pipeline;
- reasoning and tool activity;
- intervention handling;
- turn navigation.

The stream event union from Phase 2 is the source of truth.

### Analysis

Convert in this order:

1. `DataTable.vue` and table query/view state
2. `TableTab.vue`
3. `FigureTab.vue`
4. `OutputTab.vue`
5. `CodeTab.vue`
6. `TauriTerminalPane.vue` and `TerminalTab.vue`

Use narrow adapters for CodeMirror, Plotly, TanStack Table, and xterm rather
than spreading third-party types through domain code.

### Shell

Extract and convert:

- global shortcuts;
- desktop startup;
- native file drop;
- realtime settings;
- blocking operation presentation;
- sidebar orchestration;
- status aggregation;
- resizer behavior.

Convert `UnifiedSidebar.vue`, `StatusBar.vue`, `RightPanel.vue`, and `App.vue`
last.

### Exit criteria

- All Vue component scripts use `lang="ts"`.
- Root components primarily compose typed components and composables.
- Concurrent chat, artifacts, terminal, and startup workflows pass runtime
  tests.

## Phase 7: Enforcement and Cleanup

### Work

- Rename `main.js` to `main.ts`.
- Remove the last production `.js` file.
- Set `allowJs: false` in `tsconfig.json`.
- Remove `checkJs` and the temporary JavaScript inventory allowlist.
- Fail CI when:
  - a `.js` file is added under `frontend/src`;
  - a Vue component lacks a TypeScript script;
  - `vue-tsc --noEmit` fails;
  - an unused TypeScript suppression is introduced.
- Remove obsolete declarations, casts, compatibility types, and migration-only
  tests.
- Re-run bundle measurements and document any material change.

### Exit criteria

- Strict TypeScript covers all production frontend source.
- No migration suppression remains without a narrow written justification.
- Required validation and bundle budgets pass.

## Delivery Sequence

Use small, reviewable pull requests. A recommended sequence is:

| PR | Scope |
| ---: | --- |
| 1 | Inventory, CI non-regression guard, and shared type conventions |
| 2 | Constants, identifiers, date/path/model utilities |
| 3 | Dataset, execution, artifact, and result utilities |
| 4 | Plotly, SSE, dropdown, and graph helper types |
| 5 | Typed HTTP client and generated-client integration |
| 6 | Streaming and artifact cache transports |
| 7 | WebSocket and Tauri transports |
| 8 | Auth and preferences store actions |
| 9 | Artifact and execution store actions |
| 10 | Workspace store actions and activation coordinator |
| 11 | Conversation store reducers and activation coordinator |
| 12 | Snapshot/bootstrap coordinators and removal of the JS coordinator |
| 13 | Services and small composables |
| 14 | LLM, chat, table, and workspace composables |
| 15 | Shared, sidebar, and settings leaf components |
| 16 | Analysis feature components |
| 17 | Chat feature components |
| 18 | Workspace settings components |
| 19 | Shell components and `App.vue` |
| 20 | `main.ts`, strict enforcement, cleanup, and final audit |

PRs may be smaller, but combining dependent steps out of order requires
approval.

## Validation

### Every migration PR

```bash
npm run typecheck
npm run test:source
npm run test:runtime
npm run build
```

Also run focused tests for the migrated module or interaction.

### Transport, store, and feature-boundary PRs

```bash
npm run bundle:check
npm run e2e:list
```

Run the affected Playwright specification when the environment supports it.

### Final migration PR

```bash
npm test
npm run typecheck
npm run bundle:check
npm run e2e:list
make -C .. test-rust
make -C .. build
```

The final packaged application must be built and its platform bundle verified.

## Risk Controls

| Risk | Control |
| --- | --- |
| Broad `any` hides real gaps | Lint rule, review requirement, use `unknown` and narrowing |
| File renames break lazy imports | Build and lazy-boundary source tests in every affected PR |
| Generated types are duplicated | Derive domain types from generated contracts |
| SSE/WebSocket variants are missed | Discriminated unions with exhaustive `never` checks |
| Store conversion creates cycles | Coordinators own cross-domain workflows |
| Vue template inference changes behavior | Runtime component tests for props, emits, focus, and keyboard behavior |
| Third-party types infect domain models | Narrow typed adapters around Plotly, CodeMirror, xterm, and TanStack |
| Bundle size grows | Existing bundle budgets and feature-boundary report |
| Credential data leaks into types/logs | Typed persisted snapshots and explicit redaction tests |

## Definition of Done

The migration is complete when all of the following are true:

- `find frontend/src -name '*.js'` returns no files.
- Every Vue component script uses TypeScript.
- `tsconfig.json` has `strict: true` and `allowJs: false`.
- There are no broad `@ts-ignore`, `@ts-nocheck`, or unjustified explicit
  `any` uses.
- API response types come from the generated OpenAPI client.
- SSE, WebSocket, Tauri, and persisted snapshot payloads are explicitly typed
  and validated.
- The six domain stores own their state and mutations.
- The coordinator contains only typed cross-domain workflows.
- Type checking, source tests, runtime tests, production build, bundle budgets,
  and E2E discovery pass.
- A packaged desktop application builds successfully.
